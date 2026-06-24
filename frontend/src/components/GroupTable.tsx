import { Fragment } from 'react'
import type { GroupOdds, ThirdPlaceOdds } from '../lib/types'
import { FlagImg } from '../lib/FlagImg'

const COLS = ['1st', '2nd', '3rd', '4th'] as const

// Heatmap cell: amber background scales with probability; text always readable
function heatCell(p: number): React.CSSProperties {
  const alpha = Math.max(0.08, Math.pow(p, 0.6) * 0.55)
  return {
    padding: '10px 6px',
    textAlign: 'right',
    fontSize: 12,
    fontVariantNumeric: 'tabular-nums',
    fontWeight: p >= 0.35 ? 700 : 400,
    background: `rgba(181, 109, 60, ${alpha})`,
    color: 'rgba(240, 220, 200, 0.88)',
  }
}

export default function GroupTable({ group, thirdPlace }: { group: GroupOdds; thirdPlace?: ThirdPlaceOdds }) {
  const p3rdQual = thirdPlace?.p_qualify_as_3rd ?? 0

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      overflow: 'hidden',
    }}>
      {/* Card header */}
      <div style={{
        padding: '11px 16px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'var(--surface-hi)',
        borderBottom: '1px solid var(--border-hi)',
      }}>
        <span style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 800, fontSize: 15, letterSpacing: '-0.02em',
          color: 'var(--text-1)',
        }}>
          {group.group}
        </span>
        {thirdPlace && (
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
            3rd qual:{' '}
            <strong style={{ color: 'var(--text-2)', fontWeight: 600 }}>
              {(p3rdQual * 100).toFixed(0)}%
            </strong>
            {thirdPlace.pts_needed_p50 != null && ` · ~${thirdPlace.pts_needed_p50} pts`}
          </span>
        )}
      </div>

      {/* Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border-hi)' }}>
            <th style={{ padding: '8px 16px', textAlign: 'left' }}>
              <span className="label">Team</span>
            </th>
            {COLS.map(h => (
              <th key={h} style={{ padding: '8px 6px', textAlign: 'right', width: 40 }}>
                <span className="label">{h}</span>
              </th>
            ))}
            <th style={{ padding: '8px 16px 8px 6px', textAlign: 'right', width: 46 }}>
              <span className="label" style={{ color: 'var(--accent)' }}>R32</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {group.teams.map((t, i) => {
            const r32 = t.p_1st + t.p_2nd + t.p_3rd * p3rdQual
            const probs = [t.p_1st, t.p_2nd, t.p_3rd, t.p_4th]

            return (
              <Fragment key={t.team}>
                <tr style={{ borderBottom: i < 3 ? '1px solid var(--border)' : 'none' }}>
                  <td style={{ padding: '10px 16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <FlagImg team={t.team} size={19} />
                      <span style={{
                        fontSize: 13,
                        fontWeight: i < 2 ? 600 : 400,
                        color: i === 3 ? 'var(--text-3)' : 'var(--text-1)',
                      }}>
                        {t.team}
                      </span>
                    </div>
                  </td>
                  {probs.map((p, pi) => (
                    <td key={pi} style={heatCell(p)}>
                      {p === 0 ? '0%' : `${(p * 100).toFixed(0)}%`}
                    </td>
                  ))}
                  <td style={{
                    padding: '10px 16px 10px 6px',
                    textAlign: 'right',
                    fontSize: 13,
                    fontWeight: 700,
                    fontVariantNumeric: 'tabular-nums',
                    color: 'var(--accent)',
                  }}>
                    {Math.round(r32 * 100)}%
                  </td>
                </tr>
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
