import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import GroupTable from '../components/GroupTable'
import { useLiveStream } from '../hooks/useLiveStream'

export default function Groups() {
  const qc = useQueryClient()
  const { data: groups, isLoading: g1 } = useQuery({ queryKey: ['groups'],     queryFn: api.groups })
  const { data: third,  isLoading: g2 } = useQuery({ queryKey: ['thirdPlace'], queryFn: api.thirdPlace })

  useLiveStream(() => {
    qc.invalidateQueries({ queryKey: ['groups'] })
    qc.invalidateQueries({ queryKey: ['thirdPlace'] })
  })

  const isLoading = g1 || g2

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div>
        <h1 style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700, fontSize: 24,
          letterSpacing: '-0.02em', marginBottom: 6,
        }}>
          <span className="gradient-text">Group Stage Odds</span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>
          {groups ? `${groups.n_simulations.toLocaleString()} simulations` : 'Loading…'} ·
          Top 2 advance automatically. Best 8 third-place teams also qualify.
        </p>
      </div>

      {/* 3rd-place note */}
      <div style={{
        padding: '12px 16px',
        borderRadius: 10,
        background: 'var(--gold-dim)',
        border: '1px solid rgba(245,158,11,0.15)',
        fontSize: 13,
        color: 'var(--text-2)',
        display: 'flex',
        gap: 10,
        alignItems: 'center',
      }}>
        <span style={{ fontSize: 16 }}>📋</span>
        <span>
          The <strong style={{ color: 'var(--gold)', fontWeight: 600 }}>8 best 3rd-place teams</strong> across
          all 12 groups also advance to the Round of 32. Qualification chance shown on each group card.
        </span>
      </div>

      {/* Group grid */}
      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(360px,1fr))', gap: 12 }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="shimmer" style={{ height: 220 }} />
          ))}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(360px,1fr))', gap: 12 }}>
          {(groups?.groups ?? []).map(g => (
            <GroupTable
              key={g.group}
              group={g}
              thirdPlace={third?.third_place.find(t => t.group === g.group)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
