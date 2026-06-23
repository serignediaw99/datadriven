import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { flag } from '../lib/flags'
import type { PathOpponent, PathResponse, ScenarioMatchOverride, MatchEntry } from '../lib/types'

const ROUND_LABELS = ['R32', 'R16', 'QF', 'SF', 'Final'] as const
type Round = typeof ROUND_LABELS[number]

const ROUND_COLORS: Record<Round, string> = {
  R32:   '#a8896a',
  R16:   '#c49a6c',
  QF:    '#b56d3c',
  SF:    '#8b4513',
  Final: '#b57e10',
}

const ROUND_NAMES: Record<Round, string> = {
  R32:   'Round of 32',
  R16:   'Round of 16',
  QF:    'Quarter-final',
  SF:    'Semi-final',
  Final: 'Final',
}

function OpponentBar({ opp, color }: { opp: PathOpponent; color: string }) {
  const pct = Math.round(opp.p * 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
      <span style={{ width: 22, fontSize: 15, flexShrink: 0 }}>{flag(opp.opponent)}</span>
      <span style={{ flex: 1, fontSize: 13, color: 'var(--text-1)', fontWeight: 500, minWidth: 0 }}>
        {opp.opponent}
      </span>
      <div style={{
        position: 'relative', width: 80, height: 6, flexShrink: 0,
        background: 'var(--surface-hi)', borderRadius: 3,
      }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: `${pct}%`, background: color, borderRadius: 3,
        }} />
      </div>
      <span style={{
        width: 34, textAlign: 'right', fontSize: 12, fontWeight: 700, flexShrink: 0,
        color, fontVariantNumeric: 'tabular-nums',
      }}>
        {pct}%
      </span>
    </div>
  )
}

function OpponentDeltaRow({ opponent, baseline, scenario, color }: {
  opponent: string; baseline: number; scenario: number; color: string
}) {
  const delta = scenario - baseline
  const deltaColor = delta > 0.01 ? '#2e7d52' : delta < -0.01 ? '#dc2626' : 'var(--text-3)'
  const sign = delta >= 0 ? '+' : ''
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
      <span style={{ width: 22, fontSize: 15, flexShrink: 0 }}>{flag(opponent)}</span>
      <span style={{ flex: 1, fontSize: 13, color: 'var(--text-1)', fontWeight: 500, minWidth: 0 }}>{opponent}</span>
      <span style={{ width: 32, fontSize: 12, color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums', textAlign: 'right', flexShrink: 0 }}>
        {Math.round(baseline * 100)}%
      </span>
      <span style={{ width: 12, fontSize: 12, color: 'var(--text-3)', textAlign: 'center', flexShrink: 0 }}>→</span>
      <span style={{ width: 32, fontSize: 12, fontWeight: 700, color, fontVariantNumeric: 'tabular-nums', textAlign: 'right', flexShrink: 0 }}>
        {Math.round(scenario * 100)}%
      </span>
      <span style={{ width: 36, fontSize: 11, color: deltaColor, fontVariantNumeric: 'tabular-nums', textAlign: 'right', flexShrink: 0 }}>
        {Math.abs(delta) >= 0.01 ? `(${sign}${Math.round(delta * 100)})` : ''}
      </span>
    </div>
  )
}

function RoundCard({ label, opponents, p_reach, scenarioOpponents, scenarioReach }: {
  label: Round
  opponents: PathOpponent[]
  p_reach: number
  scenarioOpponents?: PathOpponent[]
  scenarioReach?: number
}) {
  const color = ROUND_COLORS[label]
  const reached = p_reach > 0.001
  const hasScenario = scenarioOpponents !== undefined

  // Merge baseline + scenario opponent lists for delta view
  const mergedOpponents = (() => {
    if (!hasScenario) return []
    const baseMap = new Map(opponents.map(o => [o.opponent, o.p]))
    const scenMap = new Map((scenarioOpponents ?? []).map(o => [o.opponent, o.p]))
    const allNames = new Set([...baseMap.keys(), ...scenMap.keys()])
    return [...allNames]
      .map(name => ({ name, base: baseMap.get(name) ?? 0, scen: scenMap.get(name) ?? 0 }))
      .sort((a, b) => b.scen - a.scen)
      .slice(0, 6)
  })()

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      borderTop: `3px solid ${color}`,
      padding: 20,
      opacity: reached || (scenarioReach !== undefined && scenarioReach > 0.001) ? 1 : 0.45,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 18 }}>
        <div>
          <span className="label" style={{ color, fontSize: 11 }}>{label}</span>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-1)', marginTop: 2 }}>
            {ROUND_NAMES[label]}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          {hasScenario ? (
            <>
              <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 2 }}>reach probability</div>
              <div style={{ fontSize: 14, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
                <span style={{ color: 'var(--text-3)' }}>{(p_reach * 100).toFixed(1)}%</span>
                <span style={{ color: 'var(--text-3)', margin: '0 4px' }}>→</span>
                <span style={{ color }}>{((scenarioReach ?? 0) * 100).toFixed(1)}%</span>
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 2 }}>reach probability</div>
              <div style={{ fontSize: 20, fontWeight: 700, color, fontVariantNumeric: 'tabular-nums' }}>
                {(p_reach * 100).toFixed(1)}%
              </div>
            </>
          )}
        </div>
      </div>

      {hasScenario ? (
        mergedOpponents.length > 0 ? (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ width: 22, flexShrink: 0 }} />
              <span style={{ flex: 1, fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Likely opponents</span>
              <span style={{ width: 32, fontSize: 10, color: 'var(--text-3)', textAlign: 'right', flexShrink: 0 }}>now</span>
              <span style={{ width: 12, flexShrink: 0 }} />
              <span style={{ width: 32, fontSize: 10, color, textAlign: 'right', flexShrink: 0 }}>if</span>
              <span style={{ width: 36, fontSize: 10, color: 'var(--text-3)', textAlign: 'right', flexShrink: 0 }}>Δ</span>
            </div>
            {mergedOpponents.map(o => (
              <OpponentDeltaRow
                key={o.name}
                opponent={o.name}
                baseline={o.base}
                scenario={o.scen}
                color={color}
              />
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: 'var(--text-3)', margin: 0 }}>Team unlikely to reach this round.</p>
        )
      ) : (
        opponents.length > 0 ? (
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Most likely opponents
            </div>
            {opponents.map(o => <OpponentBar key={o.opponent} opp={o} color={color} />)}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: 'var(--text-3)', margin: 0 }}>
            {reached ? 'No opponent data.' : 'Team unlikely to reach this round.'}
          </p>
        )
      )}
    </div>
  )
}

