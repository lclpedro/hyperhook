import time
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from eth_account import Account

class HyperliquidClient:
    def __init__(self):
        # O cliente Info não precisa de chaves e pode ser instanciado uma vez
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

    def get_all_mids(self):
        """Busca o preço médio (mid-price) para todos os ativos."""
        return self.info.all_mids()

    def get_asset_price(self, asset_name):
        """Busca o preço de um ativo específico."""
        mids = self.get_all_mids()
        return float(mids.get(asset_name, 0.0))

    def get_user_state(self, user_address):
        """Busca o estado da conta de um usuário, incluindo posições."""
        try:
            return self.info.user_state(user_address)
        except Exception as e:
            print(f"Erro ao buscar o estado do usuário: {e}")
            return None
            
    def get_asset_info(self, asset_name):
        """Busca informações detalhadas do ativo."""
        meta = self.info.meta()
        universe = meta["universe"]
        asset_info = next((item for item in universe if item["name"] == asset_name), None)
        
        if not asset_info:
            raise ValueError(f"Não foi possível encontrar metadados para o ativo {asset_name}")
        
        return asset_info
    
    def debug_asset_rules(self, asset_name):
        """Debug: mostra as regras específicas do ativo."""
        try:
            asset_info = self.get_asset_info(asset_name)
            print(f"📊 REGRAS DO ATIVO {asset_name}:")
            print(f"  szDecimals: {asset_info['szDecimals']} (casas decimais permitidas)")
            print(f"  Menor incremento: {10 ** (-asset_info['szDecimals'])}")
            print(f"  Index: {asset_info.get('index', 'N/A')}")
            return asset_info
        except Exception as e:
            print(f"❌ Erro ao buscar regras do ativo {asset_name}: {e}")
            return None

    def force_valid_order_size(self, asset_name, size):
        """
        FORÇA o tamanho da ordem para estar em conformidade com as regras da Hyperliquid.
        Sempre aplica as regras corretas, independente da fonte dos dados (TradingView, etc.)
        """
        try:
            asset_info = self.get_asset_info(asset_name)
            sz_decimals = asset_info["szDecimals"]
            
            # Converter para float
            original_size = float(size)
            
            # FORÇAR o número correto de casas decimais
            forced_size = round(original_size, sz_decimals)
            
            # Verificar tamanho mínimo
            min_size = 10 ** (-sz_decimals)
            if forced_size < min_size:
                forced_size = min_size
                print(f"🔧 FORÇA: {asset_name} tamanho {original_size} → {forced_size} (mínimo)")
            elif forced_size != original_size:
                print(f"🔧 FORÇA: {asset_name} tamanho {original_size} → {forced_size} ({sz_decimals} decimais)")
            else:
                print(f"✅ FORÇA: {asset_name} tamanho {forced_size} já válido ({sz_decimals} decimais)")
            
            return forced_size
            
        except Exception as e:
            print(f"❌ Erro ao forçar tamanho válido para {asset_name}: {e}")
            # Fallback: retornar com 2 casas decimais como padrão
            fallback_size = round(float(size), 2)
            print(f"🔄 Usando fallback: {size} → {fallback_size} (2 decimais)")
            return fallback_size

    def validate_and_fix_order_size(self, asset_name, size):
        """Alias para manter compatibilidade - usa force_valid_order_size"""
        return self.force_valid_order_size(asset_name, size)

    def calculate_order_size(self, asset_name, max_usd_value):
        """Calcula o tamanho da ordem na moeda do ativo, com base no valor em USD."""
        price = self.get_asset_price(asset_name)
        if price == 0:
            raise ValueError(f"Não foi possível obter o preço para o ativo {asset_name}")
        
        asset_info = self.get_asset_info(asset_name)
        sz_decimals = asset_info["szDecimals"]
        
        size = max_usd_value / price
        validated_size = self.validate_and_fix_order_size(asset_name, size)
        return validated_size
    
    def validate_and_fix_price(self, asset_name, price, is_spot=False):
        """
        Valida e corrige o preço seguindo as regras da Hyperliquid:
        - 5 dígitos significativos
        - 6 decimais para perpetuais, 8 decimais para spot
        - Ajustado pelo szDecimals do ativo
        """
        try:
            if price is None or price <= 0:
                raise ValueError(f"Preço inválido: {price}")
            
            # Converter para float se necessário
            px = float(price)
            
            # Obter informações do ativo
            asset_info = self.get_asset_info(asset_name)
            sz_decimals = asset_info["szDecimals"]
            
            # Aplicar regra da Hyperliquid: 5 dígitos significativos
            # e 6 decimais para perps, 8 para spot, ajustado pelo szDecimals
            max_decimals = (8 if is_spot else 6) - sz_decimals
            
            # Arredondar para 5 dígitos significativos primeiro
            rounded_px = round(float(f"{px:.5g}"), max_decimals)
            
            print(f"💰 Preço validado: {price} → {rounded_px} (max_decimals: {max_decimals}, szDecimals: {sz_decimals})")
            
            return rounded_px
            
        except Exception as e:
            print(f"❌ Erro ao validar preço {price} para {asset_name}: {e}")
            # Em caso de erro, retornar o preço original arredondado para 5 decimais
            return round(float(price), 5)

    def place_order(self, secret_key, asset_name, is_buy, size, limit_price=None, slippage=0.005, stop_loss=None, take_profit=None, comment=None, is_live_trading=False, leverage=1, retry_count=0):
        """
        Coloca uma ordem na Hyperliquid.
        Se is_live_trading=True, executa ordem real. Se False, simula.
        """
        # 1. Criar uma conta a partir da chave privada para assinar a transação
        if secret_key.startswith('0x'):
            secret_key = secret_key[2:]
        
        account = Account.from_key(secret_key)
        
        # 2. Inicializar a classe Exchange com a conta do usuário para esta transação específica
        exchange = Exchange(account, constants.MAINNET_API_URL)
        
        # 3. Configurar leverage para o ativo antes de fazer a ordem
        if is_live_trading:
            try:
                # Buscar informações do ativo para obter o índice
                asset_info = self.get_asset_info(asset_name)
                asset_index = asset_info.get("index", 0)
                
                print(f"⚙️ Configurando leverage {leverage}x para {asset_name}")
                leverage_result = exchange.update_leverage(leverage, asset_name, is_cross=True)
                print(f"✅ Leverage configurado: {leverage_result}")
            except Exception as e:
                print(f"⚠️ Erro ao configurar leverage: {e}")
                # Continuar mesmo se falhar para não bloquear a ordem

        # 3. Calcular o preço limite com base no slippage para simular uma ordem a mercado
        price = self.get_asset_price(asset_name)
        if price == 0:
            raise ValueError(f"Preço para {asset_name} é zero, não é possível colocar a ordem.")
        
        # Determinar se usar preço personalizado ou preço de mercado
        use_custom_price = False
        final_price = None
        
        # NOVA LÓGICA: Para fechamentos de posição, sempre usar ordem de mercado
        is_closing_position = comment and "CLOSE" in comment.upper()
        is_reducing_position = comment and "REDUCE" in comment.upper()
        
        if is_closing_position or is_reducing_position:
            print(f"🔄 Operação de {'close' if is_closing_position else 'reduce'} detectada - forçando MARKET ORDER")
            use_custom_price = False
            limit_price = None  # Garantir que seja market order
        elif limit_price is not None:
            # Validar e corrigir o preço seguindo as regras da Hyperliquid
            validated_price = self.validate_and_fix_price(asset_name, limit_price)
            
            price_diff_percent = abs(validated_price - price) / price
            if price_diff_percent > 0.05:  # Máximo 5% de diferença
                print(f"⚠️ Preço validado ({validated_price}) está {price_diff_percent:.1%} longe do preço de mercado ({price})")
                print(f"Usando ordem de mercado em vez do preço fornecido")
                use_custom_price = False
            else:
                use_custom_price = True
                final_price = validated_price
                print(f"Usando preço validado: {limit_price} → {final_price}")
        
        operation_mode = "Close/Reduce" if (is_closing_position or is_reducing_position) else ("Preço Específico" if use_custom_price else "Mercado")
        print(f"💰 Preço de mercado: {price}, Modo: {operation_mode}, Slippage: {slippage:.1%}")

        if is_live_trading:
            print(f"🚀 EXECUTANDO ORDEM REAL: Ativo {asset_name}, Compra: {is_buy}, Tamanho: {size}")
            
            try:
                if use_custom_price and final_price is not None:
                    # Usar order() diretamente para preços específicos com IoC
                    print(f"📍 Usando preço específico: {final_price}")
                    order_result = exchange.order(
                        name=asset_name,
                        is_buy=is_buy,
                        sz=size,
                        limit_px=final_price,
                        order_type={"limit": {"tif": "Ioc"}},  # Immediate or Cancel
                        reduce_only=False
                    )
                else:
                    # Usar market_open() para ordens de mercado (fechamentos, reduções, etc.)
                    operation_type = "close/reduce" if (is_closing_position or is_reducing_position) else "mercado"
                    print(f"📈 Usando ordem de mercado para {operation_type} com slippage: {slippage:.1%}")
                    order_result = exchange.market_open(
                        name=asset_name,
                        is_buy=is_buy,
                        sz=size,
                        slippage=slippage
                    )
                
                status = {
                    "status": "ok",
                    "response": order_result,
                    "real_order": True
                }
                print(f"✅ Ordem real executada: {status}")
                
            except Exception as e:
                print(f"❌ Erro ao executar ordem real: {e}")
                import traceback
                print(f"Traceback completo: {traceback.format_exc()}")
                # Em caso de erro, retornar formato de erro
                status = {
                    "status": "error",
                    "error": str(e),
                    "real_order": True
                }
        else:
            # Simular com o preço calculado
            if use_custom_price:
                limit_px = final_price
            else:
                limit_px = price * (1 + slippage) if is_buy else price * (1 - slippage)
                
            print(f"🔄 SIMULANDO ORDEM: Ativo {asset_name}, Compra: {is_buy}, Tamanho: {size}, Preço Limite: {limit_px}")
            
            # Simular resposta de sucesso para desenvolvimento/teste
            status = {
                "status": "ok",
                "response": {
                    "type": "order",
                    "data": {
                        "statuses": [{
                            "filled": {
                                "totalSz": str(size),
                                "avgPx": str(limit_px),
                                "oid": int(time.time())
                            }
                        }]
                    }
                },
                "simulation": True  # Flag indicando que é simulação
            }
        
        print(f"Resposta da API Hyperliquid: {status}")

        if status["status"] == "ok":
            # Verificar se é uma resposta real ou simulada e acessar a estrutura correta
            if status.get("real_order", False):
                # Para ordens reais, a estrutura pode ser mais simples
                response_data = status["response"]
                
                # Verificar se é um erro direto na resposta
                if isinstance(response_data, dict) and "status" in response_data:
                    if response_data.get("status") == "err":
                        error_msg = response_data.get("response", str(response_data))
                        print(f"❌ Erro da API: {error_msg}")
                        raise Exception(f"Falha ao colocar a ordem: {error_msg}")
                    
                    # Navegar pela estrutura de resposta da API real
                    if "response" in response_data:
                        inner_response = response_data["response"]
                        if isinstance(inner_response, dict) and "data" in inner_response and "statuses" in inner_response["data"]:
                            order_status = inner_response["data"]["statuses"][0]
                        else:
                            # Se não tem a estrutura esperada, considerar como sucesso
                            print(f"Ordem real executada - estrutura não padrão: {response_data}")
                            return status
                    else:
                        # Resposta direta - assumir sucesso se não há estrutura de erro
                        print(f"Ordem real executada - resposta direta: {response_data}")
                        return status
                else:
                    # Resposta direta sem estrutura de status
                    print(f"Ordem real executada - formato direto: {response_data}")
                    return status
            else:
                # Para ordens simuladas, usar a estrutura conhecida
                order_status = status["response"]["data"]["statuses"][0]
            
            # Processar o status da ordem apenas se chegamos até aqui
            if "filled" in order_status:
                print(f"✅ Ordem para {asset_name} preenchida com sucesso. OID: {order_status['filled']['oid']}")
            elif "resting" in order_status:
                print(f"📋 Ordem para {asset_name} colocada no livro. OID: {order_status['resting']['oid']}")
            elif "error" in order_status:
                error_msg = order_status["error"]
                print(f"❌ Erro na ordem: {error_msg}")
                
                # Se erro é de matching e ainda não tentamos market order, tentar novamente
                if ("could not immediately match" in error_msg.lower() and 
                    limit_price is not None and 
                    retry_count == 0):
                    print(f"🔄 Tentando novamente com MARKET ORDER...")
                    return self.place_order(
                        secret_key=secret_key,
                        asset_name=asset_name,
                        is_buy=is_buy,
                        size=size,
                        limit_price=None,  # Forçar market order
                        slippage=slippage,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        comment=f"{comment} [MARKET-RETRY]" if comment else "[MARKET-RETRY]",
                        is_live_trading=is_live_trading,
                        leverage=leverage,
                        retry_count=1  # Evitar loop infinito
                    )
                
                raise Exception(f"Falha ao colocar a ordem: {error_msg}")
            else:
                print(f"❓ Status da ordem desconhecido: {order_status}")
        else:
            raise Exception(f"Falha ao colocar a ordem: {status}")

        return status