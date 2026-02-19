import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { Layout } from '@/components/layout/Layout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { RoutesPage } from '@/pages/routes/RoutesPage'
import { StudentsPage } from '@/pages/students/StudentsPage'
import { BusesPage } from '@/pages/buses/BusesPage'
import { DriversPage } from '@/pages/drivers/DriversPage'
import { TrackingPage } from '@/pages/tracking/TrackingPage'
import { AnalyticsPage } from '@/pages/analytics/AnalyticsPage'
import { SettingsPage } from '@/pages/settings/SettingsPage'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useEffect } from 'react'

function App() {
  const { user, isLoading, initializeAuth } = useAuthStore()

  useEffect(() => {
    initializeAuth()
  }, [initializeAuth])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route 
        path="/login" 
        element={!user ? <LoginPage /> : <Navigate to="/" replace />} 
      />
      
      {/* Protected routes */}
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<DashboardPage />} />
        
        {/* Route management */}
        <Route path="routes" element={<RoutesPage />} />
        
        {/* Fleet management */}
        <Route path="students" element={<StudentsPage />} />
        <Route path="buses" element={<BusesPage />} />
        <Route path="drivers" element={<DriversPage />} />
        
        {/* Real-time tracking */}
        <Route path="tracking" element={<TrackingPage />} />
        
        {/* Analytics and reporting */}
        <Route path="analytics" element={<AnalyticsPage />} />
        
        {/* Settings */}
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      
      {/* Catch all - redirect to login or dashboard */}
      <Route 
        path="*" 
        element={<Navigate to={user ? "/" : "/login"} replace />} 
      />
    </Routes>
  )
}

export default App