import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import { useLiveStream } from '../hooks/useLiveStream'
import type { BracketMatch, BracketResponse } from '../lib/types'

// ─── Display order: R32 indices ordered so adjacent pairs feed the same R16 match ─────
// Each quarter: 4 R32 matches → 2 R16 → 1 QF
// Quarter 0 → QF[0] → SF[0]
// Quarter 1 → QF[1] → SF[0]
// Quarter 2 → QF[2] → SF[1]
// Quarter 3 → QF[3] → SF[1]
const R32_ORDER = [1, 4, 0, 2,   10, 11, 8, 9,   3, 5, 6, 7,   13, 15, 12, 14]
const R16_ORDER = [0, 1, 4, 5,   2,  3,  6, 7]
// QF and SF are already in the right order (0,1,2,3 and 0,1)

const CELL_H = 60  // px per R32 slot
const CONN = 18    // px connector width
const LINE = 'rgba(101,62,18,0.14)'
const CARD_W = 186



// ─── Team row ────────────────────────────────────────────────────────────────
function TeamRow({ team, isWinner }: { team: string; isWinner: boolean }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 7,
      padding: '5px 9px',
      background: isWinner ? 'rgba(181,109,60,0.10)' : 'transparent',
      borderLeft: isWinner ? '2px solid var(--accent)' : '2px solid transparent',
      minWidth: 0,
    }}>
      <FlagImg team={team} size={18} />
      <span style={{
        fontSize: 11, fontWeight: isWinner ? 700 : 400,
        color: isWinner ? 'var(--text-1)' : 'var(--text-2)',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>{team}</span>
    </div>
  )
}

// ─── Match card ──────────────────────────────────────────────────────────────
function MatchCard({ m }: { m: BracketMatch }) {
  return (
    <div style={{
      width: CARD_W,
      background: 'var(--surface)',
      border: '1px solid var(--border-hi)',
      borderRadius: 7,
      overflow: 'hidden',
      flexShrink: 0,
    }}>
      <TeamRow team={m.team_a} isWinner={m.winner === m.team_a} />
      <div style={{ height: 1, background: 'var(--border)' }} />
      <TeamRow team={m.team_b} isWinner={m.winner === m.team_b} />
    </div>
  )
}

// ─── Single cell in a column: centers content, adds connector stub ─────────────
function Cell({ h, match, isTopOfPair, isBottomOfPair, lastColumn }: {
  h: number; match: BracketMatch; isTopOfPair: boolean; isBottomOfPair: boolean;
  lastColumn?: boolean;
}) {
  return (
    <div style={{
      height: h,
      display: 'flex', alignItems: 'center',
      position: 'relative',
      flexShrink: 0,
    }}>
      {/* Entry stub: horizontal line from left */}
      <div style={{ width: CONN, height: 1, background: LINE, flexShrink: 0 }} />
      <MatchCard m={match} />
      {/* Exit connector */}
      {!lastColumn && (
        <div style={{ width: CONN, height: h, flexShrink: 0, position: 'relative' }}>
          {isTopOfPair && (
            <div style={{
              position: 'absolute', top: '50%', left: 0,
              width: '100%', height: '50%',
              borderRight: `1px solid ${LINE}`,
              borderBottom: `1px solid ${LINE}`,
              borderBottomRightRadius: 3,
            }} />
          )}
          {isBottomOfPair && (
            <div style={{
              position: 'absolute', bottom: '50%', left: 0,
              width: '100%', height: '50%',
              borderRight: `1px solid ${LINE}`,
              borderTop: `1px solid ${LINE}`,
              borderTopRightRadius: 3,
            }} />
          )}
        </div>
      )}
    </div>
  )
}

