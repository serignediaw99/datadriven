import { useEffect, useRef, useState } from 'react'
import { FlagImg } from '../lib/FlagImg'

interface GoalEvent {
  home: string; away: string
  home_score: number; away_score: number
  team: string; scorer: string; minute: string
  own_goal?: boolean; penalty?: boolean
  status?: string
  team_win_odds?: number | null
  timestamp?: number
}

interface Toast extends GoalEvent { id: string }

/**
 * App-wide live goal reactions. Opens one SSE connection and shows a toast for each
 * `goal` event pushed by the backend's ESPN scoreboard poll. Auto-dismisses.
 */
export default function GoalToasts() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  useEffect(() => {
    const es = new EventSource(`${import.meta.env.VITE_API_BASE ?? ''}/api/live/stream`)
    es.addEventListener('goal', (e: MessageEvent) => {
      let g: GoalEvent
      try { g = JSON.parse(e.data) } catch { return }
      const id = `${g.timestamp ?? Date.now()}-${g.team}-${g.scorer}-${g.minute}`
      setToasts(prev => prev.some(t => t.id === id) ? prev : [{ ...g, id }, ...prev].slice(0, 4))
      timers.current[id] = setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id))
        delete timers.current[id]
      }, 9000)
    })
    return () => {
      es.close()
      Object.values(timers.current).forEach(clearTimeout)
      timers.current = {}
    }
  }, [])

  const dismiss = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
    if (timers.current[id]) { clearTimeout(timers.current[id]); delete timers.current[id] }
  }

  if (toasts.length === 0) return null

  return (
    <div style={{
      position: 'fixed', right: 16, bottom: 16, zIndex: 1000,
      display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 340,
    }}>
      {toasts.map(t => {
        const tag = t.own_goal ? ' (OG)' : t.penalty ? ' (pen)' : ''
        return (
          <div
            key={t.id}
            onClick={() => dismiss(t.id)}
            className="goal-toast"
            style={{
              background: 'var(--surface)', border: '1px solid var(--border-hi)',
              borderLeft: '3px solid var(--accent)', borderRadius: 10,
              padding: '12px 14px', cursor: 'pointer',
              boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
            }}
          >
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 800,
              fontSize: 13, letterSpacing: '0.02em',
            }}>
              <span style={{ fontSize: 16 }}>⚽</span>
              <span className="gradient-text">GOAL</span>
              <span style={{ color: 'var(--text-3)', fontWeight: 600 }}>{t.minute}{tag}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6 }}>
              <FlagImg team={t.team} size={18} />
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>{t.scorer || t.team}</span>
            </div>

            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, fontSize: 13,
              color: 'var(--text-2)', fontVariantNumeric: 'tabular-nums',
            }}>
              <FlagImg team={t.home} size={15} />
              <span style={{ fontWeight: t.home_score > t.away_score ? 700 : 400, color: 'var(--text-1)' }}>{t.home}</span>
              <span style={{ fontWeight: 800, color: 'var(--text-1)' }}>{t.home_score}–{t.away_score}</span>
              <span style={{ fontWeight: t.away_score > t.home_score ? 700 : 400, color: 'var(--text-1)' }}>{t.away}</span>
              <FlagImg team={t.away} size={15} />
            </div>

            {typeof t.team_win_odds === 'number' && t.team_win_odds > 0.005 && (
              <div style={{ marginTop: 7, fontSize: 11, color: 'var(--text-3)' }}>
                {t.team} title odds: <strong style={{ color: 'var(--text-2)' }}>{(t.team_win_odds * 100).toFixed(1)}%</strong>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
