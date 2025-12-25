import { useEffect, useState } from 'react';
import { Search, TrendingUp, Package, DollarSign, Star, RefreshCw } from 'lucide-react';

// Telegram Web App SDK types
declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        close: () => void;
        MainButton: {
          text: string;
          show: () => void;
          hide: () => void;
          onClick: (callback: () => void) => void;
        };
        BackButton: {
          show: () => void;
          hide: () => void;
          onClick: (callback: () => void) => void;
        };
        themeParams: {
          bg_color?: string;
          text_color?: string;
          hint_color?: string;
          button_color?: string;
          button_text_color?: string;
        };
        initDataUnsafe: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
          };
        };
        sendData: (data: string) => void;
        showAlert: (message: string) => void;
        showConfirm: (message: string, callback: (confirmed: boolean) => void) => void;
        HapticFeedback: {
          impactOccurred: (style: 'light' | 'medium' | 'heavy') => void;
          notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
        };
      };
    };
  }
}

interface Opportunity {
  id: string;
  title: string;
  price: number;
  estimated_min: number;
  estimated_max: number;
  score: number;
  margin: number;
  category: string;
  image?: string;
  url: string;
  location: string;
}

interface PriceResult {
  source: string;
  price: number;
  currency: string;
}

// Backend API - usa localhost in sviluppo, altrimenti mostra dati demo
const API_BASE = 'http://localhost:8000/api/v1';
const DEMO_MODE = true; // Attiva modalità demo quando backend non disponibile

