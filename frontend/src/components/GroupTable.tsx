import type { GroupOdds, ThirdPlaceOdds, TeamGroupOdds } from '../lib/types'
import { FlagImg } from '../lib/FlagImg'

const C = {
  first:  '#2e7d52',
  second: '#2563eb',
  third:  '#d97706',
  fourth: '#dc2626',
}

function SegBar({ p1, p2, p3, p4 }: { p1: number; p2: number; p3: number; p4: number }) {
  return (
    <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden' }}>
      <div style={{ flex: p1, background: C.first, minWidth: p1 > 0.005 ? 2 : 0 }} />
      <div style={{ flex: p2, background: C.second, minWidth: p2 > 0.005 ? 2 : 0 }} />
      <div style={{ flex: p3, background: C.third, minWidth: p3 > 0.005 ? 2 : 0 }} />
      <div style={{ flex: p4, background: C.fourth, minWidth: p4 > 0.005 ? 2 : 0 }} />
    </div>
  )
}

function TeamRow({ t, p3rdQual, rank }: { t: TeamGroupOdds; p3rdQual: number; rank: number }) {
  const r32 = t.p_1st + t.p_2nd + t.p_3rd * p3rdQual
  const r32Color = r32 >= 0.75 ? C.first : r32 >= 0.45 ? '#b56d3c' : r32 >= 0.2 ? 'var(--text-2)' : C.fourth
  const zoneColor = rank === 0 ? C.first : rank === 1 ? C.second : rank === 2 ? C.third : C.fourth

  return (
    <div style={{
      padding: '14px 16px',
      borderBottom: '1px solid var(--border)',
      borderLeft: `3px solid ${zoneColor}55`,
    }}>
      {/* Name row + R32 badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 9 }}>
        <FlagImg team={t.team} size={20} />
        <span style={{ flex: 1, fontWeight: 600, fontSize: 13, color: 'var(--text-1)', minWidth: 0 }}>
          {t.team}
        </span>
        <div style={{
          display: 'inline-flex', alignItems: 'baseline', gap: 3,
          padding: '3px 9px', borderRadius: 6,
          background: `${r32Color}15`,
          border: `1px solid ${r32Color}35`,
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: r32Color, letterSpacing: '0.04em' }}>R32</span>
          <span style={{ fontSize: 13, fontWeight: 800, color: r32Color, fontVariantNumeric: 'tabular-nums' }}>
            {Math.round(r32 * 100)}%
          </span>
        </div>
      </div>

      {/* Segmented probability bar */}
      <SegBar p1={t.p_1st} p2={t.p_2nd} p3={t.p_3rd} p4={t.p_4th} />

      {/* Position breakdown + avg stats */}
      <div style={{ display: 'flex', alignItems: 'center', marginTop: 8, gap: 0 }}>
        <div style={{ display: 'flex', gap: 10, flex: 1, flexWrap: 'wrap' }}>
          {[
            { label: '1st', val: t.p_1st, color: C.first },
            { label: '2nd', val: t.p_2nd, color: C.second },
            { label: '3rd', val: t.p_3rd, color: C.third },
            { label: '4th', val: t.p_4th, color: C.fourth },
          ].map(({ label, val, color }) => (
            <span key={label} style={{ fontSize: 11, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
              <span style={{ color: 'var(--text-3)', fontWeight: 500 }}>{label} </span>
              <span style={{ color, fontWeight: 700 }}>{(val * 100).toFixed(0)}%</span>
            </span>
          ))}
        </div>
        <span style={{ fontSize: 10, color: 'var(--text-3)', whiteSpace: 'nowrap', marginLeft: 8 }}>
          {t.avg_pts.toFixed(1)} pts · {t.avg_gd >= 0 ? '+' : ''}{t.avg_gd.toFixed(1)} GD
        </span>
      </div>
    </div>
  )
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
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'var(--surface-hi)',
        borderBottom: '2px solid var(--border-hi)',
      }}>
        <span style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 800, fontSize: 16, letterSpacing: '-0.02em',
          color: 'var(--text-1)',
        }}>
          {group.group}
        </span>
        {thirdPlace && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11, color: 'var(--text-3)' }}>3rd qualifies</span>
            <span style={{
              fontSize: 13, fontWeight: 700,
              color: p3rdQual >= 0.6 ? C.first : p3rdQual >= 0.3 ? C.third : 'var(--text-2)',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {(p3rdQual * 100).toFixed(0)}%
            </span>
            {thirdPlace.pts_needed_p50 != null && (
              <span style={{ fontSize: 10, color: 'var(--text-3)' }}>
                (~{thirdPlace.pts_needed_p50} pts needed)
              </span>
            )}
          </div>
        )}
      </div>

      {/* Qual zone label */}
      <div style={{
        padding: '4px 16px 3px',
        display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 4,
        background: `${C.first}08`,
        borderLeft: `3px solid ${C.first}55`,
        borderBottom: '1px dashed var(--border)',
      }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', color: C.first, textTransform: 'uppercase' }}>
          Auto-qualify (1st & 2nd)
        </span>
      </div>

      {/* 1st & 2nd place rows */}
      {group.teams.slice(0, 2).map((t, i) => (
        <TeamRow key={t.team} t={t} p3rdQual={p3rdQual} rank={i} />
      ))}

      {/* 3rd-place row with zone header */}
      {group.teams.length > 2 && (
        <>
          <div style={{
            padding: '4px 16px 3px',
            display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 4,
            background: `${C.third}08`,
            borderLeft: `3px solid ${C.third}55`,
            borderBottom: '1px dashed var(--border)',
            borderTop: '1px dashed var(--border)',
          }}>
            <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', color: C.third, textTransform: 'uppercase' }}>
              Top-8 contention (3rd)
            </span>
          </div>
          <TeamRow key={group.teams[2].team} t={group.teams[2]} p3rdQual={p3rdQual} rank={2} />
        </>
      )}

      {/* 4th-place row with zone header */}
      {group.teams.length > 3 && (
        <>
          <div style={{
            padding: '4px 16px 3px',
            display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 4,
            background: `${C.fourth}06`,
            borderLeft: `3px solid ${C.fourth}55`,
            borderBottom: '1px dashed var(--border)',
            borderTop: '1px dashed var(--border)',
          }}>
            <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.07em', color: C.fourth, textTransform: 'uppercase' }}>
              Eliminated (4th)
            </span>
          </div>
          <TeamRow key={group.teams[3].team} t={group.teams[3]} p3rdQual={p3rdQual} rank={3} />
        </>
      )}

      {/* Legend */}
      <div style={{
        padding: '8px 16px',
        display: 'flex', gap: 14, flexWrap: 'wrap',
        background: 'var(--surface-hi)',
        borderTop: '1px solid var(--border)',
      }}>
        {[
          { color: C.first,  label: '1st · auto' },
          { color: C.second, label: '2nd · auto' },
          { color: C.third,  label: '3rd · top-8' },
          { color: C.fourth, label: '4th · out' },
        ].map(({ color, label }) => (
          <span key={label} style={{
            display: 'flex', alignItems: 'center', gap: 4,
            fontSize: 10, color: 'var(--text-3)',
          }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: color, display: 'inline-block', flexShrink: 0 }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
