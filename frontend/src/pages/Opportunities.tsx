import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Search, 
  Zap, 
  ExternalLink, 
  CheckCircle, 
  XCircle,
  AlertTriangle,
  Eye,
  DollarSign,
  Target,
  Loader2,
  RefreshCw,
  Package
} from 'lucide-react'
import { aiApi, itemsApi, Opportunity, AIAnalysis } from '../services/api'

function ScoreBadge({ score }: { score: number }) {
  const getColor = () => {
    if (score >= 80) return 'bg-green-100 text-green-800 border-green-200'
    if (score >= 60) return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    return 'bg-red-100 text-red-800 border-red-200'
  }

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-bold border ${getColor()}`}>
      {score}/100
    </span>
  )
}

function RecommendationBadge({ recommendation }: { recommendation: string }) {
  const config = {
    BUY: { icon: CheckCircle, color: 'bg-green-500 text-white', label: 'COMPRA' },
    WATCH: { icon: Eye, color: 'bg-yellow-500 text-white', label: 'OSSERVA' },
    SKIP: { icon: XCircle, color: 'bg-red-500 text-white', label: 'SALTA' },
  }[recommendation] || { icon: AlertTriangle, color: 'bg-gray-500 text-white', label: recommendation }

  const Icon = config.icon

  return (
    <span className={`px-3 py-1 rounded-lg text-sm font-bold flex items-center gap-1 ${config.color}`}>
      <Icon className="h-4 w-4" />
      {config.label}
    </span>
  )
}

function OpportunityCard({ 
  opportunity, 
  onApprove, 
  onReject 
}: { 
  opportunity: Opportunity
  onApprove: (id: string) => void
  onReject: (id: string) => void
}) {
  const { item, analysis } = opportunity
  const profit = analysis.estimated_value_min - item.original_price

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow">
      {/* Header con Score */}
      <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-blue-50 to-purple-50">
        <div className="flex items-center gap-3">
          <Target className="h-5 w-5 text-blue-600" />
          <ScoreBadge score={analysis.score} />
        </div>
        <RecommendationBadge recommendation={analysis.recommendation} />
      </div>

      {/* Immagine */}
      <div className="aspect-video relative overflow-hidden bg-gray-100">
        {item.original_images && item.original_images.length > 0 ? (
          <img
            src={item.original_images[0]}
            alt={item.original_title}
            className="w-full h-full object-cover"
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.onerror = null;
              target.src = '';
              target.parentElement!.innerHTML = `
                <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
                  <div class="text-center text-gray-400">
                    <svg class="h-12 w-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>
                    </svg>
                  </div>
                </div>
              `;
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
            <Package className="h-12 w-12 text-gray-400" />
          </div>
        )}
        {/* Badge prezzo */}
        <div className="absolute top-2 right-2 bg-black/70 text-white px-2 py-1 rounded text-xs font-bold">
          €{item.original_price}
        </div>
        {/* Badge categoria */}
        <div className="absolute bottom-2 left-2 bg-black/70 text-white px-2 py-1 rounded text-xs">
          {analysis.category}
        </div>
      </div>

      {/* Info prodotto */}
      <div className="p-4 space-y-3">
        <h3 className="font-semibold text-gray-900 line-clamp-2">{item.original_title}</h3>
        
        {/* Brand/Model */}
        {(analysis.brand || analysis.model) && (
          <p className="text-sm text-gray-500">
            {analysis.brand} {analysis.model}
          </p>
        )}

        {/* Prezzi */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-red-50 rounded-lg p-2 text-center">
            <p className="text-xs text-red-600 font-medium">Prezzo Subito</p>
            <p className="text-lg font-bold text-red-700">€{item.original_price}</p>
          </div>
          <div className="bg-green-50 rounded-lg p-2 text-center">
            <p className="text-xs text-green-600 font-medium">Valore Stimato</p>
            <p className="text-lg font-bold text-green-700">
              €{analysis.estimated_value_min}-{analysis.estimated_value_max}
            </p>
          </div>
        </div>

        {/* Margine */}
        <div className="bg-blue-50 rounded-lg p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-medium text-blue-800">Profitto Potenziale</span>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold text-blue-700">+€{profit.toFixed(0)}</p>
            <p className="text-xs text-blue-600">+{analysis.margin_percentage}%</p>
          </div>
        </div>

        {/* Reasoning */}
        <p className="text-sm text-gray-600 line-clamp-2">{analysis.reasoning}</p>

        {/* Red flags */}
        {analysis.red_flags && analysis.red_flags.length > 0 && (
          <div className="flex items-start gap-2 text-amber-600 text-sm">
            <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <span>{analysis.red_flags.join(', ')}</span>
          </div>
        )}

        {/* Location */}
        {item.original_location && (
          <p className="text-xs text-gray-400">📍 {item.original_location}</p>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-gray-100 flex gap-2">
        <button
          onClick={() => onApprove(item.id)}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <CheckCircle className="h-4 w-4" />
          Acquista
        </button>
        <button
          onClick={() => onReject(item.id)}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
        >
          <XCircle className="h-4 w-4" />
          Salta
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
  )
}

export default function Opportunities() {
  const [minPrice, setMinPrice] = useState(30)
  const [maxPrice, setMaxPrice] = useState(500)
  const [limit, setLimit] = useState(10)
  const queryClient = useQueryClient()

  const { data: opportunities, isLoading, refetch } = useQuery({
    queryKey: ['opportunities'],
    queryFn: () => aiApi.getOpportunities(60),
    staleTime: 0,
  })

  const analyzeMutation = useMutation({
    mutationFn: () => aiApi.analyzePending({ limit, min_price: minPrice, max_price: maxPrice }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      queryClient.invalidateQueries({ queryKey: ['pending-items'] })
      alert(`Analizzati ${data.analyzed} items. Trovate ${data.opportunities_found} opportunità!`)
    },
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => itemsApi.approve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      queryClient.invalidateQueries({ queryKey: ['pending-items'] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (id: string) => itemsApi.reject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      queryClient.invalidateQueries({ queryKey: ['pending-items'] })
    },
  })

  // Filtra solo items con ai_score
  const analyzedItems = opportunities?.items.filter(item => item.ai_score && item.ai_score >= 60) || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Zap className="h-7 w-7 text-yellow-500" />
            Opportunità di Arbitraggio
          </h1>
          <p className="text-gray-500 mt-1">
            Prodotti analizzati dall'AI con alto potenziale di profitto
          </p>
        </div>
      </div>

      {/* Controlli Analisi */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Search className="h-5 w-5 text-blue-600" />
          Analizza Nuovi Items
        </h3>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Prezzo Min</label>
            <input
              type="number"
              value={minPrice}
              onChange={(e) => setMinPrice(Number(e.target.value))}
              className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Prezzo Max</label>
            <input
              type="number"
              value={maxPrice}
              onChange={(e) => setMaxPrice(Number(e.target.value))}
              className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Limite Items</label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={() => analyzeMutation.mutate()}
            disabled={analyzeMutation.isPending}
            className="px-6 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {analyzeMutation.isPending ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Analizzando...
              </>
            ) : (
              <>
                <Zap className="h-5 w-5" />
                Analizza con AI
              </>
            )}
          </button>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
          >
            <RefreshCw className="h-5 w-5" />
            Aggiorna
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-green-50 rounded-xl p-4 border border-green-200">
          <p className="text-sm text-green-600 font-medium">Opportunità BUY</p>
          <p className="text-2xl font-bold text-green-700">
            {analyzedItems.filter(i => i.ai_validation?.recommendation === 'BUY').length}
          </p>
        </div>
        <div className="bg-yellow-50 rounded-xl p-4 border border-yellow-200">
          <p className="text-sm text-yellow-600 font-medium">Da Osservare</p>
          <p className="text-2xl font-bold text-yellow-700">
            {analyzedItems.filter(i => i.ai_validation?.recommendation === 'WATCH').length}
          </p>
        </div>
        <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
          <p className="text-sm text-blue-600 font-medium">Totale Analizzati</p>
          <p className="text-2xl font-bold text-blue-700">{analyzedItems.length}</p>
        </div>
      </div>

      {/* Grid Opportunità */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        </div>
      ) : analyzedItems.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Zap className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Nessuna opportunità trovata</h3>
          <p className="text-gray-500 mt-1">
            Clicca "Analizza con AI" per trovare opportunità di arbitraggio
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {analyzedItems
            .sort((a, b) => (b.ai_score || 0) - (a.ai_score || 0))
            .map((item) => (
              <OpportunityCard
                key={item.id}
                opportunity={{
                  item,
                  analysis: (item.ai_validation as unknown as AIAnalysis) || {
                    score: item.ai_score || 0,
                    category: item.ai_category || 'Altro',
                    brand: item.ai_brand,
                    model: item.ai_model,
                    estimated_value_min: item.estimated_value_min || 0,
                    estimated_value_max: item.estimated_value_max || 0,
                    margin_percentage: item.potential_margin || 0,
                    recommendation: 'WATCH',
                    reasoning: '',
                    red_flags: [],
                    selling_tips: '',
                  }
                }}
                onApprove={(id) => approveMutation.mutate(id)}
                onReject={(id) => rejectMutation.mutate(id)}
              />
            ))}
        </div>
      )}
    </div>
  )
}
