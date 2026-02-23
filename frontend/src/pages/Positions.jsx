import { useState, useEffect } from 'react';
import SummaryCard from '../components/SummaryCard';
import Modal from '../components/Modal';
import { positionsAPI, ordersAPI } from '../services/api';

const formatCurrency = (val) => {
    const num = parseFloat(val);
    if (isNaN(num)) return '₹0.00';
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export default function Positions({ addToast }) {
    const [positions, setPositions] = useState([]);
    const [summary, setSummary] = useState({});
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    // Add position modal
    const [showAddModal, setShowAddModal] = useState(false);
    const [addForm, setAddForm] = useState({ symbol: '', stock_name: '', buy_price: '', buy_date: '', quantity: 1 });

    // Sell modal
    const [sellPos, setSellPos] = useState(null);
    const [sellForm, setSellForm] = useState({ quantity: '', order_type: 'MARKET', price: '' });
    const [selling, setSelling] = useState(false);

    const fetchData = async () => {
        try {
            setLoading(true);
            const res = await positionsAPI.getAll();
            setPositions(res.data.data || []);
            setSummary(res.data.summary || {});
        } catch (err) {
            addToast('Failed to load positions: ' + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleAdd = async () => {
        if (!addForm.symbol || !addForm.buy_price) {
            addToast('Symbol and Buy Price are required', 'error');
            return;
        }
        try {
            await positionsAPI.add({
                symbol: addForm.symbol.toUpperCase(),
                stock_name: addForm.stock_name,
                buy_price: parseFloat(addForm.buy_price),
                buy_date: addForm.buy_date || undefined,
                quantity: parseInt(addForm.quantity) || 1,
            });
            addToast(`Position added for ${addForm.symbol}`, 'success');
            setShowAddModal(false);
            setAddForm({ symbol: '', stock_name: '', buy_price: '', buy_date: '', quantity: 1 });
            fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to add position', 'error');
        }
    };

    const handleSell = async () => {
        if (!sellPos) return;
        try {
            setSelling(true);
            const res = await ordersAPI.sell({
                symbol: sellPos.symbol,
                quantity: sellForm.quantity ? parseInt(sellForm.quantity) : undefined,
                order_type: sellForm.order_type,
                price: sellForm.order_type === 'LIMIT' ? parseFloat(sellForm.price) : undefined,
            });
            addToast(res.data.message, 'success');
            setSellPos(null);
            fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Sell order failed', 'error');
        } finally {
            setSelling(false);
        }
    };

    const handleRemove = async (symbol) => {
        if (!window.confirm(`Remove position for ${symbol}? This will NOT place a sell order.`)) return;
        try {
            await positionsAPI.delete(symbol);
            addToast(`Position for ${symbol} removed`, 'success');
            fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to remove', 'error');
        }
    };

    const filtered = positions.filter((p) => {
        const q = search.toLowerCase();
        return p.symbol?.toLowerCase().includes(q) || p.stock_name?.toLowerCase().includes(q);
    });

    const pnlType = summary.total_pnl >= 0 ? 'positive' : 'negative';

    return (
        <div className="page-enter">
            {/* Summary */}
            <div className="summary-cards">
                <SummaryCard
                    label="Total Investment"
                    value={formatCurrency(summary.total_investment)}
                />
                <SummaryCard
                    label="Current Value"
                    value={formatCurrency(summary.total_current_value)}
                    type={pnlType}
                />
                <SummaryCard
                    label="Total P&L"
                    value={`${summary.total_pnl >= 0 ? '+' : ''}${formatCurrency(summary.total_pnl)}`}
                    type={pnlType}
                    sub={`${summary.total_pnl_pct >= 0 ? '+' : ''}${(summary.total_pnl_pct || 0).toFixed(2)}%`}
                />
                <SummaryCard
                    label="Open Positions"
                    value={positions.length}
                />
            </div>

            {/* Toolbar */}
            <div className="toolbar">
                <button
                    className="btn btn-primary"
                    onClick={() => setShowAddModal(true)}
                    id="btn-add-position"
                >
                    + Add Position
                </button>
                <input
                    className="input input-search"
                    type="text"
                    placeholder="Search positions..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    id="input-search-positions"
                />
            </div>

            {/* Table */}
            <div className="table-container">
                {loading ? (
                    <div style={{ padding: 16 }}>
                        {[...Array(4)].map((_, i) => (
                            <div key={i} className="skeleton skeleton-row" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">💼</div>
                        <div className="empty-state-title">No open positions</div>
                        <div className="empty-state-text">
                            Add positions manually or buy stocks from the Screener tab.
                        </div>
                    </div>
                ) : (
                    <table className="data-table" id="positions-table">
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Stock Name</th>
                                <th className="text-right">Buy Price</th>
                                <th>Buy Date</th>
                                <th className="text-right">Qty</th>
                                <th className="text-right">Current Price</th>
                                <th className="text-right">P&L (₹)</th>
                                <th className="text-right">P&L (%)</th>
                                <th className="text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((pos) => {
                                const pnl = parseFloat(pos.pnl);
                                const pnlPct = parseFloat(pos.pnl_pct);
                                const pnlClass = pnl >= 0 ? 'cell-positive' : 'cell-negative';

                                return (
                                    <tr key={pos.symbol}>
                                        <td className="cell-symbol">{pos.symbol}</td>
                                        <td>{pos.stock_name}</td>
                                        <td className="text-right">{formatCurrency(pos.buy_price)}</td>
                                        <td className="cell-muted">{pos.buy_date}</td>
                                        <td className="text-right fw-600">{parseInt(pos.quantity)}</td>
                                        <td className="text-right fw-600">{formatCurrency(pos.current_price)}</td>
                                        <td className={`text-right ${pnlClass}`}>
                                            {pnl >= 0 ? '+' : ''}{formatCurrency(pnl)}
                                        </td>
                                        <td className={`text-right ${pnlClass}`}>
                                            {pnlPct >= 0 ? '+' : ''}{pnlPct?.toFixed(2)}%
                                        </td>
                                        <td className="text-center" style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                                            <button
                                                className="btn btn-sell"
                                                onClick={() => {
                                                    setSellPos(pos);
                                                    setSellForm({ quantity: pos.quantity, order_type: 'MARKET', price: '' });
                                                }}
                                                id={`btn-sell-${pos.symbol}`}
                                            >
                                                SELL
                                            </button>
                                            <button
                                                className="btn btn-icon danger"
                                                onClick={() => handleRemove(pos.symbol)}
                                                title="Remove"
                                            >
                                                🗑️
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Add Position Modal */}
            <Modal
                isOpen={showAddModal}
                onClose={() => setShowAddModal(false)}
                title="Add Position"
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
                        <button className="btn btn-primary" onClick={handleAdd} id="btn-confirm-add-pos">Add Position</button>
                    </>
                }
            >
                <div className="form-row">
                    <div className="form-group">
                        <label className="form-label">Symbol *</label>
                        <input
                            className="input"
                            placeholder="e.g. RELIANCE"
                            value={addForm.symbol}
                            onChange={(e) => setAddForm({ ...addForm, symbol: e.target.value.toUpperCase() })}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Stock Name</label>
                        <input
                            className="input"
                            placeholder="Auto-filled if in master list"
                            value={addForm.stock_name}
                            onChange={(e) => setAddForm({ ...addForm, stock_name: e.target.value })}
                        />
                    </div>
                </div>
                <div className="form-row">
                    <div className="form-group">
                        <label className="form-label">Buy Price *</label>
                        <input
                            className="input"
                            type="number"
                            placeholder="e.g. 1500.00"
                            value={addForm.buy_price}
                            onChange={(e) => setAddForm({ ...addForm, buy_price: e.target.value })}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Quantity</label>
                        <input
                            className="input"
                            type="number"
                            min="1"
                            value={addForm.quantity}
                            onChange={(e) => setAddForm({ ...addForm, quantity: e.target.value })}
                        />
                    </div>
                </div>
                <div className="form-group">
                    <label className="form-label">Buy Date</label>
                    <input
                        className="input"
                        type="date"
                        value={addForm.buy_date}
                        onChange={(e) => setAddForm({ ...addForm, buy_date: e.target.value })}
                    />
                </div>
            </Modal>

            {/* Sell Modal */}
            <Modal
                isOpen={!!sellPos}
                onClose={() => setSellPos(null)}
                title={`Sell ${sellPos?.symbol || ''}`}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setSellPos(null)}>Cancel</button>
                        <button
                            className="btn btn-sell"
                            onClick={handleSell}
                            disabled={selling}
                            id="btn-confirm-sell"
                        >
                            {selling ? 'Placing...' : `Sell ${sellPos?.symbol}`}
                        </button>
                    </>
                }
            >
                {sellPos && (
                    <>
                        <div style={{ background: 'var(--bg-input)', padding: 16, borderRadius: 8, marginBottom: 8 }}>
                            <div className="form-row" style={{ gap: 24 }}>
                                <div>
                                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Buy Price</div>
                                    <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>{formatCurrency(sellPos.buy_price)}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Current Price</div>
                                    <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>{formatCurrency(sellPos.current_price)}</div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>P&L</div>
                                    <div style={{ fontSize: '1.1rem', fontWeight: 700 }} className={parseFloat(sellPos.pnl) >= 0 ? 'text-green' : 'text-red'}>
                                        {parseFloat(sellPos.pnl) >= 0 ? '+' : ''}{formatCurrency(sellPos.pnl)}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="form-row">
                            <div className="form-group">
                                <label className="form-label">Quantity (max: {parseInt(sellPos.quantity)})</label>
                                <input
                                    className="input"
                                    type="number"
                                    min="1"
                                    max={sellPos.quantity}
                                    value={sellForm.quantity}
                                    onChange={(e) => setSellForm({ ...sellForm, quantity: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Order Type</label>
                                <select
                                    className="select"
                                    value={sellForm.order_type}
                                    onChange={(e) => setSellForm({ ...sellForm, order_type: e.target.value })}
                                >
                                    <option value="MARKET">Market</option>
                                    <option value="LIMIT">Limit</option>
                                </select>
                            </div>
                        </div>
                        {sellForm.order_type === 'LIMIT' && (
                            <div className="form-group">
                                <label className="form-label">Limit Price</label>
                                <input
                                    className="input"
                                    type="number"
                                    placeholder="Enter limit price"
                                    value={sellForm.price}
                                    onChange={(e) => setSellForm({ ...sellForm, price: e.target.value })}
                                />
                            </div>
                        )}
                    </>
                )}
            </Modal>
        </div>
    );
}
