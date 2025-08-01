import React, { useState, useEffect } from 'react';
import api from '../services/api';

function PositionsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('list');

  useEffect(() => {
    fetchPositions();
  }, []);

  const fetchPositions = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/dashboard/positions/live');
      setData(response);
    } catch (err) {
      setError('Erro ao carregar posições');
      console.error('Error fetching positions:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    }).format(value);
  };

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">{error}</p>
        <button 
          onClick={fetchPositions}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  const positions = data?.positions || [];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Live Positions</h1>
        <div className="flex items-center gap-3">
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('card')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                viewMode === 'card'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 9a2 2 0 00-2 2v2a2 2 0 002 2m0 0h14m-14 0a2 2 0 002 2v2a2 2 0 01-2 2" />
              </svg>
              Cards
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                viewMode === 'list'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
              List
            </button>
          </div>
          <button 
            onClick={fetchPositions}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 text-sm">Account Value</p>
                <p className="text-2xl font-bold">{formatCurrency(data.account_value)}</p>
              </div>
              <div className="bg-blue-400 bg-opacity-30 rounded-lg p-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                </svg>
              </div>
            </div>
          </div>
          
          <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-purple-100 text-sm">Margin Used</p>
                <p className="text-2xl font-bold">{formatCurrency(data.total_margin_used)}</p>
              </div>
              <div className="bg-purple-400 bg-opacity-30 rounded-lg p-2">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
          </div>
          
          <div className={`bg-gradient-to-r rounded-xl p-4 text-white ${
            data.total_unrealized_pnl >= 0 
              ? 'from-green-500 to-green-600' 
              : 'from-red-500 to-red-600'
          }`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-sm ${
                  data.total_unrealized_pnl >= 0 ? 'text-green-100' : 'text-red-100'
                }`}>Total Unrealized PnL</p>
                <p className="text-2xl font-bold">
                  {data.total_unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(data.total_unrealized_pnl)}
                </p>
              </div>
              <div className={`rounded-lg p-2 ${
                data.total_unrealized_pnl >= 0 
                  ? 'bg-green-400 bg-opacity-30' 
                  : 'bg-red-400 bg-opacity-30'
              }`}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      )}

      {positions.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-xl">
          <div className="mx-auto w-24 h-24 bg-gray-200 rounded-full flex items-center justify-center mb-4">
            <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <p className="text-gray-500 text-lg font-medium">No open positions</p>
          <p className="text-gray-400 text-sm mt-1">Your active positions will appear here</p>
        </div>
      ) : viewMode === 'card' ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {positions.map((position, index) => (
            <div key={index} className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 hover:shadow-xl transition-all hover:border-gray-600">
              <div className="p-5">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                      {position.asset_name.slice(0, 2)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-white text-lg">
                        {position.asset_name}
                      </h3>
                      <p className="text-sm text-gray-400">{position.leverage}x Leverage</p>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    position.side === 'LONG' 
                      ? 'bg-green-900 text-green-300' 
                      : 'bg-red-900 text-red-300'
                  }`}>
                    {position.side}
                  </span>
                </div>
                
                <div className="space-y-3">
                  <div className="flex justify-between items-center py-2 border-b border-gray-700">
                    <span className="text-sm text-gray-400">Size</span>
                    <span className="font-medium text-white">{position.size}</span>
                  </div>
                  
                  <div className="flex justify-between items-center py-2 border-b border-gray-700">
                    <span className="text-sm text-gray-400">Entry Price</span>
                    <span className="font-medium text-white">{formatCurrency(position.entry_price)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center py-2 border-b border-gray-700">
                    <span className="text-sm text-gray-400">Current Price</span>
                    <span className="font-medium text-blue-400">{formatCurrency(position.current_price)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center py-2 border-b border-gray-700">
                    <span className="text-sm text-gray-400">Margin Used</span>
                    <span className="font-medium text-white">{formatCurrency(position.margin_used)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center py-2">
                    <span className="text-sm text-gray-400">ROE</span>
                    <span className={`font-semibold ${
                      position.return_on_equity >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {formatPercentage(position.return_on_equity)}
                    </span>
                  </div>
                </div>
                
                <div className={`mt-4 p-3 rounded-lg border ${
                  position.unrealized_pnl >= 0 
                    ? 'bg-green-900 bg-opacity-20 border-green-700' 
                    : 'bg-red-900 bg-opacity-20 border-red-700'
                }`}>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-300">Unrealized PnL</span>
                    <span className={`font-bold text-lg ${
                      position.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {position.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(position.unrealized_pnl)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-700">
              <thead className="bg-gray-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Asset
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Side
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Entry Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Current Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Margin Used
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    ROE
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                    Unrealized PnL
                  </th>
                </tr>
              </thead>
              <tbody className="bg-gray-800 divide-y divide-gray-700">
                {positions.map((position, index) => (
                  <tr key={index} className="hover:bg-gray-700 transition-colors">
                     <td className="px-6 py-4 whitespace-nowrap">
                       <div className="flex items-center">
                         <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-xs mr-3">
                           {position.asset_name.slice(0, 2)}
                         </div>
                         <div>
                           <div className="text-sm font-medium text-white">{position.asset_name}</div>
                           <div className="text-sm text-gray-400">{position.leverage}x Leverage</div>
                         </div>
                       </div>
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap">
                       <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                         position.side === 'LONG'
                           ? 'bg-green-900 text-green-300'
                           : 'bg-red-900 text-red-300'
                       }`}>
                         {position.side}
                       </span>
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                       {position.size}
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                       {formatCurrency(position.entry_price)}
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-400 font-medium">
                       {formatCurrency(position.current_price)}
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm text-white">
                       {formatCurrency(position.margin_used)}
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                       <span className={position.return_on_equity >= 0 ? 'text-green-400' : 'text-red-400'}>
                         {formatPercentage(position.return_on_equity)}
                       </span>
                     </td>
                     <td className="px-6 py-4 whitespace-nowrap text-sm font-bold">
                       <span className={position.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                         {position.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(position.unrealized_pnl)}
                       </span>
                     </td>
                   </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default PositionsPage;