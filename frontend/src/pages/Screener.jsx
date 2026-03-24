import { useState, useEffect } from 'react';
import SummaryCard from '../components/SummaryCard';
import Modal from '../components/Modal';
import { screenerAPI, ordersAPI, masterAPI, positionsAPI } from '../services/api';

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

export default function Screener({ addToast }) {
    const [stocks, setStocks] = useState([]);
    const [groups, setGroups] = useState([]);
    const [loading, setLoading] = useState(true);
    const [total, setTotal] = useState(0);

    // Filter state with defaults — only CP > 80% ATH and W-EMA4 > W-EMA5 on by default
    const [filters, setFilters] = useState({
        ema10_gt_ema20: false,
        near_ath_pct: '',
        group: '',
        min_cp: '',
        max_cp: '',
        cp_gt_ath_pct_enabled: true,
        cp_gt_ath_pct: '80',
        ema_comparison_enabled: false,
        ema_comparison: 'ema5_gt_ema10',
        prev_change_lt_enabled: false,
        prev_change_lt: '0',
        prev_change_gt: '-2',
        prev_change_gt_enabled: false,
        today_change_gt_enabled: false,
        today_change_gt: '0.5',
        today_change_lt: '1.5',
        today_change_lt_enabled: false,
        l5_open_dist_gt_enabled: false,
        l5_open_dist_gt: '0',
        l5_open_dist_lt_enabled: false,
        l5_open_dist_lt: '5',
        w_ema4_gt_w_ema5: true,
        w_otoc_lt: '5',
        w_otoc_lt_enabled: true,
        weekly_l5_dist_gt: '1',
        weekly_l5_dist_gt_enabled: true,
        weekly_l5_dist_lt: '5',
        weekly_l5_dist_lt_enabled: true,
        sortBy: 'group',
        sortDir: 'asc'
    });

    // Buy modal (API order)
    const [buyStock, setBuyStock] = useState(null);
    const [buyForm, setBuyForm] = useState({ quantity: 1, order_type: 'MARKET', price: '' });
    const [buying, setBuying] = useState(false);

    // Add Position modal (manual entry)
    const [addPosStock, setAddPosStock] = useState(null);
    const [addPosForm, setAddPosForm] = useState({ quantity: 1, price: '', stoploss: '' });
    const [addingPos, setAddingPos] = useState(false);
    const [refreshingSymbol, setRefreshingSymbol] = useState(null);

    const handleRefreshOne = async (symbol) => {
        try {
            setRefreshingSymbol(symbol);
            await masterAPI.refreshOne(symbol);
            addToast(`Refreshed ${symbol}`, 'success');
            await fetchFiltered();
        } catch (err) {
            addToast(`Refresh failed for ${symbol}: ` + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setRefreshingSymbol(null);
        }
    };

    const fetchGroups = async () => {
        try {
            const res = await masterAPI.getGroups();
            setGroups(res.data.data || []);
        } catch (err) { }
    };

    const fetchFiltered = async () => {
        try {
            setLoading(true);
            const params = {};
            if (filters.ema10_gt_ema20) params.ema10_gt_ema20 = true;
            if (filters.near_ath_pct) params.near_ath_pct = parseFloat(filters.near_ath_pct);
            if (filters.group) params.group = filters.group;
            if (filters.min_cp) params.min_cp = parseFloat(filters.min_cp);
            if (filters.max_cp) params.max_cp = parseFloat(filters.max_cp);
            // New filters
            if (filters.cp_gt_ath_pct_enabled && filters.cp_gt_ath_pct) {
                params.cp_gt_ath_pct = parseFloat(filters.cp_gt_ath_pct);
            }
            if (filters.ema_comparison_enabled && filters.ema_comparison) {
                params.ema_comparison = filters.ema_comparison;
            }
            if (filters.prev_change_lt_enabled && filters.prev_change_lt !== '') {
                params.prev_change_lt = parseFloat(filters.prev_change_lt);
            }
            if (filters.prev_change_gt_enabled && filters.prev_change_gt !== '') {
                params.prev_change_gt = parseFloat(filters.prev_change_gt);
            }
            if (filters.today_change_gt_enabled && filters.today_change_gt !== '') {
                params.today_change_gt = parseFloat(filters.today_change_gt);
            }
            if (filters.today_change_lt_enabled && filters.today_change_lt !== '') {
                params.today_change_lt = parseFloat(filters.today_change_lt);
            }
            if (filters.l5_open_dist_gt_enabled && filters.l5_open_dist_gt !== '') {
                params.l5_open_dist_gt = parseFloat(filters.l5_open_dist_gt);
            }
            if (filters.l5_open_dist_lt_enabled && filters.l5_open_dist_lt !== '') {
                params.l5_open_dist_lt = parseFloat(filters.l5_open_dist_lt);
            }
            if (filters.w_ema4_gt_w_ema5) {
                params.w_ema4_gt_w_ema5 = true;
            }
            if (filters.w_otoc_gt_enabled && filters.w_otoc_gt !== '') {
                params.w_otoc_gt = parseFloat(filters.w_otoc_gt);
            }
            if (filters.w_otoc_lt_enabled && filters.w_otoc_lt !== '') {
                params.w_otoc_lt = parseFloat(filters.w_otoc_lt);
            }
            if (filters.weekly_l5_dist_gt_enabled && filters.weekly_l5_dist_gt !== '') {
                params.weekly_l5_dist_gt = parseFloat(filters.weekly_l5_dist_gt);
            }
            if (filters.weekly_l5_dist_lt_enabled && filters.weekly_l5_dist_lt !== '') {
                params.weekly_l5_dist_lt = parseFloat(filters.weekly_l5_dist_lt);
            }

            const res = await screenerAPI.getFiltered(params);
            let data = res.data.data || [];

            // Client-side sorting
            if (filters.sortBy) {
                data.sort((a, b) => {
                    let valA = a[filters.sortBy];
                    let valB = b[filters.sortBy];

                    // Handle special case for W_O->C% which is w_OtoC_pct_change
                    if (filters.sortBy === 'w_OtoC_pct_change') {
                        valA = parseFloat(valA) || 0;
                        valB = parseFloat(valB) || 0;
                    } else if (typeof valA === 'string') {
                        valA = valA.toLowerCase();
                        valB = valB.toLowerCase();
                    } else {
                        valA = parseFloat(valA) || 0;
                        valB = parseFloat(valB) || 0;
                    }

                    if (valA < valB) return filters.sortDir === 'asc' ? -1 : 1;
                    if (valA > valB) return filters.sortDir === 'asc' ? 1 : -1;
                    return 0;
                });
            }

            setStocks(data);
            setTotal(res.data.total || 0);
        } catch (err) {
            addToast('Failed to load screener: ' + (err.response?.data?.detail || err.message), 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchGroups();
        fetchFiltered(); // Initial load with default filters
    }, []);

    const applyFilters = () => {
        fetchFiltered();
    };

    const resetFilters = () => {
        setFilters({
            ema10_gt_ema20: false,
            near_ath_pct: '',
            group: '',
            min_cp: '',
            max_cp: '',
            cp_gt_ath_pct_enabled: true,
            cp_gt_ath_pct: '80',
            ema_comparison_enabled: false,
            ema_comparison: 'ema5_gt_ema10',
            prev_change_lt_enabled: false,
            prev_change_lt: '0',
            prev_change_gt: '-2',
            prev_change_gt_enabled: false,
            today_change_gt_enabled: false,
            today_change_gt: '0.5',
            today_change_lt: '1.5',
            today_change_lt_enabled: false,
            l5_open_dist_gt_enabled: false,
            l5_open_dist_gt: '0',
            l5_open_dist_lt_enabled: false,
            l5_open_dist_lt: '5',
            w_ema4_gt_w_ema5: true,
            w_otoc_lt: '5',
            w_otoc_lt_enabled: true,
            weekly_l5_dist_gt: '1',
            weekly_l5_dist_gt_enabled: true,
            weekly_l5_dist_lt: '5',
            weekly_l5_dist_lt_enabled: true,
            sortBy: 'group',
            sortDir: 'asc'
        });
        setTimeout(fetchFiltered, 0);
    };

    const toggleSort = (field) => {
        setFilters(prev => ({
            ...prev,
            sortBy: field,
            sortDir: prev.sortBy === field && prev.sortDir === 'asc' ? 'desc' : 'asc'
        }));
        // We need to re-fetch/re-sort. fetchFiltered works fine because it uses 'filters' state
        // but since setState is async, we should probably trigger it in a useEffect or use a temporary var
    };

    useEffect(() => {
        // Re-sort when sortBy/sortDir changes without hitting API if we want, 
        // but fetchFiltered currently hits API. Let's just call fetchFiltered.
        if (!loading) fetchFiltered();
    }, [filters.sortBy, filters.sortDir]);

    const handleBuy = async () => {
        if (!buyStock) return;
        try {
            setBuying(true);
            const res = await ordersAPI.buy({
                symbol: buyStock.trading_symbol || buyStock.symbol,
                quantity: parseInt(buyForm.quantity) || 1,
                order_type: buyForm.order_type,
                price: buyForm.order_type === 'LIMIT' ? parseFloat(buyForm.price) : null,
                curr_price: parseFloat(buyStock.cp),
            });
            addToast(res.data.message, 'success');
            setBuyStock(null);
            setBuyForm({ quantity: 1, order_type: 'MARKET', price: '' });
        } catch (err) {
            addToast(err.response?.data?.detail || 'Buy order failed', 'error');
        } finally {
            setBuying(false);
        }
    };

    const handleDownloadCSV = () => {
        if (!stocks || stocks.length === 0) {
            addToast('No stocks to download', 'error');
            return;
        }

        // All symbols comma-separated on a single row, e.g.: NSE:RELIANCE,NSE:TCS,NSE:INFY
        const csvContent = stocks.map(s => `NSE:${s.trading_symbol || s.symbol}`).join(',');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `screener_export_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        addToast(`Downloaded ${stocks.length} symbols`, 'success');
    };

    const handleAddToPositions = async () => {
        if (!addPosStock) return;
        try {
            setAddingPos(true);
            const res = await positionsAPI.add({
                symbol: addPosStock.trading_symbol || addPosStock.symbol,
                stock_name: addPosStock.stock_name,
                buy_price: parseFloat(addPosForm.price),
                quantity: parseInt(addPosForm.quantity) || 1,
                buy_date: new Date().toISOString().split('T')[0], // Current date
                stoploss: parseFloat(addPosForm.stoploss),
            });
            addToast(`Position added for ${addPosStock.trading_symbol || addPosStock.symbol}`, 'success');
            setAddPosStock(null);
            setAddPosForm({ quantity: 1, price: '', stoploss: '' });
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to add position', 'error');
        } finally {
            setAddingPos(false);
        }
    };

    const bullish = stocks.filter((s) => s.signal === 'Bullish').length;
    const bearish = stocks.filter((s) => s.signal === 'Bearish').length;

    return (
        <div className="page-enter">
            {/* Summary */}
            <div className="summary-cards">
                <SummaryCard label="Showing" value={`${stocks.length} / ${total}`} sub="stocks matching filters" />
                <SummaryCard label="Bullish" value={bullish} type="positive" size="small" sub="CP > EMA10 > EMA20" />
                <SummaryCard label="Bearish" value={bearish} type="negative" size="small" sub="CP < EMA10 < EMA20" />
                <SummaryCard label="Neutral" value={stocks.length - bullish - bearish} size="small" sub="Mixed signals" />
            </div>

            {/* Group Stats based on results */}
            {stocks.length > 0 && (
                <div className="group-stats-container">
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', width: '100%', marginBottom: '4px' }}>
                        Groups in result:
                    </div>
                    {Object.entries(
                        stocks.reduce((acc, s) => {
                            const g = s.group || 'Ungrouped';
                            acc[g] = (acc[g] || 0) + 1;
                            return acc;
                        }, {})
                    )
                        .sort((a, b) => b[1] - a[1]) // Sort by count descending
                        .map(([name, count]) => (
                            <div key={name} className="group-stat-item">
                                <span className="group-stat-name">{name}</span>
                                <span className="group-stat-count">{count}</span>
                            </div>
                        ))}
                </div>
            )}


            {/* Filter Panel */}
            <div className="filter-panel" style={{ padding: '16px' }}>
                <div className="filter-row" style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.2fr 1.2fr 180px', gap: '16px' }}>

                    {/* Column 1: Groups & Core */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <select
                            className="select"
                            value={filters.group}
                            onChange={(e) => setFilters({ ...filters, group: e.target.value })}
                            style={{ width: '100%' }}
                        >
                            <option value="">All Groups</option>
                            {groups.map((g) => (
                                <option key={g} value={g}>{g}</option>
                            ))}
                        </select>

                        <label className="filter-checkbox">
                            <input
                                type="checkbox"
                                checked={filters.w_ema4_gt_w_ema5}
                                onChange={(e) => setFilters({ ...filters, w_ema4_gt_w_ema5: e.target.checked })}
                            />
                            <span>W-EMA4 {'>'} W-EMA5</span>
                        </label>

                        <label className="filter-checkbox">
                            <input
                                type="checkbox"
                                checked={filters.ema10_gt_ema20}
                                onChange={(e) => setFilters({ ...filters, ema10_gt_ema20: e.target.checked })}
                            />
                            <span>EMA10 {'>'} EMA20</span>
                        </label>
                    </div>

                    {/* Column 2: ATH & EMA */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input
                                type="checkbox"
                                checked={filters.cp_gt_ath_pct_enabled}
                                onChange={(e) => setFilters({ ...filters, cp_gt_ath_pct_enabled: e.target.checked })}
                            />
                            <span style={{ fontSize: '0.85rem' }}>CP {'>'}</span>
                            <input
                                className="input"
                                type="number"
                                value={filters.cp_gt_ath_pct}
                                onChange={(e) => setFilters({ ...filters, cp_gt_ath_pct: e.target.value })}
                                disabled={!filters.cp_gt_ath_pct_enabled}
                                style={{ width: '50px', padding: '4px 8px' }}
                            />
                            <span style={{ fontSize: '0.85rem' }}>% ATH</span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input
                                type="checkbox"
                                checked={filters.ema_comparison_enabled}
                                onChange={(e) => setFilters({ ...filters, ema_comparison_enabled: e.target.checked })}
                            />
                            <select
                                className="select"
                                value={filters.ema_comparison}
                                onChange={(e) => setFilters({ ...filters, ema_comparison: e.target.value })}
                                disabled={!filters.ema_comparison_enabled}
                                style={{ flex: 1, padding: '4px 8px' }}
                            >
                                <option value="">EMA Compare...</option>
                                <option value="ema5_gt_ema10">EMA5 {'>'} EMA10</option>
                                <option value="ema10_gt_ema20">EMA10 {'>'} EMA20</option>
                                <option value="ema5_gt_ema20">EMA5 {'>'} EMA20</option>
                                <option value="ema5_lt_ema10">EMA5 {'<'} EMA10</option>
                                <option value="ema10_lt_ema20">EMA10 {'<'} EMA20</option>
                                <option value="ema5_lt_ema20">EMA5 {'<'} EMA20</option>
                            </select>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input
                                type="checkbox"
                                checked={filters.l5_open_dist_gt_enabled && filters.l5_open_dist_lt_enabled}
                                onChange={(e) => setFilters({
                                    ...filters,
                                    l5_open_dist_gt_enabled: e.target.checked,
                                    l5_open_dist_lt_enabled: e.target.checked
                                })}
                            />
                            <span style={{ fontSize: '0.8rem' }}>L5 Dist:</span>
                            <input className="input" type="number" value={filters.l5_open_dist_gt} onChange={(e) => setFilters({ ...filters, l5_open_dist_gt: e.target.value })} disabled={!filters.l5_open_dist_gt_enabled} style={{ width: '45px', padding: '4px' }} />
                            <span>to</span>
                            <input className="input" type="number" value={filters.l5_open_dist_lt} onChange={(e) => setFilters({ ...filters, l5_open_dist_lt: e.target.value })} disabled={!filters.l5_open_dist_lt_enabled} style={{ width: '45px', padding: '4px' }} />
                        </div>
                    </div>

                    {/* Column 3: Change Ranges */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input
                                type="checkbox"
                                checked={filters.prev_change_lt_enabled && filters.prev_change_gt_enabled}
                                onChange={(e) => setFilters({ ...filters, prev_change_lt_enabled: e.target.checked, prev_change_gt_enabled: e.target.checked })}
                            />
                            <span style={{ fontSize: '0.8rem' }}>Prev OC:</span>
                            <input className="input" type="number" value={filters.prev_change_gt} onChange={(e) => setFilters({ ...filters, prev_change_gt: e.target.value })} disabled={!filters.prev_change_gt_enabled} style={{ width: '45px', padding: '4px' }} />
                            <span>to</span>
                            <input className="input" type="number" value={filters.prev_change_lt} onChange={(e) => setFilters({ ...filters, prev_change_lt: e.target.value })} disabled={!filters.prev_change_lt_enabled} style={{ width: '45px', padding: '4px' }} />
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input
                                type="checkbox"
                                checked={filters.today_change_gt_enabled && filters.today_change_lt_enabled}
                                onChange={(e) => setFilters({ ...filters, today_change_gt_enabled: e.target.checked, today_change_lt_enabled: e.target.checked })}
                            />
                            <span style={{ fontSize: '0.8rem' }}>Today OC:</span>
                            <input className="input" type="number" value={filters.today_change_gt} onChange={(e) => setFilters({ ...filters, today_change_gt: e.target.value })} disabled={!filters.today_change_gt_enabled} style={{ width: '45px', padding: '4px' }} />
                            <span>to</span>
                            <input className="input" type="number" value={filters.today_change_lt} onChange={(e) => setFilters({ ...filters, today_change_lt: e.target.value })} disabled={!filters.today_change_lt_enabled} style={{ width: '45px', padding: '4px' }} />
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input
                                type="checkbox"
                                checked={filters.w_otoc_gt_enabled && filters.w_otoc_lt_enabled}
                                onChange={(e) => setFilters({ ...filters, w_otoc_gt_enabled: e.target.checked, w_otoc_lt_enabled: e.target.checked })}
                            />
                            <span style={{ fontSize: '0.8rem' }}>W OC:</span>
                            <input className="input" type="number" value={filters.w_otoc_gt} onChange={(e) => setFilters({ ...filters, w_otoc_gt: e.target.value })} disabled={!filters.w_otoc_gt_enabled} style={{ width: '45px', padding: '4px' }} />
                            <span>to</span>
                            <input className="input" type="number" value={filters.w_otoc_lt} onChange={(e) => setFilters({ ...filters, w_otoc_lt: e.target.value })} disabled={!filters.w_otoc_lt_enabled} style={{ width: '45px', padding: '4px' }} />
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input
                                type="checkbox"
                                checked={filters.weekly_l5_dist_gt_enabled && filters.weekly_l5_dist_lt_enabled}
                                onChange={(e) => setFilters({ ...filters, weekly_l5_dist_gt_enabled: e.target.checked, weekly_l5_dist_lt_enabled: e.target.checked })}
                            />
                            <span style={{ fontSize: '0.8rem' }}>W_L5 Dist:</span>
                            <input className="input" type="number" value={filters.weekly_l5_dist_gt} onChange={(e) => setFilters({ ...filters, weekly_l5_dist_gt: e.target.value })} disabled={!filters.weekly_l5_dist_gt_enabled} style={{ width: '45px', padding: '4px' }} />
                            <span>to</span>
                            <input className="input" type="number" value={filters.weekly_l5_dist_lt} onChange={(e) => setFilters({ ...filters, weekly_l5_dist_lt: e.target.value })} disabled={!filters.weekly_l5_dist_lt_enabled} style={{ width: '45px', padding: '4px' }} />
                        </div>
                    </div>

                    {/* Column 4: Actions */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', justifyContent: 'center' }}>
                        <button className="btn btn-primary" onClick={applyFilters} style={{ padding: '8px' }}>Apply Filters</button>
                        <button className="btn btn-secondary" onClick={resetFilters} style={{ padding: '8px' }}>Reset</button>
                        <button className="btn btn-secondary" onClick={handleDownloadCSV} style={{ padding: '8px' }}>⬇️ CSV</button>
                    </div>

                </div>
            </div>

            {/* Table */}
            <div className="table-container">
                {loading ? (
                    <div style={{ padding: 16 }}>
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="skeleton skeleton-row" />
                        ))}
                    </div>
                ) : stocks.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">🔍</div>
                        <div className="empty-state-title">No stocks match your criteria</div>
                        <div className="empty-state-text">Try adjusting your filters or adding more stocks to the master list.</div>
                    </div>
                ) : (
                    <table className="data-table" id="screener-table">
                        <thead>
                            <tr>
                                <th className={`sortable ${filters.sortBy === 'group' ? (filters.sortDir === 'asc' ? 'sort-asc' : 'sort-desc') : ''}`} onClick={() => toggleSort('group')}>Group</th>
                                <th>Stock Name</th>
                                <th className={`sortable ${filters.sortBy === 'trading_symbol' ? (filters.sortDir === 'asc' ? 'sort-asc' : 'sort-desc') : ''}`} onClick={() => toggleSort('trading_symbol')}>Symbol</th>
                                <th className={`text-right sortable ${filters.sortBy === 'ath' ? (filters.sortDir === 'asc' ? 'sort-asc' : 'sort-desc') : ''}`} onClick={() => toggleSort('ath')}>ATH</th>
                                <th className="text-right">Open</th>
                                <th className={`text-right sortable ${filters.sortBy === 'cp' ? (filters.sortDir === 'asc' ? 'sort-asc' : 'sort-desc') : ''}`} onClick={() => toggleSort('cp')}>Price</th>
                                <th className="text-right">L5 Open</th>
                                <th className="text-right">L5 Dist %</th>
                                <th className="text-right">Prev O→C %</th>
                                <th className="text-right">Today O→C %</th>
                                <th className="text-right">EMA 5</th>
                                <th className="text-right">EMA 10</th>
                                <th className="text-right">EMA 20</th>
                                <th className="text-right">W-EMA 4</th>
                                <th className="text-right">W-EMA 5</th>
                                <th className="text-right">W_L5-Open</th>
                                <th className="text-right">W_L5-Dist %</th>
                                <th className={`text-right sortable ${filters.sortBy === 'w_OtoC_pct_change' ? (filters.sortDir === 'asc' ? 'sort-asc' : 'sort-desc') : ''}`} onClick={() => toggleSort('w_OtoC_pct_change')}>
                                    W_O{'-'}{'>'}C %
                                </th>
                                <th className="text-center" style={{ width: '100px' }}>Last Updated</th>
                                <th className="text-center" style={{ width: '220px' }}>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stocks.map((stock) => {
                                const cp = parseFloat(stock.cp) || 0;
                                const ema5 = parseFloat(stock.ema5) || 0;
                                const ema10 = parseFloat(stock.ema10) || 0;
                                const ema20 = parseFloat(stock.ema20) || 0;
                                const cpClass = cp > ema10 ? 'cell-positive' : cp < ema10 ? 'cell-negative' : '';
                                const todayChange = parseFloat(stock.today_change_pct) || 0;

                                return (
                                    <tr key={stock.trading_symbol || stock.symbol}>
                                        <td><span className="badge badge-group">{stock.group || '-'}</span></td>
                                        <td>
                                            <div className="text-truncate" title={stock.stock_name || stock.name || '-'}>
                                                {stock.stock_name || stock.name || '-'}
                                            </div>
                                        </td>
                                        <td className="cell-symbol">
                                            <a
                                                href={`https://www.tradingview.com/chart/?symbol=NSE:${stock.trading_symbol || stock.symbol}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                style={{ color: 'var(--accent)', textDecoration: 'none' }}
                                            >
                                                {stock.trading_symbol || stock.symbol}
                                            </a>
                                        </td>
                                        <td className="text-right cell-muted">{formatCurrency(stock.ath)}</td>
                                        <td className="text-right cell-muted">{formatCurrency(stock.open)}</td>
                                        <td className={`text-right ${cpClass}`}>{formatCurrency(stock.cp)}</td>
                                        <td className="text-right cell-muted">{formatCurrency(stock.l5_open)}</td>
                                        <td className={`text-right ${parseFloat(stock.l5_open_dist_pct) > 0 ? 'cell-positive' : parseFloat(stock.l5_open_dist_pct) < 0 ? 'cell-negative' : 'cell-muted'}`}>
                                            {formatPercent(stock.l5_open_dist_pct)}
                                        </td>
                                        <td className="text-right">
                                            {formatPercent(stock.prev_change_pct)}
                                        </td>
                                        <td
                                            className={`text-right ${todayChange > 0
                                                ? 'cell-positive'
                                                : todayChange < 0
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
                                        <td className={`text-right ${parseFloat(stock.w_ema4) > parseFloat(stock.w_ema5) ? 'cell-positive' : 'cell-muted'}`}>
                                            {formatCurrency(stock.w_ema4)}
                                        </td>
                                        <td className={`text-right ${parseFloat(stock.w_ema4) > parseFloat(stock.w_ema5) ? 'cell-positive' : 'cell-muted'}`}>
                                            {formatCurrency(stock.w_ema5)}
                                        </td>
                                        <td className="text-right cell-muted">{formatCurrency(stock.w_l5_open)}</td>
                                        <td className={`text-right ${parseFloat(stock.weekly_l5_distance) > 0 ? 'cell-positive' : parseFloat(stock.weekly_l5_distance) < 0 ? 'cell-negative' : 'cell-muted'}`}>
                                            {formatPercent(stock.weekly_l5_distance)}
                                        </td>
                                        <td className={`text-right ${parseFloat(stock.w_OtoC_pct_change) > 0 ? 'cell-positive' : parseFloat(stock.w_OtoC_pct_change) < 0 ? 'cell-negative' : 'cell-muted'}`}>
                                            {formatPercent(stock.w_OtoC_pct_change)}
                                        </td>
                                        <td className="text-center cell-muted" style={{ fontSize: '0.85rem' }}>
                                            {formatRelativeTime(stock.last_updated)}
                                        </td>
                                        <td className="text-center">
                                            <div style={{ display: 'flex', gap: '4px', justifyContent: 'center', alignItems: 'center' }}>
                                                <button
                                                    className="btn btn-icon"
                                                    onClick={() => handleRefreshOne(stock.trading_symbol || stock.symbol)}
                                                    title="Refresh Price"
                                                    disabled={refreshingSymbol === (stock.trading_symbol || stock.symbol)}
                                                    style={{ padding: '4px', minWidth: 'unset' }}
                                                >
                                                    {refreshingSymbol === (stock.trading_symbol || stock.symbol) ? '↻' : '↻'}
                                                </button>
                                                <button
                                                    className="btn btn-primary"
                                                    style={{ fontSize: '0.65rem', padding: '5px 8px' }}
                                                    onClick={() => {
                                                        setAddPosStock(stock);
                                                        setAddPosForm({ quantity: 1, price: stock.cp, stoploss: stock.w_open || stock.open || 0 });
                                                    }}
                                                >
                                                    ADD POS
                                                </button>
                                                <button
                                                    className="btn btn-buy"
                                                    onClick={() => {
                                                        setBuyStock(stock);
                                                        setBuyForm({ quantity: 1, order_type: 'MARKET', price: '' });
                                                    }}
                                                    id={`btn-buy-${stock.trading_symbol || stock.symbol}`}
                                                    style={{ fontSize: '0.65rem', padding: '5px 8px' }}
                                                >
                                                    BUY
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Buy Modal */}
            <Modal
                isOpen={!!buyStock}
                onClose={() => setBuyStock(null)}
                title={`Buy ${buyStock?.trading_symbol || buyStock?.symbol || ''}`}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setBuyStock(null)}>Cancel</button>
                        <button
                            className="btn btn-buy"
                            onClick={handleBuy}
                            disabled={buying}
                            id="btn-confirm-buy"
                        >
                            {buying ? 'Placing...' : `Buy ${buyStock?.trading_symbol || buyStock?.symbol}`}
                        </button>
                    </>
                }
            >
                {buyStock && (
                    <>
                        <div style={{ background: 'var(--bg-input)', padding: 16, borderRadius: 8, marginBottom: 8 }}>
                            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 4 }}>
                                {buyStock.stock_name}
                            </div>
                            <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                                {formatCurrency(buyStock.cp)}
                            </div>
                            <span className={`badge ${buyStock.signal === 'Bullish' ? 'badge-bullish' : buyStock.signal === 'Bearish' ? 'badge-bearish' : 'badge-neutral'}`} style={{ marginTop: 8 }}>
                                {buyStock.signal}
                            </span>
                        </div>
                        <div className="form-row">
                            <div className="form-group">
                                <label className="form-label">Quantity</label>
                                <input
                                    className="input"
                                    type="number"
                                    min="1"
                                    value={buyForm.quantity}
                                    onChange={(e) => setBuyForm({ ...buyForm, quantity: e.target.value })}
                                    id="input-buy-qty"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Order Type</label>
                                <select
                                    className="select"
                                    value={buyForm.order_type}
                                    onChange={(e) => setBuyForm({ ...buyForm, order_type: e.target.value })}
                                >
                                    <option value="MARKET">Market</option>
                                    <option value="LIMIT">Limit</option>
                                </select>
                            </div>
                        </div>
                        {buyForm.order_type === 'LIMIT' && (
                            <div className="form-group">
                                <label className="form-label">Limit Price</label>
                                <input
                                    className="input"
                                    type="number"
                                    placeholder="Enter limit price"
                                    value={buyForm.price}
                                    onChange={(e) => setBuyForm({ ...buyForm, price: e.target.value })}
                                />
                            </div>
                        )}
                        <p className="text-muted" style={{ fontSize: '0.82rem' }}>
                            Estimated cost: {formatCurrency((parseFloat(buyStock.cp) || 0) * (parseInt(buyForm.quantity) || 1))}
                        </p>
                    </>
                )}
            </Modal>
            {/* Add Position Modal (Manual) */}
            <Modal
                isOpen={!!addPosStock}
                onClose={() => setAddPosStock(null)}
                title={`Add Position: ${addPosStock?.trading_symbol || addPosStock?.symbol}`}
                footer={
                    <>
                        <button className="btn btn-secondary" onClick={() => setAddPosStock(null)}>Cancel</button>
                        <button
                            className="btn btn-primary"
                            onClick={handleAddToPositions}
                            disabled={addingPos}
                        >
                            {addingPos ? 'Adding...' : 'Add Position'}
                        </button>
                    </>
                }
            >
                {addPosStock && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div style={{ background: 'var(--bg-input)', padding: '12px 16px', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Symbol / Name</div>
                            <div style={{ fontWeight: 600 }}>{addPosStock.trading_symbol || addPosStock.symbol}</div>
                            <div style={{ fontSize: '0.85rem' }}>{addPosStock.stock_name}</div>
                        </div>

                        <div className="form-row">
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Quantity</label>
                                <input
                                    className="input"
                                    type="number"
                                    min="1"
                                    value={addPosForm.quantity}
                                    onChange={(e) => setAddPosForm({ ...addPosForm, quantity: e.target.value })}
                                />
                            </div>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Buy Price</label>
                                <input
                                    className="input"
                                    type="number"
                                    step="0.05"
                                    value={addPosForm.price}
                                    onChange={(e) => setAddPosForm({ ...addPosForm, price: e.target.value })}
                                />
                                <div style={{ fontSize: '0.72rem', marginTop: 4, color: 'var(--text-muted)' }}>
                                    Live: {formatCurrency(addPosStock.cp)}
                                </div>
                            </div>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Stoploss</label>
                                <input
                                    className="input"
                                    type="number"
                                    step="0.05"
                                    value={addPosForm.stoploss}
                                    onChange={(e) => setAddPosForm({ ...addPosForm, stoploss: e.target.value })}
                                />
                                <div style={{ fontSize: '0.72rem', marginTop: 4, color: 'var(--text-muted)' }}>
                                    Open: {formatCurrency(addPosStock.open)}
                                </div>
                            </div>
                        </div>

                        <p className="text-muted" style={{ fontSize: '0.8rem', margin: 0 }}>
                            This will log the position as of <strong>today</strong>. You can override the price if needed.
                        </p>
                    </div>
                )}
            </Modal>
        </div>
    );
}
