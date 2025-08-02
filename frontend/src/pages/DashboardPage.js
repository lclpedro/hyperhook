import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services';
import Spinner from '../components/ui/Spinner';
import { TrendingUpIcon, TrendingDownIcon, ChartBarIcon, XIcon } from '../components/icons';

const DashboardPage = ({ token }) => {
  const [assetPerformance, setAssetPerformance] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [webhookDetails, setWebhookDetails] = useState(null);
  const [overallStats, setOverallStats] = useState(null);
  const [tradeDetails, setTradeDetails] = useState(null);

  const calculateTradePnl = (closeExecution, allTrades) => {
    if (closeExecution.trade_type !== 'CLOSE') return 0;
    
    const assetTrades = allTrades.filter(t => t.asset_name === closeExecution.asset_name)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    let openTrades = [];
    let totalOpenQuantity = 0;
    let totalOpenValue = 0;
    
    for (const trade of assetTrades) {
      if (trade.timestamp >= closeExecution.timestamp) break;
      
      if (trade.trade_type === 'BUY' || trade.trade_type === 'SELL' || trade.trade_type === 'DCA') {
        openTrades.push(trade);
        totalOpenQuantity += trade.quantity;
        totalOpenValue += trade.quantity * trade.price;
      } else if (trade.trade_type === 'CLOSE') {
        const quantityToRemove = Math.min(trade.quantity, totalOpenQuantity);
        totalOpenQuantity -= quantityToRemove;
        
        if (totalOpenQuantity <= 0) {
          openTrades = [];
          totalOpenValue = 0;
          totalOpenQuantity = 0;
        } else {
          const avgPrice = totalOpenValue / (totalOpenQuantity + quantityToRemove);
          totalOpenValue = totalOpenQuantity * avgPrice;
        }
      }
    }
    
    if (openTrades.length === 0 || totalOpenQuantity === 0) return 0;
    
    const avgOpenPrice = totalOpenValue / totalOpenQuantity;
    const side = openTrades[0].side;
    const leverage = closeExecution.leverage || 1;
    
    let pnl = 0;
    if (side === 'LONG') {
      pnl = (closeExecution.price - avgOpenPrice) * closeExecution.quantity;
    } else {
      pnl = (avgOpenPrice - closeExecution.price) * closeExecution.quantity;
    }
    
    return pnl * leverage;
  };


  const fetchDashboardData = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await api.get('/api/dashboard/');

      setAssetPerformance(data.asset_performance || []);

      // Calculate overall statistics
      const assets = data.asset_performance || [];
      const totalTrades = assets.reduce((sum, asset) => sum + asset.total_trades, 0);
      const totalWinningTrades = assets.reduce((sum, asset) => sum + asset.winning_trades, 0);
      const totalLosingTrades = assets.reduce((sum, asset) => sum + asset.losing_trades, 0);
      const totalPnl = assets.reduce((sum, asset) => sum + (asset.net_pnl || 0), 0);
      const totalVolume = assets.reduce((sum, asset) => sum + (asset.total_volume || 0), 0);
      const totalFees = assets.reduce((sum, asset) => sum + (asset.total_fees || 0), 0);

      // Calculate win rate based on completed trades only (winning + losing trades)
      const completedTrades = totalWinningTrades + totalLosingTrades;
      const winRate = completedTrades > 0 ? (totalWinningTrades / completedTrades) * 100 : 0;
      const lossRate = completedTrades > 0 ? (totalLosingTrades / completedTrades) * 100 : 0;

      setOverallStats({
        totalTrades,
        totalWinningTrades,
        totalLosingTrades,
        winRate,
        lossRate,
        totalPnl,
        totalVolume,
        totalFees,
        profitFactor: totalLosingTrades > 0 ? Math.abs(totalWinningTrades / totalLosingTrades) : 0
      });
    } catch (error) {
      console.error("Erro ao carregar dashboard:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const recalculatePnl = useCallback(async () => {
    try {
      await api.post('/api/dashboard/recalculate-pnl');
      await fetchDashboardData();
    } catch (error) {
      console.error("Erro ao recalcular PNL:", error);
    }
  }, [fetchDashboardData]);

  const fetchAssetDetails = async (assetName) => {
    try {
      console.log('Fetching asset details for:', assetName);
      const data = await api.get(`/api/dashboard/assets/${assetName}`);
      console.log('Asset details received:', data);
      setSelectedAsset(data);
    } catch (error) {
      console.error("Erro ao carregar detalhes do ativo:", error);
      // Mostrar uma mensagem de erro para o usuário
      alert('Erro ao carregar detalhes do ativo. Verifique o console para mais informações.');
    }
  };

  const fetchWebhookDetails = async (executionId) => {
    try {
      const data = await api.get(`/api/dashboard/webhooks/${executionId}`);
      setWebhookDetails(data);
    } catch (error) {
      console.error("Erro ao carregar detalhes do webhook:", error);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);



  if (isLoading) return <div className="flex justify-center"><Spinner /></div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Dashboard de Performance</h2>
        <button
          onClick={recalculatePnl}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors"
        >
          🔄 Recalcular PNL
        </button>
      </div>

      {/* Cards de Resumo */}
      {overallStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">PNL Total</p>
                <p className={`text-2xl font-bold ${overallStats.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                  ${overallStats.totalPnl?.toFixed(2)}
                </p>
              </div>
              {overallStats.totalPnl >= 0 ? (
                <TrendingUpIcon className="h-8 w-8 text-green-400" />
              ) : (
                <TrendingDownIcon className="h-8 w-8 text-red-400" />
              )}
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Total Trades</p>
                <p className="text-2xl font-bold text-white">
                  {overallStats.totalTrades}
                </p>
              </div>
              <ChartBarIcon className="h-8 w-8 text-blue-400" />
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Win Rate</p>
                <p className="text-2xl font-bold text-green-400">
                  {overallStats.winRate?.toFixed(1)}%
                </p>
              </div>
              <TrendingUpIcon className="h-8 w-8 text-green-400" />
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Profit Factor</p>
                <p className="text-2xl font-bold text-purple-400">
                  {overallStats.profitFactor?.toFixed(2)}
                </p>
              </div>
              <ChartBarIcon className="h-8 w-8 text-purple-400" />
            </div>
          </div>
        </div>
      )}

      {/* Trading Statistics Cards */}
      {overallStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Winning Trades</p>
                <p className="text-2xl font-bold text-green-400">
                  {overallStats.totalWinningTrades}
                </p>
              </div>
              <TrendingUpIcon className="h-8 w-8 text-green-400" />
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Losing Trades</p>
                <p className="text-2xl font-bold text-red-400">
                  {overallStats.totalLosingTrades}
                </p>
              </div>
              <TrendingDownIcon className="h-8 w-8 text-red-400" />
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Loss Rate</p>
                <p className="text-2xl font-bold text-red-400">
                  {overallStats.lossRate?.toFixed(1)}%
                </p>
              </div>
              <TrendingDownIcon className="h-8 w-8 text-red-400" />
            </div>
          </div>
        </div>
      )}

      {/* Trade Details Modal */}
      {tradeDetails && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center" style={{zIndex: 99999}} onClick={() => setTradeDetails(null)}>
          <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl shadow-2xl w-full max-w-md p-6 m-4 border border-gray-700" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm font-bold">📊</span>
                </div>
                <h3 className="text-xl font-bold text-white">Trade Details</h3>
              </div>
              <button
                onClick={() => setTradeDetails(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <XIcon className="h-6 w-6" />
              </button>
            </div>

            {/* Asset Info */}
            <div className="text-center mb-6">
              <h4 className="text-2xl font-bold text-white mb-2">{tradeDetails.asset_name || selectedAsset?.asset_name || selectedAsset?.trading_view_symbol || 'Asset'}</h4>
              <div className="flex items-center justify-center gap-2">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${tradeDetails.side === 'LONG' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
                  {tradeDetails.side}
                </span>
                <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-600 text-white">
                  {tradeDetails.leverage || '1'}X
                </span>
              </div>
            </div>

            {/* PNL Display */}
            <div className="text-center mb-6">
              {(() => {
                const tradePnl = calculateTradePnl(tradeDetails, selectedAsset?.trades || []);
                const pnlPercentage = tradeDetails.usd_value ? (tradePnl / tradeDetails.usd_value) * 100 : 0;
                return (
                  <>
                    <div className={`text-5xl font-bold mb-2 ${pnlPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {pnlPercentage >= 0 ? '+' : ''}{pnlPercentage.toFixed(1)}%
                    </div>
                  </>
                );
              })()}
              <div className="text-gray-400 text-sm">
                Trade PNL (with Leverage)
              </div>
            </div>

            {/* Date */}
            <div className="text-center">
              <div className="text-gray-400 text-sm mb-1">Operation Date</div>
              <div className="text-white font-medium">
                {tradeDetails.timestamp ? new Date(tradeDetails.timestamp).toLocaleString('en-US') : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Volume and Fees Cards */}
      {overallStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Volume Total</p>
                <p className="text-2xl font-bold text-white">${overallStats?.totalVolume?.toFixed(2)}</p>
              </div>
              <ChartBarIcon className="h-8 w-8 text-purple-400" />
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Taxas Totais</p>
                <p className="text-2xl font-bold text-orange-400">${overallStats?.totalFees?.toFixed(2)}</p>
              </div>
              <ChartBarIcon className="h-8 w-8 text-orange-400" />
            </div>
          </div>
        </div>
      )}

      {/* Asset Performance */}
      {assetPerformance.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-xl font-semibold text-white mb-4">Asset Performance</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-700">
              <thead>
                <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Asset</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Total PNL</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Trades</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Win Rate</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Winning Trades</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Losing Trades</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {assetPerformance && assetPerformance.map((asset, index) => (
              <tr key={index} className="hover:bg-gray-700 transition-colors">
                <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-white">
                  {asset.trading_view_symbol}
                </td>
                <td className={`px-4 py-4 whitespace-nowrap text-sm font-medium ${(asset.net_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                  ${(asset.net_pnl || 0).toFixed(2)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-300">
                  {asset.total_trades}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-green-400">
                  {asset.win_rate ? `${asset.win_rate.toFixed(1)}%` : 'N/A'}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-green-400">
                  {asset.winning_trades}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-red-400">
                  {asset.losing_trades}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm">
                  <button
                    onClick={() => fetchAssetDetails(asset.trading_view_symbol)}
                    className="text-blue-400 hover:text-blue-300 text-sm"
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Asset Details Modal */}
      {selectedAsset && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50" onClick={() => setSelectedAsset(null)}>
          <div className="bg-gray-900 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-y-auto p-6 m-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-2xl font-bold text-white">Performance Details - {selectedAsset?.trading_view_symbol || 'Loading...'}</h3>
              <button
                onClick={() => setSelectedAsset(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <XIcon className="h-6 w-6" />
              </button>
            </div>

        {/* Loading State */}
        {!selectedAsset.summary ? (
          <div className="flex justify-center items-center py-12">
            <Spinner />
            <span className="ml-3 text-gray-400">Carregando detalhes...</span>
          </div>
        ) : (
          <>
            {/* Asset Summary */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
              <div className="bg-gray-800 p-4 rounded-lg">
                <p className="text-sm text-gray-400">Total PNL</p>
                <p className={`text-xl font-bold ${(selectedAsset.summary?.net_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                  ${(selectedAsset.summary?.net_pnl || 0).toFixed(2)}
                </p>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <p className="text-sm text-gray-400">Total Trades</p>
                <p className="text-xl font-bold text-white">{selectedAsset.summary?.total_trades || 0}</p>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <p className="text-sm text-gray-400">Win Rate</p>
                <p className="text-xl font-bold text-green-400">
                  {selectedAsset.summary?.win_rate ? `${selectedAsset.summary.win_rate.toFixed(1)}%` : 'N/A'}
                </p>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <p className="text-sm text-gray-400">Winning Trades</p>
                <p className="text-xl font-bold text-green-400">{selectedAsset.winning_trades || 0}</p>
              </div>
              <div className="bg-gray-800 p-4 rounded-lg">
                <p className="text-sm text-gray-400">Losing Trades</p>
                <p className="text-xl font-bold text-red-400">{selectedAsset.losing_trades || 0}</p>
              </div>
            </div>

            {/* Executions List */}
            <div>
              <h4 className="text-lg font-medium text-white mb-3">Execution History</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-700">
                  <thead className="bg-gray-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Date</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Side</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Quantity</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Price</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">USD Value</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-gray-800 divide-y divide-gray-700">
                    {selectedAsset.trades && selectedAsset.trades.length > 0 ? (
                      selectedAsset.trades.map((execution, index) => (
                        <tr key={index} className="hover:bg-gray-700 transition-colors">
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-300">
                            {execution.timestamp ? new Date(execution.timestamp).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit'
                            }) : 'N/A'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-white">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${execution.trade_type === 'CLOSE' ? 'bg-red-600 text-white' : 'bg-blue-600 text-white'
                              }`}>
                              {execution.trade_type || 'N/A'}
                            </span>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${execution.side === 'LONG' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                              }`}>
                              {execution.side || 'N/A'}
                            </span>
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-300">
                            {execution.quantity || 'N/A'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-300">
                            ${execution.price?.toFixed(6) || '0.000000'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-300">
                            ${execution.usd_value?.toFixed(2) || '0.00'}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap text-sm">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => fetchWebhookDetails(execution.id)}
                                className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
                              >
                                👁️ View Webhook
                              </button>
                              {execution.trade_type === 'CLOSE' && (
                                <button
                                onClick={() => setTradeDetails(execution)}
                                className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1"
                              >
                                📊 Details
                              </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="8" className="px-4 py-8 text-center text-gray-400">
                          Nenhuma execução encontrada
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
    )}

    {/* Webhook Details Modal */}
    {webhookDetails && (
      <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50" onClick={() => setWebhookDetails(null)}>
        <div className="bg-gray-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 m-4" onClick={e => e.stopPropagation()}>
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-white">Webhook Execution Details</h3>
            <button
              onClick={() => setWebhookDetails(null)}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <XIcon className="h-6 w-6" />
            </button>
          </div>

        <div className="space-y-6">
          {/* Webhook Execution Info */}
          <div className="mb-6">
            <h4 className="text-lg font-medium text-white mb-3">Execution Information</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-sm text-gray-400">Asset</p>
                <p className="text-white font-medium">{webhookDetails.webhook_execution.asset_name}</p>
              </div>
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-sm text-gray-400">Type</p>
                <p className="text-white font-medium">
                  {webhookDetails.webhook_execution.trade_type} {webhookDetails.webhook_execution.side}
                </p>
              </div>
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-sm text-gray-400">Quantity</p>
                <p className="text-white font-medium">{webhookDetails.webhook_execution.quantity}</p>
              </div>
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-sm text-gray-400">Price</p>
                <p className="text-white font-medium">${webhookDetails.webhook_execution.price?.toFixed(6)}</p>
              </div>
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-sm text-gray-400">USD Value</p>
                <p className="text-white font-medium">${webhookDetails.webhook_execution.usd_value?.toFixed(4)}</p>
              </div>
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-sm text-gray-400">Leverage</p>
                <p className="text-white font-medium">{webhookDetails.webhook_execution.leverage}x</p>
              </div>
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-sm text-gray-400">Fees</p>
                <p className="text-white font-medium">${webhookDetails.webhook_execution.fees?.toFixed(6) || '0.000000'}</p>
              </div>
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-sm text-gray-400">Date/Time</p>
                <p className="text-white font-medium">
                  {new Date(webhookDetails.webhook_execution.timestamp).toLocaleString('en-US')}
                </p>
              </div>
            </div>
          </div>

          {/* Webhook Config Info */}
          {webhookDetails.webhook_config && (
            <div className="mb-6">
              <h4 className="text-lg font-medium text-white mb-3">Webhook Configuration</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Asset</p>
                  <p className="text-white font-medium">{webhookDetails.webhook_config.trading_view_symbol}</p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Max USD Value</p>
                  <p className="text-white font-medium">${webhookDetails.webhook_config.max_usd_value}</p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Leverage</p>
                  <p className="text-white font-medium">{webhookDetails.webhook_config.leverage}x</p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Live Trading</p>
                  <p className={`font-medium ${webhookDetails.webhook_config.is_live_trading ? 'text-green-400' : 'text-red-400'}`}>
                    {webhookDetails.webhook_config.is_live_trading ? 'Active' : 'Inactive'}
                  </p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Hyperliquid Symbol</p>
                  <p className="text-white font-medium">{webhookDetails.webhook_config.hyperliquid_symbol || 'N/A'}</p>
                </div>
              </div>
            </div>
          )}

          {/* Position Info */}
          {webhookDetails.position && (
            <div className="mb-6">
              <h4 className="text-lg font-medium text-white mb-3">Position Information</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Status</p>
                  <p className={`font-medium ${webhookDetails.position.is_open ? 'text-green-400' : 'text-red-400'}`}>
                    {webhookDetails.position.is_open ? 'Open' : 'Closed'}
                  </p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Side</p>
                  <p className={`font-medium ${webhookDetails.position.side === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                    {webhookDetails.position.side}
                  </p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Quantity</p>
                  <p className="text-white font-medium">{webhookDetails.position.quantity}</p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Average Entry Price</p>
                  <p className="text-white font-medium">${webhookDetails.position.avg_entry_price?.toFixed(6)}</p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Realized PNL</p>
                  <p className={`font-medium ${webhookDetails.position.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${webhookDetails.position.realized_pnl?.toFixed(6)}
                  </p>
                </div>
                <div className="bg-gray-700 p-3 rounded">
                  <p className="text-sm text-gray-400">Unrealized PNL</p>
                  <p className={`font-medium ${webhookDetails.position.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${webhookDetails.position.unrealized_pnl?.toFixed(6)}
                  </p>
                </div>
              </div>

              {webhookDetails.position.opened_at && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  <div className="bg-gray-700 p-3 rounded">
                    <p className="text-sm text-gray-400">Opened At</p>
                    <p className="text-white font-medium">
                      {new Date(webhookDetails.position.opened_at).toLocaleString('en-US')}
                    </p>
                  </div>
                  {webhookDetails.position.closed_at && (
                    <div className="bg-gray-700 p-3 rounded">
                      <p className="text-sm text-gray-400">Closed At</p>
                      <p className="text-white font-medium">
                        {new Date(webhookDetails.position.closed_at).toLocaleString('en-US')}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Order ID */}
          {webhookDetails.webhook_execution.order_id && (
            <div className="mb-6">
              <h4 className="text-lg font-medium text-white mb-3">Order ID</h4>
              <div className="bg-gray-700 p-3 rounded">
                <p className="text-white font-mono text-sm break-all">
                  {webhookDetails.webhook_execution.order_id}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )}
    </div>
  )
};

export default DashboardPage;