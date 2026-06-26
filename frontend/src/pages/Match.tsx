import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import ScorelineHeatmap from '../components/ScorelineHeatmap'

function StatItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '14px 0', borderBottom: '1px solid var(--border)' }}>
      <div className="label" style={{ marginBottom: 6 }}>{label}</div>
      <div style={{
        fontWeight: 700,
        fontSize: 20,
        fontFamily: "'Space Grotesk', sans-serif",
        color: color ?? 'var(--text-1)',
        fontVariantNumeric: 'tabular-nums',
      }}>
        {value}
      </div>
    </div>
  )
}

function WinBar({ p1, pD, p2, t1, t2 }: { p1: number; pD: number; p2: number; t1: string; t2: string }) {
  return (
    <div>
      <div style={{ display: 'flex', borderRadius: 8, overflow: 'hidden', height: 32 }}>
        <div style={{
          width: `${p1 * 100}%`,
          background: 'var(--accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 48,
        }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>{(p1 * 100).toFixed(0)}%</span>
        </div>
        <div style={{
          width: `${pD * 100}%`,
          background: 'var(--surface-hi)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 40,
        }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-2)' }}>{(pD * 100).toFixed(0)}%</span>
        </div>
        <div style={{
          width: `${p2 * 100}%`,
          background: 'var(--red)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 48,
        }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>{(p2 * 100).toFixed(0)}%</span>
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
        <span style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 500 }}>{t1}</span>
        <span style={{ fontSize: 11, color: 'var(--text-3)', fontWeight: 500 }}>Draw</span>
        <span style={{ fontSize: 12, color: 'var(--red)', fontWeight: 500 }}>{t2}</span>
      </div>
    </div>
  )
}

