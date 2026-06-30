import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import { useLiveStream } from '../hooks/useLiveStream'
import type { MoverRow, MoversResponse } from '../lib/types'

function MoverItem({ m, rising }: { m: MoverRow; rising: boolean }) {
  const color = rising ? '#2e7d52' : '#c0392b'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 4px', borderBottom: '1px solid var(--border)' }}>
      <FlagImg team={m.team} size={22} />
      <span style={{ fontSize: 13, fontWeight: 600, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {m.team}
      </span>
      <span style={{ fontSize: 12, color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>
        {(m.from * 100).toFixed(1)}% → <span style={{ color: 'var(--text-1)', fontWeight: 700 }}>{(m.to * 100).toFixed(1)}%</span>
      </span>
      <span style={{ width: 70, textAlign: 'right', fontSize: 12.5, fontWeight: 700, color, fontVariantNumeric: 'tabular-nums' }}>
        {rising ? '+' : ''}{(m.delta * 100).toFixed(1)} pts
      </span>
      {m.mult != null && (m.mult >= 1.5 || m.mult <= 0.67) && (
        <span style={{ width: 44, textAlign: 'right', fontSize: 11.5, fontWeight: 700, color }}>
          {m.mult.toFixed(1)}×
        </span>
      )}
    </div>
  )
}

function MoverColumn({ title, rows, rising }: { title: string; rows: MoverRow[]; rising: boolean }) {
  return (
    <div className="card" style={{ padding: 16, flex: 1, minWidth: 280 }}>
      <span className="label" style={{ color: rising ? '#2e7d52' : '#c0392b' }}>{title}</span>
      <div style={{ marginTop: 10 }}>
        {rows.length === 0
          ? <p style={{ fontSize: 12, color: 'var(--text-3)', padding: '8px 0' }}>No movement yet.</p>
          : rows.map(m => <MoverItem key={m.team} m={m} rising={rising} />)}
      </div>
    </div>
  )
}

export default function Movers() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['movers'], queryFn: api.titleMovers })
  useLiveStream(() => qc.invalidateQueries({ queryKey: ['movers'] }))
  const [mode, setMode] = useState<'baseline' | 'previous'>('baseline')

  const hasHistory = !!data && (data.history?.length ?? 0) >= 2

  const render = (d: MoversResponse) => {
    const rows = mode === 'baseline' ? d.vs_baseline : d.vs_previous
    const risers = rows.filter(r => r.delta > 0.0005)
    const fallers = rows.filter(r => r.delta < -0.0005).slice().reverse()
    const ref = mode === 'baseline' ? d.baseline : d.previous
    return (
      <>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {(['baseline', 'previous'] as const).map(k => (
            <button key={k} onClick={() => setMode(k)} style={{
              fontSize: 12, fontWeight: 600, padding: '7px 14px', borderRadius: 8, cursor: 'pointer',
              border: '1px solid var(--border-hi)',
              background: mode === k ? 'var(--accent)' : 'var(--surface)',
              color: mode === k ? '#fff' : 'var(--text-2)',
            }}>
              {k === 'baseline' ? 'Since knockouts began' : 'Since last result'}
            </button>
          ))}
          {ref && d.current && (
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
              {ref.label} → {d.current.label}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <MoverColumn title="📈 Risers" rows={risers} rising />
          <MoverColumn title="📉 Fallers" rows={fallers} rising={false} />
        </div>
      </>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ fontFamily: "'Space Grotesk',sans-serif", fontWeight: 800, fontSize: 26, letterSpacing: '-0.03em', marginBottom: 4 }}>
          <span className="gradient-text">Title Odds Movers</span>
        </h1>
        <p style={{ fontSize: 12, color: 'var(--text-3)' }}>
          {data ? `${data.n_simulations.toLocaleString()} simulations · championship-probability swings as the knockouts unfold` : 'Loading…'}
        </p>
      </div>

      {isLoading || !data ? (
        <div className="shimmer" style={{ height: 360, borderRadius: 12 }} />
      ) : !hasHistory ? (
        <div className="card" style={{ padding: 24 }}>
          <p style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 6 }}>
            Movers appear once the next knockout result lands.
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-3)' }}>
            {data.current
              ? `Baseline captured at: ${data.current.label}. Each completed knockout match adds a new snapshot to compare against.`
              : 'Waiting for the first snapshot.'}
          </p>
        </div>
      ) : (
        render(data)
      )}
    </div>
  )
}
