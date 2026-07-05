import { useEffect, useState } from 'react'
import { extractListing, getMarketStatus, predictValue, recordCorrection } from './api'
import { ListingInput } from './components/ListingInput'
import { MarketBrowser } from './components/MarketBrowser'
import { PredictionResult } from './components/PredictionResult'
import { SpecReview } from './components/SpecReview'
import { Icon } from './icons'
import type { ExtractedSpecs, MarketListing, MarketStatus, Prediction, Specs } from './types'

type View = 'market' | 'analyze'

function baseSpecs(extracted: ExtractedSpecs): Specs {
  const { asking_price: _askingPrice, extraction_warnings: _warnings, normalization_failures: _failures, ...specs } = extracted
  return specs
}

function sourceLabel(source: string) {
  return source === 'ebay' ? 'eBay' : source === 'bestbuy' ? 'Best Buy' : source
}

function relativeRefresh(iso: string | null | undefined) {
  if (!iso) return null
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) return null
  const minutes = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 60000))
  if (minutes < 1) return 'just refreshed'
  if (minutes < 60) return `refreshed ${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return hours < 24 ? `refreshed ${hours}h ago` : `refreshed ${Math.floor(hours / 24)}d ago`
}

function listingTextFromMarket(item: MarketListing) {
  const normalized = [
    item.specs.cpu,
    item.specs.gpu,
    item.specs.ram_gb ? `${item.specs.ram_gb}GB ${item.specs.ram_type ?? 'RAM'}` : null,
    item.specs.storage_gb ? `${item.specs.storage_gb}GB ${item.specs.storage_type ?? 'storage'}` : null,
  ].filter(Boolean).join(', ')
  return [
    item.title,
    item.summary,
    normalized ? `Normalized hardware: ${normalized}.` : null,
    `Condition: ${item.condition}.`,
    `Asking price: CAD $${item.price_cad.toFixed(2)}.`,
    `Source: ${sourceLabel(item.source)}${item.url ? ` — ${item.url}` : ''}`,
  ].filter(Boolean).join('\n')
}

export default function App() {
  const [view, setView] = useState<View>('market')
  const [listing, setListing] = useState('')
  const [extracted, setExtracted] = useState<ExtractedSpecs | null>(null)
  const [reviewed, setReviewed] = useState<Specs | null>(null)
  const [prediction, setPrediction] = useState<Prediction | null>(null)
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getMarketStatus().then(setMarketStatus).catch(() => undefined)
    const timer = window.setInterval(() => getMarketStatus().then(setMarketStatus).catch(() => undefined), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  async function handleExtract(text: string) {
    setBusy(true)
    setError(null)
    try {
      setListing(text)
      setExtracted(await extractListing(text))
      setReviewed(null)
      setPrediction(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not extract this listing.')
    } finally {
      setBusy(false)
    }
  }

  async function handleMarketAnalyze(item: MarketListing) {
    setView('analyze')
    window.scrollTo({ top: 0, behavior: 'smooth' })
    await handleExtract(listingTextFromMarket(item))
  }

  async function handleReview(specs: Specs, price: number) {
    if (!extracted) return
    setBusy(true)
    setError(null)
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
    } finally {
      setBusy(false)
    }
  }

  function resetAnalyzer() {
    setListing('')
    setExtracted(null)
    setReviewed(null)
    setPrediction(null)
    setError(null)
  }

  function switchView(next: View) {
    setView(next)
    if (next === 'market') resetAnalyzer()
  }

  const activeStep = prediction ? 3 : extracted ? 2 : 1
  const configuredSources = marketStatus?.sources.filter((source) => source.configured).map((source) => sourceLabel(source.source)) ?? []
  const refreshText = relativeRefresh(marketStatus?.last_refresh_at)

  return (
    <div className="app-frame">
      <header className="topbar">
        <div className="topbar-inner">
          <button className="brand brand-button" type="button" aria-label="Open live market" onClick={() => switchView('market')}>
            <span className="brand-mark"><Icon name="cpu" size={17} /></span>
            <span>PC Value</span>
            <span className="build-tag">Market v3</span>
          </button>
          <nav className="product-nav" aria-label="Primary navigation">
            <button type="button" className={view === 'market' ? 'active' : ''} onClick={() => switchView('market')}><Icon name="market" size={14} /> Market</button>
            <button type="button" className={view === 'analyze' ? 'active' : ''} onClick={() => { setView('analyze'); resetAnalyzer() }}><Icon name="edit" size={14} /> Analyze</button>
          </nav>
          <div className="market-chip" aria-live="polite">
            <span className={marketStatus?.total_active_observations ? 'live-dot is-live' : 'live-dot'} />
            <span className="market-chip-main">
              {marketStatus ? `${marketStatus.total_active_observations.toLocaleString('en-CA')} live listings` : 'Checking market feed'}
            </span>
            {refreshText && <span className="market-chip-meta">{refreshText}</span>}
          </div>
        </div>
      </header>

      <main className={view === 'market' ? 'workspace market-workspace' : 'workspace'}>
        {view === 'market' ? (
          <MarketBrowser status={marketStatus} onAnalyze={handleMarketAnalyze} />
        ) : (
          <>
            <div className="workspace-heading">
              <div>
                <span className="context-label">Listing analyzer</span>
                <h1>Price a complete PC from the listing itself.</h1>
              </div>
              <p>Paste your own listing or send one here from the live market. Verify the extracted hardware before the model compares it with current evidence.</p>
            </div>

            <nav className="step-nav" aria-label="Valuation progress">
              {[['01', 'Listing'], ['02', 'Verify specs'], ['03', 'Valuation']].map(([number, label], index) => {
                const step = index + 1
                const state = step < activeStep ? 'complete' : step === activeStep ? 'active' : 'upcoming'
                return (
                  <div className={`step-item ${state}`} key={number} aria-current={state === 'active' ? 'step' : undefined}>
                    <span className="step-number">{state === 'complete' ? <Icon name="check" size={13} /> : number}</span>
                    <span>{label}</span>
                  </div>
                )
              })}
            </nav>

            {!extracted && <ListingInput busy={busy} error={error} marketStatus={marketStatus} configuredSources={configuredSources} onSubmit={handleExtract} />}
            {extracted && !prediction && <SpecReview extracted={extracted} listing={listing} busy={busy} error={error} onBack={resetAnalyzer} onConfirm={handleReview} />}
            {prediction && reviewed && <PredictionResult prediction={prediction} specs={reviewed} onReset={resetAnalyzer} />}
          </>
        )}
      </main>

      <footer className="app-footer">
        <span>Active listings are browseable market evidence; completed-sale data remains the training target.</span>
        <span>Prices normalized to CAD where FX conversion is required.</span>
      </footer>
    </div>
  )
}
