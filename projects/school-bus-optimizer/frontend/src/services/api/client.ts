import axios, { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'

// Create axios instance
export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const tokens = useAuthStore.getState().tokens
    
    if (tokens?.accessToken) {
      config.headers.Authorization = `Bearer ${tokens.accessToken}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle auth errors and token refresh
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      const authStore = useAuthStore.getState()
      const refreshSuccess = await authStore.refreshTokens()
      
      if (refreshSuccess) {
        // Retry the original request with new token
        const newTokens = useAuthStore.getState().tokens
        if (newTokens?.accessToken) {
          originalRequest.headers.Authorization = `Bearer ${newTokens.accessToken}`
          return apiClient(originalRequest)
        }
      } else {
        // Refresh failed, redirect to login
        authStore.clearAuth()
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }
    
    // Handle other errors
    if (error.response?.status >= 500) {
      toast.error('Server error. Please try again later.')
    } else if (error.response?.status === 403) {
      toast.error('You do not have permission to perform this action.')
    } else if (error.code === 'ECONNABORTED') {
      toast.error('Request timed out. Please try again.')
    } else if (!error.response) {
      toast.error('Network error. Please check your connection.')
    }
    
    return Promise.reject(error)
  }
)

export default apiClient