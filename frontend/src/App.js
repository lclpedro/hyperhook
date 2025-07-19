import React, { useState, useEffect, useCallback } from 'react';

// --- Ícones (SVG para evitar dependências externas) ---
const EyeIcon = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z" /><path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.022 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" /></svg>;
const EyeOffIcon = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zM10 12a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" /><path d="M2 10s3.939 7 8 7a9.929 9.929 0 006.231-2.135l-3.98-3.98A4.002 4.002 0 0010 6a4 4 0 00-4 4c0 .737.208 1.42.57 2.01L2.83 12.17A10.005 10.005 0 012 10z" /></svg>;
const LinkIcon = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-4.5 0V6.375c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125-1.125h-4.5A2.25 2.25 0 0110.5 10.5v-4.5a2.25 2.25 0 012.25-2.25z" /></svg>;
const Spinner = () => <div className="w-6 h-6 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>;
const TrendingUpIcon = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.94" /></svg>;
const TrendingDownIcon = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6L9 12.75l4.286-4.286a11.948 11.948 0 014.306 6.43l.776 2.898m0 0l3.182-5.511m-3.182 5.511l-5.511-3.182" /></svg>;
const ChartBarIcon = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>;

const XIcon = ({ className }) => <svg className={className} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>;

// --- API Helper ---
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:5001'

const CACHE_DURATION = 7 * 24 * 60 * 60 * 1000;

const cacheManager = {
    set(key, data) {
        const cacheItem = {
            data,
            timestamp: Date.now(),
            expires: Date.now() + CACHE_DURATION
        };
        localStorage.setItem(`cache_${key}`, JSON.stringify(cacheItem));
    },
    
    get(key) {
        try {
            const cached = localStorage.getItem(`cache_${key}`);
            if (!cached) return null;
            
            const cacheItem = JSON.parse(cached);
            if (Date.now() > cacheItem.expires) {
                localStorage.removeItem(`cache_${key}`);
                return null;
            }
            
            return cacheItem.data;
        } catch (error) {
            console.error('Cache error:', error);
            return null;
        }
    },
    
    clear(key) {
        localStorage.removeItem(`cache_${key}`);
    }
};

const api = {
    async request(endpoint, options = {}) {
        const token = localStorage.getItem('jwt_token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: 'Erro desconhecido.' }));
                throw new Error(errorData.message || `Erro ${response.status}`);
            }
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return response.json();
            } else {
                return { success: true };
            }
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    },
    get(endpoint) { return this.request(endpoint, { method: 'GET' }); },
    post(endpoint, body) { return this.request(endpoint, { method: 'POST', body: JSON.stringify(body) }); },
    delete(endpoint) { return this.request(endpoint, { method: 'DELETE' }); },
    
    async getMeta() {
        const cached = cacheManager.get('hyperliquid_meta');
        if (cached) {
            console.log('Using cached Hyperliquid metadata');
            return cached;
        }
        
        console.log('Fetching fresh Hyperliquid metadata');
        const data = await this.get('/api/meta');
        cacheManager.set('hyperliquid_meta', data);
        return data;
    }
};


// --- Componente de Autenticação ---
const AuthScreen = ({ onLogin }) => {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            if (isLogin) {
                const data = await api.post('/login', { email, password });
                localStorage.setItem('jwt_token', data.access_token);
                onLogin(true);
            } else {
                await api.post('/register', { email, password });
                setIsLogin(true);
                alert('Cadastro realizado com sucesso! Por favor, faça o login.');
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
            <div className="w-full max-w-md p-8 space-y-8 bg-gray-800 rounded-lg shadow-lg">
                <h2 className="text-3xl font-extrabold text-center">
                    {isLogin ? 'Login' : 'Criar Nova Conta'}
                </h2>
                <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                    <div className="rounded-md shadow-sm -space-y-px">
                        <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-600 bg-gray-700 placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm rounded-t-md" placeholder="Endereço de email" />
                        <input type="password" value={password} onChange={e => setPassword(e.target.value)} required className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-600 bg-gray-700 placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm rounded-b-md" placeholder="Palavra-passe" />
                    </div>
                    {error && <p className="text-red-400 text-sm text-center">{error}</p>}
                    <button type="submit" disabled={isLoading} className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-500">
                        {isLoading ? <Spinner /> : (isLogin ? 'Entrar' : 'Registar')}
                    </button>
                </form>
                <p className="text-sm text-center text-gray-400">
                    {isLogin ? 'Não tem uma conta?' : 'Já tem uma conta?'}
                    <button onClick={() => { setIsLogin(!isLogin); setError(''); }} className="ml-1 font-medium text-blue-400 hover:text-blue-300">
                        {isLogin ? 'Registe-se' : 'Faça login'}
                    </button>
                </p>
            </div>
        </div>
    );
};


