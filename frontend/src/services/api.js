import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:8000/api');

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatically add API key to headers if present in localStorage
api.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('X-API-Key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

// Automatically handle unauthorized errors (401) by clearing the invalid key and reloading
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (localStorage.getItem('X-API-Key')) {
        localStorage.removeItem('X-API-Key');
        window.location.reload();
      }
    }
    return Promise.reject(error);
  }
);

// ---- Master List ----
export const masterAPI = {
  getAll: (group) => api.get('/master', { params: group ? { group } : {} }),
  getGroups: () => api.get('/master/groups'),
  getOne: (symbol) => api.get(`/master/${symbol}`),
  add: (stock) => api.post('/master', stock),
  update: (symbol, data) => api.put(`/master/${symbol}`, data),
  delete: (symbol) => api.delete(`/master/${symbol}`),
  refresh: () => api.post('/master/refresh'),
  refreshOne: (symbol) => api.post(`/master/${symbol}/refresh`),
  refreshWeekly: () => api.post('/master/refresh-weekly'),
  refreshOneWeekly: (symbol) => api.post(`/master/${symbol}/refresh-weekly`),
  refreshAthFromHistory: (symbol, years = 10) =>
    api.post(`/master/${symbol}/ath-from-history`, null, { params: { years } }),
};

// ---- Screener ----
export const screenerAPI = {
  getFiltered: (params) => api.get('/screener', { params }),
};

// ---- Positions ----
export const positionsAPI = {
  getAll: () => api.get('/positions'),
  add: (position) => api.post('/positions', position),
  update: (symbol, data, originalDetails) => api.put(`/positions/${symbol}`, data, { params: originalDetails }),
  delete: (symbol, params) => api.delete(`/positions/${symbol}`, { params }),
};

// ---- Orders ----
export const ordersAPI = {
  buy: (order) => api.post('/orders/buy', order),
  sell: (order) => api.post('/orders/sell', order),
};

// ---- Trade Log ----
export const tradelogAPI = {
  getAll: (params) => api.get('/tradelog', { params }),
  getSummary: () => api.get('/tradelog/summary'),
};

// ---- Upstox Auth ----
export const upstoxAPI = {
  getAuthUrl: () => api.get('/upstox/auth-url'),
  exchangeToken: (code) => api.get('/upstox/exchange-token', { params: { code } }),
  saveToken: (access_token) => api.post('/upstox/save-token', { access_token }),
};

// ---- Backtest ----
export const backtestAPI = {
  run: (params) => api.get('/backtest/run', { params }),
};

export default api;
