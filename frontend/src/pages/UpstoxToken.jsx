import { useState } from 'react';
import { upstoxAPI } from '../services/api';

export default function UpstoxToken({ addToast }) {
    const [loading, setLoading] = useState(false);

    const handleConnectUpstox = async () => {
        try {
            setLoading(true);
            const res = await upstoxAPI.getAuthUrl();
            const url = res.data.auth_url || '';
            if (!url) {
                addToast('No auth URL returned from server.', 'error');
                return;
            }
            window.open(url, '_blank', 'noopener,noreferrer');
            addToast(
                'Upstox login opened in a new tab. Enter OTP there; you will be redirected back automatically.',
                'success'
            );
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to start Upstox login', 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page-enter">
            <h2 style={{ marginBottom: 16 }}>Upstox Token Setup</h2>
            <p className="text-muted" style={{ marginBottom: 24 }}>
                Connect your Upstox account in one step. After you approve access, Upstox redirects to{' '}
                <code>http://localhost:3000/callback</code> and the app saves your token automatically.
            </p>

            <div className="filter-panel">
                <button
                    className="btn btn-primary"
                    onClick={handleConnectUpstox}
                    disabled={loading}
                    id="btn-upstox-connect"
                >
                    {loading ? 'Opening…' : 'Connect Upstox'}
                </button>
                <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: 12 }}>
                    Ensure <code>upstox.redirect_uri</code> in config is{' '}
                    <code>http://localhost:3000/callback</code> and the same URL is registered in your
                    Upstox developer app.
                </p>
            </div>
        </div>
    );
}
