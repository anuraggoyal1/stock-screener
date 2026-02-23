import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ---- Master List ----
export const masterAPI = {
  getAll: (group) => api.get('/master', { params: group ? { group } : {} }),
  getGroups: () => api.get('/master/groups'),
  getOne: (symbol) => api.get(`/master/${symbol}`),
  add: (stock) => api.post('/master', stock),
  update: (symbol, data) => api.put(`/master/${symbol}`, data),
  delete: (symbol) => api.delete(`/master/${symbol}`),
  refresh: () => api.post('/master/refresh'),
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
  delete: (symbol) => api.delete(`/positions/${symbol}`),
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

export default api;
