import { useState } from 'react'
import { extractListing } from './api'
import { ListingInput } from './components/ListingInput'
import { SpecReview } from './components/SpecReview'
import type { ExtractedSpecs, Specs } from './types'

export default function App() {
  const [listing, setListing] = useState('')
  const [extracted, setExtracted] = useState<ExtractedSpecs | null>(null)
  const [reviewed, setReviewed] = useState<{ specs: Specs; price: number } | null>(null)
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
    setReviewed({ specs, price })
  }

  function reset() {
    setExtracted(null); setReviewed(null); setError(null)
  }

  return (
    <main className="shell">
      <header className="hero">
        <div className="badge">Explainable ML valuation</div>
        <h1>Know what a gaming PC is actually worth.</h1>
        <p>Paste a messy marketplace listing. Review the hardware we extracted. Get a fair-price estimate with uncertainty and the drivers behind it.</p>
      </header>
      {!extracted && <ListingInput busy={busy} error={error} onSubmit={handleExtract} />}
      {extracted && !reviewed && <SpecReview extracted={extracted} busy={busy} error={error} onBack={reset} onConfirm={handleReview} />}
      {reviewed && <pre className="panel">{JSON.stringify({ listing, reviewed }, null, 2)}</pre>}
    </main>
  )
}
