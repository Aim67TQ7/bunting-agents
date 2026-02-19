// Common types used throughout the application

export interface District {
  id: string
  name: string
  address: string
  contactEmail: string
  contactPhone: string
  subscriptionTier: 'trial' | 'basic' | 'professional' | 'enterprise'
  subscriptionExpiresAt?: Date
  settings: DistrictSettings
  active: boolean
  createdAt: Date
  updatedAt: Date
}

export interface DistrictSettings {
  maxRouteTime: number
  maxWalkDistance: number
  defaultPickupBuffer: number
  notificationSettings: {
    smsEnabled: boolean
    emailEnabled: boolean
    pushEnabled: boolean
  }
  routeOptimizationSettings: {
    algorithm: 'nearest-neighbor' | 'genetic' | 'simulated-annealing'
    optimizeFor: 'distance' | 'time' | 'balanced'
  }
}

export interface School {
  id: string
  districtId: string
  name: string
  address: string
  lat: number
  lng: number
  startTime: string
  endTime: string
  principalName?: string
  contactEmail?: string
  contactPhone?: string
  active: boolean
}

export interface Student {
  id: string
  schoolId: string
  firstName: string
  lastName: string
  grade: string
  address: string
  lat: number
  lng: number
  parentName?: string
  parentEmail?: string
  parentPhone?: string
  hasSpecialNeeds: boolean
  specialNeedsInfo?: string
  photoUrl?: string
  preferredPickupTime?: string
  preferredDropoffTime?: string
  active: boolean
  school?: School
  fullName: string
}

export interface Bus {
  id: string
  districtId: string
  driverId?: string
  vehicleNumber: string
  capacity: number
  make?: string
  model?: string
  year?: number
  licensePlate?: string
  status: 'active' | 'maintenance' | 'out-of-service'
  lastMaintenanceDate?: Date
  nextMaintenanceDate?: Date
  mileage: number
  hasWheelchairLift: boolean
  hasAirConditioning: boolean
  features: string[]
  active: boolean
  driver?: Driver
}

export interface Driver {
  id: string
  districtId: string
  firstName: string
  lastName: string
  licenseNumber: string
  licenseExpiryDate: Date
  email?: string
  phone: string
  emergencyContact?: string
  emergencyPhone?: string
  address?: string
  hireDate?: Date
  hasCommercialLicense: boolean
  hasPassedBackgroundCheck: boolean
  hasPassedDrugTest: boolean
  lastDrugTestDate?: Date
  lastTrainingDate?: Date
  photoUrl?: string
  rating: number
  totalTrips: number
  active: boolean
  fullName: string
}

export interface Route {
  id: string
  districtId: string
  busId?: string
  routeName: string
  routeType: 'morning' | 'afternoon' | 'both'
  totalDistance: number
  totalTime: number
  totalStudents: number
  startTime?: string
  endTime?: string
  polyline?: any
  directions?: any
  optimizedAt?: Date
  optimizationMethod?: string
  estimatedFuelCost?: number
  active: boolean
  activeDays: string[]
  bus?: Bus
  stops?: RouteStop[]
}

export interface RouteStop {
  id: string
  routeId: string
  studentId: string
  stopOrder: number
  stopType: 'pickup' | 'dropoff'
  scheduledTime: string
  estimatedTime?: string
  actualTime?: string
  address: string
  lat: number
  lng: number
  distanceFromPrevious?: number
  timeFromPrevious?: number
  isClusterStop: boolean
  clusteredStudentIds: string[]
  notes?: string
  student?: Student
}

export interface GPSTracking {
  id: string
  busId: string
  lat: number
  lng: number
  speed?: number
  heading?: number
  altitude?: number
  accuracy?: number
  engineStatus?: string
  fuelLevel?: number
  odometer?: number
  timestamp: Date
}

// API Response types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: {
    message: string
    code?: string
  }
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    limit: number
    total: number
    pages: number
  }
}

// Form types
export interface PaginationParams {
  page?: number
  limit?: number
  sortBy?: string
  sortOrder?: 'ASC' | 'DESC'
}

export interface DateRange {
  startDate: Date
  endDate: Date
}

// Optimization types
export interface OptimizationOptions {
  schoolIds?: string[]
  routeType: 'morning' | 'afternoon' | 'both'
  constraints?: {
    maxRouteTime?: number
    maxWalkDistance?: number
    earliestPickupTime?: string
    optimizeFor?: 'distance' | 'time' | 'balanced'
  }
}

// Analytics types
export interface DistrictAnalytics {
  totalStudents: number
  totalBuses: number
  totalRoutes: number
  totalDrivers: number
  averageRouteTime: number
  averageRouteDistance: number
  fuelCostSavings: number
  timeSavings: number
  efficiencyScore: number
}

export interface RoutePerformance {
  routeId: string
  onTimePercentage: number
  averageDelay: number
  fuelEfficiency: number
  studentSatisfaction: number
  driverRating: number
}

// WebSocket types
export interface GPSUpdate {
  busId: string
  lat: number
  lng: number
  speed?: number
  heading?: number
  timestamp: Date
}

export interface BusStatus {
  busId: string
  status: string
  message?: string
  timestamp: Date
}

export interface ETAUpdate {
  stopId: string
  studentId: string
  eta: Date
  estimatedMinutes: number
}