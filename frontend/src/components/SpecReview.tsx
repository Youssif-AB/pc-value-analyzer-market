import { FormEvent, useMemo, useState } from 'react'
import { Icon } from '../icons'
import type { ExtractedSpecs, Specs } from '../types'

interface Props {
  extracted: ExtractedSpecs
  listing: string
  busy: boolean
  error: string | null
  onBack: () => void
  onConfirm: (specs: Specs, askingPrice: number) => Promise<void>
}

const conditionOptions = ['new', 'like_new', 'excellent', 'good', 'fair', 'parts'] as const

function prettyCondition(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function SpecReview({ extracted, listing, busy, error, onBack, onConfirm }: Props) {
  const original = useMemo<Specs>(() => ({
    cpu: extracted.cpu,
    gpu: extracted.gpu,
    ram_gb: extracted.ram_gb,
    ram_type: extracted.ram_type,
    storage_gb: extracted.storage_gb,
    storage_type: extracted.storage_type,
    condition: extracted.condition,
    brand: extracted.brand,
    system_age_years: extracted.system_age_years,
  }), [extracted])
  const [specs, setSpecs] = useState<Specs>(original)
  const [price, setPrice] = useState(extracted.asking_price ?? 0)

  function textField(key: keyof Specs, value: string) {
    setSpecs((current) => ({ ...current, [key]: value.trim() || null }))
  }

  function numericField(key: 'ram_gb' | 'storage_gb' | 'system_age_years', value: string) {
    setSpecs((current) => ({ ...current, [key]: value === '' ? null : Number(value) }))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (price <= 0) return
    await onConfirm(specs, price)
  }

  const warnings = [...extracted.extraction_warnings, ...extracted.normalization_failures]
  const changedFields = Object.entries(specs).filter(([key, value]) => original[key as keyof Specs] !== value).length + (price !== (extracted.asking_price ?? 0) ? 1 : 0)

  return (
    <section className="workbench review-workbench" aria-labelledby="review-heading">
      <div className="workbench-main">
        <div className="section-intro review-intro">
          <div>
            <span className="section-kicker">Normalization review</span>
            <h2 id="review-heading">Verify the hardware before pricing</h2>
            <p>The prediction uses these normalized values—not the raw listing text. Correct anything ambiguous or missing.</p>
          </div>
          <div className="review-state" aria-live="polite">
            <span className={warnings.length ? 'review-state-mark warning' : 'review-state-mark'}>{warnings.length ? warnings.length : <Icon name="check" size={13} />}</span>
            <span>{warnings.length ? `${warnings.length} extraction ${warnings.length === 1 ? 'check' : 'checks'}` : 'No extraction warnings'}</span>
          </div>
        </div>

        {warnings.length > 0 && (
          <div className="message warning-message" role="status">
            <Icon name="alert" size={17} />
            <div>
              <strong>Review needed</strong>
              <ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
            </div>
          </div>
        )}

        <form onSubmit={submit} className="spec-form">
          <fieldset className="form-section">
            <legend>Core hardware</legend>
            <div className="form-grid">
              <label className="field span-2"><span>Processor</span><input value={specs.cpu ?? ''} onChange={(e) => textField('cpu', e.target.value)} placeholder="AMD Ryzen 7 7800X3D" /></label>
              <label className="field span-2"><span>Graphics card</span><input value={specs.gpu ?? ''} onChange={(e) => textField('gpu', e.target.value)} placeholder="NVIDIA GeForce RTX 4070" /></label>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>Memory & storage</legend>
            <div className="form-grid four-col">
              <label className="field"><span>RAM</span><div className="input-with-unit"><input type="number" min="2" max="512" value={specs.ram_gb ?? ''} onChange={(e) => numericField('ram_gb', e.target.value)} /><em>GB</em></div></label>
              <label className="field"><span>RAM type</span><input value={specs.ram_type ?? ''} onChange={(e) => textField('ram_type', e.target.value)} placeholder="DDR5" /></label>
              <label className="field"><span>Storage</span><div className="input-with-unit"><input type="number" min="32" max="32768" value={specs.storage_gb ?? ''} onChange={(e) => numericField('storage_gb', e.target.value)} /><em>GB</em></div></label>
              <label className="field"><span>Drive type</span><input value={specs.storage_type ?? ''} onChange={(e) => textField('storage_type', e.target.value)} placeholder="NVMe SSD" /></label>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>Listing context</legend>
            <div className="form-grid">
              <label className="field"><span>Condition</span><select value={specs.condition} onChange={(e) => setSpecs((current) => ({ ...current, condition: e.target.value as Specs['condition'] }))}>{conditionOptions.map((option) => <option key={option} value={option}>{prettyCondition(option)}</option>)}</select></label>
              <label className="field"><span>Brand / builder</span><input value={specs.brand ?? ''} onChange={(e) => textField('brand', e.target.value)} placeholder="Custom build" /></label>
              <label className="field"><span>System age</span><div className="input-with-unit"><input type="number" min="0" max="20" step="0.5" value={specs.system_age_years ?? ''} onChange={(e) => numericField('system_age_years', e.target.value)} /><em>years</em></div></label>
              <label className="field price-input"><span>Asking price</span><div className="input-with-prefix"><em>$</em><input type="number" min="1" max="100000" step="1" value={price || ''} onChange={(e) => setPrice(Number(e.target.value))} required /></div></label>
            </div>
          </fieldset>

          {error && <div className="message error-message" role="alert"><Icon name="alert" size={16} /><span>{error}</span></div>}
          <div className="action-row split-actions">
            <button type="button" className="button button-secondary" onClick={onBack} disabled={busy}><Icon name="arrow-left" size={15} /><span>Back</span></button>
            <div className="action-cluster">
              <span className="change-count">{changedFields ? `${changedFields} ${changedFields === 1 ? 'field' : 'fields'} corrected` : 'No manual changes'}</span>
              <button type="submit" className="button button-primary" disabled={busy || price <= 0}><span>{busy ? 'Pricing build…' : 'Calculate fair value'}</span>{!busy && <Icon name="arrow-right" size={16} />}</button>
            </div>
          </div>
        </form>
      </div>

      <aside className="workbench-rail review-rail">
        <section className="rail-section">
          <div className="rail-title"><Icon name="edit" size={15} /><h3>Source listing</h3></div>
          <blockquote className="listing-preview">{listing}</blockquote>
        </section>
        <section className="rail-section">
          <div className="rail-title"><Icon name="signal" size={15} /><h3>Why review matters</h3></div>
          <p className="rail-copy">CPU and GPU identity carry substantial model weight. A parser miss can move the estimate far more than a cosmetic listing detail.</p>
          <div className="review-rule"><span>Parser output</span><b>Provisional</b></div>
          <div className="review-rule"><span>Your corrections</span><b>Model input</b></div>
        </section>
      </aside>
    </section>
  )
}
