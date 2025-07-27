from infrastructure.external.hyperliquid_client import HyperliquidClient

def get_meta_info() -> dict:
    """Obtém informações de metadados da Hyperliquid"""
    client = HyperliquidClient()
    meta = client.info.meta()
    
    try:
        all_mids = client.get_all_mids()
        contexts = []
        
        if meta and 'universe' in meta:
            for asset in meta['universe']:
                asset_name = asset.get('name')
                mark_price = all_mids.get(asset_name, 0.0)
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

def debug_asset_rules(asset_name: str) -> dict:
    """Obtém as regras específicas de um ativo para debug"""
    client = HyperliquidClient()
    try:
        asset_info = client.get_asset_info(asset_name)
        return {
            "asset_name": asset_name,
            "asset_info": asset_info,
            "exists": True
        }
    except Exception as e:
        return {
            "asset_name": asset_name,
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
                asset_name = asset.get('name')
                try:
                    asset_info = client.get_asset_info(asset_name)
                    assets.append({
                        "name": asset_name,
                        "info": asset_info,
                        "universe_data": asset
                    })
                except Exception as e:
                    assets.append({
                        "name": asset_name,
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