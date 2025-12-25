import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Check,
  X,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Star,
  MapPin,
  AlertCircle,
  Package,
} from 'lucide-react'
import { itemsApi, Item } from '@/services/api'
import { formatCurrency, cn } from '@/lib/utils'

function ItemCard({
  item,
  onApprove,
  onReject,
}: {
  item: Item
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  const [_showDetails, _setShowDetails] = useState(false)
  const aiValidation = item.ai_validation as Record<string, unknown> | null

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
      {/* Image */}
      <div className="relative aspect-square bg-gray-100">
        {item.original_images[0] ? (
          <img
            src={item.original_images[0]}
            alt={item.original_title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            No image
          </div>
        )}
        
        {/* Score badge */}
        {item.ai_score && (
          <div
            className={cn(
              'absolute top-3 right-3 px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1',
              item.ai_score >= 7
                ? 'bg-green-500 text-white'
                : item.ai_score >= 5
                ? 'bg-yellow-500 text-white'
                : 'bg-red-500 text-white'
            )}
          >
            <Star className="h-3 w-3" />
            {item.ai_score}/10
          </div>
        )}

        {/* Source badge */}
        <div className="absolute top-3 left-3 px-2 py-1 bg-black/70 text-white rounded-full text-xs">
          {item.source_platform}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 line-clamp-2 mb-2">
          {item.original_title}
        </h3>

        <div className="flex items-center justify-between mb-3">
          <span className="text-xl font-bold text-blue-600">
            {formatCurrency(item.original_price)}
          </span>
          {item.estimated_value_max && (
            <span className="text-sm text-gray-500">
              Stima: {formatCurrency(item.estimated_value_min || 0)} -{' '}
              {formatCurrency(item.estimated_value_max)}
            </span>
          )}
        </div>

        {/* AI Info */}
        {aiValidation && (
          <div className="space-y-2 mb-4">
            {aiValidation.categoria ? (
              <div className="text-sm text-gray-600">
                <span className="font-medium">Categoria:</span>{' '}
                <span>{String(aiValidation.categoria)}</span>
              </div>
            ) : null}
            {aiValidation.brand ? (
              <div className="text-sm text-gray-600">
                <span className="font-medium">Brand:</span>{' '}
                <span>{String(aiValidation.brand)}</span>
              </div>
            ) : null}
            {aiValidation.stato ? (
              <div className="text-sm text-gray-600">
                <span className="font-medium">Condizioni:</span>{' '}
                <span>{String(aiValidation.stato)}</span>
              </div>
            ) : null}
            {item.potential_margin && (
              <div className="text-sm text-green-600 font-medium">
                Margine potenziale: +{item.potential_margin.toFixed(0)}%
              </div>
            )}
          </div>
        )}

        {/* Location */}
        {item.original_location ? (
          <div className="flex items-center gap-1 text-sm text-gray-500 mb-3">
            <MapPin className="h-4 w-4" />
            <span>{item.original_location}</span>
          </div>
        ) : null}

        {/* Recommendation */}
        {aiValidation?.raccomandazione && (
          <div
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm mb-4',
              aiValidation.raccomandazione === 'APPROVA'
                ? 'bg-green-50 text-green-700'
                : aiValidation.raccomandazione === 'RIFIUTA'
                ? 'bg-red-50 text-red-700'
                : 'bg-yellow-50 text-yellow-700'
            )}
          >
            <AlertCircle className="h-4 w-4" />
            {aiValidation.motivo_raccomandazione as string}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => onApprove(item.id)}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Check className="h-4 w-4" />
            Approva
          </button>
          <button
            onClick={() => onReject(item.id)}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            <X className="h-4 w-4" />
            Rifiuta
          </button>
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <ExternalLink className="h-5 w-5 text-gray-600" />
          </a>
        </div>
      </div>
    </div>
  )
}

export default function Items() {
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['pending-items', page],
    queryFn: () => itemsApi.getPending({ page, per_page: 12 }),
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => itemsApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-items'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (id: string) => itemsApi.reject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-items'] })
    },
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
          <h1 className="text-2xl font-bold text-gray-900">Items da approvare</h1>
          <p className="text-gray-500 mt-1">
            {data?.total || 0} items in attesa di approvazione
          </p>
        </div>
      </div>

      {/* Items Grid */}
      {data?.items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Nessun item in attesa</h3>
          <p className="text-gray-500 mt-1">
            Gli items trovati dallo scraper appariranno qui
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {data?.items.map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              onApprove={(id) => approveMutation.mutate(id)}
              onReject={(id) => rejectMutation.mutate(id)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Pagina {page} di {data.pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
            disabled={page === data.pages}
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  )
}