export default function TelegramApp() {
  const [activeTab, setActiveTab] = useState<'opportunities' | 'search' | 'stats'>('opportunities');
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<PriceResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total: 0, pending: 0, avgScore: 0, avgMargin: 0 });

  const tg = window.Telegram?.WebApp;

  useEffect(() => {
    // Initialize Telegram Web App
    if (tg) {
      tg.ready();
      tg.expand();
    }
    
    // Load initial data
    loadOpportunities();
    loadStats();
  }, []);

  const loadOpportunities = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/items/?min_score=60&per_page=20`);
      const data = await res.json();
      
      const opps: Opportunity[] = data.items?.map((item: any) => ({
        id: item.id,
        title: item.original_title,
        price: item.original_price,
        estimated_min: item.estimated_value_min || 0,
        estimated_max: item.estimated_value_max || 0,
        score: item.ai_score || 0,
        margin: item.potential_margin || 0,
        category: item.ai_category || 'Altro',
        image: item.original_images?.[0],
        url: item.source_url,
        location: item.original_location || ''
      })) || [];
      
      setOpportunities(opps.sort((a, b) => b.score - a.score));
      tg?.HapticFeedback?.notificationOccurred('success');
    } catch (err) {
      console.error('Error loading opportunities:', err);
    }
    setLoading(false);
  };

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/items/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  const searchPrice = async () => {
    if (!searchQuery.trim()) return;
    
    setLoading(true);
    tg?.HapticFeedback?.impactOccurred('medium');
    
    try {
      // Use the price research endpoint
      const res = await fetch(`${API_BASE}/items/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: searchQuery,
          description: '',
          price: 0,
          images: []
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        // Parse results
        setSearchResults([
          { source: 'Valore stimato', price: data.estimated_value_min || 0, currency: 'EUR' }
        ]);
      }
    } catch (err) {
      console.error('Search error:', err);
      tg?.showAlert?.('Errore nella ricerca');
    }
    setLoading(false);
  };

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-green-500 bg-green-500/20';
    if (score >= 70) return 'text-yellow-500 bg-yellow-500/20';
    if (score >= 50) return 'text-orange-500 bg-orange-500/20';
    return 'text-gray-500 bg-gray-500/20';
  };

  const getScoreEmoji = (score: number) => {
    if (score >= 85) return '🔥';
    if (score >= 70) return '🎯';
    if (score >= 50) return '💡';
    return '📦';
  };

  return (
    <div className="min-h-screen bg-[var(--tg-theme-bg-color,#1a1a2e)] text-[var(--tg-theme-text-color,#ffffff)]">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-[var(--tg-theme-bg-color,#1a1a2e)] border-b border-white/10 px-4 py-3">
        <h1 className="text-xl font-bold text-center">🎯 Arbitraggio</h1>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-white/10">
        <button
          onClick={() => { setActiveTab('opportunities'); tg?.HapticFeedback?.impactOccurred('light'); }}
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            activeTab === 'opportunities' 
              ? 'text-blue-400 border-b-2 border-blue-400' 
              : 'text-gray-400'
          }`}
        >
          <TrendingUp className="w-4 h-4 mx-auto mb-1" />
          Opportunità
        </button>
        <button
          onClick={() => { setActiveTab('search'); tg?.HapticFeedback?.impactOccurred('light'); }}
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            activeTab === 'search' 
              ? 'text-blue-400 border-b-2 border-blue-400' 
              : 'text-gray-400'
          }`}
        >
          <Search className="w-4 h-4 mx-auto mb-1" />
          Cerca Prezzo
        </button>
        <button
          onClick={() => { setActiveTab('stats'); tg?.HapticFeedback?.impactOccurred('light'); }}
          className={`flex-1 py-3 text-sm font-medium transition-colors ${
            activeTab === 'stats' 
              ? 'text-blue-400 border-b-2 border-blue-400' 
              : 'text-gray-400'
          }`}
        >
          <Star className="w-4 h-4 mx-auto mb-1" />
          Stats
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Opportunities Tab */}
        {activeTab === 'opportunities' && (
          <div className="space-y-3">
            <div className="flex justify-between items-center mb-4">
              <span className="text-sm text-gray-400">{opportunities.length} opportunità</span>
              <button 
                onClick={loadOpportunities}
                className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {opportunities.length === 0 && !loading && (
              <div className="text-center py-10 text-gray-400">
                <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Nessuna opportunità trovata</p>
                <p className="text-sm">Avvia una scansione dalla dashboard</p>
              </div>
            )}

            {opportunities.map((opp) => (
              <div 
                key={opp.id}
                className="bg-white/5 rounded-xl p-4 border border-white/10"
                onClick={() => {
                  tg?.HapticFeedback?.impactOccurred('light');
                  window.open(opp.url, '_blank');
                }}
              >
                <div className="flex gap-3">
                  {opp.image && (
                    <img 
                      src={opp.image} 
                      alt="" 
                      className="w-16 h-16 rounded-lg object-cover bg-white/10"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-medium text-sm line-clamp-2">{opp.title}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-bold whitespace-nowrap ${getScoreColor(opp.score)}`}>
                        {getScoreEmoji(opp.score)} {opp.score}
                      </span>
                    </div>
                    
                    <div className="mt-2 flex items-center gap-3 text-sm">
                      <span className="text-green-400 font-bold">€{opp.price}</span>
                      <span className="text-gray-400">→</span>
                      <span className="text-blue-400">€{opp.estimated_min}-{opp.estimated_max}</span>
                    </div>
                    
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
                      <span className="text-green-400">+{opp.margin}%</span>
                      <span>•</span>
                      <span>{opp.category}</span>
                      <span>•</span>
                      <span>{opp.location}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div className="space-y-4">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && searchPrice()}
                placeholder="Es: iPhone 14 Pro 128GB"
                className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 pr-12 text-white placeholder-gray-400 focus:outline-none focus:border-blue-400"
              />
              <button
                onClick={searchPrice}
                disabled={loading}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
              >
                <Search className={`w-4 h-4 ${loading ? 'animate-pulse' : ''}`} />
              </button>
            </div>

            <p className="text-xs text-gray-400 text-center">
              Cerca il valore di mercato di qualsiasi prodotto
            </p>

            {searchResults.length > 0 && (
              <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                <h3 className="font-medium mb-3">💰 Risultati per "{searchQuery}"</h3>
                {searchResults.map((result, i) => (
                  <div key={i} className="flex justify-between items-center py-2 border-b border-white/10 last:border-0">
                    <span className="text-gray-400">{result.source}</span>
                    <span className="font-bold text-green-400">€{result.price}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="bg-blue-500/10 rounded-xl p-4 border border-blue-500/20">
              <h4 className="font-medium text-blue-400 mb-2">💡 Suggerimenti</h4>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• Includi marca e modello</li>
                <li>• Specifica la capacità/taglia</li>
                <li>• Per gaming: includi console</li>
              </ul>
            </div>
          </div>
        )}

        {/* Stats Tab */}
        {activeTab === 'stats' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white/5 rounded-xl p-4 border border-white/10 text-center">
                <Package className="w-6 h-6 mx-auto mb-2 text-blue-400" />
                <div className="text-2xl font-bold">{stats.total}</div>
                <div className="text-xs text-gray-400">Totale Items</div>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-white/10 text-center">
                <TrendingUp className="w-6 h-6 mx-auto mb-2 text-yellow-400" />
                <div className="text-2xl font-bold">{stats.pending}</div>
                <div className="text-xs text-gray-400">In Attesa</div>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-white/10 text-center">
                <Star className="w-6 h-6 mx-auto mb-2 text-green-400" />
                <div className="text-2xl font-bold">{stats.avgScore || 0}</div>
                <div className="text-xs text-gray-400">Score Medio</div>
              </div>
              <div className="bg-white/5 rounded-xl p-4 border border-white/10 text-center">
                <DollarSign className="w-6 h-6 mx-auto mb-2 text-purple-400" />
                <div className="text-2xl font-bold">+{stats.avgMargin || 0}%</div>
                <div className="text-xs text-gray-400">Margine Medio</div>
              </div>
            </div>

            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <h3 className="font-medium mb-3">📊 Fonti Prezzi</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">PriceCharting</span>
                  <span className="text-green-400">✓ Attivo</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Amazon</span>
                  <span className="text-green-400">✓ Attivo</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">eBay API</span>
                  <span className="text-yellow-400">⏳ In attesa</span>
                </div>
              </div>
            </div>

            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <h3 className="font-medium mb-3">🎯 Categorie Top</h3>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🎮</span>
                  <span className="flex-1">Gaming</span>
                  <span className="text-gray-400 text-sm">PriceCharting</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-lg">📱</span>
                  <span className="flex-1">Elettronica</span>
                  <span className="text-gray-400 text-sm">Amazon, eBay</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-lg">🧸</span>
                  <span className="flex-1">Collezionismo</span>
                  <span className="text-gray-400 text-sm">eBay venduti</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 text-center">
            <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin text-blue-400" />
            <p>Caricamento...</p>
          </div>
        </div>
      )}
    </div>
  );
}
