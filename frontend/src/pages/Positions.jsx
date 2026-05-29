import { useState, useEffect } from 'react';
import SummaryCard from '../components/SummaryCard';
import Modal from '../components/Modal';
import { positionsAPI, ordersAPI } from '../services/api';

const formatCurrency = (val) => {
    const num = parseFloat(val);
    if (isNaN(num)) return '₹0.00';
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const todayInputDate = () => {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
};

const emptyAddForm = () => ({
    symbol: '',
    stock_name: '',
    buy_price: '',
    buy_date: todayInputDate(),
    quantity: 1,
    stoploss: '',
});

const formatRelativeTime = (isoString) => {
    if (!isoString) return 'Never';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min ago`;
        if (diffHours < 24) {
            const remainingMins = diffMins % 60;
            return remainingMins > 0 ? `${diffHours}h ${remainingMins} min ago` : `${diffHours}h ago`;
        }
        if (diffDays < 7) {
            const remainingHours = diffHours % 24;
            return remainingHours > 0 ? `${diffDays}d ${remainingHours}h ago` : `${diffDays}d ago`;
        }
        return date.toLocaleDateString();
    } catch {
        return 'Invalid date';
    }
};

const isValidPosition = (p) => {
    const symbol = String(p?.symbol ?? '').trim();
    if (!symbol || symbol.toLowerCase() === 'nan') return false;
    const buyPrice = Number(p?.buy_price);
    const quantity = Number(p?.quantity);
    return Number.isFinite(buyPrice) && buyPrice > 0 && Number.isFinite(quantity) && quantity > 0;
};

const parsePositionsResponse = (res) => {
    const body = res?.data;
    if (Array.isArray(body?.data)) {
        return { rows: body.data, summary: body.summary || {} };
    }
    if (Array.isArray(body)) {
        return { rows: body, summary: {} };
    }
    return { rows: [], summary: {} };
};

export default function Positions({ addToast }) {
    const [positions, setPositions] = useState([]);
    const [summary, setSummary] = useState({});
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    // Add position modal
    const [showAddModal, setShowAddModal] = useState(false);
    const [addForm, setAddForm] = useState(emptyAddForm());

    // Sell modal
    const [sellPos, setSellPos] = useState(null);
    const [sellForm, setSellForm] = useState({ quantity: '', order_type: 'MARKET', price: '' });
    const [selling, setSelling] = useState(false);
    const [editPos, setEditPos] = useState(null);
    const [editForm, setEditForm] = useState({ buy_price: '', buy_date: '', quantity: '', stoploss: '' });

    const [sortConfig, setSortConfig] = useState({ key: 'buy_date', direction: 'desc' });
    const [refreshingSymbol, setRefreshingSymbol] = useState(null);
    const [refreshingAll, setRefreshingAll] = useState(false);

    const handleRefreshOne = async (symbol) => {
        try {
            setRefreshingSymbol(symbol);
            const res = await positionsAPI.refreshOne(symbol);
            addToast(res.data.message || `Refreshed ${symbol}`, 'success');
            await fetchData();
        } catch (err) {
            addToast(`Refresh failed for ${symbol}: ` + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setRefreshingSymbol(null);
        }
    };

    const fetchData = async (params = {}) => {
        try {
            setLoading(true);
            // console.log('Fetching positions with params:', params);
            const res = await positionsAPI.getAll(params);
            // console.log('Positions API response:', res);
            const { rows, summary: nextSummary } = parsePositionsResponse(res);
            // console.log('Parsed rows:', rows);
            // console.log('Parsed summary:', nextSummary);
            const dataWithIds = rows.filter(isValidPosition).map((p, idx) => ({
                ...p,
                id: `${p.symbol}-${p.buy_date}-${p.buy_price}-${p.quantity}-${idx}`
            }));
            // console.log('Data with IDs:', dataWithIds);
            setPositions(dataWithIds);
            setSummary(nextSummary);

            // Show a toast with the count for debugging
            if (dataWithIds.length > 0) {
                addToast(`Loaded ${dataWithIds.length} positions`, 'success');
            } else {
                addToast('No positions found', 'warning');
            }
        } catch (err) {
            addToast('Failed to load positions: ' + (err.response?.data?.detail || err.message), 'error');
            console.error('Error fetching positions:', err);
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
                stoploss: parseFloat(addForm.stoploss) || 0,
            });
            addToast(`Position added for ${addForm.symbol}`, 'success');
            setShowAddModal(false);
            setAddForm(emptyAddForm());
            fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to add position', 'error');
        }
    };

    const handleUpdate = async () => {
        if (!editPos) return;
        try {
            const originalDetails = {
                original_buy_date: editPos.buy_date,
                original_buy_price: editPos.buy_price,
                original_quantity: editPos.quantity,
            };
            await positionsAPI.update(editPos.symbol, {
                buy_price: parseFloat(editForm.buy_price),
                buy_date: editForm.buy_date,
                quantity: parseInt(editForm.quantity),
                stoploss: parseFloat(editForm.stoploss) || 0,
            }, originalDetails);

            addToast(`Position for ${editPos.symbol} updated`, 'success');
            setEditPos(null);
            fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to update position', 'error');
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
                buy_date: sellPos.buy_date,
                buy_price: parseFloat(sellPos.buy_price)
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

    const handleDelete = async (pos) => {
        if (!window.confirm(`Remove position for ${pos.symbol}?`)) return;
        const { symbol, buy_date, buy_price, quantity } = pos;
        try {
            await positionsAPI.delete(symbol, { buy_date, buy_price, quantity });
            addToast(`Position for ${symbol} removed`, 'success');
            fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to remove', 'error');
        }
    };

    const handleRefresh = async () => {
        setRefreshingAll(true);
        try {
            console.log('Starting refresh...');
            const res = await positionsAPI.refresh();
            console.log('Refresh response:', res);
            addToast(res.data.message || 'Live prices updated', 'success');
            await fetchData();
        } catch (err) {
            console.error('Refresh error:', err);
            if (err.response) {
                addToast('Refresh failed: ' + (err.response.data?.detail || err.response.statusText || 'Unknown error'), 'error');
            } else if (err.request) {
                addToast('Refresh failed: Network error - no response received', 'error');
            } else {
                addToast('Refresh failed: ' + err.message, 'error');
            }
        } finally {
            setRefreshingAll(false);
        }
    };

    const requestSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const filtered = positions.filter((p) => {
        if (!isValidPosition(p)) return false;
        const q = search.toLowerCase();
        return (
            String(p.symbol).toLowerCase().includes(q) ||
            String(p.stock_name ?? '').toLowerCase().includes(q)
        );
    });

    const sortedData = [...filtered].sort((a, b) => {
      if (!sortConfig.key) return 0;
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];

      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }

      return sortConfig.direction === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });

    const pnlType = (summary.total_pnl ?? 0) >= 0 ? 'positive' : 'negative';

    const getSortClass = (key) => {
        if (sortConfig.key !== key) return 'sortable';
        return `sortable sort-${sortConfig.direction}`;
    };

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
                    value={filtered.length}
                />
            </div>

            {/* Toolbar */}
            <div className="toolbar">
                <button
                    className="btn btn-primary"
                    onClick={() => {
                        setAddForm(emptyAddForm());
                        setShowAddModal(true);
                    }}
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
                <div className="toolbar-right">
                    <button
                        className="btn btn-secondary"
                        onClick={handleRefresh}
                        disabled={refreshingAll}
                        id="btn-refresh-positions"
                    >
                        {refreshingAll ? '↻ Refreshing...' : '↻ Refresh All'}
                    </button>
                </div>
            </div>

            {/* Table */}
            <div className="table-container">
                {loading ? (
                    <div style={{ padding: 16 }}>
                        {[...Array(4)].map((_, i) => (
                            <div key={i} className="skeleton skeleton-row" />
                        ))}
                    </div>
                ) : sortedData.length === 0 ? (
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
                                <th className={getSortClass('buy_date')} onClick={() => requestSort('buy_date')}>Buy Date</th>
                                <th className={getSortClass('symbol')} onClick={() => requestSort('symbol')}>Symbol</th>
                                <th className={getSortClass('stock_name')} onClick={() => requestSort('stock_name')}>Stock Name</th>
                                <th className={`text-right ${getSortClass('buy_price')}`} onClick={() => requestSort('buy_price')}>Buy Price</th>
                                <th className={`text-right ${getSortClass('quantity')}`} onClick={() => requestSort('quantity')}>Qty</th>
                                <th className={`text-right ${getSortClass('current_price')}`} onClick={() => requestSort('current_price')}>Current</th>
                                <th className={`text-right ${getSortClass('stoploss')}`} onClick={() => requestSort('stoploss')}>SL</th>
                                <th className={`text-right ${getSortClass('pnl')}`} onClick={() => requestSort('pnl')}>P&L (₹)</th>
                                <th className={`text-right ${getSortClass('pnl_pct')}`} onClick={() => requestSort('pnl_pct')}>P&L (%)</th>
                                <th className={getSortClass('last_updated')} onClick={() => requestSort('last_updated')}>Refreshed</th>
                                <th className="text-center">Daily</th>
                                <th className="text-center">Weekly</th>
                                <th className="text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedData.map((pos) => {
                                const pnl = parseFloat(pos.pnl);
                                const pnlPct = parseFloat(pos.pnl_pct);
                                const cp = parseFloat(pos.current_price);
                                const buyPrice = parseFloat(pos.buy_price);
                                const sl = parseFloat(pos.stoploss) || 0;

                                const dEma4 = parseFloat(pos.d_ema4);
                                const dEma7 = parseFloat(pos.d_ema7);
                                const wEma4 = parseFloat(pos.w_ema4);
                                const wEma7 = parseFloat(pos.w_ema7);

                                const isDailyBlue = !isNaN(dEma4) && !isNaN(dEma7) && dEma4 <= dEma7;
                                const isWeeklyBlue = !isNaN(wEma4) && !isNaN(wEma7) && wEma4 <= wEma7;
                                const shouldBlink = isDailyBlue || isWeeklyBlue;

                                let rowClass = '';
                                if (shouldBlink) {
                                    rowClass = 'row-blink-red';
                                } else if (cp < sl && sl > 0) {
                                    rowClass = 'row-stoploss';
                                } else if (cp < buyPrice) {
                                    rowClass = 'row-negative';
                                }

                                const pnlClass = pnl >= 0 ? 'cell-positive' : 'cell-negative';

                                let dailyLight = <span className="indicator-dot dot-gray" title="N/A"></span>;
                                if (!isNaN(dEma4) && !isNaN(dEma7)) {
                                    if (dEma4 > dEma7) {
                                        dailyLight = <span className="indicator-dot dot-yellow" title={`Daily EMA4 (${dEma4}) > EMA7 (${dEma7})`}></span>;
                                    } else {
                                        dailyLight = <span className="indicator-dot dot-blue" title={`Daily EMA4 (${dEma4}) <= EMA7 (${dEma7})`}></span>;
                                    }
                                }

                                let weeklyLight = <span className="indicator-dot dot-gray" title="N/A"></span>;
                                if (!isNaN(wEma4) && !isNaN(wEma7)) {
                                    if (wEma4 > wEma7) {
                                        weeklyLight = <span className="indicator-dot dot-yellow" title={`Weekly EMA4 (${wEma4}) > EMA7 (${wEma7})`}></span>;
                                    } else {
                                        weeklyLight = <span className="indicator-dot dot-blue" title={`Weekly EMA4 (${wEma4}) <= EMA7 (${wEma7})`}></span>;
                                    }
                                }

                                return (
                                    <tr key={pos.id} className={rowClass}>
                                        <td className="cell-muted">{pos.buy_date}</td>
                                        <td className="cell-symbol">
                                            <a
                                                href={`https://www.tradingview.com/chart/?symbol=NSE:${pos.symbol}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{ color: 'var(--accent)', textDecoration: 'none' }}
                                              >
                                                {pos.symbol}
                                            </a>
                                        </td>
                                        <td>{pos.stock_name}</td>
                                        <td className="text-right fw-600">{formatCurrency(pos.buy_price)}</td>
                                        <td className="text-right">{parseInt(pos.quantity)}</td>
                                        <td className="text-right fw-600">{formatCurrency(pos.current_price)}</td>
                                        <td className="text-right cell-muted">{formatCurrency(pos.stoploss)}</td>
                                        <td className={`text-right ${pnlClass}`}>
                                            {pnl >= 0 ? '+' : ''}{formatCurrency(pnl)}
                                        </td>
                                        <td className={`text-right ${pnlClass}`}>
                                            {pnlPct >= 0 ? '+' : ''}{pnlPct?.toFixed(2)}%
                                        </td>
                                        <td
                                            className="cell-muted"
                                            title={pos.last_updated ? new Date(pos.last_updated).toLocaleString() : 'Not refreshed yet'}
                                        >
                                            {formatRelativeTime(pos.last_updated)}
                                        </td>
                                        <td className="text-center">{dailyLight}</td>
                                        <td className="text-center">{weeklyLight}</td>
                                        <td className="text-center">
                                            <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
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
                                                    className="btn btn-icon"
                                                    onClick={() => handleRefreshOne(pos.symbol)}
                                                    title="Refresh Price"
                                                    disabled={refreshingSymbol === pos.symbol}
                                                >
                                                    ↻
                                                </button>
                                                <button
                                                    className="btn btn-icon"
                                                    onClick={() => {
                                                        setEditPos(pos);
                                                        setEditForm({ ...pos });
                                                    }}
                                                    title="Edit"
                                                >
                                                    ✏️
                                                </button>
                                                <button
                                                    className="btn btn-icon danger"
                                                    onClick={() => handleDelete(pos)}
                                                    title="Delete"
                                                >
                                                    🗑️
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )
                }
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
                <div className="form-row">
                    <div className="form-group">
                        <label className="form-label">Buy Date</label>
                        <input
                            className="input"
                            type="date"
                            value={addForm.buy_date}
                            onChange={(e) => setAddForm({ ...addForm, buy_date: e.target.value })}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Stoploss</label>
                        <input
                            className="input"
                            type="number"
                            step="0.05"
                            placeholder="e.g. 1450.00"
                            value={addForm.stoploss}
                            onChange={(e) => setAddForm({ ...addForm, stoploss: e.target.value })}
                        />
                    </div>
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

            {/* Edit Position Modal */}
            <Modal
                isOpen={!!editPos}
                onClose={() => setEditPos(null)}
                title={`Edit Position: ${editPos?.symbol || ''}`}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setEditPos(null)}>Cancel</button>
                        <button className="btn btn-primary" onClick={handleUpdate}>Save Changes</button>
                    </>
                }
            >
                {editPos && (
                    <>
                        <div className="form-row">
                            <div className="form-group">
                                <label className="form-label">Buy Price</label>
                                <input
                                    className="input"
                                    type="number"
                                    step="0.05"
                                    value={editForm.buy_price}
                                    onChange={(e) => setEditForm({ ...editForm, buy_price: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Quantity</label>
                                <input
                                    className="input"
                                    type="number"
                                    min="1"
                                    value={editForm.quantity}
                                    onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })}
                                />
                            </div>
                        </div>
                        <div className="form-row">
                            <div className="form-group">
                                <label className="form-label">Buy Date</label>
                                <input
                                    className="input"
                                    type="date"
                                    value={editForm.buy_date}
                                    onChange={(e) => setEditForm({ ...editForm, buy_date: e.target.value })}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Stoploss</label>
                                <input
                                    className="input"
                                    type="number"
                                    step="0.05"
                                    value={editForm.stoploss}
                                    onChange={(e) => setEditForm({ ...editForm, stoploss: e.target.value })}
                                />
                            </div>
                        </div>
                    </>
                )}
            </Modal>
        </div>
    );
}
