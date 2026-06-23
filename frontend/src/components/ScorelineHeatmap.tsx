import type { ScorelineEntry } from '../lib/types'

function lerp(a: number, b: number, t: number) { return a + (b - a) * t }

function heatColor(prob: number, maxProb: number): string {
  const t = Math.min(prob / maxProb, 1)
  // Dark transparent → accent
  const r = Math.round(lerp(13,  99, t))
  const g = Math.round(lerp(15, 102, t))
  const b = Math.round(lerp(26, 241, t))
  const a = lerp(0.06, 0.90, t)
  return `rgba(${r},${g},${b},${a})`
}

export default function ScorelineHeatmap({ scorelines }: { scorelines: ScorelineEntry[] }) {
  const grid: number[][] = Array.from({ length: 8 }, () => Array(8).fill(0))
  for (const s of scorelines) {
    const [g1, g2] = s.score.split('-').map(Number)
    if (g1 < 8 && g2 < 8) grid[g1][g2] = s.probability
  }
  const maxProb = Math.max(...scorelines.map(s => s.probability), 0.001)

  return (
    <div>
      <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
        {/* Y-axis (home goals) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, paddingTop: 24 }}>
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} style={{
              width: 16, height: 40,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, color: 'var(--text-3)', fontWeight: 600,
            }}>
              {i}
            </div>
          ))}
        </div>

        <div style={{ flex: 1 }}>
          {/* X-axis (away goals) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8,1fr)', gap: 4, marginBottom: 4 }}>
            {Array.from({ length: 8 }, (_, i) => (
              <div key={i} style={{
                textAlign: 'center', fontSize: 11,
                color: 'var(--text-3)', fontWeight: 600,
              }}>
                {i}
              </div>
            ))}
          </div>

          {/* Grid */}
          {grid.map((row, g1) => (
            <div key={g1} style={{ display: 'grid', gridTemplateColumns: 'repeat(8,1fr)', gap: 4, marginBottom: 4 }}>
              {row.map((prob, g2) => {
                const isTop = prob > 0 && prob === maxProb
                return (
                  <div
                    key={g2}
                    className="heatmap-cell"
                    title={`${g1}-${g2}: ${(prob * 100).toFixed(1)}%`}
                    style={{
                      height: 40, borderRadius: 5,
                      background: heatColor(prob, maxProb),
                      border: isTop
                        ? '1px solid rgba(181,109,60,0.7)'
                        : '1px solid rgba(255,255,255,0.04)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      boxShadow: isTop ? '0 0 10px rgba(181,109,60,0.35)' : 'none',
                    }}
                  >
                    {prob > maxProb * 0.28 && (
                      <span style={{
                        fontSize: 10,
                        fontWeight: 700,
                        color: prob > maxProb * 0.55 ? '#fff' : 'rgba(255,255,255,0.6)',
                        fontVariantNumeric: 'tabular-nums',
                      }}>
                        {(prob * 100).toFixed(1)}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10 }}>
        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>← Home goals (rows 0–7)</span>
        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>Away goals (cols 0–7) →</span>
      </div>
    </div>
  )
}
