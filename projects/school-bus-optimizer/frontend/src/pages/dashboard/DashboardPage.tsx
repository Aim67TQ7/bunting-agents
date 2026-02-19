import { useAuthStore } from '@/store/authStore'
import {
  TruckIcon,
  AcademicCapIcon,
  UserGroupIcon,
  MapIcon,
  ClockIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'

const stats = [
  { name: 'Total Students', value: '1,234', icon: AcademicCapIcon, change: '+4.75%', changeType: 'positive' },
  { name: 'Active Buses', value: '28', icon: TruckIcon, change: '+2.02%', changeType: 'positive' },
  { name: 'Total Routes', value: '45', icon: MapIcon, change: '-1.39%', changeType: 'negative' },
  { name: 'Active Drivers', value: '32', icon: UserGroupIcon, change: '+0.00%', changeType: 'neutral' },
]

const recentActivity = [
  { id: 1, activity: 'Route 15 optimization completed', time: '2 minutes ago', type: 'success' },
  { id: 2, activity: 'Bus 102 reported mechanical issue', time: '15 minutes ago', type: 'warning' },
  { id: 3, activity: 'New student enrolled: Sarah Johnson', time: '1 hour ago', type: 'info' },
  { id: 4, activity: 'Driver training session scheduled', time: '2 hours ago', type: 'info' },
]

export function DashboardPage() {
  const { user } = useAuthStore()

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl sm:tracking-tight">
          {getGreeting()}, {user?.firstName}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Here's what's happening with your school transportation today.
        </p>
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        {stats.map((stat) => (
          <div key={stat.name} className="stat-card">
            <div className="stat-card-content">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <stat.icon className="h-6 w-6 text-gray-400" aria-hidden="true" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="stat-label">{stat.name}</dt>
                    <dd className="flex items-baseline">
                      <div className="stat-value">{stat.value}</div>
                      <div
                        className={`ml-2 flex items-baseline text-sm font-semibold ${
                          stat.changeType === 'positive'
                            ? 'text-green-600'
                            : stat.changeType === 'negative'
                            ? 'text-red-600'
                            : 'text-gray-500'
                        }`}
                      >
                        {stat.change}
                      </div>
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Activity */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Recent Activity</h3>
          </div>
          <div className="card-body">
            <div className="flow-root">
              <ul role="list" className="-mb-8">
                {recentActivity.map((item, itemIdx) => (
                  <li key={item.id}>
                    <div className="relative pb-8">
                      {itemIdx !== recentActivity.length - 1 ? (
                        <span
                          className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"
                          aria-hidden="true"
                        />
                      ) : null}
                      <div className="relative flex space-x-3">
                        <div>
                          <span
                            className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${
                              item.type === 'success'
                                ? 'bg-green-500'
                                : item.type === 'warning'
                                ? 'bg-yellow-500'
                                : 'bg-blue-500'
                            }`}
                          >
                            <ClockIcon className="h-5 w-5 text-white" aria-hidden="true" />
                          </span>
                        </div>
                        <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                          <div>
                            <p className="text-sm text-gray-500">{item.activity}</p>
                          </div>
                          <div className="text-right text-sm whitespace-nowrap text-gray-500">
                            {item.time}
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Quick Actions</h3>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-2 gap-4">
              <button className="btn-primary">
                <MapIcon className="h-5 w-5 mr-2" />
                Optimize Routes
              </button>
              <button className="btn-outline">
                <AcademicCapIcon className="h-5 w-5 mr-2" />
                Add Student
              </button>
              <button className="btn-outline">
                <TruckIcon className="h-5 w-5 mr-2" />
                View Buses
              </button>
              <button className="btn-outline">
                <ChartBarIcon className="h-5 w-5 mr-2" />
                View Reports
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}