type OverrideMap = Record<number, { score1: string; score2: string }>

function MatchScoreRow({ match, override, onChange }: {
  match: MatchEntry
  override: { score1: string; score2: string } | undefined
  onChange: (id: number, s1: string, s2: string) => void
}) {
  const s1 = override?.score1 ?? ''
  const s2 = override?.score2 ?? ''
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 0', borderBottom: '1px solid var(--border)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, justifyContent: 'flex-end' }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-1)' }}>{match.team1}</span>
        <span style={{ fontSize: 16, lineHeight: 1 }}>{flag(match.team1)}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        <input
          type="number" min={0} max={20} value={s1} placeholder="–"
          onChange={e => onChange(match.id, e.target.value, s2)}
          style={{
            width: 44, padding: '5px 6px', textAlign: 'center',
            background: 'var(--surface-hi)', border: `1px solid ${s1 !== '' ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: 5, fontSize: 15, fontWeight: 700, color: 'var(--text-1)', fontFamily: 'inherit',
          }}
        />
        <span style={{ color: 'var(--text-3)', fontWeight: 700, fontSize: 13 }}>–</span>
        <input
          type="number" min={0} max={20} value={s2} placeholder="–"
          onChange={e => onChange(match.id, s1, e.target.value)}
          style={{
            width: 44, padding: '5px 6px', textAlign: 'center',
            background: 'var(--surface-hi)', border: `1px solid ${s2 !== '' ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: 5, fontSize: 15, fontWeight: 700, color: 'var(--text-1)', fontFamily: 'inherit',
          }}
        />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1 }}>
        <span style={{ fontSize: 16, lineHeight: 1 }}>{flag(match.team2)}</span>
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-1)' }}>{match.team2}</span>
      </div>
    </div>
  )
}

