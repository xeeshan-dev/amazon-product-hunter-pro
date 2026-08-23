import { apiClient, authenticatedApi } from './apiClient'

export const getDashboard = () => authenticatedApi().get('/dashboard')
export const getSearchHistory = (params) => authenticatedApi().get('/search/history', { params })
export const getSearchResults = (searchId, params) => authenticatedApi().get(`/search/${searchId}/results`, { params })
export const getProductAnalysis = (asin, marketplace) => apiClient.get(`/products/${asin}`, { params: { marketplace } })
export const getProductHistory = (asin, marketplace, days = 30) => apiClient.get(`/products/${asin}/history`, { params: { marketplace, days } })
