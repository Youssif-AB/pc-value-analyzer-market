import { useState } from 'react'
import { extractListing } from './api'
import { ListingInput } from './components/ListingInput'
import type { ExtractedSpecs } from './types'

export default function App() {
  const [listing, setListing] = useState('')
  const [extracted, setExtracted] = useState<ExtractedSpecs | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleExtract(text: string) {
    setBusy(true)
    setError(null)
    try {
      const result = await extractListing(text)
      setListing(text)
      setExtracted(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not extract this listing.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <div className="badge">Explainable ML valuation</div>
        <h1>Know what a gaming PC is actually worth.</h1>
        <p>Paste a messy marketplace listing. Review the hardware we extracted. Get a fair-price estimate with uncertainty and the drivers behind it.</p>
      </header>
      {!extracted ? <ListingInput busy={busy} error={error} onSubmit={handleExtract} /> : <pre>{JSON.stringify({ listing, extracted }, null, 2)}</pre>}
    </main>
  )
}
