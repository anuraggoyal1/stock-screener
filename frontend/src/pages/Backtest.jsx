import { useState } from 'react';
import { backtestAPI } from '../services/api';

const formatCurrency = (val) => {
    const num = parseFloat(val);
    if (isNaN(num)) return '₹0.00';
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export default function Backtest({ addToast }) {
    const [symbol, setSymbol] = useState('');
    const [upCandlePct, setUpCandlePct] = useState('2.0');
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(null);

    const handleRun = async () => {
        if (!symbol) {
            addToast('Please enter a trading symbol', 'error');
            return;
        }
        try {
            setLoading(true);
            const res = await backtestAPI.run({
                symbol: symbol.toUpperCase(),
                up_candle_pct: parseFloat(upCandlePct)
            });
            setResults(res.data);
            addToast(`Backtest completed for ${symbol.toUpperCase()}`, 'success');
        } catch (err) {
            addToast('Backtest failed: ' + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page-container">
            <header className="page-header">
                <div>
                    <h1 className="page-title">Backtest Engine</h1>
                    <p className="page-subtitle">Historical analysis & pattern probability</p>
                </div>
            </header>

            <div className="card" style={{ marginBottom: 24 }}>
                <div className="card-header">
                    <h3 className="card-title">Configuration</h3>
                </div>
                <div className="card-body">
                    <div className="form-row" style={{ alignItems: 'flex-end' }}>
                        <div className="form-group" style={{ flex: 1 }}>
                            <label className="form-label">Trading Symbol</label>
                            <input
                                className="input"
                                type="text"
                                placeholder="e.g. INFY, RELIANCE"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                            />
                        </div>
                        <div className="form-group" style={{ flex: 1 }}>
                            <label className="form-label">Big Up Candle (%)</label>
                            <input
                                className="input"
                                type="number"
                                step="0.1"
                                placeholder="e.g. 2.0"
                                value={upCandlePct}
                                onChange={(e) => setUpCandlePct(e.target.value)}
                            />
                        </div>
                        <div className="form-group" style={{ flex: 0 }}>
                            <button
                                className="btn btn-primary"
                                onClick={handleRun}
                                disabled={loading}
                                style={{ height: '42px', minWidth: '120px' }}
                            >
                                {loading ? 'Running...' : 'Run Backtest'}
                            </button>
                        </div>
                    </div>
                    <div style={{ marginTop: 12, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        <strong>Strategy:</strong> Identifies periods where Price &gt; 80% ATH and EMA5 &gt; EMA10.
                        In these periods, it tracks "Big Up Candles" and counts how many days (1-5) it takes for a close below the Day 0 Open.
                    </div>
                </div>
            </div>

            {results && (
                <>
                    <div className="summary-grid" style={{ marginBottom: 24 }}>
                        <div className="summary-card">
                            <div className="summary-label">Total Setups Found</div>
                            <div className="summary-value" style={{ color: 'var(--accent)' }}>{results.total_setups}</div>
                        </div>
                        {Object.entries(results.overall_success).map(([day, count]) => (
                            <div className="summary-card" key={day}>
                                <div className="summary-label">Day {day} Reversals</div>
                                <div className="summary-value">{count}</div>
                                <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                                    {results.total_setups > 0 ? ((count / results.total_setups) * 100).toFixed(1) : 0}% Prob.
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="card">
                        <div className="card-header">
                            <h3 className="card-title">Period Analysis</h3>
                        </div>
                        <div className="table-container">
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Period Range</th>
                                        <th className="text-center">Setups</th>
                                        <th className="text-center">Day 1</th>
                                        <th className="text-center">Day 2</th>
                                        <th className="text-center">Day 3</th>
                                        <th className="text-center">Day 4</th>
                                        <th className="text-center">Day 5</th>
                                        <th className="text-center">Total Rev</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.periods.map((p, i) => {
                                        const totalRev = Object.values(p.day_counts).reduce((a, b) => a + b, 0);
                                        return (
                                            <tr key={i}>
                                                <td>
                                                    <div style={{ fontWeight: 600 }}>{p.start} to {p.end}</div>
                                                </td>
                                                <td className="text-center">
                                                    <span className="badge badge-group">{p.setups}</span>
                                                </td>
                                                {[1, 2, 3, 4, 5].map(d => (
                                                    <td key={d} className="text-center">
                                                        {p.day_counts[d]}
                                                        <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>
                                                            {p.setups > 0 ? ((p.day_counts[d] / p.setups) * 100).toFixed(0) : 0}%
                                                        </div>
                                                    </td>
                                                ))}
                                                <td className="text-center" style={{ fontWeight: 700 }}>
                                                    {totalRev}
                                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                                                        {p.setups > 0 ? ((totalRev / p.setups) * 100).toFixed(0) : 0}%
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                    {results.periods.length === 0 && (
                                        <tr>
                                            <td colSpan="8" style={{ textAlign: 'center', padding: 32, color: 'var(--text-secondary)' }}>
                                                No qualifying periods found in the last 20 years.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}

            {loading && (
                <div className="card" style={{ padding: 48, textAlign: 'center' }}>
                    <div className="skeleton" style={{ height: 200, width: '100%' }}></div>
                    <p style={{ marginTop: 16, color: 'var(--text-secondary)' }}>Fetching 20 years of history and processing candle patterns...</p>
                </div>
            )}
        </div>
    );
}
