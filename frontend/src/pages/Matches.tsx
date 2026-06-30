import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import { useLiveStream } from '../hooks/useLiveStream'
import type { MatchEntry } from '../lib/types'

function groupByDate(matches: MatchEntry[]) {
  const map = new Map<string, MatchEntry[]>()
  for (const m of matches) {
    if (!map.has(m.date)) map.set(m.date, [])
    map.get(m.date)!.push(m)
  }
  return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b))
}

function MatchCard({ m }: { m: MatchEntry }) {
  const isLive = m.status === 'live'
  const isPlayed = m.status === 'played'
  const showScore = isPlayed || isLive
  const win1 = isPlayed && m.winner === m.team1
  const win2 = isPlayed && m.winner === m.team2
  // Shootout score oriented to the winner ("4–3 on penalties").
  const winPens = m.winner === m.team1 ? m.pens1 : m.pens2
  const losePens = m.winner === m.team1 ? m.pens2 : m.pens1
  const resultNote = !m.winner ? null
    : m.decided_by === 'pens' && winPens != null && losePens != null
      ? `${m.winner} win ${winPens}–${losePens} on penalties`
      : m.decided_by === 'aet'
        ? `${m.winner} win after extra time`
        : null
  return (
    <Link to={`/match/${m.id}`} style={{ textDecoration: 'none' }}>
      <div
        className="card"
        style={{ padding: '12px 16px', cursor: 'pointer', transition: 'border-color .15s, background .15s' }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-hi)'
          ;(e.currentTarget as HTMLDivElement).style.background = 'var(--surface-hi)'
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)'
          ;(e.currentTarget as HTMLDivElement).style.background = 'var(--surface)'
        }}
      >
        {/* Metadata row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          {isLive ? (
            <span className="label" style={{ color: 'var(--green)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span className="live-dot" style={{
                width: 7, height: 7, borderRadius: '50%',
                background: 'var(--green)', position: 'relative', display: 'inline-block',
              }} /> LIVE{m.live_minute ? ` ${m.live_minute}'` : ''}
            </span>
          ) : (
            <span className="label">{m.round}</span>
          )}
          {m.group && <span className="label" style={{ color: 'var(--accent)' }}>{m.group}</span>}
        </div>

        {/* Teams row */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 7 }}>
            <FlagImg team={m.team1} size={24} />
            <span style={{
              fontSize: 13,
              fontWeight: win1 ? 700 : isPlayed ? 600 : 500,
              color: win2 ? 'var(--text-3)' : 'var(--text-1)',
            }}>
              {m.team1}
            </span>
          </div>

          <div style={{ padding: '0 10px', textAlign: 'center', minWidth: 60 }}>
            {showScore ? (
              <span style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 700, fontSize: 17,
                color: isLive ? 'var(--green)' : 'var(--text-1)',
                letterSpacing: '.03em',
                fontVariantNumeric: 'tabular-nums',
              }}>
                {m.score1} – {m.score2}
              </span>
            ) : (
              <span style={{ fontSize: 11, color: 'var(--text-3)', fontWeight: 600 }}>vs</span>
            )}
          </div>

          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 7 }}>
            <span style={{
              fontSize: 13,
              fontWeight: win2 ? 700 : isPlayed ? 600 : 500,
              color: win1 ? 'var(--text-3)' : 'var(--text-1)',
              textAlign: 'right',
            }}>
              {m.team2}
            </span>
            <FlagImg team={m.team2} size={24} />
          </div>
        </div>

        {resultNote && (
          <div style={{ marginTop: 6, fontSize: 11, color: 'var(--accent)', textAlign: 'center', fontWeight: 600 }}>
            {resultNote}
          </div>
        )}
        {m.venue && (
          <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-3)', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
            <span aria-hidden style={{ opacity: 0.7 }}>📍</span>{m.venue}
          </div>
        )}
        {m.status === 'upcoming' && (
          <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-3)', textAlign: 'center', fontWeight: 500 }}>
            Prediction available →
          </div>
        )}
        {isLive && m.live_status && (
          <div style={{ marginTop: 8, fontSize: 11, color: 'var(--green)', textAlign: 'center', fontWeight: 600 }}>
            {m.live_status}
          </div>
        )}
      </div>
    </Link>
  )
}

type Filter = 'all' | 'upcoming' | 'played'
const TABS: { key: Filter; label: string }[] = [
  { key: 'upcoming', label: 'Upcoming' },
  { key: 'played',   label: 'Results'  },
  { key: 'all',      label: 'All'      },
]

export default function Matches() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<Filter>('upcoming')
  const { data, isLoading } = useQuery({ queryKey: ['matches'], queryFn: api.matches })
  useLiveStream(() => qc.invalidateQueries({ queryKey: ['matches'] }))

  const total  = data?.matches.length ?? 0
  const played = data?.matches.filter(m => m.status === 'played').length ?? 0

  // Live matches are "in progress" — surface them under the Upcoming tab.
  const filtered = (data?.matches ?? []).filter(m =>
    filter === 'all' || m.status === filter || (filter === 'upcoming' && m.status === 'live')
  )
  const byDate = groupByDate(filtered)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      {/* Header */}
      <div>
        <h1 style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700, fontSize: 24,
          letterSpacing: '-0.02em', marginBottom: 6,
        }}>
          <span className="gradient-text">Fixtures &amp; Results</span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>
          {played} of {total} matches played
        </p>
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 6 }}>
        {TABS.map(({ key, label }) => {
          const active = filter === key
          return (
            <button
              key={key}
              onClick={() => setFilter(key)}
              style={{
                padding: '6px 16px',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: active ? 600 : 400,
                border: `1px solid ${active ? 'var(--border-hi)' : 'var(--border)'}`,
                background: active ? 'var(--surface-hi)' : 'transparent',
                color: active ? 'var(--text-1)' : 'var(--text-2)',
                cursor: 'pointer',
                transition: 'all .15s',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Match list */}
      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="shimmer" style={{ height: 76 }} />
          ))}
        </div>
      ) : byDate.length === 0 ? (
        <p style={{ color: 'var(--text-2)', fontSize: 14 }}>No matches found.</p>
      ) : (
        byDate.map(([date, matches]) => (
          <div key={date}>
            <div style={{ marginBottom: 10 }}>
              <span className="label">
                {new Date(date + 'T12:00:00Z').toLocaleDateString('en-US', {
                  weekday: 'long', month: 'long', day: 'numeric',
                })}
              </span>
              <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--text-3)' }}>
                {matches.length} match{matches.length > 1 ? 'es' : ''}
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(290px,1fr))', gap: 8 }}>
              {matches.map(m => <MatchCard key={m.id} m={m} />)}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
