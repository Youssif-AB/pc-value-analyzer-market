import { FormEvent, useMemo, useState } from 'react'
import type { ExtractedSpecs, Specs } from '../types'

interface Props {
  extracted: ExtractedSpecs
  busy: boolean
  error: string | null
  onBack: () => void
  onConfirm: (specs: Specs, askingPrice: number) => Promise<void>
}

const conditionOptions = ['new', 'like_new', 'excellent', 'good', 'fair', 'parts'] as const

export function SpecReview({ extracted, busy, error, onBack, onConfirm }: Props) {
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

  const warningCount = extracted.extraction_warnings.length + extracted.normalization_failures.length

  return (
    <section className="panel review-panel" aria-labelledby="review-heading">
      <div className="eyebrow">Step 2 of 3</div>
      <div className="section-heading">
        <div>
          <h2 id="review-heading">Review the extracted specs</h2>
          <p className="muted">Corrections are intentional model inputs, not cosmetic edits. Fix anything the parser got wrong.</p>
        </div>
        <span className={`status-pill ${warningCount ? 'warning' : 'clean'}`}>{warningCount ? `${warningCount} checks` : 'Looks complete'}</span>
      </div>

      {warningCount > 0 && (
        <div className="warning-box">
          {[...extracted.extraction_warnings, ...extracted.normalization_failures].map((warning) => <div key={warning}>• {warning}</div>)}
        </div>
      )}

      <form onSubmit={submit} className="spec-form">
        <div className="field-grid">
          <label>CPU<input value={specs.cpu ?? ''} onChange={(e) => textField('cpu', e.target.value)} placeholder="e.g. AMD Ryzen 7 7800X3D" /></label>
          <label>GPU<input value={specs.gpu ?? ''} onChange={(e) => textField('gpu', e.target.value)} placeholder="e.g. NVIDIA GeForce RTX 4070" /></label>
          <label>RAM (GB)<input type="number" min="2" max="512" value={specs.ram_gb ?? ''} onChange={(e) => numericField('ram_gb', e.target.value)} /></label>
          <label>RAM type<input value={specs.ram_type ?? ''} onChange={(e) => textField('ram_type', e.target.value)} placeholder="DDR4 / DDR5" /></label>
          <label>Storage (GB)<input type="number" min="32" max="32768" value={specs.storage_gb ?? ''} onChange={(e) => numericField('storage_gb', e.target.value)} /></label>
          <label>Storage type<input value={specs.storage_type ?? ''} onChange={(e) => textField('storage_type', e.target.value)} placeholder="NVMe SSD" /></label>
          <label>Condition<select value={specs.condition} onChange={(e) => setSpecs((current) => ({ ...current, condition: e.target.value as Specs['condition'] }))}>{conditionOptions.map((option) => <option key={option} value={option}>{option.replace('_', ' ')}</option>)}</select></label>
          <label>Brand / builder<input value={specs.brand ?? ''} onChange={(e) => textField('brand', e.target.value)} placeholder="custom" /></label>
          <label>System age (years)<input type="number" min="0" max="20" step="0.5" value={specs.system_age_years ?? ''} onChange={(e) => numericField('system_age_years', e.target.value)} /></label>
          <label className="price-field">Asking price ($)<input type="number" min="1" max="100000" step="1" value={price || ''} onChange={(e) => setPrice(Number(e.target.value))} required /></label>
        </div>
        {error && <div className="error" role="alert">{error}</div>}
        <div className="form-actions split">
          <button type="button" className="ghost" onClick={onBack} disabled={busy}>Back to listing</button>
          <button type="submit" className="primary" disabled={busy || price <= 0}>{busy ? 'Valuing…' : 'Estimate fair price'}</button>
        </div>
      </form>
    </section>
  )
}
