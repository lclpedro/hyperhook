import React from 'react';
import './Header.css';

const Header = ({ activeScreen, setActiveScreen, onLogout }) => {
  const menuItems = [
    { key: 'Positions', label: 'Positions' },
    { key: 'Dashboard', label: 'Dashboard' },
    { key: 'Webhooks', label: 'Webhooks' },
    { key: 'Wallet', label: 'Wallet' },
    { key: 'Logs', label: 'Logs' }
  ];

  return (
    <header className="header">
      <div className="header-content">
        <h1 className="header-title">HyperHook</h1>
        <nav className="header-nav">
          {menuItems.map((item) => (
            <button
              key={item.key}
              className={`nav-button ${
                activeScreen === item.key ? 'nav-button-active' : ''
              }`}
              onClick={() => setActiveScreen(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <button className="logout-button" onClick={onLogout}>
          Logout
        </button>
      </div>
    </header>
  );
};

export default Header;