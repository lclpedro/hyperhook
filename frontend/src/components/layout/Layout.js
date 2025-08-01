import React from 'react';
import './Layout.css';

const Layout = ({ children }) => {
  return (
    <div className="layout">
      <header className="layout-header">
        <h1>HyperHook</h1>
        <nav>
          <a href="/positions">Positions</a>
          <a href="/dashboard">Dashboard</a>
          <a href="/webhooks">Webhooks</a>
          <a href="/wallet">Wallet</a>
          <a href="/logs">Logs</a>
        </nav>
      </header>
      <main className="layout-main">
        {children}
      </main>
    </div>
  );
};

export default Layout;