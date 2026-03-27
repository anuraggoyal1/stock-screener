import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Toast, { useToast } from './components/Toast';
import MasterList from './pages/MasterList';
import Screener from './pages/Screener';
import Positions from './pages/Positions';
import TradeLog from './pages/TradeLog';
import UpstoxToken from './pages/UpstoxToken';
import Backtest from './pages/Backtest';
import Login from './pages/Login';

function App() {
  const { toasts, addToast, removeToast } = useToast();
  const [isAuth, setIsAuth] = useState(!!localStorage.getItem('X-API-Key'));

  if (!isAuth) {
    return (
      <div className="app-layout">
        <Login setAuth={setIsAuth} />
        <Toast toasts={toasts} removeToast={removeToast} />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="app-layout">
        <Navbar />
        <main className="app-content">
          <Routes>
            <Route path="/" element={<MasterList addToast={addToast} />} />
            <Route path="/screener" element={<Screener addToast={addToast} />} />
            <Route path="/positions" element={<Positions addToast={addToast} />} />
            <Route path="/tradelog" element={<TradeLog addToast={addToast} />} />
            <Route path="/backtest" element={<Backtest addToast={addToast} />} />
            <Route path="/upstox" element={<UpstoxToken addToast={addToast} />} />
          </Routes>
        </main>
        <Toast toasts={toasts} removeToast={removeToast} />
      </div>
    </BrowserRouter>
  );
}

export default App;
