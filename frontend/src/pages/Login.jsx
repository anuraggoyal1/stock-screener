import { useState } from 'react';
import api from '../services/api';

export default function Login({ setAuth }) {
    const [key, setKey] = useState('');

    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        const cleanKey = key.trim();
        if (!cleanKey) {
            setError('Please enter an API Key');
            setLoading(false);
            return;
        }

        try {
            // Use the pre-configured api instance which points to the correct backend URL
            const resp = await api.get('/health', {
                headers: { 'X-API-Key': cleanKey }
            });

            if (resp.status === 200) {
                localStorage.setItem('X-API-Key', cleanKey);
                setAuth(true);
            }
        } catch (err) {
            console.error('Login failed:', err);
            if (err.response) {
                setError(err.response.data?.detail || 'Invalid API Key');
            } else {
                setError('Connection failed. Is the backend running?');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container" style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '80vh',
            gap: '20px'
        }}>
            <div className="login-card" style={{
                backgroundColor: 'var(--card-bg)',
                padding: '32px',
                borderRadius: '12px',
                boxShadow: 'var(--shadow)',
                width: '100%',
                maxWidth: '400px',
                border: '1px solid var(--border)'
            }}>
                <h1 style={{ marginBottom: '8px', fontSize: '1.5rem', color: 'var(--text-main)' }}>Stock Screener</h1>
                <p style={{ marginBottom: '24px', color: 'var(--text-muted)' }}>Enter your API Key to continue</p>

                {error && (
                    <div style={{ color: '#ff4d4f', fontSize: '0.85rem', marginBottom: '16px' }}>{error}</div>
                )}

                <form onSubmit={handleLogin}>
                    <div style={{ marginBottom: '16px' }}>
                        <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem' }}>API Key</label>
                        <input
                            type="password"
                            className="input"
                            placeholder="Enter X-API-Key"
                            value={key}
                            onChange={(e) => setKey(e.target.value)}
                            style={{ width: '100%', padding: '10px' }}
                            required
                            disabled={loading}
                        />
                    </div>
                    <button
                        type="submit"
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '10px' }}
                        disabled={loading}
                    >
                        {loading ? 'Verifying...' : 'Verify & Connect'}
                    </button>
                </form>
            </div>
        </div>
    );
}
