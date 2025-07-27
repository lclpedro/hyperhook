def extract_asset_from_symbol(symbol: str) -> str:
    """Extrai o nome do ativo do símbolo de trading (ex: BTCUSDT -> BTC)"""
    # Remove sufixos comuns como USDT, USDC, USD, etc.
    suffixes = ['USDT', 'USDC', 'USD', 'BTC', 'ETH']
    for suffix in suffixes:
        if symbol.endswith(suffix):
            asset = symbol[:-len(suffix)]
            if asset:  # Garantir que sobrou algo após remover o sufixo
                return asset
    # Se não encontrou sufixo conhecido, retorna o símbolo original
    return symbol

def calculate_quantity_multiplier(tradingview_asset, hyperliquid_asset, client):
    """
    Calcula o multiplicador de quantidade necessário quando há diferença de preços
    entre TradingView e Hyperliquid (ex: PEPE vs kPEPE com fator 1000x)
    """
    if tradingview_asset == hyperliquid_asset:
        return 1.0
    
    try:
        # Para ativos com prefixo 'k', aplicar multiplicador baseado na diferença de escala
        if hyperliquid_asset.startswith('k') and hyperliquid_asset[1:] == tradingview_asset:
            # Buscar apenas o preço do ativo da Hyperliquid
            hl_price = client.get_asset_price(hyperliquid_asset)
            
            if hl_price > 0:
                # Para ativos k*, geralmente há uma diferença de escala de 1000x
                # Exemplo: PEPE (0.00001) vs kPEPE (0.01) = 1000x diferença
                # Então precisamos dividir a quantidade por 1000
                multiplier = 1.0 / 1000.0
                print(f"💰 ATIVO PERSONALIZADO: {hyperliquid_asset}=${hl_price:.8f}")
                print(f"🔢 APLICANDO MULTIPLICADOR PADRÃO k*: {multiplier:.6f} (1/1000)")
                return multiplier
        
        # Para outros casos, tentar calcular baseado nos preços
        try:
            tv_price = client.get_asset_price(tradingview_asset)
            hl_price = client.get_asset_price(hyperliquid_asset)
            
            if tv_price > 0 and hl_price > 0:
                price_ratio = hl_price / tv_price
                
                if price_ratio >= 100:
                    multiplier = 1.0 / price_ratio
                    print(f"💰 PREÇOS: {tradingview_asset}=${tv_price:.8f}, {hyperliquid_asset}=${hl_price:.8f}")
                    print(f"🔢 RATIO: {price_ratio:.0f}x, MULTIPLICADOR: {multiplier:.6f}")
                    return multiplier
        except:
            pass
        
        return 1.0
        
    except Exception as e:
        print(f"⚠️ Erro ao calcular multiplicador: {e}")
        return 1.0