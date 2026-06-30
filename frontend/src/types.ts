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
}
