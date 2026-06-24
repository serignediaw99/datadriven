import type { GroupOdds, ThirdPlaceOdds, TeamGroupOdds } from '../lib/types'
import { FlagImg } from '../lib/FlagImg'

function R32Bar({ value }: { value: number }) {
  return (
    <div style={{
      height: 4, borderRadius: 2, overflow: 'hidden',
      background: 'var(--border)', width: '100%',
    }}>
      <div style={{
        height: '100%', borderRadius: 2,
        width: `${Math.round(value * 100)}%`,
        background: 'var(--accent)',
        transition: 'width .3s ease',
      }} />
    </div>
  )
}

function TeamRow({ t, p3rdQual, rank }: { t: TeamGroupOdds; p3rdQual: number; rank: number }) {
  const r32 = t.p_1st + t.p_2nd + t.p_3rd * p3rdQual

  return (
    <div style={{
      padding: '13px 16px',
      borderBottom: '1px solid var(--border)',
    }}>
      {/* Name row + R32 % */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 9 }}>
        <FlagImg team={t.team} size={20} />
        <span style={{
          flex: 1, fontWeight: rank < 2 ? 600 : 400,
          fontSize: 13, color: 'var(--text-1)', minWidth: 0,
        }}>
          {t.team}
        </span>
        <span style={{
          fontSize: 14, fontWeight: 700,
          color: 'var(--accent)', fontVariantNumeric: 'tabular-nums',
          flexShrink: 0,
        }}>
          {Math.round(r32 * 100)}%
        </span>
      </div>

      {/* R32 qualification bar */}
      <R32Bar value={r32} />

      {/* Position stats */}
      <div style={{ display: 'flex', alignItems: 'center', marginTop: 8, gap: 12 }}>
        {[
          { label: '1st', val: t.p_1st },
          { label: '2nd', val: t.p_2nd },
          { label: '3rd', val: t.p_3rd },
          { label: '4th', val: t.p_4th },
        ].map(({ label, val }) => (
          <span key={label} style={{ fontSize: 11, color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
            {label} <span style={{ color: 'var(--text-2)', fontWeight: 600 }}>{(val * 100).toFixed(0)}%</span>
          </span>
        ))}
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-3)', whiteSpace: 'nowrap' }}>
          {t.avg_pts.toFixed(1)} pts · {t.avg_gd >= 0 ? '+' : ''}{t.avg_gd.toFixed(1)} GD
        </span>
      </div>
    </div>
  )
}

function ZoneDivider({ label }: { label: string }) {
  return (
    <div style={{
      padding: '4px 16px',
      display: 'flex', alignItems: 'center', gap: 8,
      borderTop: '1px dashed var(--border)',
      borderBottom: '1px dashed var(--border)',
    }}>
      <div style={{ flex: 1, height: 1 }} />
      <span style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.08em', color: 'var(--text-3)', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 1 }} />
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
        borderBottom: '1px solid var(--border-hi)',
      }}>
        <span style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 800, fontSize: 15, letterSpacing: '-0.02em',
          color: 'var(--text-1)',
        }}>
          {group.group}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>R32 = chance to qualify</span>
        </div>
      </div>

      {/* Auto-qualify zone (1st + 2nd) */}
      {group.teams.slice(0, 2).map((t, i) => (
        <TeamRow key={t.team} t={t} p3rdQual={p3rdQual} rank={i} />
      ))}

      {/* 3rd-place team */}
      {group.teams.length > 2 && (
        <>
          <ZoneDivider label={
            thirdPlace
              ? `3rd place · top-8 qual ${(p3rdQual * 100).toFixed(0)}%${thirdPlace.pts_needed_p50 != null ? ` · ~${thirdPlace.pts_needed_p50} pts needed` : ''}`
              : '3rd place · top-8 contention'
          } />
          <TeamRow t={group.teams[2]} p3rdQual={p3rdQual} rank={2} />
        </>
      )}

      {/* 4th-place team */}
      {group.teams.length > 3 && (
        <>
          <ZoneDivider label="4th place · eliminated" />
          <TeamRow t={group.teams[3]} p3rdQual={p3rdQual} rank={3} />
        </>
      )}
    </div>
  )
}
