import { FormEvent, useState } from 'react'

const EXAMPLE = `Gaming PC - like new. Ryzen 7 7800X3D, GeForce RTX 4070 12GB, 32GB DDR5, 2TB NVMe SSD. Asking $1,650. Built about 1 year ago.`

interface Props {
  busy: boolean
  error: string | null
  onSubmit: (text: string) => Promise<void>
}

export function ListingInput({ busy, error, onSubmit }: Props) {
  const [text, setText] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (text.trim().length < 20) return
    await onSubmit(text.trim())
  }

  return (
    <section className="panel input-panel" aria-labelledby="listing-heading">
      <div className="eyebrow">Step 1 of 3</div>
      <h2 id="listing-heading">Paste the full PC listing</h2>
      <p className="muted">Include the asking price and as many hardware details as the seller provides. You’ll review every extracted field before the model sees it.</p>
      <form onSubmit={submit}>
        <label htmlFor="listing">Listing text</label>
        <textarea
          id="listing"
          rows={10}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={EXAMPLE}
          disabled={busy}
        />
        <div className="form-actions">
          <button type="button" className="ghost" onClick={() => setText(EXAMPLE)} disabled={busy}>Use example</button>
          <button type="submit" className="primary" disabled={busy || text.trim().length < 20}>{busy ? 'Extracting…' : 'Extract specs'}</button>
        </div>
        {error && <div className="error" role="alert">{error}</div>}
      </form>
    </section>
  )
}
