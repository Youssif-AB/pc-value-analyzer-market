export type Condition = 'new' | 'like_new' | 'excellent' | 'good' | 'fair' | 'parts'

export interface Specs {
  cpu: string | null
  gpu: string | null
  ram_gb: number | null
  ram_type: string | null
  storage_gb: number | null
  storage_type: string | null
  condition: Condition
  brand: string | null
  system_age_years: number | null
}

export interface ExtractedSpecs extends Specs {
  asking_price: number | null
  extraction_warnings: string[]
  normalization_failures: string[]
}

export interface MarketComparable {
  source: string
  title: string
  price_cad: number
  condition: string
  similarity: number
  url: string | null
  observed_at: string | null
}

export interface LiveMarketEvidence {
  enabled: boolean
  comp_count: number
  source_count: number
  sources: string[]
  median_asking_price_cad: number | null
  adjusted_market_estimate_cad: number | null
  blend_weight: number
  newest_observation_at: string | null
  valuation_method: 'model_only' | 'hybrid_live_comps'
  comparables: MarketComparable[]
  note: string
}

export interface Prediction {
  estimated_fair_price: number
  asking_price: number
  difference_percent: number
  rating: 'GREAT DEAL' | 'GOOD VALUE' | 'FAIR' | 'OVERPRICED' | 'HIGHLY OVERPRICED'
  lower_bound: number
  upper_bound: number
  model_version: string
  confidence: 'low' | 'medium' | 'high'
  drivers: Array<{ feature: string; direction: 'up' | 'down' | 'neutral'; explanation: string }>
  warnings: string[]
  live_market: LiveMarketEvidence
}

export interface MarketStatus {
  live_market_enabled: boolean
  target_currency: string
  total_active_observations: number
  sources: Array<{
    source: string
    configured: boolean
    active_observations: number
    newest_observation_at: string | null
  }>
  last_refresh_status: string | null
  last_refresh_at: string | null
}
