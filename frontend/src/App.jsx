import React, { useState } from 'react';
import Login from './Login';
import Dashboard from './Dashboard';
import './index.css';

import { Toaster } from 'react-hot-toast';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [message, setMessage] = useState('');

  const handleLogin = (msg) => {
    setIsLoggedIn(true);
    setMessage(msg);
  };

  return (
    <div className="app-container">
      <Toaster position="bottom-right" />
      {!isLoggedIn ? (
        <Login onLogin={handleLogin} />
      ) : (
        <Dashboard />
      )}
    </div>
  );
}

export default App;
