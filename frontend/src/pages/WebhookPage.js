import React, { useState, useEffect } from 'react';
import { api } from '../services';

const WebhookPage = () => {
  const [webhooks, setWebhooks] = useState([]);
  const [filteredWebhooks, setFilteredWebhooks] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [hyperliquidAssets, setHyperliquidAssets] = useState([]);
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [copiedStates, setCopiedStates] = useState({});
  const [userData, setUserData] = useState(null);
  const [expandedWebhooks, setExpandedWebhooks] = useState({});
  const [formData, setFormData] = useState({
    hyperliquidSymbol: '',
    tradingViewSymbol: '',
    maxUsdValue: '500',
    leverage: 1,
    isLiveTrading: false
  });

  useEffect(() => {
    fetchWebhooks();
    fetchHyperliquidAssets();
    fetchUserData();
  }, []);

  useEffect(() => {
    const filtered = webhooks.filter(webhook => 
      webhook.assetName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      webhook.hyperliquidSymbol?.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredWebhooks(filtered);
  }, [webhooks, searchTerm]);

  const copyToClipboard = async (text, key) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedStates(prev => ({ ...prev, [key]: true }));
      setTimeout(() => {
        setCopiedStates(prev => ({ ...prev, [key]: false }));
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const fetchWebhooks = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/webhooks');
      setWebhooks(response || []);
      setFilteredWebhooks(response || []);
    } catch (err) {
      setError('Failed to fetch webhooks');
    } finally {
      setLoading(false);
    }
  };

  const fetchHyperliquidAssets = async () => {
    try {
      setLoadingAssets(true);
      const response = await api.get('/api/hyperliquid/assets');
      setHyperliquidAssets(response.assets || []);
    } catch (err) {
      console.error('Failed to fetch Hyperliquid assets:', err);
    } finally {
      setLoadingAssets(false);
    }
  };

  const fetchUserData = async () => {
    try {
      const response = await api.get('/api/me');
      setUserData(response);
    } catch (err) {
      console.error('Failed to fetch user data:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setIsAdding(true);
      await api.post('/api/webhooks', {
        assetName: formData.tradingViewSymbol || formData.hyperliquidSymbol,
        hyperliquidSymbol: formData.hyperliquidSymbol,
        maxUsdValue: parseFloat(formData.maxUsdValue),
        leverage: formData.leverage,
        isLiveTrading: formData.isLiveTrading
      });
      setFormData({
        hyperliquidSymbol: '',
        tradingViewSymbol: '',
        maxUsdValue: '500',
        leverage: 1,
        isLiveTrading: false
      });
      fetchWebhooks();
    } catch (err) {
      setError('Failed to create webhook');
    } finally {
      setIsAdding(false);
    }
  };

  const handleDelete = async (webhookId) => {
    try {
      await api.delete(`/api/webhooks/${webhookId}`);
      fetchWebhooks();
    } catch (err) {
      setError('Failed to delete webhook');
    }
  };

  const toggleWebhookExpansion = (webhookId) => {
    setExpandedWebhooks(prev => ({
      ...prev,
      [webhookId]: !prev[webhookId]
    }));
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-white">Loading webhooks...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-white">🔗 Os seus Webhooks Ativos</h1>
      </div>
      
      {error && (
        <div className="bg-red-900/20 border border-red-500 text-red-400 p-3 rounded-lg mb-4">
          ⚠️ {error}
        </div>
      )}
      
      <div className="bg-gray-800 p-6 rounded-lg mb-6 border border-gray-700">
        <h2 className="text-xl font-semibold text-white mb-4">➕ Adicionar Novo Webhook</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-gray-400 mb-2">🏦 Hyperliquid Asset</label>
              <select
                value={formData.hyperliquidSymbol}
                onChange={(e) => {
                  const selectedAsset = e.target.value;
                  setFormData({
                    ...formData, 
                    hyperliquidSymbol: selectedAsset
                  });
                }}
                className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                disabled={loadingAssets}
              >
                <option value="">Selecione um ativo</option>
                {hyperliquidAssets.map((asset) => (
                  <option key={asset} value={asset}>
                    {asset}
                  </option>
                ))}
              </select>
              {loadingAssets && (
                <p className="text-gray-400 text-sm mt-1">Carregando ativos...</p>
              )}
            </div>
            <div>
              <label className="block text-gray-400 mb-2">📊 TradingView Symbol</label>
              <input
                type="text"
                value={formData.tradingViewSymbol}
                onChange={(e) => setFormData({...formData, tradingViewSymbol: e.target.value})}
                className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                placeholder="Ex: PEPE (deixe vazio se TradingView envia BTC)"
              />
              <p className="text-gray-400 text-sm mt-1">Ex: se você selecionar "kPEPE" acima mas o TradingView envia "PEPE", digite "PEPE" aqui</p>
            </div>
            <div>
              <label className="block text-gray-400 mb-2">💵 Max USD Value</label>
              <input
                type="number"
                step="0.01"
                value={formData.maxUsdValue}
                onChange={(e) => setFormData({...formData, maxUsdValue: e.target.value})}
                className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-gray-400 mb-2">⚡ Leverage</label>
              <input
                type="number"
                min="1"
                max="20"
                value={formData.leverage}
                onChange={(e) => setFormData({...formData, leverage: parseInt(e.target.value)})}
                className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              id="isLiveTrading"
              checked={formData.isLiveTrading}
              onChange={(e) => setFormData({...formData, isLiveTrading: e.target.checked})}
              className="mr-2"
            />
            <label htmlFor="isLiveTrading" className="text-gray-400">🚀 Live Trading</label>
          </div>
          <button
            type="submit"
            disabled={isAdding}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
          >
            {isAdding ? '⏳ Adicionando...' : '➕ Adicionar Webhook'}
          </button>
        </form>
      </div>
      
      <div className="mb-6">
        <div className="relative">
          <input
            type="text"
            placeholder="🔍 Pesquisar webhooks por ativo..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full p-3 bg-gray-800 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none pl-4"
          />
        </div>
      </div>
      
      <div className="space-y-4">
        {filteredWebhooks.length === 0 && !loading ? (
          <div className="text-center py-8">
            <div className="text-gray-400 text-lg mb-2">🔍 Nenhum webhook encontrado</div>
            <div className="text-gray-500">Tente ajustar sua pesquisa ou adicione um novo webhook</div>
          </div>
        ) : (
          filteredWebhooks.map((webhook) => {
            const webhookUrl = `https://hyperhook.fly.dev/v1/webhook`;
            const payload = {
              "data": {
                "action": "{{strategy.order.action}}",
                "contracts": "{{strategy.order.contracts}}",
                "position_size": "{{strategy.position_size}}"
              },
              "price": "{{close}}",
              "user_info": "STRATEGY_{{ticker}}_{{strategy.order.id}}",
              "symbol": "{{ticker}}",
              "time": "{{timenow}}",
              "user_uuid": userData?.uuid || "<user_id>",
              "secret": userData?.webhook_secret || "<secret>"
            };
          
          const isExpanded = expandedWebhooks[webhook.id];
          
          return (
          <div key={webhook.id} className="bg-gray-800 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors">
            <div 
              className="flex justify-between items-center p-4 cursor-pointer"
              onClick={() => toggleWebhookExpansion(webhook.id)}
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm font-bold">{webhook.assetName?.charAt(0) || webhook.hyperliquidSymbol?.charAt(0) || 'W'}</span>
                </div>
                <div>
                  <h3 className="text-white font-bold text-lg">{webhook.assetName || webhook.hyperliquidSymbol}</h3>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      webhook.isLiveTrading ? 'bg-green-900/30 text-green-400 border border-green-500/30' : 'bg-yellow-900/30 text-yellow-400 border border-yellow-500/30'
                    }`}>
                      {webhook.isLiveTrading ? '🚀 REAL' : '🧪 TEST'}
                    </span>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-900/30 text-blue-400 border border-blue-500/30">
                      {webhook.leverage}X
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(webhook.id);
                  }}
                  className="bg-red-600 hover:bg-red-700 text-white p-2 rounded-lg transition-colors"
                >
                  🗑️
                </button>
                <div className={`transform transition-transform ${
                  isExpanded ? 'rotate-180' : 'rotate-0'
                }`}>
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>
            
            {isExpanded && (
              <div className="border-t border-gray-700 p-4 space-y-4">
                {webhook.isLiveTrading && (
                  <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3 mb-4">
                    <span className="text-red-400 text-sm font-medium">
                      ⚠️ ATENÇÃO: Este webhook executará ordens reais com dinheiro real!
                    </span>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                  <div>
                    <span className="text-gray-400">🏦 Hyperliquid:</span>
                    <span className="text-white ml-2">{webhook.hyperliquidSymbol || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">📊 TradingView:</span>
                    <span className="text-white ml-2">{webhook.assetName || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">💵 Max USD:</span>
                    <span className="text-white ml-2">${webhook.maxUsdValue}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">⚡ Leverage:</span>
                    <span className="text-white ml-2">{webhook.leverage}x</span>
                  </div>
                </div>
              <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-600">
                <label className="block text-gray-300 mb-3 font-semibold flex items-center gap-2">
                  🔗 URL do Webhook (Genérico):
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={webhookUrl}
                    readOnly
                    className="flex-1 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 text-sm font-mono"
                  />
                  <button
                    onClick={() => copyToClipboard(webhookUrl, `url-${webhook.id}`)}
                    className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                      copiedStates[`url-${webhook.id}`] 
                        ? 'bg-green-600 text-white' 
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
                  >
                    {copiedStates[`url-${webhook.id}`] ? '✅' : '📋 Copiar'}
                  </button>
                </div>
                <p className="text-gray-400 text-xs mt-2">
                  💡 Nota: Uma URL única para todos os ativos. O ativo é determinado automaticamente pelo campo 'symbol' no payload.
                </p>
              </div>
              
              <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-600">
                <label className="block text-gray-300 mb-3 font-semibold flex items-center gap-2">
                  📋 Payload do TradingView:
                </label>
                <div className="flex items-start space-x-2">
                  <textarea
                    value={JSON.stringify(payload, null, 2)}
                    readOnly
                    rows={5}
                    className="flex-1 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 text-sm font-mono"
                  />
                  <button
                    onClick={() => copyToClipboard(JSON.stringify(payload, null, 2), `payload-${webhook.id}`)}
                    className={`px-4 py-3 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                      copiedStates[`payload-${webhook.id}`] 
                        ? 'bg-green-600 text-white' 
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
                  >
                    {copiedStates[`payload-${webhook.id}`] ? '✅' : '📋 Copiar'}
                  </button>
                </div>
                <p className="text-gray-400 text-xs mt-2">
                  💡 Use esta estrutura no seu alerta do TradingView. Mude 'action' para 'buy' ou 'sell'.
                </p>
              </div>
            </div>
            )}
          </div>
          )
          })
        )}
      </div>
    </div>
  );
};

export default WebhookPage;