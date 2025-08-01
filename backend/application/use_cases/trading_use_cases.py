import time
from typing import List
from infrastructure.external.hyperliquid_client import HyperliquidClient

_assets_cache = None
_cache_timestamp = 0
CACHE_DURATION = 24 * 60 * 60

def get_meta_info() -> dict:
    """Obtém informações de metadados da Hyperliquid"""
    client = HyperliquidClient()
    meta = client.info.meta()
    
    try:
        all_mids = client.get_all_mids()
        contexts = []
        
        if meta and 'universe' in meta:
            for asset in meta['universe']:
                trading_view_symbol = asset.get('name')
                mark_price = all_mids.get(trading_view_symbol, 0.0)
                contexts.append({
                    'markPx': str(mark_price)
                })
        
        return {
            'universe': meta.get('universe', []),
            'contexts': contexts
        }
    except Exception as e:
        print(f"Error fetching meta with prices: {e}")
        return meta

def debug_asset_rules(trading_view_symbol: str) -> dict:
    """Obtém as regras específicas de um ativo para debug"""
    client = HyperliquidClient()
    try:
        asset_info = client.get_asset_info(trading_view_symbol)
        return {
            "asset_name": trading_view_symbol,
            "asset_info": asset_info,
            "exists": True
        }
    except Exception as e:
        return {
            "asset_name": trading_view_symbol,
            "error": str(e),
            "exists": False
        }

def list_all_assets() -> dict:
    """Lista todos os ativos disponíveis com suas regras de tamanho"""
    client = HyperliquidClient()
    try:
        meta = client.info.meta()
        assets = []
        
        if meta and 'universe' in meta:
            for asset in meta['universe']:
                trading_view_symbol = asset.get('name')
                try:
                    asset_info = client.get_asset_info(trading_view_symbol)
                    assets.append({
                        "name": trading_view_symbol,
                        "info": asset_info,
                        "universe_data": asset
                    })
                except Exception as e:
                    assets.append({
                        "name": trading_view_symbol,
                        "error": str(e),
                        "universe_data": asset
                    })
        
        return {
            "total_assets": len(assets),
            "assets": assets
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_assets": 0,
            "assets": []
        }

def get_hyperliquid_assets() -> List[str]:
    """Busca lista de ativos da Hyperliquid com cache de 24h"""
    global _assets_cache, _cache_timestamp
    
    current_time = time.time()
    
    if _assets_cache is None or (current_time - _cache_timestamp) > CACHE_DURATION:
        try:
            client = HyperliquidClient()
            meta = client.info.meta()
            
            if meta and 'universe' in meta:
                assets = [asset.get('name') for asset in meta['universe'] if asset.get('name')]
                assets.sort()
                
                _assets_cache = assets
                _cache_timestamp = current_time
            else:
                return []
        except Exception as e:
            print(f"Error fetching Hyperliquid assets: {e}")
            return _assets_cache or []
    
    return _assets_cache