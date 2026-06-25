import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { FlagImg } from '../lib/FlagImg'
import type { ScenarioMatchOverride, ScenarioResponse, MatchEntry, KnockoutProbs } from '../lib/types'

type OverrideMap = Record<number, { score1: string; score2: string }>

const STAGES: { key: keyof KnockoutProbs; label: string; title: string }[] = [
  { key: 'R32',    label: 'R32',   title: 'Reach Round of 32 (qualify from group)' },
  { key: 'R16',    label: 'R16',   title: 'Reach Round of 16' },
  { key: 'QF',     label: 'QF',    title: 'Reach quarter-finals' },
  { key: 'SF',     label: 'SF',    title: 'Reach semi-finals' },
  { key: 'Final',  label: 'Final', title: 'Reach the final' },
  { key: 'Winner', label: 'Champ', title: 'Win the tournament' },
]

function ScoreInput({
  label, value, onChange,
}: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      <input
        type="number" min={0} max={20} value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          width: 56, padding: '6px 8px', textAlign: 'center',
          background: 'var(--surface-hi)', border: '1px solid var(--border)',
          borderRadius: 6, fontSize: 16, fontWeight: 700, color: 'var(--text-1)',
          fontFamily: 'inherit', outline: 'none',
        }}
      />
    </div>
  )
}

function MatchRow({
  match, override, onChange, onClear,
}: {
  match: MatchEntry
  override: { score1: string; score2: string } | undefined
  onChange: (num: number, s1: string, s2: string) => void
  onClear: (num: number) => void
}) {
  const hasOverride = override !== undefined
  const actualScore = match.status === 'played' ? `${match.score1} – ${match.score2}` : null

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 0', borderBottom: '1px solid var(--border)',
    }}>
      <span style={{ width: 80, fontSize: 11, color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>
        {match.group ?? match.round}
      </span>
      <span style={{ width: 28, textAlign: 'right' }}><FlagImg team={match.team1} size={18} /></span>
      <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: 'var(--text-1)', textAlign: 'right' }}>{match.team1}</span>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {actualScore && !hasOverride ? (
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-2)', width: 64, textAlign: 'center', fontVariantNumeric: 'tabular-nums' }}>
            {actualScore}
          </span>
        ) : (
          <>
            <ScoreInput
              label=""
              value={override?.score1 ?? (match.score1 != null ? String(match.score1) : '')}
              onChange={v => onChange(match.id, v, override?.score2 ?? (match.score2 != null ? String(match.score2) : '0'))}
            />
            <span style={{ color: 'var(--text-3)', fontWeight: 700 }}>–</span>
            <ScoreInput
              label=""
              value={override?.score2 ?? (match.score2 != null ? String(match.score2) : '')}
              onChange={v => onChange(match.id, override?.score1 ?? (match.score1 != null ? String(match.score1) : '0'), v)}
            />
          </>
        )}
      </div>

      <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: 'var(--text-1)' }}>{match.team2}</span>
      <span style={{ width: 28 }}><FlagImg team={match.team2} size={18} /></span>

      <div style={{ width: 72, textAlign: 'right' }}>
        {!actualScore ? (
          <button
            onClick={() => onChange(match.id,
              override?.score1 ?? '1',
              override?.score2 ?? '1')}
            style={{
              fontSize: 11, padding: '3px 8px',
              background: hasOverride ? 'var(--accent)' : 'var(--surface-hi)',
              color: hasOverride ? 'white' : 'var(--text-2)',
              border: 'none', borderRadius: 4, cursor: 'pointer',
            }}
          >
            {hasOverride ? 'set ✓' : 'override'}
          </button>
        ) : (
          hasOverride && (
            <button
              onClick={() => onClear(match.id)}
              style={{
                fontSize: 11, padding: '3px 8px',
                background: 'var(--surface-hi)', color: 'var(--text-3)',
                border: 'none', borderRadius: 4, cursor: 'pointer',
              }}
            >
              clear
            </button>
          )
        )}
      </div>
    </div>
  )
}

