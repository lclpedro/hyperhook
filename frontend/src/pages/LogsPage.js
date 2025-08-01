import React, { useState, useEffect } from 'react';
import { api } from '../services';

const LogsPage = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/webhooks/logs');
      setLogs(response || []);
    } catch (err) {
      setError('Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getStatusColor = (status) => {
    if (status >= 200 && status < 300) return 'text-green-400';
    if (status >= 400) return 'text-red-400';
    return 'text-yellow-400';
  };

  const getStatusBadgeColor = (status) => {
    if (status >= 200 && status < 300) return 'bg-green-900/30 text-green-400 border-green-500/30';
    if (status >= 400) return 'bg-red-900/30 text-red-400 border-red-500/30';
    return 'bg-yellow-900/30 text-yellow-400 border-yellow-500/30';
  };

  const formatJson = (jsonString) => {
    try {
      return JSON.stringify(JSON.parse(jsonString), null, 2);
    } catch {
      return jsonString;
    }
  };

  const openLogDetails = (log) => {
    setSelectedLog(log);
  };

  const closeLogDetails = () => {
    setSelectedLog(null);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-white">Loading logs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-red-400">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">Webhook Logs</h1>
        <button 
          onClick={fetchLogs}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          🔄 Atualizar
        </button>
      </div>
      
      {logs.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 text-lg mb-2">📋 Nenhum log encontrado</div>
          <div className="text-gray-500">Os logs dos webhooks aparecerão aqui</div>
        </div>
      ) : (
        <div className="grid gap-4">
          {logs.map((log) => (
            <div key={log.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:bg-gray-750 transition-colors">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-white font-semibold text-lg">#{log.id}</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusBadgeColor(log.response_status)}`}>
                    {log.is_success ? '✅ Sucesso' : '❌ Erro'}
                  </span>
                </div>
                <div className="text-right">
                  <span className={`font-bold text-lg ${getStatusColor(log.response_status)}`}>
                    {log.response_status}
                  </span>
                  <div className="text-gray-400 text-sm">
                    {formatDate(log.timestamp)}
                  </div>
                </div>
              </div>
              
              <div className="mb-3">
                <div className="text-gray-300 font-medium mb-1">URL Chamada</div>
                <div className="bg-gray-900/50 p-2 rounded border border-gray-600 text-sm font-mono text-gray-300">
                  {log.request_url}
                </div>
              </div>
              
              {log.error_message && (
                <div className="mb-3">
                  <div className="text-red-400 font-medium mb-1">❌ Erro</div>
                  <div className="bg-red-900/20 border border-red-500/30 p-2 rounded text-red-300 text-sm">
                    {log.error_message}
                  </div>
                </div>
              )}
              
              <button
                onClick={() => openLogDetails(log)}
                className="w-full bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-lg transition-colors text-sm font-medium"
              >
                📋 Ver Detalhes Completos
              </button>
            </div>
          ))}
        </div>
      )}
      
      {selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-4" onClick={closeLogDetails}>
          <div className="bg-gray-900 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-6 flex items-center justify-between">
              <h3 className="text-2xl font-bold text-white">Detalhes do Log #{selectedLog.id}</h3>
              <button 
                onClick={closeLogDetails}
                className="text-gray-400 hover:text-white transition-colors text-2xl"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-lg font-medium text-white mb-2">Status</h4>
                  <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border ${getStatusBadgeColor(selectedLog.response_status)}`}>
                    <span>{selectedLog.is_success ? '✅' : '❌'}</span>
                    <span className="font-medium">{selectedLog.is_success ? 'Sucesso' : 'Erro'}</span>
                  </div>
                </div>
                
                <div>
                  <h4 className="text-lg font-medium text-white mb-2">Código HTTP</h4>
                  <div className={`text-2xl font-bold ${getStatusColor(selectedLog.response_status)}`}>
                    {selectedLog.response_status}
                  </div>
                </div>
              </div>
              
              <div>
                <h4 className="text-lg font-medium text-white mb-2">Timestamp</h4>
                <div className="text-gray-300 font-mono">
                  {formatDate(selectedLog.timestamp)}
                </div>
              </div>
              
              <div>
                <h4 className="text-lg font-medium text-white mb-2">URL Chamada</h4>
                <div className="bg-gray-800 p-3 rounded-lg border border-gray-600 text-sm font-mono text-gray-300">
                  {selectedLog.request_url}
                </div>
              </div>
              
              <div>
                <h4 className="text-lg font-medium text-white mb-2 flex items-center gap-2">
                  📤 Headers da Requisição
                </h4>
                <pre className="bg-gray-800 p-4 rounded-lg border border-gray-600 text-sm text-gray-300 overflow-x-auto">
                  {formatJson(selectedLog.request_headers)}
                </pre>
              </div>
              
              <div>
                <h4 className="text-lg font-medium text-white mb-2 flex items-center gap-2">
                  📊 Payload do TradingView
                </h4>
                <pre className="bg-gray-800 p-4 rounded-lg border border-gray-600 text-sm text-gray-300 overflow-x-auto">
                  {formatJson(selectedLog.request_body)}
                </pre>
              </div>
              
              <div>
                <h4 className="text-lg font-medium text-white mb-2 flex items-center gap-2">
                  📥 Headers da Resposta
                </h4>
                <pre className="bg-gray-800 p-4 rounded-lg border border-gray-600 text-sm text-gray-300 overflow-x-auto">
                  {formatJson(selectedLog.response_headers)}
                </pre>
              </div>
              
              <div>
                <h4 className="text-lg font-medium text-white mb-2 flex items-center gap-2">
                  🔄 Resposta do Servidor
                </h4>
                <pre className="bg-gray-800 p-4 rounded-lg border border-gray-600 text-sm text-gray-300 overflow-x-auto">
                  {formatJson(selectedLog.response_body)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LogsPage;