export default function Path() {
  const [selectedTeam, setSelectedTeam] = useState<string>('')
  const [overrides, setOverrides] = useState<OverrideMap>({})
  const [scenarioPath, setScenarioPath] = useState<PathResponse | null>(null)
  const [scenarioReach, setScenarioReach] = useState<Record<string, number>>({})
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  const { data: koData } = useQuery({ queryKey: ['knockout'], queryFn: api.knockout })
  const { data: matchesData } = useQuery({ queryKey: ['matches'], queryFn: api.matches })
  const allTeams = (koData?.teams ?? []).map(t => t.team).sort()

  const { data: pathData, isLoading, error } = useQuery({
    queryKey: ['path', selectedTeam],
    queryFn: () => api.path(selectedTeam),
    enabled: !!selectedTeam,
  })

  const teamKo = koData?.teams.find(t => t.team === selectedTeam)
  const roundReach: Record<string, number> = {
    R32:   teamKo?.probs.R32   ?? 0,
    R16:   teamKo?.probs.R16   ?? 0,
    QF:    teamKo?.probs.QF    ?? 0,
    SF:    teamKo?.probs.SF    ?? 0,
    Final: teamKo?.probs.Final ?? 0,
  }

  const upcomingMatches = (matchesData?.matches ?? []).filter((m: MatchEntry) =>
    m.status === 'upcoming' && m.group != null && (
      !selectedTeam || m.team1 === selectedTeam || m.team2 === selectedTeam
    )
  )

  const handleChange = useCallback((id: number, s1: string, s2: string) => {
    setOverrides(prev => ({ ...prev, [id]: { score1: s1, score2: s2 } }))
    setScenarioPath(null)
  }, [])

  const handleReset = useCallback(() => {
    setOverrides({})
    setScenarioPath(null)
    setScenarioReach({})
    setRunError(null)
  }, [])

  const handleRunScenario = async () => {
    const payload: ScenarioMatchOverride[] = Object.entries(overrides)
      .filter(([, sc]) => sc.score1 !== '' && sc.score2 !== '')
      .map(([id, sc]) => ({
        match_num: Number(id),
        score1: parseInt(sc.score1) || 0,
        score2: parseInt(sc.score2) || 0,
      }))

    if (payload.length === 0) {
      setRunError('Enter at least one score first.')
      return
    }
    setRunError(null)
    setRunning(true)
    try {
      const res = await api.scenario({ overrides: payload, n_sims: 20000, focus_team: selectedTeam })
      if (res.path) setScenarioPath(res.path)
      const reach: Record<string, number> = {}
      for (const t of res.knockout_odds) {
        if (t.team === selectedTeam) {
          reach.R32   = t.probs.R32   ?? 0
          reach.R16   = t.probs.R16   ?? 0
          reach.QF    = t.probs.QF    ?? 0
          reach.SF    = t.probs.SF    ?? 0
          reach.Final = t.probs.Final ?? 0
        }
      }
      setScenarioReach(reach)
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : 'Scenario failed')
    } finally {
      setRunning(false)
    }
  }

  const hasOverrides = Object.values(overrides).some(o => o.score1 !== '' && o.score2 !== '')
  const hasScenario = scenarioPath !== null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700, fontSize: 24,
          letterSpacing: '-0.02em', marginBottom: 6,
        }}>
          <span className="gradient-text">Path to the Final</span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>
          Select a team to see their projected knockout path. Enter upcoming match scores to run a scenario.
        </p>
      </div>

      <div style={{ maxWidth: 320 }}>
        <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
          Select Team
        </label>
        <select
          value={selectedTeam}
          onChange={e => { setSelectedTeam(e.target.value); handleReset() }}
          style={{
            width: '100%', padding: '10px 12px',
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 8, fontSize: 14, color: 'var(--text-1)',
            fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
          }}
        >
          <option value="">— choose a team —</option>
          {allTeams.map(t => (
            <option key={t} value={t}>{flag(t)} {t}</option>
          ))}
        </select>
      </div>

      {!selectedTeam && (
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 12, padding: 48, textAlign: 'center', color: 'var(--text-3)',
        }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>🏆</div>
          <p style={{ margin: 0, fontSize: 14 }}>Pick a team above to explore their projected bracket path.</p>
        </div>
      )}

      {selectedTeam && upcomingMatches.length > 0 && (
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 12, padding: 20,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>
              Upcoming matches — {selectedTeam}
            </h2>
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Enter scores to run a scenario</span>
          </div>
          {upcomingMatches.map((m: MatchEntry) => (
            <MatchScoreRow key={m.id} match={m} override={overrides[m.id]} onChange={handleChange} />
          ))}
          {runError && <p style={{ color: '#dc2626', fontSize: 13, marginTop: 10 }}>{runError}</p>}
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button
              onClick={handleRunScenario}
              disabled={running || !hasOverrides}
              style={{
                padding: '9px 20px', borderRadius: 8, border: 'none',
                background: hasOverrides ? 'var(--accent)' : 'var(--surface-hi)',
                color: hasOverrides ? 'white' : 'var(--text-3)',
                fontSize: 13, fontWeight: 700,
                cursor: hasOverrides && !running ? 'pointer' : 'not-allowed',
                opacity: running ? 0.7 : 1, fontFamily: 'inherit',
              }}
            >
              {running ? 'Running…' : 'Run Scenario (20k sims)'}
            </button>
            {(hasOverrides || hasScenario) && (
              <button onClick={handleReset} style={{
                padding: '9px 16px', borderRadius: 8,
                border: '1px solid var(--border)', background: 'transparent',
                color: 'var(--text-2)', fontSize: 13, cursor: 'pointer', fontFamily: 'inherit',
              }}>
                Reset
              </button>
            )}
          </div>
        </div>
      )}

      {selectedTeam && isLoading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {ROUND_LABELS.map(r => (
            <div key={r} className="shimmer" style={{ height: 180, borderRadius: 12 }} />
          ))}
        </div>
      )}

      {selectedTeam && error && (
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 12, padding: 20, color: 'var(--text-3)', textAlign: 'center',
        }}>
          Could not load path data for {selectedTeam}.
        </div>
      )}

      {pathData && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {ROUND_LABELS.map(r => (
            <RoundCard
              key={r}
              label={r}
              opponents={pathData.path[r] ?? []}
              p_reach={roundReach[r]}
              scenarioOpponents={hasScenario ? (scenarioPath?.path[r] ?? []) : undefined}
              scenarioReach={hasScenario ? scenarioReach[r] : undefined}
            />
          ))}
        </div>
      )}
    </div>
  )
}
