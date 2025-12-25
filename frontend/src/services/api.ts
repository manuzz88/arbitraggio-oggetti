import axios from 'axios'

const API_BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Item {
  id: string
  source_platform: string
  source_url: string
  source_id: string
  original_title: string
  original_description: string | null
  original_price: number
  original_currency: string
  original_images: string[]
  original_location: string | null
  seller_info: Record<string, unknown> | null
  ai_validation: Record<string, unknown> | null
  ai_score: number | null
  ai_category: string | null
  ai_brand: string | null
  ai_model: string | null
  ai_condition: string | null
  estimated_value_min: number | null
  estimated_value_max: number | null
  potential_margin: number | null
  status: string
  rejection_reason: string | null
  found_at: string
  analyzed_at: string | null
  approved_at: string | null
  created_at: string
  updated_at: string
}

export interface ItemListResponse {
  items: Item[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface Listing {
  id: string
  item_id: string
  platform: string
  platform_listing_id: string | null
  listing_url: string | null
  enhanced_title: string
  enhanced_description: string
  enhanced_images: string[]
  listing_price: number
  shipping_price: number
  views: number
  watchers: number
  status: string
  error_message: string | null
  published_at: string | null
  sold_at: string | null
  created_at: string
  updated_at: string
}

export interface Order {
  id: string
  listing_id: string
  platform_order_id: string | null
  sale_price: number
  platform_fees: number | null
  shipping_cost_received: number | null
  purchase_price: number | null
  purchase_shipping: number | null
  purchase_date: string | null
  purchase_url: string | null
  shipping_cost_paid: number | null
  tracking_number: string | null
  gross_profit: number | null
  net_profit: number | null
  status: string
  notes: string | null
  buyer_username: string | null
  sold_at: string
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface DashboardStats {
  items: {
    pending: number
    approved: number
    listed: number
  }
  listings: {
    active: number
  }
  orders: {
    pending_action: number
    completed: number
  }
  profit: {
    total: number
    monthly: number
  }
}

export const itemsApi = {
  getAll: async (params?: { status?: string; page?: number; per_page?: number }) => {
    const response = await api.get<ItemListResponse>('/items', { params })
    return response.data
  },

  getPending: async (params?: { page?: number; per_page?: number }) => {
    const response = await api.get<ItemListResponse>('/items/pending', { params })
    return response.data
  },

  getById: async (id: string) => {
    const response = await api.get<Item>(`/items/${id}`)
    return response.data
  },

  approve: async (id: string, data?: { listing_price?: number; platform?: string }) => {
    const response = await api.post<Item>(`/items/${id}/approve`, data || {})
    return response.data
  },

  reject: async (id: string, reason?: string) => {
    const response = await api.post<Item>(`/items/${id}/reject`, null, {
      params: { reason },
    })
    return response.data
  },

  delete: async (id: string) => {
    await api.delete(`/items/${id}`)
  },
}

export const listingsApi = {
  getAll: async (params?: { status?: string; page?: number; per_page?: number }) => {
    const response = await api.get('/listings', { params })
    return response.data
  },

  getActive: async (params?: { page?: number; per_page?: number }) => {
    const response = await api.get('/listings/active', { params })
    return response.data
  },

  getById: async (id: string) => {
    const response = await api.get<Listing>(`/listings/${id}`)
    return response.data
  },

  publish: async (id: string) => {
    const response = await api.post(`/listings/${id}/publish`)
    return response.data
  },

  end: async (id: string) => {
    const response = await api.post(`/listings/${id}/end`)
    return response.data
  },
}

export const ordersApi = {
  getAll: async (params?: { status?: string; page?: number; per_page?: number }) => {
    const response = await api.get('/orders', { params })
    return response.data
  },

  getPending: async (params?: { page?: number; per_page?: number }) => {
    const response = await api.get('/orders/pending', { params })
    return response.data
  },

  getById: async (id: string) => {
    const response = await api.get<Order>(`/orders/${id}`)
    return response.data
  },

  markPurchased: async (
    id: string,
    data: { purchase_price: number; purchase_shipping?: number; purchase_url?: string }
  ) => {
    const response = await api.post<Order>(`/orders/${id}/mark-purchased`, null, {
      params: data,
    })
    return response.data
  },

  markShipped: async (
    id: string,
    data: { tracking_number: string; shipping_cost?: number }
  ) => {
    const response = await api.post<Order>(`/orders/${id}/mark-shipped`, null, {
      params: data,
    })
    return response.data
  },

  complete: async (id: string) => {
    const response = await api.post<Order>(`/orders/${id}/complete`)
    return response.data
  },
}

export const analyticsApi = {
  getDashboard: async () => {
    const response = await api.get<DashboardStats>('/analytics/dashboard')
    return response.data
  },

  getDailyProfit: async (days: number = 30) => {
    const response = await api.get(`/analytics/profit/daily?days=${days}`)
    return response.data
  },

  getSources: async () => {
    const response = await api.get('/analytics/sources')
    return response.data
  },

  getCategories: async () => {
    const response = await api.get('/analytics/categories')
    return response.data
  },
}

// Scraper API
export const scraperApi = {
  startScraping: async (queries: string[], maxPages: number = 3) => {
    const response = await api.post('/scraper/start', {
      queries,
      max_pages: maxPages,
      platform: 'subito'
    })
    return response.data
  },

  getStatus: async () => {
    const response = await api.get('/scraper/status')
    return response.data
  },
}

// AI Analysis API
export interface AIAnalysis {
  score: number
  category: string
  brand: string | null
  model: string | null
  estimated_value_min: number
  estimated_value_max: number
  margin_percentage: number
  recommendation: 'BUY' | 'SKIP' | 'WATCH'
  reasoning: string
  red_flags: string[]
  selling_tips: string
}

export interface Opportunity {
  item: Item
  analysis: AIAnalysis
}

export const aiApi = {
  analyzeItem: async (itemId: string) => {
    const response = await api.post<{ item: Item; analysis: AIAnalysis }>(`/items/${itemId}/analyze`)
    return response.data
  },

  analyzePending: async (params?: { limit?: number; min_price?: number; max_price?: number }) => {
    const response = await api.post<{
      analyzed: number
      opportunities_found: number
      opportunities: Opportunity[]
    }>('/items/analyze-pending', null, { params })
    return response.data
  },

  getOpportunities: async (minScore?: number) => {
    const response = await api.get<ItemListResponse>('/items/', {
      params: { min_score: minScore || 60, status: 'pending' }
    })
    return response.data
  },
}

// Scheduler API
export interface SchedulerStatus {
  running: boolean
  last_scrape: string | null
  last_analysis: string | null
  scrape_interval_minutes: number
  analysis_interval_minutes: number
  queries: string[]
  min_score_for_alert: number
}

export interface CategoryPreset {
  name: string
  queries: string[]
  min_price: number
  max_price: number
}

export const schedulerApi = {
  getStatus: async () => {
    const response = await api.get<SchedulerStatus>('/scheduler/status')
    return response.data
  },

  start: async () => {
    const response = await api.post('/scheduler/start')
    return response.data
  },

  stop: async () => {
    const response = await api.post('/scheduler/stop')
    return response.data
  },

  updateSettings: async (settings: {
    queries?: string[]
    scrape_interval_minutes?: number
    analysis_interval_minutes?: number
    min_score_for_alert?: number
  }) => {
    const response = await api.put<SchedulerStatus>('/scheduler/settings', settings)
    return response.data
  },

  testTelegram: async () => {
    const response = await api.post('/scheduler/test-telegram')
    return response.data
  },

  getCategories: async () => {
    const response = await api.get<Record<string, CategoryPreset>>('/scheduler/categories')
    return response.data
  },

  scrapeCategory: async (categoryId: string) => {
    const response = await api.post(`/scheduler/scrape-category/${categoryId}`)
    return response.data
  },
}

export default api
