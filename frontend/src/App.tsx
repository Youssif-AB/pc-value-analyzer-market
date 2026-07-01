import { useState } from 'react'
import { extractListing, predictValue, recordCorrection } from './api'
import { ListingInput } from './components/ListingInput'
import { PredictionResult } from './components/PredictionResult'
import { SpecReview } from './components/SpecReview'
import type { ExtractedSpecs, Prediction, Specs } from './types'

function baseSpecs(extracted: ExtractedSpecs): Specs {
  const { asking_price: _askingPrice, extraction_warnings: _warnings, normalization_failures: _failures, ...specs } = extracted
  return specs
}

export default function App() {
  const [listing, setListing] = useState('')
  const [extracted, setExtracted] = useState<ExtractedSpecs | null>(null)
  const [reviewed, setReviewed] = useState<Specs | null>(null)
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not estimate this PC.')
    } finally { setBusy(false) }
  }

  function reset() {
    setListing(''); setExtracted(null); setReviewed(null); setPrediction(null); setError(null)
  }

  return (
    <main className="shell">
      <header className="hero">
        <div className="badge">Explainable ML valuation</div>
        <h1>Know what a gaming PC is actually worth.</h1>
        <p>Paste a messy marketplace listing. Review the hardware we extracted. Get a fair-price estimate with uncertainty and the drivers behind it.</p>
      </header>
      {!extracted && <ListingInput busy={busy} error={error} onSubmit={handleExtract} />}
      {extracted && !prediction && <SpecReview extracted={extracted} busy={busy} error={error} onBack={reset} onConfirm={handleReview} />}
      {prediction && reviewed && <PredictionResult prediction={prediction} specs={reviewed} onReset={reset} />}
      <footer>Demo model included for reproducibility. Production accuracy requires recent licensed market observations.</footer>
    </main>
  )
}
