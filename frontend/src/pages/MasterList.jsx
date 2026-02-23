import { useState, useEffect } from 'react';
import SummaryCard from '../components/SummaryCard';
import Modal from '../components/Modal';
import { masterAPI } from '../services/api';

const formatCurrency = (val) => {
    const num = parseFloat(val);
    if (isNaN(num)) return '₹0.00';
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const formatPercent = (val) => {
    const num = parseFloat(val);
    if (isNaN(num)) return '0.00%';
    return `${num.toFixed(2)}%`;
};

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
    } catch (e) {
        return 'Invalid date';
    }
};

export default function MasterList({ addToast }) {
    const [stocks, setStocks] = useState([]);
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [search, setSearch] = useState('');
    const [groupFilter, setGroupFilter] = useState('');
    const [showAddModal, setShowAddModal] = useState(false);
    const [editStock, setEditStock] = useState(null);
    const [form, setForm] = useState({ group: '', trading_symbol: '' });
    const [athLoadingSymbol, setAthLoadingSymbol] = useState(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [stocksRes, groupsRes] = await Promise.all([
                masterAPI.getAll(groupFilter || undefined),
                masterAPI.getGroups(),
            ]);
            setStocks(stocksRes.data.data || []);
            setGroups(groupsRes.data.data || []);
        } catch (err) {
            addToast('Failed to load stocks: ' + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [groupFilter]);

    const handleAdd = async () => {
        if (!form.trading_symbol) {
            addToast('Symbol is required', 'error');
            return;
        }
        try {
            await masterAPI.add(form);
            addToast(`${form.trading_symbol} added to watchlist`, 'success');
            setShowAddModal(false);
            setForm({ group: '', trading_symbol: '' });
            setRefreshing(true);
            try {
                const res = await masterAPI.refresh();
                addToast(res.data.message || 'Data refreshed', 'success');
            } catch (refreshErr) {
                addToast('Refresh failed: ' + (refreshErr.response?.data?.detail || refreshErr.message), 'error');
            } finally {
                setRefreshing(false);
            }
            await fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to add stock', 'error');
        }
    };

    const handleUpdate = async () => {
        try {
            await masterAPI.update(editStock.trading_symbol, {
                group: editStock.group,
                stock_name: editStock.stock_name,
            });
            addToast(`${editStock.trading_symbol} updated`, 'success');
            setEditStock(null);
            fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to update', 'error');
        }
    };

    const handleDelete = async (trading_symbol) => {
        if (!window.confirm(`Remove ${trading_symbol} from watchlist?`)) return;
        try {
            await masterAPI.delete(trading_symbol);
            addToast(`${trading_symbol} removed`, 'success');
            fetchData();
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to remove', 'error');
        }
    };

    const handleRefresh = async () => {
        try {
            setRefreshing(true);
            const res = await masterAPI.refresh();
            addToast(res.data.message, 'success');
            fetchData();
        } catch (err) {
            addToast('Refresh failed: ' + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setRefreshing(false);
        }
    };

    const handleFetchAth = async (trading_symbol) => {
        try {
            setAthLoadingSymbol(trading_symbol);
            const res = await masterAPI.refreshAthFromHistory(trading_symbol, 10);
            addToast(res.data.message || `ATH updated for ${trading_symbol}`, 'success');
            await fetchData();
        } catch (err) {
            addToast(
                err.response?.data?.detail || `Failed to refresh ATH for ${trading_symbol}`,
                'error',
            );
        } finally {
            setAthLoadingSymbol(null);
        }
    };

    const filtered = stocks.filter((s) => {
        const q = search.toLowerCase();
        return (
            s.stock_name?.toLowerCase().includes(q) ||
            s.trading_symbol?.toLowerCase().includes(q)
        );
    });

    const uniqueGroups = [...new Set(stocks.map((s) => s.group))].filter(Boolean);

    return (
        <div className="page-enter">
            {/* Summary Cards */}
            <div className="summary-cards">
                <SummaryCard label="Total Stocks" value={stocks.length} />
                <SummaryCard label="Groups" value={uniqueGroups.length} sub={uniqueGroups.join(', ')} />
                <SummaryCard
                    label="Above EMA10"
                    value={stocks.filter((s) => parseFloat(s.cp) > parseFloat(s.ema10)).length}
                    type="positive"
                    sub={`of ${stocks.length} stocks`}
                />
                <SummaryCard
                    label="Near ATH (5%)"
                    value={stocks.filter((s) => {
                        const cp = parseFloat(s.cp);
                        const ath = parseFloat(s.ath);
                        return ath > 0 && ((ath - cp) / ath) * 100 <= 5;
                    }).length}
                    sub="within 5% of ATH"
                />
            </div>

            {/* Toolbar */}
            <div className="toolbar">
                <button
                    className="btn btn-primary"
                    onClick={() => setShowAddModal(true)}
                    id="btn-add-stock"
                >
                    + Add Stock
                </button>
                <input
                    className="input input-search"
                    type="text"
                    placeholder="Search stocks..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    id="input-search-master"
                />
                <select
                    className="select"
                    value={groupFilter}
                    onChange={(e) => setGroupFilter(e.target.value)}
                    id="select-group-filter"
                >
                    <option value="">All Groups</option>
                    {groups.map((g) => (
                        <option key={g} value={g}>{g}</option>
                    ))}
                </select>
                <div className="toolbar-right">
                    <button
                        className="btn btn-secondary"
                        onClick={handleRefresh}
                        disabled={refreshing}
                        id="btn-refresh"
                    >
                        {refreshing ? '↻ Refreshing...' : '↻ Refresh Data'}
                    </button>
                </div>
            </div>

            {/* Data Table */}
            <div className="table-container">
                {loading ? (
                    <div style={{ padding: 16 }}>
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="skeleton skeleton-row" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">📋</div>
                        <div className="empty-state-title">No stocks found</div>
                        <div className="empty-state-text">
                            {search ? 'Try a different search term.' : 'Add stocks to your watchlist to get started.'}
                        </div>
                    </div>
                ) : (
                    <table className="data-table" id="master-table">
                        <thead>
                            <tr>
                                <th>Group</th>
                                <th>Stock Name</th>
                                <th>Symbol</th>
                                <th className="text-right">ATH</th>
                                <th className="text-right">Current Price</th>
                                <th className="text-right">Prev O→C %</th>
                                <th className="text-right">Today O→C %</th>
                                <th className="text-right">EMA 5</th>
                                <th className="text-right">EMA 10</th>
                                <th className="text-right">EMA 20</th>
                                <th className="text-center">Last Updated</th>
                                <th className="text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((stock) => {
                                const cp = parseFloat(stock.cp);
                                const ema5 = parseFloat(stock.ema5);
                                const ema10 = parseFloat(stock.ema10);
                                const ema20 = parseFloat(stock.ema20);
                                const cpClass = cp > ema10 ? 'cell-positive' : cp < ema10 ? 'cell-negative' : '';
                                const athValue = parseFloat(stock.ath);
                                const isAthMissing = !athValue || Number.isNaN(athValue);

                                return (
                                    <tr key={stock.trading_symbol}>
                                        <td><span className="badge badge-group">{stock.group}</span></td>
                                        <td>{stock.stock_name}</td>
                                        <td className="cell-symbol">{stock.trading_symbol}</td>
                                        <td className="text-right cell-muted">
                                            {isAthMissing ? (
                                                <button
                                                    className="btn btn-secondary"
                                                    style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                                                    onClick={() => handleFetchAth(stock.trading_symbol)}
                                                    disabled={athLoadingSymbol === stock.trading_symbol}
                                                >
                                                    {athLoadingSymbol === stock.trading_symbol
                                                        ? 'Fetching...'
                                                        : 'Fetch ATH'}
                                                </button>
                                            ) : (
                                                formatCurrency(stock.ath)
                                            )}
                                        </td>
                                        <td className={`text-right ${cpClass}`}>{formatCurrency(stock.cp)}</td>
                                        <td className="text-right">
                                            {formatPercent(stock.prev_change_pct)}
                                        </td>
                                        <td
                                            className={`text-right ${
                                                parseFloat(stock.today_change_pct) > 0
                                                    ? 'cell-positive'
                                                    : parseFloat(stock.today_change_pct) < 0
                                                        ? 'cell-negative'
                                                        : 'cell-muted'
                                            }`}
                                        >
                                            {formatPercent(stock.today_change_pct)}
                                        </td>
                                        <td className={`text-right ${cp > ema5 ? 'cell-positive' : 'cell-muted'}`}>
                                            {formatCurrency(stock.ema5)}
                                        </td>
                                        <td className={`text-right ${cp > ema10 ? 'cell-positive' : 'cell-muted'}`}>
                                            {formatCurrency(stock.ema10)}
                                        </td>
                                        <td className={`text-right ${ema10 > ema20 ? 'cell-positive' : 'cell-muted'}`}>
                                            {formatCurrency(stock.ema20)}
                                        </td>
                                        <td className="text-center cell-muted" style={{ fontSize: '0.85rem' }}>
                                            {formatRelativeTime(stock.last_updated)}
                                        </td>
                                        <td className="text-center">
                                            <button
                                                className="btn btn-icon"
                                                onClick={() => setEditStock({ ...stock })}
                                                title="Edit"
                                            >
                                                ✏️
                                            </button>
                                            <button
                                                className="btn btn-icon danger"
                                                onClick={() => handleDelete(stock.trading_symbol)}
                                                title="Delete"
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

            {/* Add Stock Modal */}
            <Modal
                isOpen={showAddModal}
                onClose={() => setShowAddModal(false)}
                title="Add Stock to Watchlist"
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
                        <button className="btn btn-primary" onClick={handleAdd} id="btn-confirm-add">Add Stock</button>
                    </>
                }
            >
                <div className="form-group">
                    <label className="form-label">Symbol *</label>
                    <input
                        className="input"
                        placeholder="e.g. RELIANCE, ICICIBANK"
                        value={form.trading_symbol}
                        onChange={(e) => setForm({ ...form, trading_symbol: e.target.value.toUpperCase() })}
                        id="input-add-symbol"
                    />
                </div>
                <div className="form-group">
                    <label className="form-label">Group</label>
                    <input
                        className="input"
                        placeholder="e.g. Energy, IT, Banking"
                        value={form.group}
                        onChange={(e) => setForm({ ...form, group: e.target.value })}
                        id="input-add-group"
                    />
                </div>
                <p className="text-muted" style={{ fontSize: '0.82rem' }}>
                    Stock name will be auto-populated from NSE list. Values start at 0; data will refresh automatically after add.
                </p>
            </Modal>

            {/* Edit Stock Modal */}
            <Modal
                isOpen={!!editStock}
                onClose={() => setEditStock(null)}
                title={`Edit ${editStock?.trading_symbol || ''}`}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setEditStock(null)}>Cancel</button>
                        <button className="btn btn-primary" onClick={handleUpdate}>Save Changes</button>
                    </>
                }
            >
                {editStock && (
                    <>
                        <div className="form-group">
                            <label className="form-label">Stock Name</label>
                            <input
                                className="input"
                                value={editStock.stock_name}
                                onChange={(e) => setEditStock({ ...editStock, stock_name: e.target.value })}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Group</label>
                            <input
                                className="input"
                                value={editStock.group}
                                onChange={(e) => setEditStock({ ...editStock, group: e.target.value })}
                            />
                        </div>
                    </>
                )}
            </Modal>
        </div>
    );
}
