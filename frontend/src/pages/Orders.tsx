import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ShoppingCart,
  ChevronLeft,
  ChevronRight,
  Truck,
  CheckCircle,
  Package,
} from 'lucide-react'
import { ordersApi } from '@/services/api'
import { formatCurrency, formatDate, cn } from '@/lib/utils'

const statusColors: Record<string, string> = {
  pending_purchase: 'bg-yellow-100 text-yellow-700',
  purchased: 'bg-blue-100 text-blue-700',
  shipped_to_me: 'bg-purple-100 text-purple-700',
  received: 'bg-indigo-100 text-indigo-700',
  shipped_to_buyer: 'bg-cyan-100 text-cyan-700',
  delivered: 'bg-teal-100 text-teal-700',
  completed: 'bg-green-100 text-green-700',
  refunded: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-700',
}

const statusLabels: Record<string, string> = {
  pending_purchase: 'Da acquistare',
  purchased: 'Acquistato',
  shipped_to_me: 'In arrivo',
  received: 'Ricevuto',
  shipped_to_buyer: 'Spedito',
  delivered: 'Consegnato',
  completed: 'Completato',
  refunded: 'Rimborsato',
  cancelled: 'Cancellato',
}

export default function Orders() {
  const [page, setPage] = useState(1)
  const [showPendingOnly, setShowPendingOnly] = useState(true)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['orders', page, showPendingOnly],
    queryFn: () =>
      showPendingOnly
        ? ordersApi.getPending({ page, per_page: 20 })
        : ordersApi.getAll({ page, per_page: 20 }),
  })

  const completeMutation = useMutation({
    mutationFn: (id: string) => ordersApi.complete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
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
          <h1 className="text-2xl font-bold text-gray-900">Ordini</h1>
          <p className="text-gray-500 mt-1">
            {data?.total || 0} ordini{' '}
            {showPendingOnly ? 'da gestire' : 'totali'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPendingOnly(true)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              showPendingOnly
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            Da gestire
          </button>
          <button
            onClick={() => setShowPendingOnly(false)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              !showPendingOnly
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            Tutti
          </button>
        </div>
      </div>

      {/* Orders List */}
      {data?.orders.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <ShoppingCart className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Nessun ordine</h3>
          <p className="text-gray-500 mt-1">
            Gli ordini appariranno qui quando venderai qualcosa
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {data?.orders.map((order: any) => (
            <div
              key={order.id}
              className="bg-white rounded-xl border border-gray-200 p-6"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span
                      className={cn(
                        'px-2 py-1 rounded-full text-xs font-medium',
                        statusColors[order.status] || 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {statusLabels[order.status] || order.status}
                    </span>
                    {order.platform_order_id && (
                      <span className="text-sm text-gray-500">
                        #{order.platform_order_id}
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                    <div>
                      <p className="text-sm text-gray-500">Venduto a</p>
                      <p className="font-semibold text-gray-900">
                        {formatCurrency(order.sale_price)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Costo acquisto</p>
                      <p className="font-semibold text-gray-900">
                        {order.purchase_price
                          ? formatCurrency(order.purchase_price)
                          : '-'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Profitto netto</p>
                      <p
                        className={cn(
                          'font-semibold',
                          order.net_profit && order.net_profit > 0
                            ? 'text-green-600'
                            : 'text-gray-900'
                        )}
                      >
                        {order.net_profit
                          ? formatCurrency(order.net_profit)
                          : '-'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Data vendita</p>
                      <p className="text-gray-900">{formatDate(order.sold_at)}</p>
                    </div>
                  </div>

                  {order.buyer_username && (
                    <p className="text-sm text-gray-500 mt-3">
                      Acquirente: {order.buyer_username}
                    </p>
                  )}

                  {order.tracking_number && (
                    <p className="text-sm text-gray-500 mt-1">
                      Tracking: {order.tracking_number}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2 ml-4">
                  {order.status === 'pending_purchase' && (
                    <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">
                      <Package className="h-4 w-4" />
                      Segna acquistato
                    </button>
                  )}
                  {order.status === 'received' && (
                    <button className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm">
                      <Truck className="h-4 w-4" />
                      Segna spedito
                    </button>
                  )}
                  {order.status === 'shipped_to_buyer' && (
                    <button
                      onClick={() => completeMutation.mutate(order.id)}
                      className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm"
                    >
                      <CheckCircle className="h-4 w-4" />
                      Completa
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
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
          <span className="px-4 py-2 text-sm text-gray-600">Pagina {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={data.orders.length < 20}
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  )
}