function StageCell({ base, scen }: { base: number; scen: number }) {
  const delta = scen - base
  const color = delta > 0.005 ? '#2e7d52' : delta < -0.005 ? '#dc2626' : 'var(--text-1)'
  const faded = scen < 0.001 && delta > -0.005
  return (
    <td style={{ padding: '6px 6px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
      <div style={{ fontSize: 12, fontWeight: 700, color, opacity: faded ? 0.35 : 1 }}>
        {(scen * 100).toFixed(1)}
      </div>
      {Math.abs(delta) >= 0.005 && (
        <div style={{ fontSize: 9, color, fontWeight: 600 }}>
          {delta > 0 ? '+' : ''}{(delta * 100).toFixed(1)}
        </div>
      )}
    </td>
  )
}

export default function Scenario() {
  const [overrides, setOverrides] = useState<OverrideMap>({})
  const [result, setResult] = useState<ScenarioResponse | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: matchesData } = useQuery({ queryKey: ['matches'], queryFn: api.matches })
  const { data: koData } = useQuery({ queryKey: ['knockout'], queryFn: api.knockout })

  const upcomingMatches = (matchesData?.matches ?? []).filter(m => m.status === 'upcoming' && m.group)

  const handleChange = useCallback((num: number, s1: string, s2: string) => {
    setOverrides(prev => ({ ...prev, [num]: { score1: s1, score2: s2 } }))
  }, [])

  const handleClear = useCallback((num: number) => {
    setOverrides(prev => {
      const next = { ...prev }
      delete next[num]
      return next
    })
  }, [])

  const handleRun = async () => {
    const payload: ScenarioMatchOverride[] = Object.entries(overrides)
      .map(([num, sc]) => ({
        match_num: Number(num),
        score1: parseInt(sc.score1) || 0,
        score2: parseInt(sc.score2) || 0,
      }))
      .filter(o => !isNaN(o.score1) && !isNaN(o.score2))

    if (payload.length === 0) {
      setError('Add at least one score override first.')
      return
    }
    setError(null)
    setRunning(true)
    try {
      const res = await api.scenario({ overrides: payload, n_sims: 5000 })
      setResult(res)
    } catch (e: any) {
      setError(e?.message ?? 'Simulation failed')
    } finally {
      setRunning(false)
    }
  }

  const baselineProbs: Record<string, KnockoutProbs> = {}
  for (const t of koData?.teams ?? []) {
    baselineProbs[t.team] = t.probs
  }
  const scenarioProbs: Record<string, KnockoutProbs> = {}
  for (const t of result?.knockout_odds ?? []) {
    scenarioProbs[t.team] = t.probs
  }

  // Largest probability swing across any stage — surfaces the teams the scenario
  // actually moved (group overrides shift qualification odds most, not the title).
  const maxSwing = (team: string): number => {
    const b = baselineProbs[team], s = scenarioProbs[team]
    if (!b || !s) return 0
    return Math.max(...STAGES.map(st => Math.abs((s[st.key] ?? 0) - (b[st.key] ?? 0))))
  }

  const allTeams = Object.keys(baselineProbs)
  const movers = allTeams
    .filter(t => maxSwing(t) >= 0.005 || (baselineProbs[t]?.Winner ?? 0) >= 0.015)
    .sort((a, b) => {
      const d = maxSwing(b) - maxSwing(a)
      if (Math.abs(d) > 1e-9) return d
      return (scenarioProbs[b]?.Winner ?? 0) - (scenarioProbs[a]?.Winner ?? 0)
    })
    .slice(0, 24)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700, fontSize: 24,
          letterSpacing: '-0.02em', marginBottom: 6,
        }}>
          <span className="gradient-text">Scenario Explorer</span>
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>
          Set hypothetical match scores for upcoming group stage games and see how the odds shift at every stage — from qualifying to the title.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: result ? 'minmax(0, 0.85fr) minmax(0, 1.15fr)' : '1fr', gap: 24, alignItems: 'start' }}>
        {/* Left: match overrides */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-1)' }}>
              Upcoming Group Matches
            </h2>
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
              {Object.keys(overrides).length} override{Object.keys(overrides).length !== 1 ? 's' : ''} set
            </span>
          </div>

          {upcomingMatches.length === 0 && (
            <p style={{ color: 'var(--text-3)', fontSize: 13 }}>No upcoming group stage matches.</p>
          )}

          {upcomingMatches.map(m => (
            <MatchRow
              key={m.id}
              match={m}
              override={overrides[m.id]}
              onChange={handleChange}
              onClear={handleClear}
            />
          ))}

          {error && (
            <p style={{ color: '#dc2626', fontSize: 13, marginTop: 12 }}>{error}</p>
          )}

          <div style={{ marginTop: 20, display: 'flex', gap: 10 }}>
            <button
              onClick={handleRun}
              disabled={running}
              style={{
                padding: '10px 24px', borderRadius: 8, border: 'none',
                background: 'var(--accent)', color: 'white',
                fontSize: 14, fontWeight: 700, cursor: running ? 'not-allowed' : 'pointer',
                opacity: running ? 0.7 : 1, fontFamily: 'inherit',
              }}
            >
              {running ? 'Running…' : 'Run Scenario (5k sims)'}
            </button>
            {Object.keys(overrides).length > 0 && (
              <button
                onClick={() => { setOverrides({}); setResult(null) }}
                style={{
                  padding: '10px 16px', borderRadius: 8,
                  border: '1px solid var(--border)',
                  background: 'transparent', color: 'var(--text-2)',
                  fontSize: 14, cursor: 'pointer', fontFamily: 'inherit',
                }}
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Right: results — per-stage advancement odds */}
        {result && (
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-1)' }}>
                Stage-by-Stage Odds
              </h2>
              <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
                {result.n_simulations.toLocaleString()} sims · {result.elapsed_seconds.toFixed(1)}s
              </span>
            </div>
            <p style={{ margin: '0 0 12px', fontSize: 11, color: 'var(--text-3)' }}>
              Scenario % to reach each round; small number is the change vs. baseline.
            </p>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 380 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    <th style={{ textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-3)', padding: '0 6px 8px', position: 'sticky', left: 0, background: 'var(--surface)' }}>
                      Team
                    </th>
                    {STAGES.map(s => (
                      <th key={s.key} title={s.title} style={{ textAlign: 'right', fontSize: 11, fontWeight: 600, color: 'var(--text-3)', padding: '0 6px 8px', cursor: 'help' }}>
                        {s.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {movers.map(team => {
                    const base = baselineProbs[team]
                    const scen = scenarioProbs[team]
                    return (
                      <tr key={team} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '6px 6px', position: 'sticky', left: 0, background: 'var(--surface)' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}>
                            <FlagImg team={team} size={16} />
                            <span style={{ fontSize: 12, color: 'var(--text-1)' }}>{team}</span>
                          </span>
                        </td>
                        {STAGES.map(s => (
                          <StageCell key={s.key} base={base?.[s.key] ?? 0} scen={scen?.[s.key] ?? 0} />
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
