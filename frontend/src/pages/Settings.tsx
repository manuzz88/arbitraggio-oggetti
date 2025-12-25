import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Save, Key, Bell, Cpu, Globe, Play, Square, Send, 
  Loader2, Clock, Smartphone, Gamepad2, Apple, Package, 
  Camera, Headphones, Footprints
} from 'lucide-react'
import { schedulerApi } from '../services/api'

const categoryIcons: Record<string, any> = {
  smartphone: Smartphone,
  gaming: Gamepad2,
  apple: Apple,
  vintage: Package,
  lego: Package,
  audio: Headphones,
  fotografia: Camera,
  sneakers: Footprints,
}

export default function Settings() {
  const [saved, setSaved] = useState(false)
  const queryClient = useQueryClient()

  const { data: schedulerStatus } = useQuery({
    queryKey: ['scheduler-status'],
    queryFn: schedulerApi.getStatus,
    refetchInterval: 5000,
  })

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: schedulerApi.getCategories,
  })

  const startMutation = useMutation({
    mutationFn: schedulerApi.start,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler-status'] }),
  })

  const stopMutation = useMutation({
    mutationFn: schedulerApi.stop,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler-status'] }),
  })

  const testTelegramMutation = useMutation({
    mutationFn: schedulerApi.testTelegram,
    onSuccess: () => alert('Messaggio di test inviato su Telegram!'),
    onError: (err: any) => alert(err.response?.data?.detail || 'Errore invio Telegram'),
  })

  const scrapeCategoryMutation = useMutation({
    mutationFn: schedulerApi.scrapeCategory,
    onSuccess: (data) => {
      alert(`Scraping completato! Trovati ${data.new_items} nuovi items`)
      queryClient.invalidateQueries({ queryKey: ['pending-items'] })
    },
  })

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Impostazioni</h1>
        <p className="text-gray-500 mt-1">
          Configura scraping automatico, notifiche e API
        </p>
      </div>

      {/* Scheduler Automatico */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Clock className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Scraping Automatico</h2>
              <p className="text-sm text-gray-500">Scraping e analisi AI programmata</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {schedulerStatus?.running ? (
              <span className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                Attivo
              </span>
            ) : (
              <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm font-medium">
                Fermo
              </span>
            )}
            {schedulerStatus?.running ? (
              <button
                onClick={() => stopMutation.mutate()}
                disabled={stopMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <Square className="h-4 w-4" />
                Stop
              </button>
            ) : (
              <button
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <Play className="h-4 w-4" />
                Avvia
              </button>
            )}
          </div>
        </div>

        {schedulerStatus && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="bg-white rounded-lg p-3">
              <p className="text-xs text-gray-500">Ultimo Scraping</p>
              <p className="text-sm font-medium">
                {schedulerStatus.last_scrape 
                  ? new Date(schedulerStatus.last_scrape).toLocaleString('it-IT')
                  : 'Mai'}
              </p>
            </div>
            <div className="bg-white rounded-lg p-3">
              <p className="text-xs text-gray-500">Ultima Analisi</p>
              <p className="text-sm font-medium">
                {schedulerStatus.last_analysis 
                  ? new Date(schedulerStatus.last_analysis).toLocaleString('it-IT')
                  : 'Mai'}
              </p>
            </div>
            <div className="bg-white rounded-lg p-3">
              <p className="text-xs text-gray-500">Intervallo Scraping</p>
              <p className="text-sm font-medium">{schedulerStatus.scrape_interval_minutes} min</p>
            </div>
            <div className="bg-white rounded-lg p-3">
              <p className="text-xs text-gray-500">Min Score Alert</p>
              <p className="text-sm font-medium">{schedulerStatus.min_score_for_alert}/100</p>
            </div>
          </div>
        )}
      </div>

      {/* Categorie Scraping */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Package className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Categorie Scraping</h2>
            <p className="text-sm text-gray-500">Clicca per avviare scraping per categoria</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {categories && Object.entries(categories).map(([id, cat]) => {
            const Icon = categoryIcons[id] || Package
            return (
              <button
                key={id}
                onClick={() => scrapeCategoryMutation.mutate(id)}
                disabled={scrapeCategoryMutation.isPending}
                className="flex flex-col items-center gap-2 p-4 border border-gray-200 rounded-xl hover:border-purple-300 hover:bg-purple-50 transition-all disabled:opacity-50"
              >
                <Icon className="h-8 w-8 text-purple-600" />
                <span className="text-sm font-medium text-gray-900">{cat.name}</span>
                <span className="text-xs text-gray-500">{cat.queries.length} query</span>
              </button>
            )
          })}
        </div>
        
        {scrapeCategoryMutation.isPending && (
          <div className="flex items-center justify-center gap-2 mt-4 text-purple-600">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Scraping in corso...</span>
          </div>
        )}
      </div>

      {/* eBay API */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Globe className="h-5 w-5 text-blue-600" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">eBay API</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              App ID
            </label>
            <input
              type="text"
              placeholder="Inserisci App ID"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cert ID
            </label>
            <input
              type="password"
              placeholder="Inserisci Cert ID"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Refresh Token
            </label>
            <input
              type="password"
              placeholder="Inserisci Refresh Token"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="sandbox" className="rounded" />
            <label htmlFor="sandbox" className="text-sm text-gray-600">
              Usa ambiente Sandbox (per testing)
            </label>
          </div>
        </div>
      </div>

      {/* OpenAI API */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-green-100 rounded-lg">
            <Key className="h-5 w-5 text-green-600" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">OpenAI API</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              API Key
            </label>
            <input
              type="password"
              placeholder="sk-..."
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-sm text-gray-500 mt-1">
              Usato per GPT-4 Vision (analisi immagini) e generazione descrizioni
            </p>
          </div>
        </div>
      </div>

      {/* AI Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Cpu className="h-5 w-5 text-purple-600" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">
            Impostazioni AI
          </h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Score minimo per approvazione automatica
            </label>
            <input
              type="number"
              defaultValue={8}
              min={1}
              max={10}
              className="w-24 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Score minimo per mostrare in dashboard
            </label>
            <input
              type="number"
              defaultValue={5}
              min={1}
              max={10}
              className="w-24 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Margine minimo (%)
            </label>
            <input
              type="number"
              defaultValue={25}
              min={0}
              max={100}
              className="w-24 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-orange-100 rounded-lg">
            <Bell className="h-5 w-5 text-orange-600" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Notifiche</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Telegram Bot Token
            </label>
            <input
              type="password"
              placeholder="Inserisci token bot"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Telegram Chat ID
            </label>
            <input
              type="text"
              placeholder="Inserisci chat ID"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm text-gray-600">
                Notifica nuovi items con score alto
              </span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm text-gray-600">
                Notifica vendite completate
              </span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="rounded" />
              <span className="text-sm text-gray-600">
                Notifica items non più disponibili
              </span>
            </label>
          </div>
          
          <button
            onClick={() => testTelegramMutation.mutate()}
            disabled={testTelegramMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {testTelegramMutation.isPending ? 'Invio...' : 'Invia messaggio di test'}
          </button>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Save className="h-5 w-5" />
          {saved ? 'Salvato!' : 'Salva impostazioni'}
        </button>
      </div>
    </div>
  )
}
