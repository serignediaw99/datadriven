import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import { useLiveStream } from '../hooks/useLiveStream'

const ROUNDS = ['Winner','Final','SF','QF'] as const

function WinnerCard({ team, pct, rank }: { team: string; pct: number; rank: number }) {
  const isFirst = rank === 0
  return (
    <div className={isFirst ? 'card-hi' : 'card'} style={{
      padding: '20px 16px',
      textAlign: 'center',
      background: isFirst ? 'linear-gradient(160deg, rgba(181,109,60,0.08), var(--surface-hi))' : undefined,
      border: isFirst ? '1px solid rgba(181,109,60,0.20)' : undefined,
      transition: 'border-color .15s',
    }}>
      <div style={{ marginBottom: 10 }}><FlagImg team={team} size={32} /></div>
      <div style={{ fontSize: 12, color: 'var(--text-2)', fontWeight: 500, marginBottom: 8 }}>{team}</div>
      <div style={{
        fontSize: 30,
        fontWeight: 700,
        fontFamily: "'Space Grotesk', sans-serif",
        color: isFirst ? 'var(--gold)' : 'var(--text-1)',
        letterSpacing: '-0.02em',
        lineHeight: 1,
      }}>
        {(pct * 100).toFixed(1)}%
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 6, fontWeight: 500 }}>to win</div>
    </div>
  )
}

function RoundRow({ team, probs }: { team: string; probs: Record<string,number> }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '26px 1fr repeat(4,72px)',
      gap: 8,
      alignItems: 'center',
      padding: '9px 16px',
      borderBottom: '1px solid var(--border)',
    }}>
      <FlagImg team={team} size={20} />
      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-1)' }}>{team}</span>
      {ROUNDS.map(r => {
        const v = probs[r] ?? 0
        return (
          <span key={r} style={{
            fontSize: 12,
            textAlign: 'right',
            fontWeight: 600,
            fontVariantNumeric: 'tabular-nums',
            color: v > 0.15 ? 'var(--text-1)' : v > 0.05 ? 'var(--text-2)' : 'var(--text-3)',
          }}>
            {(v * 100).toFixed(1)}%
          </span>
        )
      })}
    </div>
  )
}

function BootLeader({ player, goals, pWin, rank }: { player: string; goals: number; pWin: number; rank: number }) {
  const medals = ['🥇','🥈','🥉']
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      padding: '12px 0',
      borderBottom: rank < 2 ? '1px solid var(--border)' : 'none',
    }}>
      <span style={{ fontSize: 18, width: 24, textAlign: 'center' }}>{medals[rank]}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-1)' }}>{player}</div>
        <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 2 }}>{goals} goal{goals !== 1 ? 's' : ''}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div className="gold-text" style={{ fontWeight: 700, fontSize: 18, fontFamily: "'Space Grotesk', sans-serif" }}>
          {(pWin * 100).toFixed(1)}%
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const qc = useQueryClient()
  const { data: ko }     = useQuery({ queryKey: ['knockout'],   queryFn: api.knockout })
  const { data: boot }   = useQuery({ queryKey: ['goldenBoot'], queryFn: api.goldenBoot })
  const { data: groups } = useQuery({ queryKey: ['groups'],     queryFn: api.groups })

  useLiveStream(() => qc.invalidateQueries())

  const top5   = ko?.teams.slice(0, 5)  ?? []
  const next7  = ko?.teams.slice(5, 12) ?? []
  const topBoot = boot?.players.slice(0, 3) ?? []
  const nSims  = ko?.n_simulations ?? 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 48 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 13, color: 'var(--text-2)' }}>
              {nSims > 0 ? `${nSims.toLocaleString()} simulations` : 'Loading…'}
            </span>
            {nSims > 0 && (
              <span style={{
                display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 11, color: 'var(--green)', fontWeight: 600, letterSpacing: '.04em',
              }}>
                <span style={{
                  width: 7, height: 7, borderRadius: '50%',
                  background: 'var(--green)', position: 'relative', display: 'inline-block',
                }} className="live-dot" />
                LIVE
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Win odds */}
      <section>
        <p className="label" style={{ marginBottom: 16 }}>To Win the World Cup</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))', gap: 10 }}>
          {top5.length === 0
            ? Array.from({length:5}).map((_,i) => <div key={i} className="shimmer" style={{ height: 140 }} />)
            : top5.map((t, i) => <WinnerCard key={t.team} team={t.team} pct={t.probs.Winner} rank={i} />)
          }
        </div>
      </section>

      {/* Other contenders */}
      {next7.length > 0 && (
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <p className="label">Other Contenders</p>
            <div style={{ display: 'grid', gridTemplateColumns: '26px 1fr repeat(4,72px)', gap: 8, width: '100%', marginLeft: 16 }}>
              <div /><div />
              {ROUNDS.map(r => (
                <div key={r} className="label" style={{ textAlign: 'right' }}>{r}</div>
              ))}
            </div>
          </div>
          <div className="card">
            {next7.map(t => (
              <RoundRow key={t.team} team={t.team} probs={t.probs as unknown as Record<string,number>} />
            ))}
            <div style={{ padding: '10px 16px' }}>
              <Link to="/knockout" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none', fontWeight: 500 }}>
                View all 48 teams →
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* Two-column: golden boot + group grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,2fr)', gap: 24 }}>

        {/* Golden boot */}
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <p className="label">Golden Boot</p>
            <Link to="/awards" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none', fontWeight: 500 }}>
              Full race →
            </Link>
          </div>
          <div className="card" style={{ padding: '4px 16px 8px' }}>
            {topBoot.length === 0
              ? Array.from({length:3}).map((_,i) => <div key={i} className="shimmer" style={{ height: 56, marginBottom: 8 }} />)
              : topBoot.map((p, i) => <BootLeader key={p.player} player={p.player} goals={p.current} pWin={p.p_win} rank={i} />)
            }
          </div>
        </section>

        {/* Group snapshot */}
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <p className="label">Group Stage</p>
            <Link to="/groups" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none', fontWeight: 500 }}>
              Detailed view →
            </Link>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(180px,1fr))', gap: 8 }}>
            {(groups?.groups ?? []).map(g => (
              <div key={g.group} className="card" style={{ padding: '12px 14px' }}>
                <div className="label" style={{ marginBottom: 10 }}>{g.group}</div>
                {g.teams.map((t, i) => (
                  <div key={t.team} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '4px 0',
                    borderBottom: i < 3 ? '1px solid var(--border)' : 'none',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                      <FlagImg team={t.team} size={16} />
                      <span style={{
                        fontSize: 12,
                        color: i < 2 ? 'var(--text-1)' : 'var(--text-2)',
                        fontWeight: i < 2 ? 500 : 400,
                      }}>
                        {t.team.length > 12 ? t.team.slice(0, 11) + '…' : t.team}
                      </span>
                    </div>
                    <span style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: i === 0 ? 'var(--green)' : i === 1 ? 'var(--accent)' : 'var(--text-3)',
                      fontVariantNumeric: 'tabular-nums',
                    }}>
                      {((i === 0 ? t.p_1st : i === 1 ? t.p_2nd : t.p_3rd) * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
