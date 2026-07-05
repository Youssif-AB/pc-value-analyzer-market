import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { browseMarket } from '../api'
import { Icon } from '../icons'
import type { MarketBrowseParams, MarketListing, MarketStatus } from '../types'

interface Props {
  status: MarketStatus | null
  onAnalyze: (listing: MarketListing) => void
}

const PAGE_SIZE = 24

function money(value: number) {
  return new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 }).format(value)
}

function sourceLabel(source: string) {
  return source === 'ebay' ? 'eBay' : source === 'bestbuy' ? 'Best Buy' : source
}

function pretty(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function relativeTime(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'recently'
  const minutes = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60000))
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function specLine(listing: MarketListing) {
  const parts = [
    listing.specs.gpu,
    listing.specs.cpu,
    listing.specs.ram_gb ? `${listing.specs.ram_gb}GB${listing.specs.ram_type ? ` ${listing.specs.ram_type}` : ''}` : null,
    listing.specs.storage_gb ? `${listing.specs.storage_gb >= 1024 ? `${Math.round(listing.specs.storage_gb / 1024 * 10) / 10}TB` : `${listing.specs.storage_gb}GB`} ${listing.specs.storage_type ?? ''}`.trim() : null,
  ]
  return parts.filter(Boolean).join(' · ')
}

