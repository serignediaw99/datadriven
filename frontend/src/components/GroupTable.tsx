import type { GroupOdds, ThirdPlaceOdds } from '../lib/types'
import { FlagImg } from '../lib/FlagImg'

function StackedBar({ p1, p2, p3, p4 }: { p1: number; p2: number; p3: number; p4: number }) {
  return (
    <div style={{
      display: 'flex',
      height: 5,
      borderRadius: 3,
      overflow: 'hidden',
      width: '100%',
      background: 'var(--border)',
    }}>
      {[
        { pct: p1, color: '#2e7d52' },
        { pct: p2, color: '#2563eb' },
        { pct: p3, color: '#f59e0b' },
        { pct: p4, color: '#dc2626' },
      ].map(({ pct, color }, i) => (
        <div
          key={i}
          className="prob-bar-fill"
          style={{ width: `${pct * 100}%`, background: color, animationDelay: `${i * 60}ms` }}
        />
      ))}
    </div>
  )
}

export default function GroupTable({ group, thirdPlace }: { group: GroupOdds; thirdPlace?: ThirdPlaceOdds }) {
  return (
    <div className="card">
      {/* Header */}
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span className="label">{group.group}</span>
        {thirdPlace && (
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
            3rd qual:{' '}
            <span style={{ color: 'var(--gold)', fontWeight: 600 }}>
              {(thirdPlace.p_qualify_as_3rd * 100).toFixed(0)}%
            </span>
          </span>
        )}
      </div>

      {/* Team rows */}
      <div>
        {group.teams.map((t, i) => (
          <div
            key={t.team}
            style={{
              display: 'grid',
              gridTemplateColumns: '22px 1fr 40px 40px 44px',
              gap: 8,
              alignItems: 'center',
              padding: '10px 14px',
              borderBottom: i < 3 ? '1px solid var(--border)' : 'none',
            }}
          >
            <FlagImg team={t.team} size={20} />
            <div>
              <div style={{
                fontSize: 13,
                fontWeight: 500,
                color: i < 2 ? 'var(--text-1)' : 'var(--text-2)',
                marginBottom: 5,
              }}>
                {t.team}
              </div>
              <StackedBar p1={t.p_1st} p2={t.p_2nd} p3={t.p_3rd} p4={t.p_4th} />
            </div>
            <span style={{
              fontSize: 12, fontWeight: 600, textAlign: 'right',
              color: '#2e7d52', fontVariantNumeric: 'tabular-nums',
            }}>
              {(t.p_1st * 100).toFixed(0)}%
            </span>
            <span style={{
              fontSize: 12, fontWeight: 600, textAlign: 'right',
              color: '#2563eb', fontVariantNumeric: 'tabular-nums',
            }}>
              {(t.p_2nd * 100).toFixed(0)}%
            </span>
            <span style={{
              fontSize: 12, textAlign: 'right',
              color: 'var(--text-2)', fontVariantNumeric: 'tabular-nums',
            }}>
              {t.avg_pts.toFixed(1)} pts
            </span>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div style={{
        padding: '8px 14px',
        display: 'flex',
        gap: 14,
        borderTop: '1px solid var(--border)',
      }}>
        {[
          { color: '#2e7d52', label: '1st' },
          { color: '#2563eb', label: '2nd' },
          { color: '#f59e0b', label: '3rd' },
          { color: '#dc2626', label: 'Out' },
        ].map(({ color, label }) => (
          <span key={label} style={{
            fontSize: 10,
            color: 'var(--text-3)',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: 2,
              background: color, display: 'inline-block', flexShrink: 0,
            }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
