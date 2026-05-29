import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { upstoxAPI } from '../services/api';

export default function UpstoxCallback({ addToast }) {
    const [status, setStatus] = useState('loading');
    const [message, setMessage] = useState('Completing Upstox login…');

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');
        const error = params.get('error') || params.get('error_description');

        if (error) {
            setStatus('error');
            setMessage(decodeURIComponent(error));
            return;
        }

        if (!code) {
            setStatus('error');
            setMessage('No authorization code in callback URL. Expected ?code=… from Upstox.');
            return;
        }

        let cancelled = false;

        (async () => {
            try {
                const res = await upstoxAPI.completeAuth(code);
                if (cancelled) return;
                setStatus('success');
                setMessage(res.data.message || 'Upstox access token saved.');
                addToast?.('Upstox connected successfully.', 'success');
            } catch (err) {
                if (cancelled) return;
                const detail = err.response?.data?.detail || err.message || 'Token exchange failed';
                setStatus('error');
                setMessage(detail);
                addToast?.(detail, 'error');
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [addToast]);

    return (
        <div className="page-enter" style={{ maxWidth: 520, margin: '48px auto', padding: 24 }}>
            <h2 style={{ marginBottom: 12 }}>Upstox Login</h2>
            {status === 'loading' && (
                <>
                    <div className="skeleton skeleton-row" style={{ marginBottom: 12 }} />
                    <p className="text-muted">{message}</p>
                </>
            )}
            {status === 'success' && (
                <>
                    <p style={{ color: 'var(--green)', marginBottom: 16 }}>{message}</p>
                    <p className="text-muted" style={{ fontSize: '0.85rem', marginBottom: 16 }}>
                        You can close this tab and return to the app. Market data requests will use the new token.
                    </p>
                    <Link to="/upstox" className="btn btn-primary">
                        Back to Upstox Settings
                    </Link>
                </>
            )}
            {status === 'error' && (
                <>
                    <p style={{ color: 'var(--red)', marginBottom: 16 }}>{message}</p>
                    <Link to="/upstox" className="btn btn-secondary">
                        Try again
                    </Link>
                </>
            )}
        </div>
    );
}
