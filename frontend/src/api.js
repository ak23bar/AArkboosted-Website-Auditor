/**
 * API client for AArkboosted Audit Tool
 */


import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
});

export const auditsAPI = {
  create: async (data) => {
    const response = await api.post('/api/audits/', data);
    return response.data;
  },
  get: async (id) => {
    const response = await api.get(`/api/audits/${id}`);
    return response.data;
  },
  list: async () => {
    const response = await api.get('/api/audits/');
    return response.data;
  },
  clearAll: async () => {
    const response = await api.delete('/api/audits/');
    return response.data;
  },
  delete: async (id) => {
    const response = await api.delete(`/api/audits/${id}`);
    return response.data;
  },
}