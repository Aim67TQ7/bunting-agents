import { NavLink } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import {
  HomeIcon,
  MapIcon,
  AcademicCapIcon,
  TruckIcon,
  UserGroupIcon,
  ClockIcon,
  ChartBarIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Routes', href: '/routes', icon: MapIcon },
  { name: 'Students', href: '/students', icon: AcademicCapIcon },
  { name: 'Buses', href: '/buses', icon: TruckIcon },
  { name: 'Drivers', href: '/drivers', icon: UserGroupIcon },
  { name: 'Tracking', href: '/tracking', icon: ClockIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
]

export function Sidebar() {
  const { user } = useAuthStore()

  // Filter navigation based on user role
  const filteredNavigation = navigation.filter(item => {
    if (user?.role === 'parent') {
      return ['Dashboard', 'Tracking'].includes(item.name)
    }
    if (user?.role === 'driver') {
      return ['Dashboard', 'Tracking', 'Routes'].includes(item.name)
    }
    return true // Admin and district_admin see all
  })

  return (
    <div className="fixed inset-y-0 z-50 flex w-72 flex-col">
      <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-white px-6 pb-4 shadow-lg">
        <div className="flex h-16 shrink-0 items-center">
          <div className="flex items-center space-x-3">
            <TruckIcon className="h-8 w-8 text-primary-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">SchoolBus</h1>
              <p className="text-xs text-gray-500">Optimizer</p>
            </div>
          </div>
        </div>
        
        <nav className="flex flex-1 flex-col">
          <ul role="list" className="flex flex-1 flex-col gap-y-7">
            <li>
              <ul role="list" className="-mx-2 space-y-1">
                {filteredNavigation.map((item) => (
                  <li key={item.name}>
                    <NavLink
                      to={item.href}
                      className={({ isActive }) =>
                        `group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold transition-colors ${
                          isActive
                            ? 'bg-primary-50 text-primary-600'
                            : 'text-gray-700 hover:text-primary-600 hover:bg-gray-50'
                        }`
                      }
                    >
                      <item.icon
                        className="h-6 w-6 shrink-0"
                        aria-hidden="true"
                      />
                      {item.name}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </li>
            
            <li className="mt-auto">
              <div className="rounded-lg bg-gray-50 p-4">
                <div className="flex items-center space-x-3">
                  <div className="h-10 w-10 rounded-full bg-primary-600 flex items-center justify-center">
                    <span className="text-white font-semibold">
                      {user?.firstName?.[0]}{user?.lastName?.[0]}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {user?.firstName} {user?.lastName}
                    </p>
                    <p className="text-xs text-gray-500 capitalize">
                      {user?.role?.replace('_', ' ')}
                    </p>
                  </div>
                </div>
              </div>
            </li>
          </ul>
        </nav>
      </div>
    </div>
  )
}