// --- NOVO COMPONENTE: PositionCard ---
const PositionCard = ({ position, markPrice, onClose }) => {
    if (!position) return null;

    const { coin, szi, leverage, returnOnEquity, entryPx } = position.position;
    const isLong = parseFloat(szi) > 0;
    const roePercentage = (parseFloat(returnOnEquity) * 100).toFixed(1);

    return (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 transition-opacity duration-300" onClick={onClose}>
            <div className="bg-gray-900 rounded-2xl shadow-2xl w-full max-w-sm p-6 sm:p-8 border border-gray-700 relative transform transition-all duration-300 scale-95 hover:scale-100" onClick={e => e.stopPropagation()}>
                <div className="relative z-10">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center font-bold text-white text-lg">{coin.charAt(0)}</div>
                            <span className="text-2xl font-bold text-white">{coin}</span>
                        </div>
                        <span className={`px-3 py-1 text-xs font-bold rounded-full ${isLong ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
                            {isLong ? 'LONG' : 'SHORT'} {leverage.value}X
                        </span>
                    </div>

                    <div className="text-center my-10">
                        <p className={`text-6xl font-bold ${roePercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {roePercentage}%
                        </p>
                        <p className="text-sm text-gray-400 mt-1">PNL (ROE %)</p>
                    </div>

                    <div className="flex justify-between text-center border-t border-gray-700 pt-4">
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Preço de Entrada</p>
                            <p className="text-lg font-mono text-white">${parseFloat(entryPx).toFixed(5)}</p>
                        </div>
                    </div>
                </div>
                <button onClick={onClose} className="absolute top-4 right-4 text-gray-500 hover:text-white text-2xl">&times;</button>
            </div>
        </div>
    );
};


// --- Componente de Posições ATUALIZADO ---
const PositionsScreen = () => {
    const [positions, setPositions] = useState([]);
    const [assetData, setAssetData] = useState({ meta: { universe: [] }, contexts: [] });
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedPosition, setSelectedPosition] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            setError('');
            try {
                const [positionsData, metaData] = await Promise.all([
                    api.get('/api/positions'),
                    api.getMeta()
                ]);
                setPositions(positionsData.assetPositions || []);
                setAssetData({ meta: { universe: metaData.universe || [] }, contexts: metaData.contexts || [] });
            } catch (err) {
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, []);

    const getMarkPrice = (coin) => {
        const { meta, contexts } = assetData;
        if (!meta.universe || !contexts) return 'N/A';
        const assetIndex = meta.universe.findIndex(asset => asset.name === coin);
        if (assetIndex !== -1 && contexts[assetIndex]) {
            return contexts[assetIndex].markPx;
        }
        return 'N/A';
    };

    if (isLoading) return <div className="flex justify-center"><Spinner /></div>;
    if (error) return <p className="text-yellow-400 text-center">Não foi possível carregar as posições: {error}. Verifique se a sua carteira está configurada.</p>;
    if (positions.length === 0) return <p className="text-gray-400 text-center">Nenhuma posição aberta encontrada.</p>;

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-4">Posições Abertas</h2>
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-700">
                    <thead className="bg-gray-800">
                        <tr>
                            {['Ativo', 'Tamanho', 'Preço de Entrada', 'Valor', 'PNL (ROE %)'].map(header => (
                                <th key={header} className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">{header}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="bg-gray-900 divide-y divide-gray-700">
                        {positions.map((pos, index) => {
                            const pnl = parseFloat(pos.position.unrealizedPnl);
                            const roe = (parseFloat(pos.position.returnOnEquity) * 100);
                            return (
                                <tr key={index}>
                                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-white">{pos.position.coin}</td>
                                    <td className={`px-4 py-4 whitespace-nowrap text-sm ${parseFloat(pos.position.szi) > 0 ? 'text-green-400' : 'text-red-400'}`}>{pos.position.szi}</td>
                                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-300">${parseFloat(pos.position.entryPx).toFixed(4)}</td>
                                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-300">${parseFloat(pos.position.positionValue).toFixed(2)}</td>
                                    <td className={`px-4 py-4 whitespace-nowrap text-sm font-semibold ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        ${pnl.toFixed(2)} ({roe.toFixed(1)}%)
                                        <button onClick={() => setSelectedPosition(pos)} className="ml-2 inline-block align-middle text-gray-400 hover:text-white">
                                            <LinkIcon className="h-4 w-4" />
                                        </button>
                                    </td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
            {selectedPosition && (
                <PositionCard 
                    position={selectedPosition} 
                    markPrice={getMarkPrice(selectedPosition.position.coin)}
                    onClose={() => setSelectedPosition(null)} 
                />
            )}
        </div>
    );
};


const WalletScreen = () => {
    const [secretKey, setSecretKey] = useState('');
    const [publicAddress, setPublicAddress] = useState('');
    const [showSecret, setShowSecret] = useState(false);
    const [message, setMessage] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        api.get('/api/wallet')
            .then(data => {
                setPublicAddress(data.publicAddress || '');
            })
            .catch(err => console.error("Não foi possível carregar a carteira:", err.message))
            .finally(() => setIsLoading(false));
    }, []);

    const handleSave = async () => {
        setMessage('');
        try {
            await api.post('/api/wallet', { secretKey, publicAddress });
            setMessage('Carteira guardada com sucesso!');
            setSecretKey('');
            setTimeout(() => setMessage(''), 3000);
        } catch (err) {
            setMessage(`Erro: ${err.message}`);
        }
    };

    if (isLoading) return <div className="flex justify-center"><Spinner /></div>;

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-4">Gerir Carteira</h2>
            <div className="bg-gray-800 p-6 rounded-lg space-y-4 max-w-lg mx-auto">
                <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-200 text-xs">
                    <strong>AVISO DE SEGURANÇA:</strong> A sua chave privada é enviada para o seu backend e guardada de forma encriptada. Nunca a partilhe com mais ninguém.
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Endereço Público da Carteira (0x...)</label>
                    <input type="text" value={publicAddress} onChange={(e) => setPublicAddress(e.target.value)} placeholder="O seu endereço público da carteira" className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white" />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Chave Privada (Secret Key)</label>
                    <div className="relative">
                        <input type={showSecret ? "text" : "password"} value={secretKey} onChange={(e) => setSecretKey(e.target.value)} placeholder="Insira a sua chave privada para guardar" className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white pr-10" />
                        <button onClick={() => setShowSecret(!showSecret)} className="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-white">
                            {showSecret ? <EyeOffIcon className="h-5 w-5"/> : <EyeIcon className="h-5 w-5"/>}
                        </button>
                    </div>
                </div>
                <button onClick={handleSave} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md transition duration-300">Guardar Carteira</button>
                {message && <p className="text-green-400 text-sm text-center mt-2">{message}</p>}
            </div>
        </div>
    );
};

// --- Dashboard Screen ---
const DashboardScreen = ({ token }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [assetsPerformance, setAssetsPerformance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState('7d');
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [assetDetails, setAssetDetails] = useState(null);

  const periods = [
    { value: '1d', label: '1 Dia' },
    { value: '7d', label: '7 Dias' },
    { value: '30d', label: '30 Dias' },
    { value: '90d', label: '90 Dias' }
  ];

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [summary, assets] = await Promise.all([
          api.get('/api/dashboard/summary', token),
          api.get('/api/dashboard/assets', token)
        ]);
        setDashboardData(summary);
        setAssetsPerformance(assets);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [token]);

  const fetchAssetDetails = async (asset) => {
    try {
      const details = await api.get(`/api/dashboard/asset/${asset}/performance?period=${selectedPeriod}`, token);
      setAssetDetails(details);
      setSelectedAsset(asset);
    } catch (err) {
      console.error('Error fetching asset details:', err);
    }
  };

  if (loading) return <div className="flex justify-center items-center h-64"><Spinner /></div>;
  if (error) return <div className="text-red-500 text-center p-4">Error: {error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">Dashboard PNL</h2>
      </div>

      {/* Summary Cards */}
      {dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gray-800 p-6 rounded-lg shadow-md border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">PNL Total</p>
                <p className={`text-2xl font-bold ${dashboardData.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  ${dashboardData.total_pnl?.toFixed(2) || '0.00'}
                </p>
              </div>
              {dashboardData.total_pnl >= 0 ? 
                <TrendingUpIcon className="w-8 h-8 text-green-400" /> : 
                <TrendingDownIcon className="w-8 h-8 text-red-400" />
              }
            </div>
          </div>

          <div className="bg-gray-800 p-6 rounded-lg shadow-md border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Total de Trades</p>
                <p className="text-2xl font-bold text-white">{dashboardData.total_trades || 0}</p>
              </div>
              <ChartBarIcon className="w-8 h-8 text-blue-400" />
            </div>
          </div>

          <div className="bg-gray-800 p-6 rounded-lg shadow-md border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Trades Vencedores</p>
                <p className="text-2xl font-bold text-green-400">{dashboardData.winning_trades || 0}</p>
              </div>
              <TrendingUpIcon className="w-8 h-8 text-green-400" />
            </div>
          </div>

          <div className="bg-gray-800 p-6 rounded-lg shadow-md border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-400">Taxa de Sucesso</p>
                <p className="text-2xl font-bold text-blue-400">
                  {dashboardData.total_trades > 0 ? 
                    ((dashboardData.winning_trades / dashboardData.total_trades) * 100).toFixed(1) : '0.0'
                  }%
                </p>
              </div>
              <ChartBarIcon className="w-8 h-8 text-blue-400" />
            </div>
          </div>
        </div>
      )}

      {/* Assets Performance */}
      <div className="bg-gray-800 rounded-lg shadow-md border border-gray-700">
        <div className="p-6 border-b border-gray-700">
          <h3 className="text-lg font-semibold text-white">Performance por Ativo</h3>
        </div>
        <div className="p-6">
          {assetsPerformance.length === 0 ? (
            <div className="text-center text-gray-400 py-8">
              <p>Nenhum dado de performance encontrado.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-3 px-4 font-medium text-gray-400">Ativo</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-400">PNL</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-400">Trades</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-400">Taxa Sucesso</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-400">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {assetsPerformance.map((asset, index) => (
                    <tr key={index} className="border-b border-gray-600 hover:bg-gray-700">
                      <td className="py-3 px-4 font-medium text-white">{asset.asset}</td>
                      <td className={`py-3 px-4 font-medium ${asset.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${asset.total_pnl?.toFixed(2) || '0.00'}
                      </td>
                      <td className="py-3 px-4 text-gray-300">{asset.total_trades || 0}</td>
                      <td className="py-3 px-4 text-gray-300">
                        {asset.total_trades > 0 ? 
                          ((asset.winning_trades / asset.total_trades) * 100).toFixed(1) : '0.0'
                        }%
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => fetchAssetDetails(asset.asset)}
                          className="text-blue-400 hover:text-blue-300 font-medium"
                        >
                          Ver Detalhes
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Asset Details Modal */}
      {selectedAsset && assetDetails && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-gray-700">
            <div className="p-6 border-b border-gray-700">
              <div className="flex justify-between items-center">
                <h3 className="text-xl font-semibold text-white">
                  Detalhes de Performance - {selectedAsset}
                </h3>
                <button
                  onClick={() => setSelectedAsset(null)}
                  className="text-gray-400 hover:text-white"
                >
                  <XIcon className="w-6 h-6" />
                </button>
              </div>
              <div className="mt-4 flex space-x-2">
                {periods.map(period => (
                  <button
                    key={period.value}
                    onClick={() => setSelectedPeriod(period.value)}
                    className={`px-3 py-1 rounded-md text-sm font-medium ${
                      selectedPeriod === period.value
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {period.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-700 p-4 rounded-lg">
                  <p className="text-sm font-medium text-gray-400">PNL Total</p>
                  <p className={`text-xl font-bold ${assetDetails.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${assetDetails.total_pnl?.toFixed(2) || '0.00'}
                  </p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <p className="text-sm font-medium text-gray-400">Total de Trades</p>
                  <p className="text-xl font-bold text-white">{assetDetails.total_trades || 0}</p>
                </div>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <p className="text-sm font-medium text-gray-400">Taxa de Sucesso</p>
                  <p className="text-xl font-bold text-blue-400">
                    {assetDetails.total_trades > 0 ? 
                      ((assetDetails.winning_trades / assetDetails.total_trades) * 100).toFixed(1) : '0.0'
                    }%
                  </p>
                </div>
              </div>
              
              {assetDetails.recent_trades && assetDetails.recent_trades.length > 0 && (
                <div>
                  <h4 className="text-lg font-medium text-white mb-4">Trades Recentes</h4>
                  <div className="overflow-x-auto">
                    <table className="min-w-full">
                      <thead>
                        <tr className="border-b border-gray-600">
                          <th className="text-left py-2 px-3 text-sm font-medium text-gray-400">Data</th>
                          <th className="text-left py-2 px-3 text-sm font-medium text-gray-400">Tipo</th>
                          <th className="text-left py-2 px-3 text-sm font-medium text-gray-400">Lado</th>
                          <th className="text-left py-2 px-3 text-sm font-medium text-gray-400">Quantidade</th>
                          <th className="text-left py-2 px-3 text-sm font-medium text-gray-400">Preço</th>
                          <th className="text-left py-2 px-3 text-sm font-medium text-gray-400">PNL</th>
                        </tr>
                      </thead>
                      <tbody>
                        {assetDetails.recent_trades.map((trade, index) => (
                          <tr key={index} className="border-b border-gray-700">
                            <td className="py-2 px-3 text-sm text-gray-300">
                              {new Date(trade.timestamp).toLocaleDateString('pt-BR')}
                            </td>
                            <td className="py-2 px-3 text-sm text-gray-300">{trade.trade_type}</td>
                            <td className="py-2 px-3 text-sm">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                trade.side === 'buy' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
                              }`}>
                                {trade.side === 'buy' ? 'Compra' : 'Venda'}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-sm text-gray-300">{trade.quantity}</td>
                            <td className="py-2 px-3 text-sm text-gray-300">${trade.price?.toFixed(2) || '0.00'}</td>
                            <td className={`py-2 px-3 text-sm font-medium ${
                              trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                            }`}>
                              ${trade.pnl?.toFixed(2) || '0.00'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const WebhookList = ({ configs, onDelete, user }) => {
    const [expandedItems, setExpandedItems] = useState(new Set());
    const [copiedItem, setCopiedItem] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');

    const toggleExpanded = (configId) => {
        const newExpanded = new Set(expandedItems);
        if (newExpanded.has(configId)) {
            newExpanded.delete(configId);
        } else {
            newExpanded.add(configId);
        }
        setExpandedItems(newExpanded);
    };

    const filteredConfigs = configs.filter(config => 
        config.assetName.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const copyPayload = async (config) => {
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
            "user_uuid": user.uuid,
            "secret": user.webhook_secret
        };

        try {
            await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
            setCopiedItem(config.id);
            setTimeout(() => setCopiedItem(null), 2000);
        } catch (err) {
            console.error('Erro ao copiar:', err);
        }
    };

    return (
        <div className="space-y-4">
            <div className="mb-4">
                <input
                    type="text"
                    placeholder="Pesquisar webhooks por ativo..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full p-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                />
            </div>
            
            {filteredConfigs.length === 0 && searchTerm && (
                <div className="text-center py-8 text-gray-400">
                    Nenhum webhook encontrado para "{searchTerm}"
                </div>
            )}
            
            {filteredConfigs.length === 0 && !searchTerm && configs.length > 0 && (
                <div className="text-center py-8 text-gray-400">
                    Digite algo para pesquisar seus webhooks
                </div>
            )}
            
            <div className="space-y-3">
                {filteredConfigs.map(config => {
                const isExpanded = expandedItems.has(config.id);
                const isCopied = copiedItem === config.id;
                
                return (
                    <div key={config.id} className="bg-gray-800 rounded-lg border border-gray-700">
                        {/* Header da linha */}
                        <div className="p-4 flex items-center justify-between">
                            <div className="flex items-center space-x-4">
                                <button
                                    onClick={() => toggleExpanded(config.id)}
                                    className="text-gray-400 hover:text-white transition-colors"
                                >
                                    {isExpanded ? (
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    ) : (
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                        </svg>
                                    )}
                                </button>
                                
                                <div>
                                    <h4 className="font-bold text-lg text-green-400">{config.assetName}</h4>
                                    {config.hyperliquidSymbol && (
                                        <div className="text-xs text-blue-400 mb-1">
                                            🔄 Webhook Received: {config.hyperliquidSymbol}
                                        </div>
                                    )}
                                    <div className="flex gap-4 text-sm text-gray-300">
                                        <span>💰 ${config.maxUsdValue}</span>
                                        <span>⚡ {config.leverage || 1}x</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div className="flex items-center space-x-3">
                                <span className={`px-2 py-1 text-xs rounded-full font-bold ${config.isLiveTrading ? 'bg-red-500/20 text-red-300' : 'bg-blue-500/20 text-blue-300'}`}>
                                    {config.isLiveTrading ? '🚀 REAL' : '🔄 SIM'}
                                </span>
                                
                                <button
                                    onClick={() => copyPayload(config)}
                                    className={`px-3 py-1 text-xs rounded-md transition-colors ${
                                        isCopied 
                                            ? 'bg-green-600 text-white' 
                                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                                    }`}
                                >
                                    {isCopied ? '✓ Copiado!' : '📋 Copiar Payload'}
                                </button>
                                
                                <button
                                    onClick={() => onDelete(config.id)}
                                    className="text-red-400 hover:text-red-200 p-1"
                                    title="Deletar webhook"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                        
                        {/* Detalhes expandidos */}
                        {isExpanded && (
                            <div className="px-4 pb-4 border-t border-gray-700">
                                {config.isLiveTrading && (
                                    <div className="mt-3 p-3 bg-red-900/20 border border-red-700 rounded text-red-200 text-xs">
                                        ⚠️ <strong>ATENÇÃO:</strong> Este webhook executará ordens reais com dinheiro real!
                                    </div>
                                )}
                                
                                <div className="mt-4 space-y-4">
                                    <div>
                                        <p className="text-sm text-gray-300 mb-2">🔗 URL do Webhook (Genérica):</p>
                                        <div className="bg-gray-900 p-3 rounded-md">
                                            <code className="text-xs text-yellow-300 break-all">
                                                {`${API_BASE_URL}/v1/webhook`}
                                            </code>
                                            <button
                                                onClick={() => navigator.clipboard.writeText(`${API_BASE_URL}/v1/webhook`)}
                                                className="ml-2 text-blue-400 hover:text-blue-300 text-xs"
                                            >
                                                📋
                                            </button>
                                        </div>
                                        <p className="text-xs text-blue-400 mt-1">
                                            ✨ <strong>Novo:</strong> Uma URL única para todos os ativos! O ativo é determinado automaticamente pelo campo 'symbol' no payload.
                                        </p>
                                    </div>
                                    
                                    <div>
                                        <div className="flex items-center justify-between mb-2">
                                            <p className="text-sm text-gray-300">📋 Payload do TradingView:</p>
                                            <button
                                                onClick={() => copyPayload(config)}
                                                className={`px-2 py-1 text-xs rounded transition-colors ${
                                                    isCopied 
                                                        ? 'bg-green-600 text-white' 
                                                        : 'bg-gray-600 hover:bg-gray-500 text-white'
                                                }`}
                                            >
                                                {isCopied ? '✓ Copiado!' : '📋 Copiar'}
                                            </button>
                                        </div>
                                        <pre className="bg-gray-900 p-3 rounded-md text-xs text-yellow-300 overflow-x-auto max-h-64">
                                            <code>{JSON.stringify({
                                                "data": {
                                                    "action": "{{strategy.order.action}}",
                                                    "contracts": "{{strategy.order.contracts}}",
                                                    "position_size": "{{strategy.position_size}}"
                                                },
                                                "price": "{{close}}",
                                                "user_info": "STRATEGY_{{ticker}}_{{strategy.order.id}}",
                                                "symbol": "{{ticker}}",
                                                "time": "{{timenow}}",
                                                "user_uuid": user.uuid,
                                                "secret": user.webhook_secret
                                            }, null, 2)}</code>
                                        </pre>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                );
                })}
            </div>
        </div>
    );
};

const WebhookScreen = ({ user }) => {
    const [configs, setConfigs] = useState([]);
    const [universe, setUniverse] = useState([]);
    const [newConfig, setNewConfig] = useState({ assetName: '', hyperliquidSymbol: null, maxUsdValue: '50', leverage: 1, isLiveTrading: false });
    const [isLoading, setIsLoading] = useState(true);
    
    const fetchWebhooks = useCallback(async () => {
        try {
            const data = await api.get('/api/webhooks');
            setConfigs(data);
        } catch (error) {
            console.error("Erro ao carregar webhooks:", error);
        }
    }, []);
    
    useEffect(() => {
        async function loadData() {
            setIsLoading(true);
            await fetchWebhooks();
            try {
                const meta = await api.getMeta();
                setUniverse(meta.universe || []);
                if (meta.universe.length > 0) {
                    setNewConfig(prev => ({ ...prev, assetName: meta.universe[0].name }));
                }
            } catch (error) {
                console.error("Erro ao carregar metadados:", error);
            }
            setIsLoading(false);
        }
        loadData();
    }, [fetchWebhooks]);

    const handleAddConfig = async () => {
        if (newConfig.maxUsdValue && parseFloat(newConfig.maxUsdValue) > 0 && newConfig.assetName) {
            if (configs.find(c => c.assetName === newConfig.assetName)) {
                alert("Este ativo já foi configurado.");
                return;
            }
            try {
                await api.post('/api/webhooks', newConfig);
                await fetchWebhooks();
                // Reset form
                setNewConfig({ assetName: universe[0]?.name || '', hyperliquidSymbol: null, maxUsdValue: '50', leverage: 1, isLiveTrading: false });
            } catch (error) {
                alert(`Erro ao criar webhook: ${error.message}`);
            }
        }
    };
    
    const handleDeleteConfig = async (id) => {
        if (window.confirm("Tem a certeza que quer apagar este webhook?")) {
            try {
                await api.delete(`/api/webhooks/${id}`);
                await fetchWebhooks();
            } catch (error) {
                alert(`Erro ao apagar webhook: ${error.message}`);
            }
        }
    };


    
    if (isLoading || !user) return <div className="flex justify-center"><Spinner /></div>;

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6">Gerir Webhooks de Automação</h2>
            
            <div className="mb-8 p-4 bg-blue-900/20 border border-blue-700 rounded-lg">
                <h3 className="text-lg font-semibold text-blue-300 mb-2">💡 Como Funciona</h3>
                <p className="text-blue-200 text-sm mb-3">
                    <strong>🆕 Webhook:</strong> Configure os ativos que deseja negociar e use uma única URL no TradingView. 
                    O sistema detecta automaticamente o ativo através do campo 'symbol' e aplica as configurações específicas 
                    (leverage, valor máximo, modo real/simulação).
                </p>
                <div className="bg-yellow-900/20 border border-yellow-700 rounded p-3">
                    <p className="text-yellow-200 text-sm">
                        🔄 <strong>Modo Simulação:</strong> Ordens são apenas simuladas (seguro para testes)<br/>
                        🚀 <strong>Modo Real:</strong> Ordens são executadas de verdade na Hyperliquid (usa dinheiro real!)
                    </p>
                </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-8">
                <h3 className="text-xl font-semibold mb-4 text-white">Registar Novo Ativo</h3>
                <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1">Ativo</label>
                                <select 
                                    value={newConfig.assetName} 
                                    onChange={(e) => setNewConfig({...newConfig, assetName: e.target.value})} 
                                    className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white"
                                >
                                    {universe.map((asset, index) => (
                                        <option key={index} value={asset.name}>{asset.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1">Leverage</label>
                                <select 
                                    value={newConfig.leverage} 
                                    onChange={(e) => setNewConfig({...newConfig, leverage: parseInt(e.target.value)})}
                                    className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white"
                                >
                                    {[1, 2, 3, 5, 10, 20, 25, 50].map(lev => (
                                        <option key={lev} value={lev}>{lev}x</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1">Símbolo do TradingView (Opcional)</label>
                            <input 
                                type="text" 
                                value={newConfig.hyperliquidSymbol || ''} 
                                onChange={(e) => setNewConfig({...newConfig, hyperliquidSymbol: e.target.value || null})} 
                                placeholder={newConfig.assetName ? `Ex: PEPE (deixe vazio se TradingView envia ${newConfig.assetName})` : 'Ex: PEPE'}
                                className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white" 
                            />
                            <p className="text-xs text-gray-400 mt-1">Ex: Se você selecionar "kPEPE" acima mas o TradingView envia "PEPE", digite "PEPE" aqui</p>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-1">Valor Máximo por Operação (USD)</label>
                            <input 
                                type="number" 
                                value={newConfig.maxUsdValue} 
                                onChange={(e) => setNewConfig({...newConfig, maxUsdValue: e.target.value})} 
                                placeholder="50" 
                                className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white" 
                            />
                            <p className="text-xs text-gray-400 mt-1">Usado apenas como fallback se o TradingView não enviar o tamanho da posição</p>
                        </div>
                        
                        <div className="bg-red-900/20 border border-red-700 rounded-lg p-3">
                            <div className="flex items-center space-x-3">
                                <input 
                                    type="checkbox" 
                                    id="liveTrading"
                                    checked={newConfig.isLiveTrading} 
                                    onChange={(e) => setNewConfig({...newConfig, isLiveTrading: e.target.checked})}
                                    className="w-4 h-4"
                                />
                                <label htmlFor="liveTrading" className="text-sm font-medium text-red-300">
                                    🚀 Ativar Trading Real (CUIDADO!)
                                </label>
                            </div>
                            <p className="text-xs text-red-400 mt-2">
                                ⚠️ Se ativado, as ordens serão executadas de verdade na Hyperliquid com dinheiro real!
                            </p>
                        </div>
                    <button 
                        onClick={handleAddConfig} 
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-md transition duration-300"
                    >
                        Adicionar Webhook
                    </button>
                </div>
            </div>

            {configs.length > 0 && (
                <div className="mb-8">
                    <h3 className="text-xl font-semibold mb-4 text-white">Os seus Webhooks Ativos</h3>
                    <WebhookList configs={configs} onDelete={handleDeleteConfig} user={user} />
                </div>
            )}
            
            {configs.length === 0 && (
                <div className="bg-gray-800 p-6 rounded-lg text-center mb-8">
                    <p className="text-gray-400">Nenhum webhook configurado.</p>
                    <p className="text-sm text-gray-500 mt-2">Configure um ativo para começar a receber sinais do TradingView.</p>
                </div>
            )}

            {user && (
                <div className="mt-8 p-4 bg-yellow-900/20 border border-yellow-700 rounded-lg">
                    <h4 className="text-yellow-300 font-semibold mb-2">🔐 Dados da sua Conta</h4>
                    <div className="text-sm text-yellow-200 space-y-1">
                        <p><strong>UUID:</strong> <code className="bg-gray-800 px-2 py-1 rounded">{user.uuid}</code></p>
                        <p><strong>Webhook Secret:</strong> <code className="bg-gray-800 px-2 py-1 rounded">{user.webhook_secret}</code></p>
                        <p className="text-xs text-yellow-400 mt-2">⚠️ Mantenha estes dados seguros! São necessários para autenticar os webhooks.</p>
                    </div>
                </div>
            )}
        </div>
    );
};

const LogsScreen = ({ user }) => {
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedLog, setSelectedLog] = useState(null);

    useEffect(() => {
        const fetchLogs = async () => {
            setIsLoading(true);
            try {
                const data = await api.get('/api/webhooks/logs');
                setLogs(data);
            } catch (error) {
                console.error("Erro ao carregar logs:", error);
            } finally {
                setIsLoading(false);
            }
        };

        if (user) {
            fetchLogs();
        }
    }, [user]);

    const formatTimestamp = (timestamp) => {
        return new Date(timestamp).toLocaleString('pt-BR');
    };

    const getStatusColor = (status, isSuccess) => {
        if (!isSuccess) return 'text-red-400';
        if (status >= 200 && status < 300) return 'text-green-400';
        if (status >= 400) return 'text-red-400';
        return 'text-yellow-400';
    };

    const getStatusIcon = (isSuccess) => {
        return isSuccess ? '✅' : '❌';
    };

    const extractAssetFromUrl = (url) => {
        // Extrai o nome do ativo da URL: /webhook/trigger/{uuid}/{asset_name}
        const parts = url.split('/');
        return parts[parts.length - 1] || 'N/A';
    };

    if (isLoading) return <div className="flex justify-center"><Spinner /></div>;

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6">Logs de Auditoria dos Webhooks</h2>
            
            <div className="mb-4 p-4 bg-blue-900/20 border border-blue-700 rounded-lg">
                <h3 className="text-lg font-semibold text-blue-300 mb-2">📊 Sobre os Logs</h3>
                <p className="text-blue-200 text-sm">
                    Aqui você pode acompanhar todas as chamadas feitas aos seus webhooks, incluindo payloads recebidos, 
                    status de resposta e possíveis erros. Útil para debugging e auditoria das operações.
                </p>
            </div>

            {logs.length === 0 ? (
                <div className="bg-gray-800 p-6 rounded-lg text-center">
                    <p className="text-gray-400">Nenhum log de webhook encontrado.</p>
                    <p className="text-sm text-gray-500 mt-2">Os logs aparecerão aqui assim que o TradingView fizer chamadas aos seus webhooks.</p>
                </div>
            ) : (
                <div className="bg-gray-800 rounded-lg overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-700">
                            <thead className="bg-gray-900">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Status</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Timestamp</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Ativo</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Método</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Código</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Erro</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Ações</th>
                                </tr>
                            </thead>
                            <tbody className="bg-gray-800 divide-y divide-gray-700">
                                {logs.map((log, index) => (
                                    <tr key={log.id} className="hover:bg-gray-700 transition-colors">
                                        <td className="px-4 py-4 whitespace-nowrap text-sm">
                                            <span className="text-lg">{getStatusIcon(log.is_success)}</span>
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-300">
                                            {formatTimestamp(log.timestamp)}
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap text-sm text-yellow-400 font-semibold">
                                            {extractAssetFromUrl(log.request_url)}
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap text-sm text-white font-mono">
                                            {log.request_method}
                                        </td>
                                        <td className={`px-4 py-4 whitespace-nowrap text-sm font-mono ${getStatusColor(log.response_status, log.is_success)}`}>
                                            {log.response_status}
                                        </td>
                                        <td className="px-4 py-4 text-sm text-red-400 max-w-xs truncate">
                                            {log.error_message || '-'}
                                        </td>
                                        <td className="px-4 py-4 whitespace-nowrap text-sm">
                                            <button 
                                                onClick={() => setSelectedLog(log)}
                                                className="text-blue-400 hover:text-blue-300 text-sm"
                                            >
                                                Ver Detalhes
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Modal de Detalhes do Log */}
            {selectedLog && (
                <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50" onClick={() => setSelectedLog(null)}>
                    <div className="bg-gray-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 m-4" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-white">Detalhes do Log #{selectedLog.id}</h3>
                            <button 
                                onClick={() => setSelectedLog(null)}
                                className="text-gray-400 hover:text-white text-2xl"
                            >
                                &times;
                            </button>
                        </div>
                        
                        <div className="space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">Status</label>
                                    <p className="text-lg">{getStatusIcon(selectedLog.is_success)} {selectedLog.is_success ? 'Sucesso' : 'Erro'}</p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">Código HTTP</label>
                                    <p className={`text-lg font-mono ${getStatusColor(selectedLog.response_status, selectedLog.is_success)}`}>
                                        {selectedLog.response_status}
                                    </p>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1">Timestamp</label>
                                <p className="text-white font-mono">{formatTimestamp(selectedLog.timestamp)}</p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1">URL Chamada</label>
                                <p className="text-white font-mono text-sm break-all bg-gray-800 p-2 rounded">{selectedLog.request_url}</p>
                            </div>

                            {selectedLog.error_message && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">Mensagem de Erro</label>
                                    <p className="text-red-400 bg-red-900/20 p-2 rounded">{selectedLog.error_message}</p>
                                </div>
                            )}

                            {/* Headers da Requisição */}
                            {selectedLog.request_headers && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">📥 Headers da Requisição</label>
                                    <pre className="bg-gray-800 p-3 rounded text-xs text-green-300 overflow-x-auto max-h-32">
                                        {JSON.stringify(JSON.parse(selectedLog.request_headers), null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* Payload da Requisição (TradingView) */}
                            {selectedLog.request_body && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">📤 Payload do TradingView</label>
                                    <pre className="bg-gray-800 p-3 rounded text-xs text-yellow-300 overflow-x-auto max-h-40">
                                        {(() => {
                                            try {
                                                return JSON.stringify(JSON.parse(selectedLog.request_body), null, 2);
                                            } catch {
                                                return selectedLog.request_body;
                                            }
                                        })()}
                                    </pre>
                                </div>
                            )}

                            {/* Headers da Resposta */}
                            {selectedLog.response_headers && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">📤 Headers da Resposta</label>
                                    <pre className="bg-gray-800 p-3 rounded text-xs text-blue-300 overflow-x-auto max-h-32">
                                        {JSON.stringify(JSON.parse(selectedLog.response_headers), null, 2)}
                                    </pre>
                                </div>
                            )}

                            {/* Resposta do Servidor */}
                            {selectedLog.response_body && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-1">📥 Resposta do Servidor</label>
                                    <pre className={`bg-gray-800 p-3 rounded text-xs overflow-x-auto max-h-40 ${selectedLog.is_success ? 'text-green-300' : 'text-red-300'}`}>
                                        {(() => {
                                            try {
                                                return JSON.stringify(JSON.parse(selectedLog.response_body), null, 2);
                                            } catch {
                                                return selectedLog.response_body;
                                            }
                                        })()}
                                    </pre>
                                </div>
                            )}

                            <div className="mt-6 p-3 bg-blue-900/20 border border-blue-700 rounded">
                                <p className="text-blue-200 text-sm">
                                    💡 <strong>Dica:</strong> Use essas informações para debug da integração com TradingView. 
                                    Verifique se o payload está sendo enviado corretamente e se as respostas estão conforme esperado.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};


// --- Componente Principal da Aplicação ---
const App = () => {
    const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('jwt_token'));
    const [activeScreen, setActiveScreen] = useState('positions');
    const [user, setUser] = useState(null);

    useEffect(() => {
        const fetchUser = async () => {
            const token = localStorage.getItem('jwt_token');
            if (token) {
                try {
                    const userData = await api.get('/api/me');
                    setUser(userData);
                    setIsAuthenticated(true);
                } catch (e) {
                    console.error("Sessão inválida:", e);
                    handleLogout();
                }
            }
        };
        if (isAuthenticated) {
            fetchUser();
        }
    }, [isAuthenticated]);

    const handleLogin = (status) => {
        if (status) {
            setIsAuthenticated(true);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('jwt_token');
        setIsAuthenticated(false);
        setUser(null);
    };

    if (!isAuthenticated) {
        return <AuthScreen onLogin={handleLogin} />;
    }

    const NavButton = ({ screenName, label }) => (
        <button
            onClick={() => setActiveScreen(screenName)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${activeScreen === screenName ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-700'}`}
        >
            {label}
        </button>
    );

    const renderScreen = () => {
        if (!user && activeScreen !== 'wallet') {
             return <div className="flex justify-center mt-10"><Spinner /></div>;
        }
        switch (activeScreen) {
            case 'positions': return <PositionsScreen />;
            case 'dashboard': return <DashboardScreen token={localStorage.getItem('jwt_token')} />;
            case 'wallet': return <WalletScreen />;
            case 'webhooks': return <WebhookScreen user={user} />;
            case 'logs': return <LogsScreen user={user} />;
            default: return <PositionsScreen />;
        }
    };

    return (
        <div className="bg-gray-900 text-white min-h-screen font-sans">
            <header className="bg-gray-800 shadow-md">
                <nav className="container mx-auto px-6 py-3 flex justify-between items-center">
                    <h1 className="text-xl font-bold text-white">Dashboard Hyperliquid</h1>
                    <div className="flex items-center space-x-2">
                        <NavButton screenName="positions" label="Posições" />
                        <NavButton screenName="dashboard" label="Dashboard PNL" />
                        <NavButton screenName="webhooks" label="Webhooks" />
                        <NavButton screenName="wallet" label="Carteira" />
                        <NavButton screenName="logs" label="Logs" />
                        <button onClick={handleLogout} className="ml-4 text-red-400 hover:text-red-300 text-sm font-medium">Sair</button>
                    </div>
                </nav>
            </header>
            <main className="container mx-auto p-6">
                {renderScreen()}
            </main>
        </div>
    );
};

export default App;
