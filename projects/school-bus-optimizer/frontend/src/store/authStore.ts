import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { authApi } from '@/services/api/authApi'
import { User, LoginCredentials, RegisterData } from '@/types/auth'
import toast from 'react-hot-toast'

interface AuthState {
  user: User | null
  tokens: {
    accessToken: string
    refreshToken: string
  } | null
  isLoading: boolean
  isInitialized: boolean
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
  refreshTokens: () => Promise<boolean>
  initializeAuth: () => Promise<void>
  setUser: (user: User) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set, get) => ({
        user: null,
        tokens: null,
        isLoading: false,
        isInitialized: false,

        login: async (credentials) => {
          set({ isLoading: true })
          try {
            const response = await authApi.login(credentials)
            const { user, tokens } = response.data

            set({
              user,
              tokens,
              isLoading: false,
              isInitialized: true
            })

            toast.success(`Welcome back, ${user.firstName}!`)
          } catch (error: any) {
            set({ isLoading: false })
            const message = error.response?.data?.error?.message || 'Login failed'
            toast.error(message)
            throw error
          }
        },

        register: async (data) => {
          set({ isLoading: true })
          try {
            const response = await authApi.register(data)
            const { user, tokens } = response.data

            set({
              user,
              tokens,
              isLoading: false,
              isInitialized: true
            })

            toast.success('Account created successfully!')
          } catch (error: any) {
            set({ isLoading: false })
            const message = error.response?.data?.error?.message || 'Registration failed'
            toast.error(message)
            throw error
          }
        },

        logout: async () => {
          try {
            await authApi.logout()
          } catch (error) {
            // Continue with logout even if API call fails
            console.warn('Logout API call failed:', error)
          }

          set({
            user: null,
            tokens: null,
            isInitialized: true
          })

          toast.success('Logged out successfully')
        },

        refreshTokens: async () => {
          const { tokens } = get()
          if (!tokens?.refreshToken) {
            return false
          }

          try {
            const response = await authApi.refreshToken(tokens.refreshToken)
            const newTokens = response.data.tokens

            set({
              tokens: newTokens
            })

            return true
          } catch (error) {
            // Refresh failed, clear auth state
            get().clearAuth()
            return false
          }
        },

        initializeAuth: async () => {
          const { tokens } = get()
          
          if (tokens?.accessToken) {
            try {
              // Verify token by fetching user data
              const response = await authApi.getMe()
              const user = response.data.user

              set({
                user,
                isInitialized: true
              })
            } catch (error) {
              // Token is invalid, try to refresh
              const refreshSuccess = await get().refreshTokens()
              
              if (refreshSuccess) {
                // Try again with new token
                try {
                  const response = await authApi.getMe()
                  const user = response.data.user
                  
                  set({
                    user,
                    isInitialized: true
                  })
                } catch (error) {
                  get().clearAuth()
                }
              } else {
                get().clearAuth()
              }
            }
          } else {
            set({ isInitialized: true })
          }
        },

        setUser: (user) => {
          set({ user })
        },

        clearAuth: () => {
          set({
            user: null,
            tokens: null,
            isInitialized: true
          })
        }
      }),
      {
        name: 'auth-storage',
        partialize: (state) => ({
          tokens: state.tokens,
          user: state.user
        })
      }
    ),
    {
      name: 'auth-store'
    }
  )
)