// ─── A column of matches for one round ───────────────────────────────────────
function RoundColumn({ label, matches, cellH, lastColumn, halfBreak }: {
  label: string; matches: BracketMatch[];
  cellH: number;
  lastColumn?: boolean; halfBreak?: number;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{
        fontSize: 10, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase',
        color: 'var(--text-3)', textAlign: 'center', paddingBottom: 10,
        width: CARD_W + CONN * 2,
      }}>
        {label}
      </div>
      <div style={{ position: 'relative' }}>
        {matches.map((m, i) => {
          const posInPair = i % 2  // 0 = top, 1 = bottom
          return (
            <div key={m.id + '-' + i}>
              {halfBreak !== undefined && i === halfBreak && (
                <div style={{ height: 2, background: 'rgba(181,109,60,0.18)', margin: '6px 0', borderRadius: 1 }} />
              )}
              <Cell
                h={cellH}
                match={m}
                isTopOfPair={posInPair === 0}
                isBottomOfPair={posInPair === 1}
                lastColumn={lastColumn}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Final match (centered vertically) ────────────────────────────────────────
function FinalColumn({ data, totalH }: { data: BracketResponse['final']; totalH: number }) {
  const m: BracketMatch = {
    id: 99, team_a: data.team_a, team_b: data.team_b,
    winner: data.winner, p_win: data.p_win, p_a_wins: data.p_a_wins,
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{
        fontSize: 10, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase',
        color: 'var(--text-3)', textAlign: 'center', paddingBottom: 10,
        width: CARD_W + CONN,
      }}>
        Final
      </div>
      <div style={{
        height: totalH,
        display: 'flex', flexDirection: 'column',
        alignItems: 'flex-start',
        justifyContent: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ width: CONN, height: 1, background: LINE }} />
          <div style={{ position: 'relative' }}>
            <MatchCard m={m} />
            {/* Winner badge */}
            <div style={{
              position: 'absolute', top: -22, left: 0, right: 0,
              textAlign: 'center', fontSize: 10, fontWeight: 700,
              color: '#f59e0b', letterSpacing: '.05em',
            }}>
              🏆 {data.winner}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Main Bracket page ────────────────────────────────────────────────────────
export default function Bracket() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['bracket'], queryFn: api.bracket })
  useLiveStream(() => qc.invalidateQueries({ queryKey: ['bracket'] }))

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ height: 28, width: 240, borderRadius: 6 }} className="shimmer" />
        <div style={{ height: 600, borderRadius: 12 }} className="shimmer" />
      </div>
    )
  }
  if (!data) return <p style={{ color: 'var(--text-3)' }}>Bracket not available.</p>

  const r32 = R32_ORDER.map(i => data.r32[i])
  const r16 = R16_ORDER.map(i => data.r16[i])
  const qf  = data.qf   // [0,1,2,3]
  const sf  = data.sf   // [0,1]

  const totalH = CELL_H * 16  // total bracket height

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Header */}
      <div>
        <h1 style={{
          fontFamily: "'Space Grotesk',sans-serif", fontWeight: 800,
          fontSize: 26, letterSpacing: '-0.03em', marginBottom: 4,
        }}>
          <span className="gradient-text">Projected Bracket</span>
        </h1>
        <p style={{ fontSize: 12, color: 'var(--text-3)' }}>
          Most-likely team per slot from {data && (50000).toLocaleString()} simulations. Projected winners highlighted.
        </p>
      </div>

      {/* Bracket scroll container */}
      <div style={{ overflowX: 'auto', overflowY: 'visible', paddingBottom: 16 }}>
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          paddingTop: 24,
          paddingLeft: 8,
          gap: 0,
          minWidth: 'max-content',
        }}>
          {/* R32 column */}
          <RoundColumn
            label="Round of 32"
            matches={r32}
            cellH={CELL_H}
            halfBreak={8}
          />

          {/* R16 column */}
          <RoundColumn
            label="Round of 16"
            matches={r16}
            cellH={CELL_H * 2}
            halfBreak={4}
          />

          {/* QF column */}
          <RoundColumn
            label="Quarter-finals"
            matches={qf}
            cellH={CELL_H * 4}
            halfBreak={2}
          />

          {/* SF column */}
          <RoundColumn
            label="Semi-finals"
            matches={sf}
            cellH={CELL_H * 8}
          />

          {/* Final */}
          <FinalColumn data={data.final} totalH={totalH} />
        </div>
      </div>

      {/* Legend */}
      <div className="card" style={{ padding: '12px 16px', display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(181,109,60,0.25)', borderLeft: '2px solid var(--accent)' }} />
          <span style={{ fontSize: 12, color: 'var(--text-2)' }}>Projected winner advances</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
          Win probabilities computed from Elo ratings. Bracket seeding based on FIFA 2026 schedule.
        </div>
      </div>
    </div>
  )
}
