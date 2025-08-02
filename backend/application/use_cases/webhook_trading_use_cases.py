import json
from typing import Dict, Any
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from domain.models import User, WebhookConfig
from domain.schemas import GenericWebhookPayload
from infrastructure.security import decrypt_data
from application.services.quantity_calculator import extract_asset_from_symbol, calculate_quantity_multiplier
from application.services.trade_analyzer import analyze_trade_intent
from application.services.webhook_logger import create_webhook_log
from infrastructure.external.hyperliquid_client import HyperliquidClient

def process_generic_webhook(payload: GenericWebhookPayload, request: Request, db: Session) -> Dict[str, Any]:
    """Processa webhook genérico que recebe todos os ativos numa única URL"""
    
    # Serializar o payload para logs
    request_body = payload.model_dump_json()
    
    # Extrair asset name do symbol (ex: BTCUSDT -> BTC)
    trading_view_symbol = extract_asset_from_symbol(payload.symbol)
    
    # Encontrar usuário
    user = db.query(User).filter(User.uuid == payload.user_uuid).first()
    if not user:
        error_msg = "UUID de usuário inválido"
        raise HTTPException(status_code=404, detail=error_msg)

    # Validação do segredo
    if payload.secret != user.webhook_secret:
        error_msg = "Segredo de webhook inválido"
        raise HTTPException(status_code=403, detail=error_msg)

    # Encontrar configuração do webhook para este ativo
    config = _find_webhook_config(db, user.id, trading_view_symbol)
    
    if not config or not user.wallet:
        error_msg = f"Configuração de webhook não encontrada para o ativo '{trading_view_symbol}' (extraído de '{payload.symbol}'). Configure este ativo na interface primeiro."
        raise HTTPException(status_code=404, detail=error_msg)

    print(f"🔥 WEBHOOK GENÉRICO: Usuário {user.id}, Symbol {payload.symbol} → Ativo {trading_view_symbol}")
    print(f"Payload completo: {payload.model_dump()}")
    print(f"Config encontrada: ID={config.id}, Leverage={config.leverage}, Max=${config.max_usd_value}, Live={config.is_live_trading}")
    
    try:
        # Descriptografar chave privada
        secret_key = decrypt_data(user.wallet.encrypted_secret_key)
        if not secret_key:
            error_msg = "Chave privada não configurada"
            create_webhook_log(db, config, request, request_body, 500, "", False, error_msg)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        client = HyperliquidClient()
        
        # Extrair dados do payload TradingView
        action = payload.data.action
        contracts = payload.data.contracts
        symbol = payload.symbol
        price_data = payload.price
        user_info = payload.user_info
        position_size = payload.data.position_size
        
        # Determinar ativo da Hyperliquid e se é personalizado
        hyperliquid_asset, is_custom_asset = _determine_hyperliquid_asset(client, config, trading_view_symbol)
        
        # Ajustar quantidade para ativos personalizados
        quantity_multiplier, adjusted_contracts, adjusted_position_size = _adjust_quantities(
            client, trading_view_symbol, hyperliquid_asset, is_custom_asset, contracts, position_size
        )
        
        # Análise inteligente da intenção de trading
        trade_type, adjusted_size, trade_details = _analyze_trading_intent(
            client, user.wallet.public_address, hyperliquid_asset, action, adjusted_position_size, adjusted_contracts, db
        )
        
        # Determinar tamanho final da ordem
        order_size = _determine_order_size(client, hyperliquid_asset, adjusted_size, config)
        
        # Validar e ajustar o tamanho da ordem
        order_size = client.validate_and_fix_order_size(hyperliquid_asset, order_size)
        print(f"✅ TAMANHO FINAL DA ORDEM (validado): {order_size}")
        
        is_buy = action.lower() in ['buy', 'long']
        
        # Determinar preço limite com validação
        limit_price = _determine_limit_price(price_data, client, hyperliquid_asset)
        
        # Usar leverage configurado
        leverage_to_use = getattr(config, 'leverage', 1)
        print(f"Usando leverage configurado: {leverage_to_use}x")
        print(f"Modo: {'🚀 REAL' if bool(config.is_live_trading) else '🔄 SIMULAÇÃO'}")
        
        # Executar ordem na Hyperliquid
        result = client.place_order(
            secret_key=secret_key,
            asset_name=hyperliquid_asset,
            is_buy=is_buy,
            size=order_size,
            limit_price=limit_price,
            stop_loss=None,
            take_profit=None,
            comment=f"{user_info} | {trade_type}: {trade_details['description']}",
            is_live_trading=bool(config.is_live_trading),
            leverage=leverage_to_use
        )
        
        print(f"Resultado da Hyperliquid: {result}")
        
        # Preparar resposta
        response_data = {
            "status": "sucesso", 
            "details": result,
            "processed_data": {
                "action": action,
                "size": order_size,
                "price": limit_price,
                "leverage": leverage_to_use,
                "asset": trading_view_symbol,
                "hyperliquid_asset": hyperliquid_asset,
                "symbol": symbol,
                "user_info": user_info,
                "is_live_trading": bool(config.is_live_trading)
            },
            "quantity_adjustment": {
                "multiplier": quantity_multiplier,
                "original_contracts": contracts,
                "adjusted_contracts": adjusted_contracts,
                "original_position_size": position_size,
                "adjusted_position_size": adjusted_position_size
            },
            "trade_analysis": {
                "type": trade_type,
                "description": trade_details["description"],
                "original_contracts": contracts,
                "adjusted_size": order_size,
                "details": trade_details
            }
        }
        
        # Registrar trade no sistema de PNL
        _record_pnl_trade(db, config, user.id, trading_view_symbol, trade_type, is_buy, order_size, limit_price, leverage_to_use, result)
        
        # Log de sucesso
        create_webhook_log(db, config, request, request_body, 200, json.dumps(response_data), True)
        
        return response_data
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Falha ao executar ordem: {str(e) if str(e) else 'Erro desconhecido'}"
        print(f"ERRO AO PROCESSAR ORDEM: {e}")
        print(f"TRACEBACK COMPLETO: {error_details}")
        
        # Log de erro
        create_webhook_log(db, config, request, request_body, 500, "", False, error_msg)
        
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

