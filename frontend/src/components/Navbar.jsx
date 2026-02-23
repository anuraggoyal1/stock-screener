import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const tabs = [
    { path: '/', label: 'Master Watchlist', icon: '📋' },
    { path: '/screener', label: 'Screener', icon: '🔍' },
    { path: '/positions', label: 'Positions', icon: '💼' },
    { path: '/tradelog', label: 'Trade Log', icon: '📊' },
    { path: '/upstox', label: 'Upstox Token', icon: '🔑' },
];

const THEME_STORAGE_KEY = 'stockscreener-theme';

export default function Navbar() {
    const location = useLocation();
    const navigate = useNavigate();
    const [theme, setTheme] = useState('dark');

    useEffect(() => {
        const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
        const prefersLight =
            window.matchMedia &&
            window.matchMedia('(prefers-color-scheme: light)').matches;
        const initial = stored || (prefersLight ? 'light' : 'dark');
        setTheme(initial);
        document.documentElement.setAttribute('data-theme', initial);
    }, []);

    const toggleTheme = () => {
        const next = theme === 'dark' ? 'light' : 'dark';
        setTheme(next);
        document.documentElement.setAttribute('data-theme', next);
        window.localStorage.setItem(THEME_STORAGE_KEY, next);
    };

    const isLight = theme === 'light';

    return (
        <nav className="navbar">
            <div className="navbar-inner">
                <div className="navbar-logo">
                    <span className="logo-icon">📈</span>
                    <span>
                        Stock<span className="logo-accent">Screener</span>
                    </span>
                </div>
                <div className="navbar-tabs">
                    {tabs.map((tab) => (
                        <button
                            key={tab.path}
                            className={`nav-tab ${location.pathname === tab.path ? 'active' : ''}`}
                            onClick={() => navigate(tab.path)}
                            id={`nav-tab-${tab.label.toLowerCase().replace(/\s+/g, '-')}`}
                        >
                            <span style={{ marginRight: 6 }}>{tab.icon}</span>
                            {tab.label}
                        </button>
                    ))}
                </div>
                <div className="toolbar-right">
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={toggleTheme}
                        id="btn-theme-toggle"
                    >
                        {isLight ? '🌙 Dark' : '☀️ Light'}
                    </button>
                </div>
            </div>
        </nav>
    );
}
