import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useLiveStream } from '../hooks/useLiveStream'
import type { PlayerAwardEntry } from '../lib/types'
import { FlagImg } from '../lib/FlagImg'

function PodiumCard({ player, rank, stat }: { player: PlayerAwardEntry; rank: number; stat: string }) {
  const config = [
    { medal: '🥇', accent: 'var(--gold)',   dim: 'var(--gold-dim)' },
    { medal: '🥈', accent: '#94a3b8',        dim: 'rgba(148,163,184,.06)' },
    { medal: '🥉', accent: '#cd7c2f',        dim: 'rgba(205,124,47,.06)' },
  ][rank] ?? { medal: `${rank+1}`, accent: 'var(--text-2)', dim: 'transparent' }

  return (
    <div className="card" style={{
      padding: '20px 18px',
      background: config.dim,
      border: `1px solid ${config.accent}22`,
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 28, marginBottom: 8 }}>{config.medal}</div>
      <div style={{ marginBottom: 6 }}><FlagImg team={player.team} size={24} /></div>
      <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-1)', marginBottom: 4 }}>{player.player}</div>
      <div style={{
        fontFamily: "'Space Grotesk', sans-serif",
        fontWeight: 700, fontSize: 28,
        color: config.accent,
        lineHeight: 1,
        marginBottom: 2,
      }}>
        {player.current}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-2)', marginBottom: 16 }}>
        {stat} · {player.expected_total.toFixed(1)} projected
      </div>
      <div style={{
        fontSize: 18,
        fontWeight: 700,
        fontFamily: "'Space Grotesk', sans-serif",
      }} className="gold-text">
        {(player.p_win * 100).toFixed(1)}%
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 3 }}>chance to win</div>
    </div>
  )
}

function LeaderRow({ player, rank, stat, maxP }: { player: PlayerAwardEntry; rank: number; stat: string; maxP: number }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '32px 1fr 56px 1fr 64px',
      gap: 12, alignItems: 'center',
      padding: '11px 16px',
      borderBottom: '1px solid var(--border)',
    }}>
      <span style={{ fontSize: 12, color: 'var(--text-3)', fontWeight: 600, textAlign: 'center' }}>
        {rank + 1}
      </span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ flexShrink: 0 }}><FlagImg team={player.team} size={20} /></span>
        <div>
        <div style={{ fontWeight: 500, fontSize: 13, color: 'var(--text-1)' }}>{player.player}</div>
        <div style={{ fontSize: 11, color: 'var(--text-2)', marginTop: 2 }}>
          {player.current} {stat} · {player.expected_total.toFixed(1)} proj
        </div>
        </div>
      </div>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
        {player.current}
      </span>
      {/* Probability bar */}
      <div style={{ height: 4, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
        <div
          className="prob-bar-fill"
          style={{
            height: '100%',
            borderRadius: 2,
            width: `${Math.min(player.p_win / (maxP || 1), 1) * 100}%`,
            background: 'var(--gold)',
          }}
        />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--gold)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
        {(player.p_win * 100).toFixed(1)}%
      </span>
    </div>
  )
}

function AwardSection({ title, icon, players, stat }: {
  title: string; icon: string; players: PlayerAwardEntry[]; stat: string
}) {
  const top3 = players.slice(0, 3)
  const rest = players.slice(3, 20)
  const maxP = rest[0]?.p_win ?? 0.01

  return (
    <section>
      <h2 style={{
        fontFamily: "'Space Grotesk', sans-serif",
        fontWeight: 700, fontSize: 20,
        letterSpacing: '-0.01em', marginBottom: 18,
        color: 'var(--text-1)',
      }}>
        {icon} {title}
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 16 }}>
        {top3.length === 0
          ? Array.from({length:3}).map((_,i) => <div key={i} className="shimmer" style={{ height: 180 }} />)
          : top3.map((p, i) => <PodiumCard key={p.player} player={p} rank={i} stat={stat} />)
        }
      </div>

      {rest.length > 0 && (
        <div className="card">
          <div style={{
            display: 'grid',
            gridTemplateColumns: '32px 1fr 56px 1fr 64px',
            gap: 12,
            padding: '8px 16px',
            borderBottom: '1px solid var(--border-hi)',
          }}>
            <div /><span className="label">Player</span>
            <span className="label" style={{ textAlign: 'right' }}>Now</span>
            <div />
            <span className="label" style={{ textAlign: 'right' }}>Win %</span>
          </div>
          {rest.map((p, i) => (
            <LeaderRow key={p.player} player={p} rank={i + 3} stat={stat} maxP={maxP} />
          ))}
        </div>
      )}
    </section>
  )
}

export default function Awards() {
  const qc = useQueryClient()
  const { data: boot }    = useQuery({ queryKey: ['goldenBoot'], queryFn: api.goldenBoot })
  const { data: assists } = useQuery({ queryKey: ['topAssists'], queryFn: api.topAssists })
  useLiveStream(() => {
    qc.invalidateQueries({ queryKey: ['goldenBoot'] })
    qc.invalidateQueries({ queryKey: ['topAssists'] })
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 48 }}>
      <div>
        <h1 style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700, fontSize: 24,
          letterSpacing: '-0.02em', marginBottom: 6,
        }}>
          <span className="gradient-text">Individual Awards</span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>
          {boot?.n_simulations.toLocaleString() ?? '…'} simulations
        </p>
      </div>
      <AwardSection title="Golden Boot" icon="🏆" players={boot?.players ?? []} stat="goals" />
      <AwardSection title="Most Assists" icon="🎯" players={assists?.players ?? []} stat="assists" />
    </div>
  )
}