def _find_webhook_config(db: Session, user_id: int, trading_view_symbol: str) -> WebhookConfig:
    """Encontra configuração do webhook para o ativo"""
    # Primeiro tenta buscar pelo trading_view_symbol
    config = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == user_id,
        WebhookConfig.trading_view_symbol == trading_view_symbol
    ).first()
    
    # Se não encontrou, tenta buscar pelo hyperliquid_symbol (símbolo do TradingView)
    if not config:
        config = db.query(WebhookConfig).filter(
            WebhookConfig.user_id == user_id, 
            WebhookConfig.hyperliquid_symbol == trading_view_symbol
        ).first()
    
    return config

def _determine_hyperliquid_asset(client: HyperliquidClient, config: WebhookConfig, trading_view_symbol: str) -> tuple[str, bool]:
    """Determina o ativo da Hyperliquid e se é personalizado"""
    # Verificar se há configuração manual
    if config.hyperliquid_symbol and config.hyperliquid_symbol != trading_view_symbol:
        hyperliquid_asset = config.hyperliquid_symbol
        is_custom_asset = True
        print(f"🔄 ATIVO PERSONALIZADO (manual): {trading_view_symbol} → {hyperliquid_asset}")
    else:
        # Verificar se o ativo existe na Hyperliquid diretamente
        try:
            client.get_asset_info(trading_view_symbol)
            hyperliquid_asset = trading_view_symbol
            is_custom_asset = False
            print(f"🔄 ATIVO ORIGINAL: {trading_view_symbol} (existe na Hyperliquid)")
        except:
            # Tentar com prefixo 'k' minúsculo
            try:
                k_asset = f"k{trading_view_symbol}"
                client.get_asset_info(k_asset)
                hyperliquid_asset = k_asset
                is_custom_asset = True
                print(f"🔄 ATIVO PERSONALIZADO (auto-detectado): {trading_view_symbol} → {hyperliquid_asset}")
            except:
                hyperliquid_asset = trading_view_symbol
        is_custom_asset = False
        print(f"⚠️ ATIVO NÃO ENCONTRADO: usando {trading_view_symbol} (pode falhar)")
    
    return hyperliquid_asset, is_custom_asset

def _adjust_quantities(client: HyperliquidClient, trading_view_symbol: str, hyperliquid_asset: str, 
                      is_custom_asset: bool, contracts: str, position_size: str) -> tuple[float, str, str]:
    """Ajusta quantidades para ativos personalizados"""
    if is_custom_asset:
        quantity_multiplier = calculate_quantity_multiplier(trading_view_symbol, hyperliquid_asset, client)
        print(f"📊 MULTIPLICADOR DE QUANTIDADE (personalizado): {quantity_multiplier}x")
    else:
        quantity_multiplier = 1.0
        print(f"📊 MULTIPLICADOR DE QUANTIDADE (original): {quantity_multiplier}x")
    
    original_contracts = contracts
    original_position_size = position_size
    
    if is_custom_asset and quantity_multiplier != 1.0:
        try:
            adjusted_contracts = float(contracts) * quantity_multiplier if contracts else 0
            adjusted_position_size = float(position_size) * quantity_multiplier if position_size else 0
            contracts = str(adjusted_contracts)
            position_size = str(adjusted_position_size)
            print(f"🔄 AJUSTE DE QUANTIDADE (ativo personalizado):")
            print(f"  Contracts: {original_contracts} → {contracts}")
            print(f"  Position Size: {original_position_size} → {position_size}")
        except (ValueError, TypeError) as e:
            print(f"⚠️ Erro ao aplicar multiplicador: {e}")
    else:
        print(f"📋 USANDO DADOS ORIGINAIS (ativo original): Contracts={contracts}, Position Size={position_size}")
    
    return quantity_multiplier, contracts, position_size

