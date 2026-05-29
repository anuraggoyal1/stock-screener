import { useState, useEffect } from 'react';
import SummaryCard from '../components/SummaryCard';
import Modal from '../components/Modal';
import { tradelogAPI } from '../services/api';

const formatCurrency = (val) => {
    const num = parseFloat(val);
    if (isNaN(num)) return '₹0.00';
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export default function TradeLog({ addToast }) {
    const [trades, setTrades] = useState([]);
    const [summary, setSummary] = useState({});
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [editTrade, setEditTrade] = useState(null);
    const [editForm, setEditForm] = useState(null);

    const handleDelete = async (trade) => {
        if (!window.confirm(`Delete trade log for ${trade.symbol}? This cannot be undone.`)) return;
        try {
            await tradelogAPI.delete(trade.symbol, {
                buy_date: trade.buy_date,
                sell_date: trade.sell_date,
                buy_price: trade.buy_price,
                sell_price: trade.sell_price,
                quantity: trade.quantity
            });
            addToast(`Trade ${trade.symbol} deleted`, 'success');
            fetchData();
        } catch (err) {
            addToast('Failed to delete trade: ' + (err.response?.data?.detail || err.message), 'error');
        }
    };

    const handleEditSave = async () => {
        if (!editTrade || !editForm) return;
        try {
            await tradelogAPI.update(editTrade.symbol, {
                original_buy_date: editTrade.buy_date,
                original_sell_date: editTrade.sell_date,
                original_buy_price: parseFloat(editTrade.buy_price),
                original_sell_price: parseFloat(editTrade.sell_price),
                original_quantity: parseInt(editTrade.quantity),

                symbol: editForm.symbol.toUpperCase(),
                stock_name: editForm.stock_name,
                buy_price: parseFloat(editForm.buy_price),
                sell_price: parseFloat(editForm.sell_price),
                quantity: parseInt(editForm.quantity),
                buy_date: editForm.buy_date,
                sell_date: editForm.sell_date
            });
            addToast(`Trade updated`, 'success');
            setEditTrade(null);
            fetchData();
        } catch (err) {
            addToast('Failed to update trade: ' + (err.response?.data?.detail || err.message), 'error');
        }
    };

    const fetchData = async () => {
        try {
            setLoading(true);
            const params = {};
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;

            const res = await tradelogAPI.getAll(params);
            setTrades(res.data.data || []);
            setSummary(res.data.summary || {});
        } catch (err) {
            addToast('Failed to load trades: ' + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const applyDateFilter = () => {
        fetchData();
    };

    const filtered = trades.filter((t) => {
        const q = search.toLowerCase();
        return t.symbol?.toLowerCase().includes(q) || t.stock_name?.toLowerCase().includes(q);
    });

    const totalPnl = filtered.reduce((sum, t) => sum + parseFloat(t.pnl || 0), 0);

    return (
        <div className="page-enter">
            {/* Summary Cards */}
            <div className="summary-cards">
                <SummaryCard
                    label="Total Trades"
                    value={summary.total_trades || 0}
                />
                <SummaryCard
                    label="Winning Trades"
                    value={`${summary.winning_trades || 0} (${summary.win_rate || 0}%)`}
                    type="positive"
                />
                <SummaryCard
                    label="Losing Trades"
                    value={summary.losing_trades || 0}
                    type="negative"
                />
                <SummaryCard
                    label="Net P&L"
                    value={`${(summary.net_pnl || 0) >= 0 ? '+' : ''}${formatCurrency(summary.net_pnl)}`}
                    type={(summary.net_pnl || 0) >= 0 ? 'positive' : 'negative'}
                    sub={`${(summary.net_pnl_pct || 0) >= 0 ? '+' : ''}${(summary.net_pnl_pct || 0).toFixed(2)}% return`}
                />
            </div>

            {/* Toolbar */}
            <div className="toolbar">
                <input
                    className="input input-search"
                    type="text"
                    placeholder="Search trades..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    id="input-search-tradelog"
                />
                <div className="filter-input-group">
                    <label>From:</label>
                    <input
                        className="input"
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                        style={{ width: 160 }}
                    />
                </div>
                <div className="filter-input-group">
                    <label>To:</label>
                    <input
                        className="input"
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                        style={{ width: 160 }}
                    />
                </div>
                <button className="btn btn-primary" onClick={applyDateFilter} id="btn-filter-dates">
                    Filter
                </button>
            </div>

            {/* Table */}
            <div className="table-container">
                {loading ? (
                    <div style={{ padding: 16 }}>
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="skeleton skeleton-row" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📊</div>
                        <div className="empty-state-title">No trades recorded</div>
                        <div className="empty-state-text">
                            Trades will appear here when you sell positions from the Positions tab.
                        </div>
                    </div>
                ) : (
                    <table className="data-table" id="tradelog-table">
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Stock Name</th>
                                <th className="text-right">Buy Price</th>
                                <th className="text-right">Sell Price</th>
                                <th className="text-right">Qty</th>
                                <th>Buy Date</th>
                                <th>Sell Date</th>
                                <th className="text-right">P&L (₹)</th>
                                <th className="text-right">P&L (%)</th>
                                <th className="text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((trade, idx) => {
                                const pnl = parseFloat(trade.pnl);
                                const pnlPct = parseFloat(trade.pnl_pct);
                                const pnlClass = pnl >= 0 ? 'cell-positive' : 'cell-negative';

                                return (
                                    <tr key={`${trade.symbol}-${idx}`}>
                                        <td className="cell-symbol">
                                            <a
                                                href={`https://www.tradingview.com/chart/?symbol=NSE:${trade.symbol}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{ color: 'var(--accent)', textDecoration: 'none' }}
                                            >
                                                {trade.symbol}
                                            </a>
                                        </td>
                                        <td>{trade.stock_name}</td>
                                        <td className="text-right">{formatCurrency(trade.buy_price)}</td>
                                        <td className="text-right fw-600">{formatCurrency(trade.sell_price)}</td>
                                        <td className="text-right">{parseInt(trade.quantity)}</td>
                                        <td className="cell-muted">{trade.buy_date}</td>
                                        <td className="cell-muted">{trade.sell_date}</td>
                                        <td className={`text-right ${pnlClass}`}>
                                            {pnl >= 0 ? '+' : ''}{formatCurrency(pnl)}
                                        </td>
                                        <td className={`text-right ${pnlClass}`}>
                                            {pnlPct >= 0 ? '+' : ''}{pnlPct?.toFixed(2)}%
                                        </td>
                                        <td className="text-center">
                                            <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
                                                <button
                                                    className="btn btn-icon"
                                                    onClick={() => {
                                                        setEditTrade(trade);
                                                        setEditForm({ ...trade });
                                                    }}
                                                    title="Edit Trade"
                                                >
                                                    ✏️
                                                </button>
                                                <button
                                                    className="btn btn-icon danger"
                                                    onClick={() => handleDelete(trade)}
                                                    title="Delete Trade"
                                                >
                                                    🗑️
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                            {/* Summary Row */}
                            <tr style={{ background: 'rgba(0,0,0,0.2)', fontWeight: 700 }}>
                                <td colSpan="7" className="text-right" style={{ color: 'var(--text-secondary)' }}>
                                    TOTAL ({filtered.length} trades)
                                </td>
                                <td className={`text-right ${totalPnl >= 0 ? 'cell-positive' : 'cell-negative'}`}>
                                    {totalPnl >= 0 ? '+' : ''}{formatCurrency(totalPnl)}
                                </td>
                                <td></td>
                                <td></td>
                            </tr>
                        </tbody>
                    </table>
                )}
            </div>

            {/* Edit Trade Modal */}
            <Modal
                isOpen={!!editTrade}
                onClose={() => setEditTrade(null)}
                title={`Edit Trade: ${editTrade?.symbol}`}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setEditTrade(null)}>Cancel</button>
                        <button className="btn btn-primary" onClick={handleEditSave}>Save Changes</button>
                    </>
                }
            >
                {editForm && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div className="form-row">
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Symbol</label>
                                <input
                                    className="input"
                                    value={editForm.symbol}
                                    onChange={(e) => setEditForm({ ...editForm, symbol: e.target.value })}
                                />
                            </div>
                            <div className="form-group" style={{ flex: 2 }}>
                                <label className="form-label">Stock Name</label>
                                <input
                                    className="input"
                                    value={editForm.stock_name}
                                    onChange={(e) => setEditForm({ ...editForm, stock_name: e.target.value })}
                                />
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Buy Price</label>
                                <input
                                    className="input"
                                    type="number"
                                    step="0.05"
                                    value={editForm.buy_price}
                                    onChange={(e) => setEditForm({ ...editForm, buy_price: e.target.value })}
                                />
                            </div>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Sell Price</label>
                                <input
                                    className="input"
                                    type="number"
                                    step="0.05"
                                    value={editForm.sell_price}
                                    onChange={(e) => setEditForm({ ...editForm, sell_price: e.target.value })}
                                />
                            </div>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Quantity</label>
                                <input
                                    className="input"
                                    type="number"
                                    value={editForm.quantity}
                                    onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })}
                                />
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Buy Date</label>
                                <input
                                    className="input"
                                    type="date"
                                    value={editForm.buy_date}
                                    onChange={(e) => setEditForm({ ...editForm, buy_date: e.target.value })}
                                />
                            </div>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Sell Date</label>
                                <input
                                    className="input"
                                    type="date"
                                    value={editForm.sell_date}
                                    onChange={(e) => setEditForm({ ...editForm, sell_date: e.target.value })}
                                />
                            </div>
                        </div>
                    </div>
                )}
            </Modal>
        </div>
    );
}
