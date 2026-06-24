import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import { useLiveStream } from '../hooks/useLiveStream'
import type { TeamKnockoutOdds } from '../lib/types'

const ROUNDS = ['R32','R16','QF','SF','Final','Winner'] as const
type Round = typeof ROUNDS[number]

const ROUND_COLORS: Record<Round, string> = {
  R32:    '#a8896a',
  R16:    '#c49a6c',
  QF:     '#b56d3c',
  SF:     '#8b4513',
  Final:  '#b57e10',
  Winner: '#2e7d52',
}

function ProbCell({ value, round }: { value: number; round: Round }) {
  if (value < 0.001) {
    return (
      <td style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--text-3)', fontSize: 12 }}>—</td>
    )
  }
  const color = ROUND_COLORS[round]
  const opacity = Math.max(0.35, Math.min(value * 2.5, 1))
  return (
    <td style={{ padding: '10px 14px', textAlign: 'right' }}>
      <span style={{
        fontSize: 12,
        fontWeight: 600,
        fontVariantNumeric: 'tabular-nums',
        color,
        opacity,
      }}>
        {(value * 100).toFixed(1)}%
      </span>
    </td>
  )
}

function TeamRow({ t, rank }: { t: TeamKnockoutOdds; rank: number }) {
  return (
    <tr style={{
      borderBottom: '1px solid var(--border)',
      background: 'transparent',
    }}>
      <td style={{ padding: '10px 14px', fontSize: 12, color: 'var(--text-3)', width: 32, fontVariantNumeric: 'tabular-nums' }}>
        {rank + 1}
      </td>
      <td style={{ padding: '10px 6px', width: 36 }}>
        <FlagImg team={t.team} size={22} />
      </td>
      <td style={{ padding: '10px 8px', fontSize: 13, fontWeight: 500, color: 'var(--text-1)', minWidth: 140 }}>
        {t.team}
      </td>
      {ROUNDS.map(r => <ProbCell key={r} value={t.probs[r] ?? 0} round={r} />)}
    </tr>
  )
}

export default function Knockout() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['knockout'], queryFn: api.knockout })
  useLiveStream(() => qc.invalidateQueries({ queryKey: ['knockout'] }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700, fontSize: 24,
          letterSpacing: '-0.02em', marginBottom: 6,
        }}>
          <span className="gradient-text">Knockout Probabilities</span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>
          {data ? `${data.n_simulations.toLocaleString()} simulations · sorted by win probability` : 'Loading…'}
        </p>
      </div>

      {isLoading ? (
        <div className="shimmer" style={{ height: 600, borderRadius: 12 }} />
      ) : (
        <div className="card" style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-hi)' }}>
                <th style={{ padding: '10px 14px', width: 32 }} />
                <th style={{ padding: '10px 6px',  width: 36 }} />
                <th style={{ padding: '10px 8px',  textAlign: 'left' }}>
                  <span className="label">Team</span>
                </th>
                {ROUNDS.map(r => (
                  <th key={r} style={{
                    padding: '10px 14px',
                    textAlign: 'right',
                    fontSize: 11, fontWeight: 700,
                    letterSpacing: '.06em',
                    textTransform: 'uppercase',
                    color: ROUND_COLORS[r],
                  }}>
                    {r}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.teams ?? []).map((t, i) => <TeamRow key={t.team} t={t} rank={i} />)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
