import { useState } from 'react';
import { upstoxAPI } from '../services/api';

export default function UpstoxToken({ addToast }) {
    const [authUrl, setAuthUrl] = useState('');
    const [code, setCode] = useState('');
    const [rawToken, setRawToken] = useState('');
    const [accessToken, setAccessToken] = useState('');
    const [loadingAuth, setLoadingAuth] = useState(false);
    const [loadingExchange, setLoadingExchange] = useState(false);
    const [savingToken, setSavingToken] = useState(false);

    const handleGetAuthUrl = async () => {
        try {
            setLoadingAuth(true);
            const res = await upstoxAPI.getAuthUrl();
            const url = res.data.auth_url || '';
            setAuthUrl(url);
            if (url) {
                addToast('Auth URL generated. Open it in your browser to log in.', 'success');
            }
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to get auth URL', 'error');
        } finally {
            setLoadingAuth(false);
        }
    };

    const handleExchangeCode = async () => {
        if (!code.trim()) {
            addToast('Paste the code from the Upstox redirect URL.', 'error');
            return;
        }
        try {
            setLoadingExchange(true);
            const res = await upstoxAPI.exchangeToken(code.trim());
            const token = res.data.token || {};
            setRawToken(JSON.stringify(token, null, 2));
            if (token.access_token) {
                setAccessToken(token.access_token);
            }
            addToast('Token fetched from Upstox.', 'success');
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to exchange code for token', 'error');
        } finally {
            setLoadingExchange(false);
        }
    };

    const handleSaveToken = async () => {
        if (!accessToken.trim()) {
            addToast('Enter an access token to save.', 'error');
            return;
        }
        try {
            setSavingToken(true);
            const res = await upstoxAPI.saveToken(accessToken.trim());
            addToast(res.data.message || 'Access token saved.', 'success');
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to save token', 'error');
        } finally {
            setSavingToken(false);
        }
    };

    return (
        <div className="page-enter">
            <h2 style={{ marginBottom: 16 }}>Upstox Token Setup</h2>
            <p className="text-muted" style={{ marginBottom: 24 }}>
                Use this screen to generate the OAuth URL, exchange the callback code for a token,
                and save the access token into the backend config.
            </p>

            <div className="filter-panel" style={{ marginBottom: 20 }}>
                <div className="filter-panel-title">Step 1 — Get Auth URL</div>
                <div className="toolbar" style={{ marginBottom: 12 }}>
                    <button
                        className="btn btn-secondary"
                        onClick={handleGetAuthUrl}
                        disabled={loadingAuth}
                        id="btn-upstox-auth-url"
                    >
                        {loadingAuth ? 'Generating...' : 'Generate Auth URL'}
                    </button>
                </div>
                <div className="form-group">
                    <label className="form-label">Auth URL</label>
                    <textarea
                        className="input"
                        rows={3}
                        value={authUrl}
                        readOnly
                        style={{ fontSize: '0.8rem', resize: 'vertical' }}
                    />
                    {authUrl && (
                        <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: 6 }}>
                            Open this URL in your browser, log in to Upstox, approve the app, then copy the
                            <code> code=...</code> value from the redirect URL.
                        </p>
                    )}
                </div>
            </div>

            <div className="filter-panel" style={{ marginBottom: 20 }}>
                <div className="filter-panel-title">Step 2 — Exchange Code for Token</div>
                <div className="form-group">
                    <label className="form-label">Code from Upstox Redirect URL</label>
                    <input
                        className="input"
                        placeholder="Paste ?code=... value here"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        id="input-upstox-code"
                    />
                </div>
                <div className="toolbar" style={{ marginTop: 12, marginBottom: 12 }}>
                    <button
                        className="btn btn-primary"
                        onClick={handleExchangeCode}
                        disabled={loadingExchange}
                        id="btn-upstox-exchange"
                    >
                        {loadingExchange ? 'Exchanging...' : 'Exchange Code for Token'}
                    </button>
                </div>
                <div className="form-group">
                    <label className="form-label">Raw Token Payload</label>
                    <textarea
                        className="input"
                        rows={6}
                        value={rawToken}
                        readOnly
                        style={{ fontFamily: 'monospace', fontSize: '0.8rem', resize: 'vertical' }}
                    />
                </div>
            </div>

            <div className="filter-panel">
                <div className="filter-panel-title">Step 3 — Save Access Token</div>
                <div className="form-group">
                    <label className="form-label">Access Token to Save</label>
                    <input
                        className="input"
                        placeholder="access_token from token payload"
                        value={accessToken}
                        onChange={(e) => setAccessToken(e.target.value)}
                        id="input-upstox-access-token"
                    />
                </div>
                <div className="toolbar" style={{ marginTop: 12 }}>
                    <button
                        className="btn btn-primary"
                        onClick={handleSaveToken}
                        disabled={savingToken}
                        id="btn-upstox-save-token"
                    >
                        {savingToken ? 'Saving...' : 'Save Token to Backend'}
                    </button>
                </div>
                <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: 6 }}>
                    This will write the token into <code>config.yaml</code> on the backend and
                    update the running app so new Upstox API calls use it immediately.
                </p>
            </div>
        </div>
    );
}