export default function Match() {
  const { id } = useParams<{ id: string }>()
  const matchId = parseInt(id ?? '0', 10)

  const { data: pred, isLoading } = useQuery({
    queryKey: ['prediction', matchId],
    queryFn: () => api.prediction(matchId),
    enabled: matchId > 0,
  })
  const { data: matches } = useQuery({ queryKey: ['matches'], queryFn: api.matches })

  const upcoming = matches?.matches
    .filter(m => m.status === 'upcoming' && m.id !== matchId)
    .slice(0, 8) ?? []

  if (isLoading) {
    return (
      <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {Array.from({length: 3}).map((_,i) => (
          <div key={i} className="shimmer" style={{ height: 100 }} />
        ))}
      </div>
    )
  }

  if (!pred) return <p style={{ color: 'var(--text-2)' }}>Match not found.</p>

  if (pred.status === 'played') {
    return (
      <div style={{ maxWidth: 560, margin: '0 auto', paddingTop: 32 }}>
        <Link to="/matches" style={{ fontSize: 13, color: 'var(--text-2)', textDecoration: 'none', display: 'block', marginBottom: 24 }}>
          ← Fixtures
        </Link>
        <div className="card" style={{ padding: 48, textAlign: 'center' }}>
          <div className="label" style={{ marginBottom: 20 }}>
            Final Result{pred.venue ? ` · 📍 ${pred.venue}` : ''}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 28 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ marginBottom: 8 }}><FlagImg team={pred.team1} size={44} /></div>
              <div style={{ fontSize: 13, fontWeight: 500, marginTop: 8, color: 'var(--text-1)' }}>{pred.team1}</div>
            </div>
            <div style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700, fontSize: 44,
              color: 'var(--text-1)',
              letterSpacing: '-0.02em',
            }}>
              {pred.result}
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ marginBottom: 8 }}><FlagImg team={pred.team2} size={44} /></div>
              <div style={{ fontSize: 13, fontWeight: 500, marginTop: 8, color: 'var(--text-1)' }}>{pred.team2}</div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Link to="/matches" style={{ fontSize: 13, color: 'var(--text-2)', textDecoration: 'none', fontWeight: 500 }}>
        ← Fixtures
      </Link>

      {/* Match header */}
      <div className="card" style={{ padding: 28 }}>
        <div className="label" style={{ marginBottom: 20 }}>
          {pred.date} · Pre-match Prediction{pred.venue ? ` · 📍 ${pred.venue}` : ''}
        </div>

        {/* Teams + xG */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
          <div style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ marginBottom: 10 }}><FlagImg team={pred.team1} size={52} /></div>
            <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-1)', marginBottom: 10 }}>{pred.team1}</div>
            <div style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700, fontSize: 36,
              color: 'var(--accent)',
              letterSpacing: '-0.02em',
              lineHeight: 1,
            }}>
              {pred.xg_home?.toFixed(2)}
            </div>
            <div className="label" style={{ marginTop: 4 }}>xG</div>
          </div>
          <div style={{ color: 'var(--text-3)', fontWeight: 600, fontSize: 16 }}>vs</div>
          <div style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ marginBottom: 10 }}><FlagImg team={pred.team2} size={52} /></div>
            <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-1)', marginBottom: 10 }}>{pred.team2}</div>
            <div style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700, fontSize: 36,
              color: 'var(--red)',
              letterSpacing: '-0.02em',
              lineHeight: 1,
            }}>
              {pred.xg_away?.toFixed(2)}
            </div>
            <div className="label" style={{ marginTop: 4 }}>xG</div>
          </div>
        </div>

        {pred.p_home_win != null && (
          <WinBar
            p1={pred.p_home_win}
            pD={pred.p_draw ?? 0}
            p2={pred.p_away_win ?? 0}
            t1={pred.team1}
            t2={pred.team2}
          />
        )}
      </div>

      {/* Key stats — flat row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 0 }} className="card">
        <StatItem label="Most Likely"  value={pred.most_likely_score ?? '—'} color="var(--accent)" />
        <StatItem label="Over 2.5"     value={pred.p_over_25 != null ? `${(pred.p_over_25 * 100).toFixed(1)}%` : '—'} />
        <StatItem label="BTTS"         value={pred.p_btts != null ? `${(pred.p_btts * 100).toFixed(1)}%` : '—'} />
        <StatItem label="CS (home)"    value={pred.p_clean_sheet_home != null ? `${(pred.p_clean_sheet_home * 100).toFixed(1)}%` : '—'} color="var(--green)" />
        <StatItem label="CS (away)"    value={pred.p_clean_sheet_away != null ? `${(pred.p_clean_sheet_away * 100).toFixed(1)}%` : '—'} color="var(--green)" />
      </div>

      {/* Heatmap */}
      {pred.top_scorelines && (
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <span className="label">Scoreline Heatmap</span>
            <span style={{ fontSize: 11, color: 'var(--text-3)' }}>Home (row) × Away (col)</span>
          </div>
          <ScorelineHeatmap scorelines={pred.top_scorelines} />
        </div>
      )}

      {/* Upcoming matches */}
      {upcoming.length > 0 && (
        <div>
          <p className="label" style={{ marginBottom: 10 }}>Other Upcoming Matches</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 8 }}>
            {upcoming.map(m => (
              <Link key={m.id} to={`/match/${m.id}`} style={{ textDecoration: 'none' }}>
                <div
                  className="card"
                  style={{ padding: '11px 14px', cursor: 'pointer', transition: 'border-color .15s, background .15s' }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-hi)'
                    ;(e.currentTarget as HTMLDivElement).style.background = 'var(--surface-hi)'
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)'
                    ;(e.currentTarget as HTMLDivElement).style.background = 'var(--surface)'
                  }}
                >
                  <div className="label" style={{ marginBottom: 6 }}>{m.date}</div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-1)', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                    <FlagImg team={m.team1} size={20} />
                    <span>{m.team1}</span>
                    <span style={{ color: 'var(--text-3)' }}>vs</span>
                    <span>{m.team2}</span>
                    <FlagImg team={m.team2} size={20} />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
