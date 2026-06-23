export default function About() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40, maxWidth: 720 }}>

      {/* Header */}
      <div>
        <h1 style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700, fontSize: 24,
          letterSpacing: '-0.02em', marginBottom: 8,
        }}>
          <span className="gradient-text">About datadriven</span>
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-2)', lineHeight: 1.7 }}>
          A live Monte Carlo simulator for the 2026 FIFA World Cup — built to turn raw match data
          and team ratings into real-time probability estimates for every remaining outcome.
        </p>
      </div>

      {/* How it works */}
      <section>
        <p className="label" style={{ marginBottom: 16 }}>How it works</p>
        <div className="card" style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
          <Step n="1" title="Data ingestion">
            Every 5 minutes, live match results are pulled from OpenFootball's open-source
            worldcup.json feed. Player goal and assist tallies are sourced from the ESPN statistics
            API. Elo ratings for all 48 teams are fetched from eloratings.net.
          </Step>
          <Divider />
          <Step n="2" title="Team strength model">
            Each team's Elo rating is converted into attack (α) and defense (β) parameters.
            Expected goals for any matchup are computed as{' '}
            <code style={code}>λ = 1.15 × exp(α_i − β_j)</code>, where 1.15 is the
            neutral-venue World Cup average. Completed matches are treated as fixed outcomes —
            only unplayed fixtures are simulated.
          </Step>
          <Divider />
          <Step n="3" title="50,000 simulations">
            Goals for every unplayed match are sampled simultaneously using vectorized NumPy
            Poisson draws — 50,000 full tournaments in roughly 4 seconds. Each simulation runs
            the complete group stage (with FIFA tiebreakers including head-to-head), selects the
            8 best third-place teams, and plays out R32 → R16 → QF → SF → Final.
          </Step>
          <Divider />
          <Step n="4" title="Player awards">
            For each unplayed match, team goals are distributed among tracked players using each
            player's historical share of their team's scoring. Simulated future goals are stacked
            on top of current tournament tallies to estimate golden boot and top assists odds.
          </Step>
          <Divider />
          <Step n="5" title="Live updates">
            When a new result is detected, the simulator re-runs all 50,000 simulations and
            pushes a server-sent event to all connected clients. Every page updates automatically
            within seconds of a goal being recorded.
          </Step>
        </div>
      </section>

      {/* Pages */}
      <section>
        <p className="label" style={{ marginBottom: 16 }}>What each page shows</p>
        <div className="card" style={{ overflow: 'hidden' }}>
          {[
            { page: 'Dashboard',  desc: 'Top win probabilities, golden boot leaders, and a snapshot of all 12 groups.' },
            { page: 'Groups',     desc: 'Per-group finish probabilities as stacked bars, with third-place qualification odds.' },
            { page: 'Knockout',   desc: 'All 48 teams ranked by P(win), with round-by-round reach probabilities.' },
            { page: 'Bracket',    desc: 'The single most-likely projected bracket path from R32 to the Final.' },
            { page: 'Awards',     desc: 'Golden boot and top assists race — current tally, projected total, and win probability.' },
            { page: 'Matches',    desc: 'Full fixture list with results and upcoming kick-off times.' },
          ].map(({ page, desc }, i, arr) => (
            <div key={page} style={{
              display: 'grid',
              gridTemplateColumns: '100px 1fr',
              gap: 16,
              padding: '14px 20px',
              borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none',
              alignItems: 'start',
            }}>
              <span style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 600,
                fontSize: 13,
                color: 'var(--accent)',
              }}>{page}</span>
              <span style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6 }}>{desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Stack */}
      <section>
        <p className="label" style={{ marginBottom: 16 }}>Tech stack</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {[
            { label: 'Backend',    value: 'Python · FastAPI · NumPy · APScheduler' },
            { label: 'Frontend',   value: 'React · TypeScript · Vite · React Query' },
            { label: 'Model',      value: 'Poisson regression · Elo ratings · H2H tiebreakers' },
            { label: 'Data',       value: 'OpenFootball · ESPN API · eloratings.net' },
          ].map(({ label, value }) => (
            <div key={label} className="card" style={{ padding: '16px 18px' }}>
              <div className="label" style={{ marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6 }}>{value}</div>
            </div>
          ))}
        </div>
      </section>

    </div>
  )
}

function Step({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      <div style={{
        width: 26, height: 26, borderRadius: '50%',
        background: 'var(--accent-dim)',
        border: '1px solid var(--accent)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        fontFamily: "'Space Grotesk', sans-serif",
        fontWeight: 700, fontSize: 12,
        color: 'var(--accent)',
        marginTop: 1,
      }}>{n}</div>
      <div>
        <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-1)', marginBottom: 4 }}>{title}</div>
        <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.7 }}>{children}</div>
      </div>
    </div>
  )
}

function Divider() {
  return <div style={{ height: 1, background: 'var(--border)', margin: '0 -24px' }} />
}

const code: React.CSSProperties = {
  fontFamily: 'monospace',
  fontSize: 12,
  background: 'var(--surface-hi)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  padding: '1px 5px',
  color: 'var(--accent)',
}
