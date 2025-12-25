import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Package,
  ShoppingCart,
  TrendingUp,
  Clock,
  CheckCircle,
  Euro,
  Search,
  Loader2,
} from 'lucide-react'
import { analyticsApi, scraperApi } from '@/services/api'
import { formatCurrency } from '@/lib/utils'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  subtitle,
}: {
  title: string
  value: string | number
  icon: React.ElementType
  color: string
  subtitle?: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && (
            <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [searchQuery, setSearchQuery] = useState('')
  const [isScrapingStarted, setIsScrapingStarted] = useState(false)

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: analyticsApi.getDashboard,
    refetchInterval: 30000,
  })

  const { data: profitData } = useQuery({
    queryKey: ['daily-profit'],
    queryFn: () => analyticsApi.getDailyProfit(30),
  })

  const scrapeMutation = useMutation({
    mutationFn: (queries: string[]) => scraperApi.startScraping(queries),
    onSuccess: () => {
      setIsScrapingStarted(true)
      setTimeout(() => setIsScrapingStarted(false), 5000)
    },
  })

  const handleStartScraping = () => {
    const queries = searchQuery.split(',').map(q => q.trim()).filter(q => q)
    if (queries.length > 0) {
      scrapeMutation.mutate(queries)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">
            Panoramica del sistema di arbitraggio
          </p>
        </div>

        {/* Quick Scrape */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="es: iphone, nintendo switch"
            className="px-4 py-2 border border-gray-200 rounded-lg w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleStartScraping}
            disabled={scrapeMutation.isPending || !searchQuery}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {scrapeMutation.isPending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Search className="h-5 w-5" />
            )}
            Cerca
          </button>
          {isScrapingStarted && (
            <span className="text-green-600 text-sm">Scraping avviato!</span>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Items in attesa"
          value={stats?.items.pending || 0}
          icon={Clock}
          color="bg-yellow-500"
          subtitle="Da approvare"
        />
        <StatCard
          title="Listings attivi"
          value={stats?.listings.active || 0}
          icon={Package}
          color="bg-blue-500"
          subtitle="Su eBay"
        />
        <StatCard
          title="Ordini da gestire"
          value={stats?.orders.pending_action || 0}
          icon={ShoppingCart}
          color="bg-orange-500"
          subtitle="Azione richiesta"
        />
        <StatCard
          title="Profitto mensile"
          value={formatCurrency(stats?.profit.monthly || 0)}
          icon={Euro}
          color="bg-green-500"
          subtitle={`Totale: ${formatCurrency(stats?.profit.total || 0)}`}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Profit Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Profitto ultimi 30 giorni
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={profitData?.data || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => {
                    const date = new Date(value)
                    return `${date.getDate()}/${date.getMonth() + 1}`
                  }}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  formatter={(value: number) => [formatCurrency(value), 'Profitto']}
                  labelFormatter={(label) => {
                    const date = new Date(label)
                    return date.toLocaleDateString('it-IT')
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="profit"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Riepilogo
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
                <span className="text-gray-600">Ordini completati</span>
              </div>
              <span className="font-semibold text-gray-900">
                {stats?.orders.completed || 0}
              </span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Package className="h-5 w-5 text-blue-600" />
                </div>
                <span className="text-gray-600">Items approvati</span>
              </div>
              <span className="font-semibold text-gray-900">
                {stats?.items.approved || 0}
              </span>
            </div>
            <div className="flex items-center justify-between py-3 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-purple-600" />
                </div>
                <span className="text-gray-600">Items listati</span>
              </div>
              <span className="font-semibold text-gray-900">
                {stats?.items.listed || 0}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
