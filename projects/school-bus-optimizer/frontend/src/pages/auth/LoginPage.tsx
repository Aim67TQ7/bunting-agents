import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useAuthStore } from '@/store/authStore'
import { LoginCredentials } from '@/types/auth'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { TruckIcon } from '@heroicons/react/24/outline'

export function LoginPage() {
  const { login, isLoading } = useAuthStore()
  const [showTestCredentials, setShowTestCredentials] = useState(false)
  
  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue
  } = useForm<LoginCredentials>()

  const onSubmit = async (data: LoginCredentials) => {
    try {
      await login(data)
    } catch (error) {
      // Error is handled by the store and toast
    }
  }

  const testCredentials = [
    { email: 'admin@schoolbusoptimizer.com', password: 'superadmin123', role: 'Super Admin' },
    { email: 'admin@riversideschooldistrict.edu', password: 'admin123', role: 'District Admin' },
    { email: 'driver1@riversideschooldistrict.edu', password: 'driver123', role: 'Driver' },
    { email: 'parent1@email.com', password: 'parent123', role: 'Parent' },
  ]

  const useTestCredentials = (email: string, password: string) => {
    setValue('email', email)
    setValue('password', password)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex justify-center">
            <div className="flex items-center space-x-3">
              <TruckIcon className="h-12 w-12 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">SchoolBus</h1>
                <p className="text-sm text-gray-500">Optimizer</p>
              </div>
            </div>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Route optimization and fleet management for school districts
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          <div className="rounded-md shadow-sm space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                {...register('email', {
                  required: 'Email is required',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Invalid email address'
                  }
                })}
                type="email"
                autoComplete="email"
                className={`mt-1 input ${errors.email ? 'input-error' : ''}`}
                placeholder="Enter your email"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
              )}
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                {...register('password', {
                  required: 'Password is required',
                  minLength: {
                    value: 6,
                    message: 'Password must be at least 6 characters'
                  }
                })}
                type="password"
                autoComplete="current-password"
                className={`mt-1 input ${errors.password ? 'input-error' : ''}`}
                placeholder="Enter your password"
              />
              {errors.password && (
                <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
              )}
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading && <LoadingSpinner size="sm" className="mr-2" />}
              Sign in
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={() => setShowTestCredentials(!showTestCredentials)}
              className="text-sm text-primary-600 hover:text-primary-500"
            >
              {showTestCredentials ? 'Hide' : 'Show'} test credentials
            </button>
          </div>

          {showTestCredentials && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg">
              <h3 className="text-sm font-medium text-blue-900 mb-2">Test Accounts:</h3>
              <div className="space-y-2">
                {testCredentials.map((cred, index) => (
                  <div key={index} className="flex items-center justify-between text-xs">
                    <span className="text-blue-800">{cred.role}:</span>
                    <button
                      type="button"
                      onClick={() => useTestCredentials(cred.email, cred.password)}
                      className="text-blue-600 hover:text-blue-500 underline"
                    >
                      {cred.email}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}