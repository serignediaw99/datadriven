import { Fragment } from 'react'
import type { GroupOdds, ThirdPlaceOdds } from '../lib/types'
import { FlagImg } from '../lib/FlagImg'

const COLS = ['1st', '2nd', '3rd', '4th'] as const

const ZONE_LABELS: Record<number, string> = {
  2: 'top-8 contention',
  3: 'eliminated',
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
            const zoneLabel = ZONE_LABELS[i]

            return (
              <Fragment key={t.team}>
                {zoneLabel && (
                  <tr>
                    <td colSpan={6} style={{ padding: '3px 0' }}>
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '0 16px',
                      }}>
                        <div style={{ flex: 1, borderTop: '1px dashed var(--border)' }} />
                        <span style={{
                          fontSize: 9, fontWeight: 600, letterSpacing: '0.07em',
                          color: 'var(--text-3)', textTransform: 'uppercase', whiteSpace: 'nowrap',
                        }}>
                          {zoneLabel}
                        </span>
                        <div style={{ flex: 1, borderTop: '1px dashed var(--border)' }} />
                      </div>
                    </td>
                  </tr>
                )}
                <tr style={{
                  borderBottom: i < 3 ? '1px solid var(--border)' : 'none',
                  opacity: i === 3 ? 0.65 : 1,
                }}>
                  <td style={{ padding: '10px 16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <FlagImg team={t.team} size={19} />
                      <span style={{
                        fontSize: 13,
                        fontWeight: i < 2 ? 600 : 400,
                        color: 'var(--text-1)',
                      }}>
                        {t.team}
                      </span>
                    </div>
                  </td>
                  {probs.map((p, pi) => (
                    <td key={pi} style={{
                      padding: '10px 6px',
                      textAlign: 'right',
                      fontSize: 12,
                      fontVariantNumeric: 'tabular-nums',
                      color: p >= 0.5 ? 'var(--text-1)' : p >= 0.1 ? 'var(--text-2)' : 'var(--text-3)',
                      fontWeight: p >= 0.5 ? 700 : 400,
                    }}>
                      {(p * 100).toFixed(0)}%
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
