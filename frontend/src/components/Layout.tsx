import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  ClipboardList,
  Settings,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Items', href: '/items', icon: Package },
  { name: 'Opportunità', href: '/opportunities', icon: Zap },
  { name: 'Listings', href: '/listings', icon: ClipboardList },
  { name: 'Ordini', href: '/orders', icon: ShoppingCart },
  { name: 'Impostazioni', href: '/settings', icon: Settings },
]

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200">
        <div className="flex items-center gap-2 h-16 px-6 border-b border-gray-200">
          <TrendingUp className="h-8 w-8 text-blue-600" />
          <span className="text-xl font-bold text-gray-900">Arbitraggio</span>
        </div>
        
        <nav className="p-4 space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )
              }
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="pl-64">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
