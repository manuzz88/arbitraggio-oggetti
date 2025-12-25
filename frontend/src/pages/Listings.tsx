import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ExternalLink,
  Eye,
  Heart,
  ChevronLeft,
  ChevronRight,
  Package,
} from 'lucide-react'
import { listingsApi } from '@/services/api'
import { formatCurrency, formatDate, cn } from '@/lib/utils'

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  publishing: 'bg-yellow-100 text-yellow-700',
  active: 'bg-green-100 text-green-700',
  paused: 'bg-orange-100 text-orange-700',
  sold: 'bg-blue-100 text-blue-700',
  ended: 'bg-gray-100 text-gray-700',
  error: 'bg-red-100 text-red-700',
}

const statusLabels: Record<string, string> = {
  draft: 'Bozza',
  publishing: 'Pubblicazione...',
  active: 'Attivo',
  paused: 'In pausa',
  sold: 'Venduto',
  ended: 'Terminato',
  error: 'Errore',
}

export default function Listings() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()

  const { data, isLoading } = useQuery({
    queryKey: ['listings', page, statusFilter],
    queryFn: () => listingsApi.getAll({ page, per_page: 20, status: statusFilter }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Listings</h1>
          <p className="text-gray-500 mt-1">
            {data?.total || 0} listings totali
          </p>
        </div>

        {/* Status Filter */}
        <select
          value={statusFilter || ''}
          onChange={(e) => setStatusFilter(e.target.value || undefined)}
          className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Tutti gli stati</option>
          <option value="active">Attivi</option>
          <option value="draft">Bozze</option>
          <option value="sold">Venduti</option>
          <option value="ended">Terminati</option>
        </select>
      </div>

      {/* Listings Table */}
      {data?.listings.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Nessun listing</h3>
          <p className="text-gray-500 mt-1">
            I listings appariranno qui dopo l'approvazione degli items
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Prodotto
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Piattaforma
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Prezzo
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Performance
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stato
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Azioni
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data?.listings.map((listing: any) => (
                <tr key={listing.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      {listing.enhanced_images[0] && (
                        <img
                          src={listing.enhanced_images[0]}
                          alt=""
                          className="w-12 h-12 rounded-lg object-cover"
                        />
                      )}
                      <div className="max-w-xs">
                        <p className="font-medium text-gray-900 truncate">
                          {listing.enhanced_title}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600 capitalize">
                      {listing.platform}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-semibold text-gray-900">
                      {formatCurrency(listing.listing_price)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <Eye className="h-4 w-4" />
                        {listing.views}
                      </span>
                      <span className="flex items-center gap-1">
                        <Heart className="h-4 w-4" />
                        {listing.watchers}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={cn(
                        'px-2 py-1 rounded-full text-xs font-medium',
                        statusColors[listing.status] || 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {statusLabels[listing.status] || listing.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {listing.published_at
                      ? formatDate(listing.published_at)
                      : formatDate(listing.created_at)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {listing.listing_url && (
                      <a
                        href={listing.listing_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-700"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {data && data.total > 20 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Pagina {page}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={data.listings.length < 20}
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  )
}
