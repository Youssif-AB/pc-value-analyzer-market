import { useEffect, useState } from 'react'
import { getModelPerformance } from '../api'
import { Icon } from '../icons'
import type { ModelPerformance, Prediction, Specs } from '../types'

interface Props {
  prediction: Prediction
  specs: Specs
  onReset: () => void
}

function money(value: number) {
  return new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 }).format(value)
}

function sourceName(source: string) {
  if (source === 'ebay') return 'eBay'
  if (source === 'google_shopping') return 'Google Shopping'
  if (source === 'bestbuy') return 'Best Buy'
  return source
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
  const [performance, setPerformance] = useState<ModelPerformance | null>(null)
  useEffect(() => {
    getModelPerformance().then(setPerformance).catch(() => setPerformance(null))
  }, [prediction.model_version])
  const buyerSavings = prediction.estimated_fair_price - prediction.asking_price
  const live = prediction.live_market
  const errorBands = performance?.price_bands ?? []
  const lowestErrorBand = errorBands.length ? errorBands.reduce((best, band) => band.mae < best.mae ? band : best) : null
  const highestErrorBand = errorBands.length ? errorBands.reduce((worst, band) => band.mae > worst.mae ? band : worst) : null
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
          <h2 id="result-heading">Estimated market listing price: {money(prediction.estimated_fair_price)}.</h2>
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

            <div className="visualization-block">
              <div className="visualization-copy">
                <strong>Estimate in today’s comparable market</strong>
                <span>{live.comp_count > 0 ? `${live.comp_count} current asking-price comparable${live.comp_count === 1 ? '' : 's'}; dots are individual listings, not completed sales.` : 'No suitable comparable listings were available for this valuation.'}</span>
              </div>
              {live.market_context_figure ? (
                <img src={live.market_context_figure} alt={`Market context from ${live.comp_count} live comparable asking prices. Model estimate ${money(prediction.estimated_fair_price)} with prediction interval ${money(prediction.lower_bound)} to ${money(prediction.upper_bound)}.`} />
              ) : (
                <div className="chart-unavailable">Market context visualization unavailable. The valuation remains valid without it.</div>
              )}
              {live.comp_count > 0 && live.comp_count < 5 && <p className="sample-caution">Small sample: these listings provide limited context, not a reliable market distribution.</p>}
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

          <details className="performance-section">
            <summary><span><span className="section-kicker">Model transparency</span><strong>Held-out model performance</strong></span><span>View evaluation</span></summary>
            <div className="performance-body">
              {performance?.available && performance.model_version === prediction.model_version ? (
                <>
                  <p className="performance-context">Historical held-out evaluation only — separate from current market comparables. N={performance.sample_count}. {performance.note}</p>
                  <div className="metric-strip">
                    <div><span>MAE</span><strong>{performance.mae === null ? '—' : money(performance.mae)}</strong></div>
                    <div><span>RMSE</span><strong>{performance.rmse === null ? '—' : money(performance.rmse)}</strong></div>
                    <div><span>R²</span><strong>{performance.r2 === null ? '—' : performance.r2.toFixed(3)}</strong></div>
                  </div>
                  {performance.figures.map((figure) => (
                    <figure className="performance-figure" key={figure.key}>
                      <figcaption><strong>{figure.key === 'predicted_vs_actual' ? 'Predicted vs. actual' : 'Error by price band'}</strong><span>{figure.key === 'predicted_vs_actual' ? 'Points near the diagonal are closer predictions; distance from it is error.' : 'Mean absolute error by actual observed price. N labels show the evidence behind each bar.'}</span></figcaption>
                      <img src={figure.data_uri} alt={figure.alt} />
                    </figure>
                  ))}
                  {lowestErrorBand && highestErrorBand && <p className="performance-context">Measured segment range: lowest MAE was {lowestErrorBand.label} ({money(lowestErrorBand.mae)}, N={lowestErrorBand.count}); highest was {highestErrorBand.label} ({money(highestErrorBand.mae)}, N={highestErrorBand.count}). {Math.min(...errorBands.map((band) => band.count)) < 20 ? 'At least one band has a small sample, so comparisons are tentative.' : ''}</p>}
                  {performance.data_scope === 'synthetic_demo' && <p className="sample-caution">Demo limitation: these observations are synthetic workflow data, not evidence of real-market accuracy.</p>}
                </>
              ) : <div className="chart-unavailable">Matching held-out figures are unavailable for model {prediction.model_version}.</div>}
            </div>
          </details>
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

          <section className="config-section">
            <div className="rail-title"><Icon name="database" size={15} /><h3>Training coverage</h3></div>
            <p><strong>{pretty(prediction.coverage_label)}</strong> ({Math.round(prediction.coverage_score * 100)}%)</p>
            <p>The likely range is a conformal interval, not a guarantee.{prediction.interval_empirical_coverage !== null ? ` Its held-out empirical coverage was ${Math.round(prediction.interval_empirical_coverage * 100)}%.` : ''}</p>
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
