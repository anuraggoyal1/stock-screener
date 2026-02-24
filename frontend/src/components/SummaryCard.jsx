export default function SummaryCard({ label, value, sub, type, size }) {
    const valueClass = type === 'positive' ? 'positive' : type === 'negative' ? 'negative' : '';
    const sizeClass = size === 'small' ? 'small' : '';

    return (
        <div className={`summary-card ${sizeClass}`}>
            <div className="summary-card-label">{label}</div>
            <div className={`summary-card-value ${valueClass}`}>{value}</div>
            {sub && <div className="summary-card-sub">{sub}</div>}
        </div>
    );
}
