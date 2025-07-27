def analyze_trade_intent(client, user_address, hyperliquid_asset, action, position_size_str, contracts_str):
    """
    Analisa a intenção de trading para determinar se é:
    - Fechamento de posição (position_size = 0)
    - DCA (Dollar Cost Average) - aumentar posição existente
    - Nova posição
    
    Retorna: (tipo_operacao, quantidade_ajustada, detalhes)
    """
    try:
        # Obter posições atuais do usuário
        user_state = client.get_user_state(user_address)
        current_positions = {}
        
        if user_state and "assetPositions" in user_state:
            for pos in user_state["assetPositions"]:
                if "position" in pos:
                    position_data = pos["position"]
                    coin = position_data.get("coin", "")
                    size = float(position_data.get("szi", "0"))
                    if size != 0:  # Apenas posições abertas
                        current_positions[coin] = {
                            "size": size,
                            "side": "LONG" if size > 0 else "SHORT",
                            "abs_size": abs(size),
                            "unrealized_pnl": float(position_data.get("unrealizedPnl", "0"))
                        }
        
        print(f"🔍 Posições atuais: {current_positions}")
        
        # Verificar se já tem posição no ativo
        current_position = current_positions.get(hyperliquid_asset)
        is_buy = action.lower() in ['buy', 'long']
        position_size = float(position_size_str) if position_size_str and position_size_str.strip() else 0
        contracts = float(contracts_str) if contracts_str and contracts_str.strip() else 0
        
        # Cenário 1: SEM POSIÇÃO ATUAL - Nova posição
        if not current_position:
            print("📈 NOVA POSIÇÃO: Nenhuma posição existente encontrada")
            return "NOVA_POSICAO", contracts, {
                "description": "Abrindo nova posição",
                "current_position": None,
                "action_type": "NEW_POSITION"
            }
        
        # Cenário 2: FECHAMENTO DE POSIÇÃO - position_size = 0 e direção oposta
        if position_size == 0:
            current_side = current_position["side"]
            is_opposite_direction = (current_side == "LONG" and not is_buy) or (current_side == "SHORT" and is_buy)
            
            if is_opposite_direction:
                # Fechar a posição inteira
                close_size = current_position["abs_size"]
                # FORÇAR casas decimais corretas para fechamento
                forced_close_size = client.force_valid_order_size(hyperliquid_asset, close_size)
                print(f"🔄 FECHAMENTO: Fechando posição {current_side} de {close_size} → {forced_close_size} {hyperliquid_asset}")
                return "FECHAMENTO", forced_close_size, {
                    "description": f"Fechando posição {current_side} de {close_size}",
                    "current_position": current_position,
                    "action_type": "CLOSE_POSITION",
                    "original_size": current_position["abs_size"]
                }
        
        # Cenário 3: DCA - Mesma direção da posição existente
        current_side = current_position["side"]
        is_same_direction = (current_side == "LONG" and is_buy) or (current_side == "SHORT" and not is_buy)
        
        if is_same_direction:
            # FORÇAR casas decimais corretas para DCA
            forced_contracts = client.force_valid_order_size(hyperliquid_asset, contracts)
            print(f"📊 DCA: Aumentando posição {current_side} existente de {current_position['abs_size']} com +{contracts} → +{forced_contracts}")
            return "DCA", forced_contracts, {
                "description": f"DCA - Aumentando posição {current_side} de {current_position['abs_size']} para {current_position['abs_size'] + contracts}",
                "current_position": current_position,
                "action_type": "DCA",
                "original_size": current_position["abs_size"],
                "new_total_size": current_position["abs_size"] + contracts
            }
        
        # Cenário 4: REDUÇÃO DE POSIÇÃO - Direção oposta mas não position_size = 0
        if not is_same_direction:
            reduction_size = min(contracts, current_position["abs_size"])
            # FORÇAR casas decimais corretas para redução
            forced_reduction_size = client.force_valid_order_size(hyperliquid_asset, reduction_size)
            print(f"📉 REDUÇÃO: Reduzindo posição {current_side} de {current_position['abs_size']} em {reduction_size} → {forced_reduction_size}")
            return "REDUCAO", forced_reduction_size, {
                "description": f"Reduzindo posição {current_side} de {current_position['abs_size']} em {reduction_size}",
                "current_position": current_position,
                "action_type": "REDUCE_POSITION",
                "original_size": current_position["abs_size"],
                "reduction_amount": reduction_size,
                "remaining_size": current_position["abs_size"] - reduction_size
            }
        
        # Fallback - usar quantidade original
        return "PADRAO", contracts, {
            "description": "Usando quantidade padrão do payload",
            "current_position": current_position,
            "action_type": "DEFAULT"
        }
        
    except Exception as e:
        print(f"⚠️ Erro ao analisar intenção de trading: {e}")
        # Em caso de erro, usar quantidade original
        contracts = float(contracts_str) if contracts_str and contracts_str.strip() else 0
        return "ERRO", contracts, {
            "description": f"Erro na análise - usando quantidade original: {str(e)}",
            "current_position": None,
            "action_type": "ERROR"
        }