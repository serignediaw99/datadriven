import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import { useLiveStream } from '../hooks/useLiveStream'
import type { FinalMatchupsResponse } from '../lib/types'

const ACCENT = '181,109,60'  // var(--accent) rgb
const MAX_GRID = 8           // top-N finalists per axis for a legible/screenshottable grid

function Pct({ v, digits = 1 }: { v: number; digits?: number }) {
  return <>{(v * 100).toFixed(digits)}%</>
}

// ─── Hero: the single most likely final ───────────────────────────────────────
function Hero({ pair }: { pair: FinalMatchupsResponse['most_likely'][number] }) {
  return (
    <div className="card" style={{
      padding: '22px 26px', display: 'flex', flexDirection: 'column', gap: 14,
      alignItems: 'center', textAlign: 'center',
    }}>
      <span className="label" style={{ color: 'var(--text-3)' }}>Most likely final</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <FlagImg team={pair.team_a} size={46} />
          <span style={{ fontSize: 15, fontWeight: 700 }}>{pair.team_a}</span>
        </div>
        <span style={{ fontFamily: "'Space Grotesk',sans-serif", fontWeight: 800, fontSize: 18, color: 'var(--text-3)' }}>vs</span>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <FlagImg team={pair.team_b} size={46} />
          <span style={{ fontSize: 15, fontWeight: 700 }}>{pair.team_b}</span>
        </div>
      </div>
      <div style={{
        fontFamily: "'Space Grotesk',sans-serif", fontWeight: 800, fontSize: 30,
        letterSpacing: '-0.02em',
      }}>
        <span className="gradient-text"><Pct v={pair.p} digits={2} /></span>
      </div>
    </div>
  )
}

// ─── Ranked list of most likely finals ────────────────────────────────────────
function RankedFinals({ pairs }: { pairs: FinalMatchupsResponse['most_likely'] }) {
  const max = pairs.length ? pairs[0].p : 1
  return (
    <div className="card" style={{ padding: 16 }}>
      <span className="label" style={{ color: 'var(--text-3)' }}>Most likely finals</span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 12 }}>
        {pairs.map((p, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 4px' }}>
            <span style={{ width: 18, fontSize: 12, color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>{i + 1}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, width: 168 }}>
              <FlagImg team={p.team_a} size={18} />
              <span style={{ fontSize: 12.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.team_a}</span>
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-3)' }}>v</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, width: 168 }}>
              <FlagImg team={p.team_b} size={18} />
              <span style={{ fontSize: 12.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.team_b}</span>
            </div>
            <div style={{ flex: 1, height: 6, background: 'var(--surface-hi)', borderRadius: 3, overflow: 'hidden', minWidth: 40 }}>
              <div style={{ width: `${(p.p / max) * 100}%`, height: '100%', background: `rgb(${ACCENT})`, borderRadius: 3 }} />
            </div>
            <span style={{ width: 48, textAlign: 'right', fontSize: 12.5, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
              <Pct v={p.p} digits={2} />
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Finalist probability heatmap ─────────────────────────────────────────────
function Heatmap({ data }: { data: FinalMatchupsResponse['heatmap'] }) {
  const rows = data.rows.slice(0, MAX_GRID)
  const cols = data.cols.slice(0, MAX_GRID)
  let max = 0
  for (let i = 0; i < rows.length; i++)
    for (let j = 0; j < cols.length; j++)
      max = Math.max(max, data.matrix[i][j])
  if (max <= 0) max = 1

  return (
    <div className="card" style={{ padding: 16, overflowX: 'auto' }}>
      <span className="label" style={{ color: 'var(--text-3)' }}>Finalist matchup matrix · P(this exact final)</span>
      <table style={{ borderCollapse: 'collapse', marginTop: 14 }}>
        <thead>
          <tr>
            <th style={{ position: 'sticky', left: 0, background: 'var(--surface)' }} />
            {cols.map(c => (
              <th key={c.team} style={{ padding: '4px 2px', minWidth: 44 }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }} title={c.team}>
                  <FlagImg team={c.team} size={20} />
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.team}>
              <td style={{ position: 'sticky', left: 0, background: 'var(--surface)', paddingRight: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }} title={r.team}>
                  <FlagImg team={r.team} size={18} />
                  <span style={{ fontSize: 11.5, fontWeight: 600, whiteSpace: 'nowrap' }}>{r.team}</span>
                </div>
              </td>
              {cols.map((c, j) => {
                const v = data.matrix[i][j]
                const alpha = v <= 0 ? 0 : 0.12 + 0.88 * (v / max)
                return (
                  <td key={c.team} style={{
                    textAlign: 'center', padding: '8px 2px',
                    background: v > 0 ? `rgba(${ACCENT},${alpha.toFixed(3)})` : 'transparent',
                    border: '1px solid var(--border)',
                    fontSize: 10.5, fontWeight: 600,
                    color: alpha > 0.55 ? '#fff' : 'var(--text-2)',
                    fontVariantNumeric: 'tabular-nums',
                  }}>
                    {v > 0 ? (v * 100).toFixed(1) : '·'}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 10 }}>
        Rows and columns are the two bracket halves — each cell is the probability those two teams meet in the final.
      </p>
    </div>
  )
}

export default function FinalMatchups() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['final-matchups'], queryFn: api.finalMatchups })
  useLiveStream(() => qc.invalidateQueries({ queryKey: ['final-matchups'] }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ fontFamily: "'Space Grotesk',sans-serif", fontWeight: 800, fontSize: 26, letterSpacing: '-0.03em', marginBottom: 4 }}>
          <span className="gradient-text">Most Likely Final</span>
        </h1>
        <p style={{ fontSize: 12, color: 'var(--text-3)' }}>
          {data ? `${data.n_simulations.toLocaleString()} simulations · probability of every possible final matchup` : 'Loading…'}
        </p>
      </div>

      {isLoading || !data ? (
        <div className="shimmer" style={{ height: 480, borderRadius: 12 }} />
      ) : data.most_likely.length === 0 ? (
        <p style={{ color: 'var(--text-3)' }}>No finalist data yet.</p>
      ) : (
        <>
          <Hero pair={data.most_likely[0]} />
          <RankedFinals pairs={data.most_likely} />
          <Heatmap data={data.heatmap} />
        </>
      )}
    </div>
  )
}
