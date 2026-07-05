import { FormEvent, useState } from 'react'
import { Icon } from '../icons'
import type { MarketStatus } from '../types'

const EXAMPLE = `Gaming PC - like new. Ryzen 7 7800X3D, GeForce RTX 4070 12GB, 32GB DDR5, 2TB NVMe SSD. Asking $1,650. Built about 1 year ago.`

interface Props {
  busy: boolean
  error: string | null
  marketStatus: MarketStatus | null
  configuredSources: string[]
  onSubmit: (text: string) => Promise<void>
}

export function ListingInput({ busy, error, marketStatus, configuredSources, onSubmit }: Props) {
  const [text, setText] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (text.trim().length < 20) return
    await onSubmit(text.trim())
  }

  const characters = text.trim().length

  return (
    <section className="workbench input-workbench" aria-labelledby="listing-heading">
      <div className="workbench-main">
        <div className="section-intro">
          <span className="section-kicker">Listing input</span>
          <h2 id="listing-heading">Paste the seller's full description</h2>
          <p>Include the asking price, condition, and any hardware details. Extraction is only the first pass—you will verify every field before valuation.</p>
        </div>

        <form onSubmit={submit} className="listing-form">
          <div className="field-label-row">
            <label htmlFor="listing">Listing text</label>
            <span>{characters ? `${characters.toLocaleString('en-CA')} characters` : 'Minimum 20 characters'}</span>
          </div>
          <textarea
            id="listing"
            rows={12}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste a Marketplace, Kijiji, eBay, or retailer listing here…"
            disabled={busy}
            autoFocus
          />
          {error && <div className="message error-message" role="alert"><Icon name="alert" size={16} /><span>{error}</span></div>}
          <div className="action-row">
            <button type="button" className="button button-secondary" onClick={() => setText(EXAMPLE)} disabled={busy}>Load example</button>
            <button type="submit" className="button button-primary" disabled={busy || characters < 20}>
              <span>{busy ? 'Reading listing…' : 'Extract hardware'}</span>
              {!busy && <Icon name="arrow-right" size={16} />}
            </button>
          </div>
        </form>
      </div>

      <aside className="workbench-rail" aria-label="Extraction and market details">
        <section className="rail-section">
          <div className="rail-title"><Icon name="edit" size={15} /><h3>What gets extracted</h3></div>
          <div className="rail-list">
            <div><span>Processor</span><b>CPU model + generation</b></div>
            <div><span>Graphics</span><b>GPU model + tier</b></div>
            <div><span>Memory</span><b>Capacity + DDR type</b></div>
            <div><span>Storage</span><b>Capacity + drive type</b></div>
            <div><span>Context</span><b>Condition, age, brand</b></div>
            <div><span>Price</span><b>Seller asking price</b></div>
          </div>
        </section>

        <section className="rail-section market-rail">
          <div className="rail-title"><Icon name="database" size={15} /><h3>Market feed</h3></div>
          {marketStatus ? (
            <>
              <div className="market-total">
                <strong>{marketStatus.total_active_observations.toLocaleString('en-CA')}</strong>
                <span>active observations in cache</span>
              </div>
              <div className="source-list">
                {marketStatus.sources.map((source) => (
                  <div className="source-row" key={source.source}>
                    <span className={source.configured ? 'source-state on' : 'source-state'} />
                    <span className="source-name">{source.source === 'bestbuy' ? 'Best Buy' : source.source === 'ebay' ? 'eBay' : source.source}</span>
                    <span>{source.configured ? source.active_observations.toLocaleString('en-CA') : 'not configured'}</span>
                  </div>
                ))}
              </div>
              {configuredSources.length === 0 && <p className="rail-note">Add source API credentials in <code>.env</code> to enable live calibration.</p>}
            </>
          ) : (
            <div className="rail-loading"><span className="loading-bar" /><span className="loading-bar short" /></div>
          )}
        </section>
      </aside>
    </section>
  )
}
