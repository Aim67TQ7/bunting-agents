import { apiClient } from './client'
import { LoginCredentials, RegisterData, User, AuthResponse } from '@/types/auth'

export const authApi = {
  login: (credentials: LoginCredentials) => 
    apiClient.post<AuthResponse>('/auth/login', credentials),

  register: (data: RegisterData) => 
    apiClient.post<AuthResponse>('/auth/register', data),

  logout: () => 
    apiClient.post('/auth/logout'),

  refreshToken: (refreshToken: string) => 
    apiClient.post<{ tokens: { accessToken: string; refreshToken: string } }>('/auth/refresh', {
      refreshToken
    }),

  getMe: () => 
    apiClient.get<{ user: User }>('/auth/me'),

  changePassword: (data: { currentPassword: string; newPassword: string }) =>
    apiClient.post('/auth/change-password', data),

  forgotPassword: (email: string) =>
    apiClient.post('/auth/forgot-password', { email }),

  resetPassword: (data: { token: string; newPassword: string }) =>
    apiClient.post('/auth/reset-password', data)
}