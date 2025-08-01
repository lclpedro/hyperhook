import React, { useState, useEffect } from 'react';
import { api } from './services';
import { Header } from './components/layout';
import { 
  AuthPage, 
  PositionsPage, 
  WalletPage, 
  DashboardPage, 
  WebhookPage, 
  LogsPage 
} from './pages';

// --- Componente Principal ---
function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeScreen, setActiveScreen] = useState('Positions');

  useEffect(() => {
    const token = localStorage.getItem('jwt_token');
    if (token) {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('jwt_token');
    setIsAuthenticated(false);
    setActiveScreen('Positions');
  };

  if (!isAuthenticated) {
    return <AuthPage onLogin={setIsAuthenticated} />;
  }

  const renderScreen = () => {
    switch (activeScreen) {
      case 'Positions':
        return <PositionsPage />;
      case 'Dashboard':
        return <DashboardPage />;
      case 'Webhooks':
        return <WebhookPage />;
      case 'Wallet':
        return <WalletPage />;
      case 'Logs':
        return <LogsPage />;
      default:
        return <PositionsPage />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header 
        activeScreen={activeScreen} 
        setActiveScreen={setActiveScreen} 
        onLogout={handleLogout} 
      />
      {renderScreen()}
    </div>
  );
}

export default App;
