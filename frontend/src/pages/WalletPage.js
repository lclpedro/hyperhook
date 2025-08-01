import React, { useState, useEffect } from 'react';
import { api } from '../services';

const WalletPage = () => {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [publicAddress, setPublicAddress] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  useEffect(() => {
    fetchWallet();
  }, []);

  const fetchWallet = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/wallet');
      setWallet(response.data);
    } catch (err) {
      if (err.response?.status !== 404) {
        setError('Failed to fetch wallet');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAddWallet = async (e) => {
    e.preventDefault();
    try {
      setIsAdding(true);
      await api.post('/api/wallet', {
        secretKey,
        publicAddress
      });
      setSecretKey('');
      setPublicAddress('');
      fetchWallet();
    } catch (err) {
      setError('Failed to add wallet');
    } finally {
      setIsAdding(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-white">Loading wallet...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-white mb-6">Wallet</h1>
      
      {error && (
        <div className="text-red-400 mb-4">{error}</div>
      )}
      
      {wallet ? (
        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibold text-white mb-4">Connected Wallet</h2>
          <div className="space-y-2">
            <div>
              <span className="text-gray-400">Public Address:</span>
              <p className="text-white font-mono">{wallet.publicAddress}</p>
            </div>
            <div>
              <span className="text-gray-400">Status:</span>
              <span className="text-green-400 ml-2">Connected</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded-lg">
          <h2 className="text-xl font-semibold text-white mb-4">Add Wallet</h2>
          <form onSubmit={handleAddWallet} className="space-y-4">
            <div>
              <label className="block text-gray-400 mb-2">Secret Key</label>
              <input
                type="password"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-gray-400 mb-2">Public Address</label>
              <input
                type="text"
                value={publicAddress}
                onChange={(e) => setPublicAddress(e.target.value)}
                className="w-full p-3 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
            <button
              type="submit"
              disabled={isAdding}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
            >
              {isAdding ? 'Adding...' : 'Add Wallet'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default WalletPage;