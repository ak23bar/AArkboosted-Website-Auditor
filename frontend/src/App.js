import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

// Components
import Dashboard from './components/Dashboard';
import AuditForm from './components/AuditForm';
import AuditResults from './components/AuditResults';
import Login from './components/Login';

// Styles
import './styles/tailwind.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);

  const handleLogin = (username, password) => {
    if (username === 'admin' && password === 'ArkBoosted2024!') {
      setIsAuthenticated(true);
    } else {
      alert('Invalid credentials');
    }
  };

  return (
    <Router>
      <div className="App">
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
            },
            error: {
              duration: 4000,
            },
          }}
        />
        {!isAuthenticated ? (
          <Login onLogin={handleLogin} />
        ) : (
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new-audit" element={<AuditForm />} />
            <Route path="/audit/:id" element={<AuditResults />} />
          </Routes>
        )}
      </div>
    </Router>
  );
}

export default App;