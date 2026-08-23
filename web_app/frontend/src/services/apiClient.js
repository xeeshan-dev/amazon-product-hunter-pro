import axios from 'axios'

export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

export const apiClient = axios.create({ baseURL: API_URL })

export function authenticatedClient(token) {
    return axios.create({
        baseURL: API_URL,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
}

export function getAccessToken() {
    return localStorage.getItem('trackingAccessToken')
}

export function authenticatedApi() {
    return authenticatedClient(getAccessToken())
}
