export interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  role: 'admin' | 'district_admin' | 'driver' | 'parent'
  districtId: string
  phone?: string
  active: boolean
  district?: {
    id: string
    name: string
    subscriptionTier: string
  }
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  firstName: string
  lastName: string
  districtId: string
  role: 'district_admin' | 'driver' | 'parent'
  phone?: string
}

export interface AuthResponse {
  success: boolean
  user: User
  tokens: {
    accessToken: string
    refreshToken: string
  }
}