def _analyze_trading_intent(client: HyperliquidClient, user_address: str, hyperliquid_asset: str, 
                           action: str, position_size: str, contracts: str, db: Session) -> tuple[str, float, dict]:
    """Analisa a intenção de trading"""
    print(f"\n🧠 ANALISANDO INTENÇÃO DE TRADING...")
    print(f"Action: {action}, Contracts: {contracts}, Position Size: {position_size}")
    
    try:
        trade_type, adjusted_size, trade_details = analyze_trade_intent(
            client=client,
            user_address=user_address,
            hyperliquid_asset=hyperliquid_asset,
            action=action,
            position_size_str=position_size,
            contracts_str=contracts,
            db_session=db
        )
        
        print(f"🎯 RESULTADO DA ANÁLISE:")
        print(f"  Tipo: {trade_type}")
        print(f"  Descrição: {trade_details['description']}")
        print(f"  Quantidade original: {contracts}")
        print(f"  Quantidade ajustada pela análise: {adjusted_size}")
        
        # Forçar casas decimais corretas
        if adjusted_size > 0:
            forced_adjusted_size = client.force_valid_order_size(hyperliquid_asset, adjusted_size)
            print(f"🔧 Quantidade final forçada: {adjusted_size} → {forced_adjusted_size}")
            adjusted_size = forced_adjusted_size
        
        return trade_type, adjusted_size, trade_details
        
    except Exception as analysis_error:
        print(f"⚠️ Erro na análise de trading: {analysis_error}")
        # Fallback para comportamento original
        trade_type = "ERRO"
        fallback_size = float(contracts) if contracts else 0
        adjusted_size = client.force_valid_order_size(hyperliquid_asset, fallback_size) if fallback_size > 0 else 0
        trade_details = {
            "description": f"Erro na análise - usando quantidade original: {str(analysis_error)}",
            "action_type": "ERROR"
        }
        return trade_type, adjusted_size, trade_details

def _determine_order_size(client: HyperliquidClient, hyperliquid_asset: str, adjusted_size: float, config: WebhookConfig) -> float:
    """Determina o tamanho final da ordem"""
    order_size = adjusted_size
    
    # Se a análise resultou em tamanho 0, usar fallback
    if order_size == 0:
        max_usd_value = getattr(config, 'max_usd_value', 0)
        if max_usd_value and max_usd_value > 0:
            order_size = client.calculate_order_size(hyperliquid_asset, max_usd_value)
            print(f"⚠️ Quantidade zero detectada - usando valor máximo configurado: {order_size} (baseado em ${max_usd_value})")
        else:
            raise ValueError("Quantidade da ordem é zero e não há valor máximo configurado")
    
    return order_size

def _determine_limit_price(price_data, client: HyperliquidClient = None, trading_view_symbol: str = None) -> float:
    """Determina o preço limite da ordem com validação"""
    limit_price = None
    if price_data and str(price_data).strip():
        try:
            raw_price = float(price_data)
            print(f"Preço bruto do TradingView: {raw_price}")
            
            # Se temos cliente e nome do ativo, validar o preço
            if client and trading_view_symbol:
                try:
                    limit_price = client.validate_and_fix_price(trading_view_symbol, raw_price)
                    print(f"Preço validado: {raw_price} → {limit_price}")
                except Exception as e:
                    print(f"⚠️ Erro na validação de preço: {e}")
                    limit_price = raw_price
            else:
                limit_price = raw_price
                
        except (ValueError, TypeError):
            print(f"Erro ao converter price '{price_data}' para float")
    return limit_price

def _record_pnl_trade(db: Session, config: WebhookConfig, user_id: int, trading_view_symbol: str, 
                     trade_type: str, is_buy: bool, order_size: float, limit_price: float, 
                     leverage: int, result: dict):
    """Registra trade no sistema de PNL"""
    try:
        from infrastructure.services.pnl_calculator import PnlCalculator
        pnl_calculator = PnlCalculator(db)
        
        side = "LONG" if is_buy else "SHORT"
        usd_value = order_size * (limit_price if limit_price else 0)
        
        # Mapear tipos de trade do analyzer para tipos do PnlCalculator
        if trade_type in ["BUY", "SELL"]:
            pnl_trade_type = trade_type
        elif trade_type == "CLOSE":
            pnl_trade_type = "CLOSE"
        elif trade_type == "REDUCE":
            pnl_trade_type = "REDUCE"
        elif trade_type == "DCA":
            pnl_trade_type = "DCA"
        else:
            pnl_trade_type = trade_type
        
        pnl_calculator.record_trade(
            webhook_config_id=config.id,
            user_id=user_id,
            asset_name=trading_view_symbol,
            trade_type=pnl_trade_type,
            side=side,
            quantity=order_size,
            price=limit_price if limit_price else 0,
            usd_value=usd_value,
            leverage=leverage,
            order_id=result.get('order_id') if isinstance(result, dict) else None,
            fees=0.0
        )
        
        print(f"✅ Trade registrado no sistema de PNL (tipo: {trade_type} -> {pnl_trade_type})")
        
    except Exception as pnl_error:
        print(f"⚠️ Erro ao registrar trade no PNL: {pnl_error}")
        # Não falhar o webhook por erro no PNL