export function MarketBrowser({ status, onAnalyze }: Props) {
  const [items, setItems] = useState<MarketListing[]>([])
  const [total, setTotal] = useState(0)
  const [nextOffset, setNextOffset] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [draftQuery, setDraftQuery] = useState('')
  const [source, setSource] = useState('all')
  const [condition, setCondition] = useState('all')
  const [sort, setSort] = useState<MarketBrowseParams['sort']>('newest')
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sentinel = useRef<HTMLDivElement | null>(null)

  const params = useMemo<MarketBrowseParams>(() => ({
    q: query || undefined,
    source,
    condition,
    sort,
    min_price: minPrice ? Number(minPrice) : undefined,
    max_price: maxPrice ? Number(maxPrice) : undefined,
    limit: PAGE_SIZE,
  }), [query, source, condition, sort, minPrice, maxPrice])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    browseMarket({ ...params, offset: 0 })
      .then((response) => {
        if (!active) return
        setItems(response.items)
        setTotal(response.total)
        setNextOffset(response.next_offset)
      })
      .catch((err) => active && setError(err instanceof Error ? err.message : 'Could not load the market feed.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [params])

  async function loadMore() {
    if (nextOffset === null || loadingMore) return
    setLoadingMore(true)
    try {
      const response = await browseMarket({ ...params, offset: nextOffset })
      setItems((current) => [...current, ...response.items])
      setNextOffset(response.next_offset)
      setTotal(response.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load more listings.')
    } finally {
      setLoadingMore(false)
    }
  }

  useEffect(() => {
    const target = sentinel.current
    if (!target || nextOffset === null) return
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMore()
    }, { rootMargin: '320px 0px' })
    observer.observe(target)
    return () => observer.disconnect()
  }, [nextOffset, loadingMore, params])

  function submitSearch(event: FormEvent) {
    event.preventDefault()
    setQuery(draftQuery.trim())
  }

  function clearFilters() {
    setDraftQuery('')
    setQuery('')
    setSource('all')
    setCondition('all')
    setSort('newest')
    setMinPrice('')
    setMaxPrice('')
  }

  const configured = status?.sources.filter((entry) => entry.configured) ?? []
  const hasFilters = Boolean(query || source !== 'all' || condition !== 'all' || minPrice || maxPrice || sort !== 'newest')

  return (
    <section className="market-browser" aria-labelledby="market-heading">
      <div className="market-page-heading">
        <div>
          <span className="context-label">Live market</span>
          <h1 id="market-heading">Browse complete PCs across the current feed.</h1>
          <p>Normalized listings from configured providers, refreshed by the market worker and priced in CAD for comparison.</p>
        </div>
        <div className="market-feed-summary" aria-live="polite">
          <strong>{status?.total_active_observations.toLocaleString('en-CA') ?? '—'}</strong>
          <span>active listings</span>
          <small>{status?.last_refresh_at ? `Updated ${relativeTime(status.last_refresh_at)}` : 'Waiting for first refresh'}</small>
        </div>
      </div>

      <div className="market-source-strip" aria-label="Market sources">
        {(status?.sources ?? []).map((entry) => (
          <div className="market-source-stat" key={entry.source}>
            <span className={entry.configured ? 'source-state on' : 'source-state'} />
            <span>{sourceLabel(entry.source)}</span>
            <strong>{entry.configured ? entry.active_observations.toLocaleString('en-CA') : 'Not configured'}</strong>
          </div>
        ))}
      </div>

      <div className="market-layout">
        <aside className="market-filter-panel" aria-label="Market filters">
          <div className="filter-panel-heading">
            <span className="section-kicker">Filter market</span>
            {hasFilters && <button className="text-button" type="button" onClick={clearFilters}>Clear</button>}
          </div>

          <form onSubmit={submitSearch} className="market-search-form">
            <label htmlFor="market-search">Search hardware or listing</label>
            <div className="search-control">
              <Icon name="search" size={15} />
              <input id="market-search" value={draftQuery} onChange={(event) => setDraftQuery(event.target.value)} placeholder="RTX 4070, 7800X3D…" />
              <button type="submit" aria-label="Search market"><Icon name="arrow-right" size={14} /></button>
            </div>
          </form>

          <div className="filter-group">
            <label htmlFor="market-source">Source</label>
            <select id="market-source" value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="all">All configured sources</option>
              {configured.map((entry) => <option value={entry.source} key={entry.source}>{sourceLabel(entry.source)}</option>)}
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="market-condition">Condition</label>
            <select id="market-condition" value={condition} onChange={(event) => setCondition(event.target.value)}>
              <option value="all">Any condition</option>
              <option value="new">New</option>
              <option value="like_new">Like new</option>
              <option value="excellent">Excellent</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
            </select>
          </div>

          <fieldset className="price-filter">
            <legend>Price range · CAD</legend>
            <div>
              <label><span>Min</span><input type="number" inputMode="numeric" min="0" step="50" placeholder="500" value={minPrice} onChange={(event) => setMinPrice(event.target.value)} /></label>
              <label><span>Max</span><input type="number" inputMode="numeric" min="0" step="50" placeholder="3000" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} /></label>
            </div>
          </fieldset>

          <div className="filter-note">
            <Icon name="database" size={14} />
            <p>Active asking and retail prices are browseable market evidence, not completed-sale labels.</p>
          </div>
        </aside>

        <div className="market-results">
          <div className="market-results-toolbar">
            <div>
              <span>{loading ? 'Loading feed…' : `${total.toLocaleString('en-CA')} listings`}</span>
              {query && <b>matching “{query}”</b>}
            </div>
            <label className="sort-control">
              <span>Sort</span>
              <select value={sort} onChange={(event) => setSort(event.target.value as MarketBrowseParams['sort'])}>
                <option value="newest">Recently seen</option>
                <option value="price_asc">Price · low to high</option>
                <option value="price_desc">Price · high to low</option>
                <option value="quality">Best normalized</option>
              </select>
            </label>
          </div>

          {error && <div className="message error-message market-message" role="alert"><Icon name="alert" size={16} /><span>{error}</span></div>}

          {loading ? (
            <div className="market-loading" aria-label="Loading market listings">
              {Array.from({ length: 7 }).map((_, index) => <div className="market-skeleton" key={index}><span /><div><i /><i /></div><b /></div>)}
            </div>
          ) : items.length ? (
            <div className="market-list">
              {items.map((listing) => (
                <article className="market-listing" key={listing.id}>
                  <div className="listing-media">
                    {listing.image_url ? <img src={listing.image_url} alt="" loading="lazy" /> : <div className="listing-image-placeholder"><Icon name="cpu" size={22} /></div>}
                  </div>
                  <div className="listing-body">
                    <div className="listing-meta">
                      <span className={`source-word source-${listing.source}`}>{sourceLabel(listing.source)}</span>
                      <span>{pretty(listing.condition)}</span>
                      <span>{pretty(listing.listing_type)}</span>
                      <span>seen {relativeTime(listing.last_seen_at)}</span>
                    </div>
                    <h2>{listing.title}</h2>
                    <p className="listing-spec-line">{specLine(listing) || 'Hardware details partially normalized'}</p>
                    {listing.summary && <p className="listing-summary">{listing.summary}</p>}
                    <div className="listing-actions">
                      <button type="button" className="analyze-link" onClick={() => onAnalyze(listing)}>
                        Analyze this PC <Icon name="arrow-right" size={14} />
                      </button>
                      {listing.url && <a href={listing.url} target="_blank" rel="noreferrer">Open original <Icon name="external" size={12} /></a>}
                    </div>
                  </div>
                  <div className="listing-price-block">
                    <strong>{money(listing.price_cad)}</strong>
                    {listing.currency !== 'CAD' && <span>{listing.currency} {listing.price.toLocaleString('en-CA', { maximumFractionDigits: 0 })} source</span>}
                    <small>{Math.round(listing.extraction_quality * 100)}% specs parsed</small>
                  </div>
                </article>
              ))}
              <div ref={sentinel} className="market-scroll-sentinel" aria-hidden="true" />
              {loadingMore && <div className="load-more-state">Loading more listings…</div>}
              {nextOffset === null && items.length > 0 && <div className="market-end">End of the current market cache.</div>}
            </div>
          ) : (
            <div className="market-empty">
              <Icon name="market" size={24} />
              <h2>{configured.length ? 'No listings match these filters.' : 'Connect a market source to populate the feed.'}</h2>
              <p>{configured.length ? 'Clear the filters or wait for the next hourly market refresh.' : 'Add eBay or Best Buy credentials to .env, then restart the market refresher.'}</p>
              {hasFilters && <button type="button" className="button button-secondary" onClick={clearFilters}>Clear filters</button>}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
