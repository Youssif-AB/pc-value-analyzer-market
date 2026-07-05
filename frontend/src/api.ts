import type { ExtractedSpecs, MarketBrowseParams, MarketBrowseResponse, MarketStatus, Prediction, Specs } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8002'

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(body.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function extractListing(listingText: string) {
  return request<ExtractedSpecs>('/api/v1/extract', {
    method: 'POST',
    body: JSON.stringify({ listing_text: listingText }),
  })
}

export function predictValue(specs: Specs, askingPrice: number, sourceListing: string) {
  return request<Prediction>('/api/v1/predict', {
    method: 'POST',
    body: JSON.stringify({ specs, asking_price: askingPrice, source_listing: sourceListing }),
  })
}

export function recordCorrection(originalSpecs: Specs, correctedSpecs: Specs, sourceListing: string) {
  return request<{ id: number; status: string }>('/api/v1/corrections', {
    method: 'POST',
    body: JSON.stringify({ original_specs: originalSpecs, corrected_specs: correctedSpecs, source_listing: sourceListing }),
  })
}

export function getMarketStatus() {
  return request<MarketStatus>('/api/v1/market/status')
}

export function browseMarket(params: MarketBrowseParams = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  return request<MarketBrowseResponse>(`/api/v1/market/listings${query.size ? `?${query.toString()}` : ''}`)
}
