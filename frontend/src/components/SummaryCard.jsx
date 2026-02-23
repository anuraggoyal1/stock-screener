export default function SummaryCard({ label, value, sub, type }) {
    const valueClass = type === 'positive' ? 'positive' : type === 'negative' ? 'negative' : '';

    return (
        <div className="summary-card">
            <div className="summary-card-label">{label}</div>
            <div className={`summary-card-value ${valueClass}`}>{value}</div>
            {sub && <div className="summary-card-sub">{sub}</div>}
        </div>
    );
}
