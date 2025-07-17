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
            
    def calculate_order_size(self, asset_name, max_usd_value):
        """Calcula o tamanho da ordem na moeda do ativo, com base no valor em USD."""
        price = self.get_asset_price(asset_name)
        if price == 0:
            raise ValueError(f"Não foi possível obter o preço para o ativo {asset_name}")
        
        meta = self.info.meta()
        universe = meta["universe"]
        asset_info = next((item for item in universe if item["name"] == asset_name), None)
        
        if not asset_info:
            raise ValueError(f"Não foi possível encontrar metadados para o ativo {asset_name}")
            
        sz_decimals = asset_info["szDecimals"]
        
        size = round(max_usd_value / price, sz_decimals)
        return size

    def place_order(self, secret_key, asset_name, is_buy, size, limit_price=None, slippage=0.005, stop_loss=None, take_profit=None, comment=None, is_live_trading=False):
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

        # 3. Calcular o preço limite com base no slippage para simular uma ordem a mercado
        price = self.get_asset_price(asset_name)
        if price == 0:
            raise ValueError(f"Preço para {asset_name} é zero, não é possível colocar a ordem.")
        
        # Determinar se usar preço personalizado ou preço de mercado
        use_custom_price = False
        final_price = None
        
        if limit_price is not None:
            price_diff_percent = abs(limit_price - price) / price
            if price_diff_percent > 0.05:  # Máximo 5% de diferença
                print(f"⚠️ Preço fornecido ({limit_price}) está {price_diff_percent:.1%} longe do preço de mercado ({price})")
                print(f"Usando ordem de mercado em vez do preço fornecido")
                use_custom_price = False
            else:
                use_custom_price = True
                final_price = limit_price
                print(f"Usando preço fornecido: {final_price}")
        
        print(f"💰 Preço de mercado: {price}, Modo: {'Preço Específico' if use_custom_price else 'Mercado'}, Slippage: {slippage:.1%}")

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
                    # Usar market_open() para ordens de mercado verdadeiras
                    print(f"📈 Usando ordem de mercado com slippage: {slippage:.1%}")
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
                raise Exception(f"Falha ao colocar a ordem: {error_msg}")
            else:
                print(f"❓ Status da ordem desconhecido: {order_status}")
        else:
            raise Exception(f"Falha ao colocar a ordem: {status}")

        return status
