import React, { useState, useEffect } from 'react';
import Login from './Login';
import AucSimActions from './AucSimActions';
import './styles.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userType, setUserType] = useState(null);
  const [username, setUsername] = useState(null);

  const handleAuthenticationSuccess = (user) => {
    setIsAuthenticated(true);
    setUserType(localStorage.getItem('userType'));
    setUsername(user);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('date_expires');
    localStorage.removeItem('userType');
    localStorage.removeItem('username');
    setIsAuthenticated(false);
    setUserType(null);
    setUsername(null);
  };

  const checkAuthentication = () => {
    const expirationDate = localStorage.getItem('date_expires');
    const storedUserType = localStorage.getItem('userType');
    const storedUsername = localStorage.getItem('username');
    const currentDate = new Date();

    if (!expirationDate || new Date(expirationDate) < currentDate) {
      localStorage.clear();
      setIsAuthenticated(false);
      setUserType(null);
      setUsername(null);
    } else {
      setIsAuthenticated(true);
      setUserType(storedUserType);
      setUsername(storedUsername);
    }
  };

  useEffect(() => {
    checkAuthentication();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') checkAuthentication();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    const intervalId = setInterval(checkAuthentication, 5 * 60 * 1000);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return (
    <div className="App">
      {isAuthenticated ? (
        <AucSimActions
          onLogout={handleLogout}
          userType={userType}
          username={username}
        />
      ) : (
        <Login onAuthSuccess={handleAuthenticationSuccess} />
      )}
    </div>
  );
}

export default App;
