import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import { useLiveStream } from '../hooks/useLiveStream'
import type { RoadTeam, RoadRound } from '../lib/types'

// Easy (green) → hard (red) hue ramp across the field's difficulty range.
function diffColor(v: number, lo: number, hi: number): string {
  const f = hi - lo < 1e-6 ? 0.5 : (v - lo) / (hi - lo)
  const hue = 140 - 132 * f   // 140=green → 8=red
  return `hsl(${hue}, 62%, 44%)`
}

function RoundChip({ r }: { r: RoadRound }) {
  if (!r.likely_opp || r.p_reach <= 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, width: 58, opacity: 0.4 }}>
        <span style={{ fontSize: 9, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase' }}>{r.round}</span>
        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>—</span>
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, width: 58 }}
         title={`${r.round}: vs ${r.likely_opp} (${(r.likely_opp_p! * 100).toFixed(0)}% likely) · reach ${(r.p_reach * 100).toFixed(0)}% · opp power ${r.opp_power}`}>
      <span style={{ fontSize: 9, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase' }}>{r.round}</span>
      <FlagImg team={r.likely_opp} size={18} />
      <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-2)', fontVariantNumeric: 'tabular-nums' }}>{r.opp_power}</span>
    </div>
  )
}

function TeamRow({ t, rank, lo, hi }: { t: RoadTeam; rank: number; lo: number; hi: number }) {
  const color = diffColor(t.difficulty, lo, hi)
  const barW = hi - lo < 1e-6 ? 50 : 12 + 88 * ((t.difficulty - lo) / (hi - lo))
  return (
    <tr style={{ borderBottom: '1px solid var(--border)' }}>
      <td style={{ padding: '10px 10px', fontSize: 12, color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>{rank + 1}</td>
      <td style={{ padding: '10px 6px' }}><FlagImg team={t.team} size={22} /></td>
      <td style={{ padding: '10px 8px', fontSize: 13, fontWeight: 600, minWidth: 120 }}>{t.team}</td>
      <td style={{ padding: '10px 10px', minWidth: 150 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, height: 7, background: 'var(--surface-hi)', borderRadius: 4, overflow: 'hidden', minWidth: 60 }}>
            <div style={{ width: `${barW}%`, height: '100%', background: color, borderRadius: 4 }} />
          </div>
          <span style={{ fontSize: 12.5, fontWeight: 700, color, fontVariantNumeric: 'tabular-nums', width: 34, textAlign: 'right' }}>
            {t.difficulty.toFixed(0)}
          </span>
        </div>
      </td>
      <td style={{ padding: '10px 10px', textAlign: 'right', fontSize: 12.5, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
        {(t.p_reach_final * 100).toFixed(1)}%
      </td>
      <td style={{ padding: '8px 10px' }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {t.rounds.map(r => <RoundChip key={r.round} r={r} />)}
        </div>
      </td>
    </tr>
  )
}

export default function Road() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['road'], queryFn: api.roadToFinal })
  useLiveStream(() => qc.invalidateQueries({ queryKey: ['road'] }))
  const [hardestFirst, setHardestFirst] = useState(false)

  const teams = data?.teams ?? []
  const diffs = teams.map(t => t.difficulty)
  const lo = diffs.length ? Math.min(...diffs) : 0
  const hi = diffs.length ? Math.max(...diffs) : 1
  const ordered = hardestFirst ? [...teams].reverse() : teams

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontFamily: "'Space Grotesk',sans-serif", fontWeight: 800, fontSize: 26, letterSpacing: '-0.03em', marginBottom: 4 }}>
            <span className="gradient-text">Road to the Final</span>
          </h1>
          <p style={{ fontSize: 12, color: 'var(--text-3)' }}>
            {data ? `${data.n_simulations.toLocaleString()} simulations · projected opponent strength from the Round of 16 onward` : 'Loading…'}
          </p>
        </div>
        <button onClick={() => setHardestFirst(h => !h)} style={{
          fontSize: 12, fontWeight: 600, padding: '7px 14px', borderRadius: 8,
          border: '1px solid var(--border-hi)', background: 'var(--surface)', color: 'var(--text-2)', cursor: 'pointer',
        }}>
          {hardestFirst ? '↑ Easiest first' : '↓ Hardest first'}
        </button>
      </div>

      {isLoading ? (
        <div className="shimmer" style={{ height: 560, borderRadius: 12 }} />
      ) : (
        <div className="card" style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-hi)' }}>
                <th style={{ padding: '10px', width: 28 }} />
                <th style={{ padding: '10px 6px', width: 34 }} />
                <th style={{ padding: '10px 8px', textAlign: 'left' }}><span className="label">Team</span></th>
                <th style={{ padding: '10px', textAlign: 'left' }}><span className="label">Path difficulty</span></th>
                <th style={{ padding: '10px', textAlign: 'right' }}><span className="label">P(final)</span></th>
                <th style={{ padding: '10px', textAlign: 'left' }}><span className="label">Likely opponents · power</span></th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((t, i) => (
                <TeamRow key={t.team} t={t} rank={hardestFirst ? teams.length - 1 - i : i} lo={lo} hi={hi} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p style={{ fontSize: 11, color: 'var(--text-3)' }}>
        Difficulty = probability-weighted average opponent power rating (0–100) across the Round of 16 through the Final. Lower is an easier road.
      </p>
    </div>
  )
}
