import { useState, useEffect, useCallback } from 'react';

export default function Toast({ toasts, removeToast }) {
    return (
        <div className="toast-container">
            {toasts.map((toast) => (
                <ToastItem key={toast.id} toast={toast} onRemove={() => removeToast(toast.id)} />
            ))}
        </div>
    );
}

function ToastItem({ toast, onRemove }) {
    useEffect(() => {
        const timer = setTimeout(onRemove, 4000);
        return () => clearTimeout(timer);
    }, [onRemove]);

    const icon = toast.type === 'success' ? '✓' : toast.type === 'error' ? '✕' : 'ℹ';

    return (
        <div className={`toast toast-${toast.type}`}>
            <span style={{ fontSize: '1.1rem' }}>{icon}</span>
            <span className="toast-message">{toast.message}</span>
        </div>
    );
}

// Custom hook for toast management
export function useToast() {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info') => {
        const id = Date.now() + Math.random();
        setToasts((prev) => [...prev, { id, message, type }]);
    }, []);

    const removeToast = useCallback((id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return { toasts, addToast, removeToast };
}
