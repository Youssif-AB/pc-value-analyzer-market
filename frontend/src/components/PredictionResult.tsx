import { Icon } from '../icons'
import type { Prediction, Specs } from '../types'

interface Props {
  prediction: Prediction
  specs: Specs
  onReset: () => void
}

function money(value: number) {
  return new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 }).format(value)
}

function sourceName(source: string) {
  return source === 'ebay' ? 'eBay' : source === 'bestbuy' ? 'Best Buy' : source
}

function pretty(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function observedLabel(iso: string | null) {
  if (!iso) return 'Current cache'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'Current cache'
  return new Intl.DateTimeFormat('en-CA', { month: 'short', day: 'numeric' }).format(date)
}

export function PredictionResult({ prediction, specs, onReset }: Props) {
  const buyerSavings = prediction.estimated_fair_price - prediction.asking_price
  const live = prediction.live_market
  const scaleMin = Math.max(0, Math.min(prediction.lower_bound, prediction.asking_price) * 0.9)
  const scaleMax = Math.max(prediction.upper_bound, prediction.asking_price) * 1.1
  const span = Math.max(1, scaleMax - scaleMin)
  const askPosition = Math.min(100, Math.max(0, ((prediction.asking_price - scaleMin) / span) * 100))
  const fairPosition = Math.min(100, Math.max(0, ((prediction.estimated_fair_price - scaleMin) / span) * 100))
  const rangeStart = Math.min(100, Math.max(0, ((prediction.lower_bound - scaleMin) / span) * 100))
  const rangeEnd = Math.min(100, Math.max(0, ((prediction.upper_bound - scaleMin) / span) * 100))

  return (
    <section className="result-workspace" aria-labelledby="result-heading">
      <div className="result-header">
        <div>
          <span className="section-kicker">Valuation complete</span>
          <div className="rating-line">
            <span className={`rating-mark rating-${prediction.rating.toLowerCase().replaceAll(' ', '-')}`} />
            <span className="rating-text">{prediction.rating}</span>
            <span className="confidence-text">{prediction.confidence} confidence</span>
          </div>
          <h2 id="result-heading">Fair value is about {money(prediction.estimated_fair_price)}.</h2>
          <p>{buyerSavings >= 0 ? `The seller is asking ${money(Math.abs(buyerSavings))} less than the estimate.` : `The seller is asking ${money(Math.abs(buyerSavings))} more than the estimate.`}</p>
        </div>
        <div className="decision-price">
          <span>Seller asks</span>
          <strong>{money(prediction.asking_price)}</strong>
          <b className={buyerSavings >= 0 ? 'positive' : 'negative'}>{prediction.difference_percent > 0 ? '+' : ''}{prediction.difference_percent.toFixed(1)}% vs fair value</b>
        </div>
      </div>

      <section className="price-band" aria-label={`Estimated range ${money(prediction.lower_bound)} to ${money(prediction.upper_bound)}; fair value ${money(prediction.estimated_fair_price)}; asking price ${money(prediction.asking_price)}`}>
        <div className="price-band-labels">
          <div><span>Likely range</span><strong>{money(prediction.lower_bound)} — {money(prediction.upper_bound)}</strong></div>
          <div className="model-id">Model {prediction.model_version}</div>
        </div>
        <div className="price-axis">
          <div className="range-segment" style={{ left: `${rangeStart}%`, width: `${Math.max(2, rangeEnd - rangeStart)}%` }} />
          <div className="axis-marker fair-marker" style={{ left: `${fairPosition}%` }}><span>Fair</span><i /></div>
          <div className="axis-marker ask-marker" style={{ left: `${askPosition}%` }}><i /><span>Ask</span></div>
        </div>
        <div className="axis-ends"><span>{money(scaleMin)}</span><span>{money(scaleMax)}</span></div>
      </section>

      <div className="result-grid">
        <div className="result-main-column">
          <section className="result-section market-section">
            <div className="result-section-heading">
              <div>
                <span className="section-kicker">Current market evidence</span>
                <h3>{live.valuation_method === 'hybrid_live_comps' ? `${live.comp_count} comparable listings informed this price` : 'Not enough fresh comparables to adjust the model'}</h3>
              </div>
              <div className="method-summary">
                <span>Live weight</span>
                <strong>{Math.round(live.blend_weight * 100)}%</strong>
              </div>
            </div>

            <div className="market-summary-row">
              <div><span>Sources</span><strong>{live.source_count || '—'}</strong></div>
              <div><span>Median ask</span><strong>{live.median_asking_price_cad ? money(live.median_asking_price_cad) : '—'}</strong></div>
              <div><span>Adjusted market</span><strong>{live.adjusted_market_estimate_cad ? money(live.adjusted_market_estimate_cad) : '—'}</strong></div>
              <div><span>Newest observation</span><strong>{observedLabel(live.newest_observation_at)}</strong></div>
            </div>

            {live.comparables.length > 0 ? (
              <div className="comp-table" role="table" aria-label="Comparable market listings">
                <div className="comp-table-head" role="row">
                  <span role="columnheader">Source</span><span role="columnheader">Listing</span><span role="columnheader">Match</span><span role="columnheader">Price</span>
                </div>
                {live.comparables.slice(0, 7).map((comp) => (
                  <div className="comp-table-row" key={`${comp.source}-${comp.title}-${comp.price_cad}`} role="row">
                    <span className="comp-source" role="cell">{sourceName(comp.source)}</span>
                    <span className="comp-title" role="cell">
                      {comp.url ? <a className="comp-link" href={comp.url} target="_blank" rel="noreferrer"><b>{comp.title}</b><Icon name="external" size={12} /></a> : <b>{comp.title}</b>}
                      <small>{pretty(comp.condition)} · {observedLabel(comp.observed_at)}</small>
                    </span>
                    <span className="comp-match" role="cell">{Math.round(comp.similarity * 100)}%</span>
                    <span className="comp-price" role="cell">{money(comp.price_cad)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state"><Icon name="database" size={18} /><div><strong>No suitable live comparables</strong><span>The estimate falls back to the structural model until the market pool contains enough similar builds.</span></div></div>
            )}
            <p className="evidence-note">{live.note}</p>
          </section>

          <section className="result-section driver-section">
            <div className="result-section-heading compact">
              <div><span className="section-kicker">Model explanation</span><h3>What moved the estimate</h3></div>
            </div>
            <div className="driver-list">
              {prediction.drivers.map((driver) => (
                <div className="driver-row" key={`${driver.feature}-${driver.explanation}`}>
                  <span className={`driver-direction ${driver.direction}`}>{driver.direction === 'up' ? '↗' : driver.direction === 'down' ? '↘' : '—'}</span>
                  <strong>{driver.feature}</strong>
                  <p>{driver.explanation}</p>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="result-sidebar">
          <section className="config-section">
            <div className="rail-title"><Icon name="cpu" size={15} /><h3>Reviewed configuration</h3></div>
            <dl className="config-list">
              <div><dt>CPU</dt><dd>{specs.cpu ?? 'Unknown'}</dd></div>
              <div><dt>GPU</dt><dd>{specs.gpu ?? 'Unknown'}</dd></div>
              <div><dt>Memory</dt><dd>{specs.ram_gb ? `${specs.ram_gb} GB ${specs.ram_type ?? ''}`.trim() : 'Unknown'}</dd></div>
              <div><dt>Storage</dt><dd>{specs.storage_gb ? `${specs.storage_gb} GB ${specs.storage_type ?? ''}`.trim() : 'Unknown'}</dd></div>
              <div><dt>Condition</dt><dd>{pretty(specs.condition)}</dd></div>
              {specs.system_age_years !== null && <div><dt>Age</dt><dd>{specs.system_age_years} years</dd></div>}
              {specs.brand && <div><dt>Builder</dt><dd>{specs.brand}</dd></div>}
            </dl>
          </section>

          {prediction.warnings.length > 0 && (
            <section className="sidebar-warning">
              <div className="rail-title"><Icon name="alert" size={15} /><h3>Estimate caveats</h3></div>
              {prediction.warnings.map((warning) => <p key={warning}>{warning}</p>)}
            </section>
          )}

          <button className="button button-secondary full-width" onClick={onReset}><Icon name="refresh" size={15} /><span>Analyze another listing</span></button>
        </aside>
      </div>
    </section>
  )
}
