import { useEffect, useState } from 'react'
import { extractListing, getMarketStatus, predictValue, recordCorrection } from './api'
import { ListingInput } from './components/ListingInput'
import { PredictionResult } from './components/PredictionResult'
import { SpecReview } from './components/SpecReview'
import type { ExtractedSpecs, MarketStatus, Prediction, Specs } from './types'

function baseSpecs(extracted: ExtractedSpecs): Specs {
  const { asking_price: _askingPrice, extraction_warnings: _warnings, normalization_failures: _failures, ...specs } = extracted
  return specs
}

export default function App() {
  const [listing, setListing] = useState('')
  const [extracted, setExtracted] = useState<ExtractedSpecs | null>(null)
  const [reviewed, setReviewed] = useState<Specs | null>(null)
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getMarketStatus().then(setMarketStatus).catch(() => undefined)
  }, [])

  async function handleExtract(text: string) {
    setBusy(true); setError(null)
    try {
      setListing(text)
      setExtracted(await extractListing(text))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not extract this listing.')
    } finally { setBusy(false) }
  }

  async function handleReview(specs: Specs, price: number) {
    if (!extracted) return
    setBusy(true); setError(null)
    try {
      const original = baseSpecs(extracted)
      if (JSON.stringify(original) !== JSON.stringify(specs)) {
        await recordCorrection(original, specs, listing).catch(() => undefined)
      }
      const result = await predictValue(specs, price, listing)
      setReviewed(specs)
      setPrediction(result)
      getMarketStatus().then(setMarketStatus).catch(() => undefined)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not estimate this PC.')
    } finally { setBusy(false) }
  }

  function reset() {
    setListing(''); setExtracted(null); setReviewed(null); setPrediction(null); setError(null)
  }

  const configuredSources = marketStatus?.sources.filter((source) => source.configured).map((source) => source.source) ?? []

  return (
    <main className="shell">
      <header className="hero">
        <div className="badge">Hybrid ML + live market valuation</div>
        <h1>Know what a gaming PC is actually worth.</h1>
        <p>Paste a messy marketplace listing. Review the hardware we extracted. Get an ML estimate calibrated against fresh comparable listings, with uncertainty and source provenance.</p>
        <div className="market-status" aria-live="polite">
          <span className={marketStatus?.total_active_observations ? 'status-dot live' : 'status-dot'} />
          {marketStatus
            ? `${marketStatus.total_active_observations} fresh market observations${configuredSources.length ? ` · ${configuredSources.join(' + ')}` : ' · add API credentials to enable live sources'}`
            : 'Checking live market cache…'}
        </div>
      </header>
      {!extracted && <ListingInput busy={busy} error={error} onSubmit={handleExtract} />}
      {extracted && !prediction && <SpecReview extracted={extracted} busy={busy} error={error} onBack={reset} onConfirm={handleReview} />}
      {prediction && reviewed && <PredictionResult prediction={prediction} specs={reviewed} onReset={reset} />}
      <footer>Live asking/open-box evidence is kept separate from completed-sale training labels. Review extracted specs before every valuation.</footer>
    </main>
  )
}
