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

export function PredictionResult({ prediction, specs, onReset }: Props) {
  const buyerSavings = prediction.estimated_fair_price - prediction.asking_price
  const live = prediction.live_market
  return (
    <section className="panel result-panel" aria-labelledby="result-heading">
      <div className="eyebrow">Step 3 of 3</div>
      <div className="result-topline">
        <div>
          <div className="muted small">Value rating</div>
          <div className={`rating rating-${prediction.rating.toLowerCase().replaceAll(' ', '-')}`}>{prediction.rating}</div>
        </div>
        <div className={`confidence confidence-${prediction.confidence}`}>{prediction.confidence} confidence</div>
      </div>
      <h2 id="result-heading">{buyerSavings >= 0 ? 'The asking price is below the estimated fair value.' : 'The asking price is above the estimated fair value.'}</h2>

      <div className="price-grid">
        <div className="price-card"><span>Listing price</span><strong>{money(prediction.asking_price)}</strong></div>
        <div className="price-card featured"><span>Estimated fair price</span><strong>{money(prediction.estimated_fair_price)}</strong><small>Likely range {money(prediction.lower_bound)}–{money(prediction.upper_bound)}</small></div>
        <div className="price-card"><span>Difference</span><strong>{prediction.difference_percent > 0 ? '+' : ''}{prediction.difference_percent.toFixed(1)}%</strong><small>{buyerSavings >= 0 ? `${money(buyerSavings)} below estimate` : `${money(Math.abs(buyerSavings))} above estimate`}</small></div>
      </div>

      <section className="market-evidence">
        <div className="market-evidence-heading">
          <div>
            <div className="eyebrow">Live market evidence</div>
            <h3>{live.valuation_method === 'hybrid_live_comps' ? 'Fresh comparables were blended into this valuation.' : 'The ML baseline is carrying this valuation.'}</h3>
          </div>
          <span className="blend-pill">{Math.round(live.blend_weight * 100)}% live weight</span>
        </div>
        <div className="market-metrics">
          <div><span>Comparable listings</span><strong>{live.comp_count}</strong></div>
          <div><span>Source diversity</span><strong>{live.source_count}</strong></div>
          <div><span>Median asking price</span><strong>{live.median_asking_price_cad ? money(live.median_asking_price_cad) : '—'}</strong></div>
          <div><span>Hardware-adjusted market</span><strong>{live.adjusted_market_estimate_cad ? money(live.adjusted_market_estimate_cad) : '—'}</strong></div>
        </div>
        {live.comparables.length > 0 && (
          <div className="comp-list">
            {live.comparables.slice(0, 6).map((comp) => (
              <a className="comp-row" href={comp.url ?? undefined} target="_blank" rel="noreferrer" key={`${comp.source}-${comp.title}-${comp.price_cad}`}>
                <div>
                  <span className="source-tag">{sourceName(comp.source)}</span>
                  <strong>{comp.title}</strong>
                  <small>{comp.condition.replaceAll('_', ' ')} · {Math.round(comp.similarity * 100)}% spec similarity</small>
                </div>
                <b>{money(comp.price_cad)}</b>
              </a>
            ))}
          </div>
        )}
        <p className="market-note">{live.note}</p>
      </section>

      <div className="explanation-grid">
        <div>
          <h3>What influenced the estimate</h3>
          <div className="driver-list">
            {prediction.drivers.map((driver) => (
              <div className="driver" key={`${driver.feature}-${driver.explanation}`}>
                <span className={`direction ${driver.direction}`} aria-hidden="true">{driver.direction === 'up' ? '↑' : driver.direction === 'down' ? '↓' : '•'}</span>
                <div><strong>{driver.feature}</strong><p>{driver.explanation}</p></div>
              </div>
            ))}
          </div>
        </div>
        <aside className="summary-card">
          <h3>Reviewed configuration</h3>
          <dl>
            <div><dt>CPU</dt><dd>{specs.cpu ?? 'Unknown'}</dd></div>
            <div><dt>GPU</dt><dd>{specs.gpu ?? 'Unknown'}</dd></div>
            <div><dt>RAM</dt><dd>{specs.ram_gb ? `${specs.ram_gb} GB ${specs.ram_type ?? ''}` : 'Unknown'}</dd></div>
            <div><dt>Storage</dt><dd>{specs.storage_gb ? `${specs.storage_gb} GB ${specs.storage_type ?? ''}` : 'Unknown'}</dd></div>
            <div><dt>Condition</dt><dd>{specs.condition.replace('_', ' ')}</dd></div>
          </dl>
          <div className="model-version">Model {prediction.model_version}</div>
        </aside>
      </div>

      {prediction.warnings.length > 0 && <div className="notice">{prediction.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div>}
      <div className="form-actions"><button className="primary" onClick={onReset}>Analyze another listing</button></div>
    </section>
  )
}
