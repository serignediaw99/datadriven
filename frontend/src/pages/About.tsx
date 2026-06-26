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
            worldcup.json feed, and ESPN's scoreboard is polled every 45 seconds for in-play
            scores and goals. Player goal and assist tallies come from the ESPN statistics API.
            The strength model is fit from ~28,000 historical international results, with Elo
            ratings from eloratings.net kept as a fallback.
          </Step>
          <Divider />
          <Step n="2" title="Team strength model">
            Team ratings come from a time-weighted Dixon-Coles model fit to ~28,000 international
            matches, giving each team attack (α) and defense (β) parameters. Expected goals for a
            matchup are{' '}
            <code style={code}>λ = exp(μ + α_i − β_j + γ·home)</code>, where μ ≈ 0.18 sets the
            baseline (~1.2 goals), γ ≈ 0.24 is home advantage, recent matches are weighted more
            heavily (exponential time-decay), and a low-score correction (ρ) adjusts the frequency
            of 0–0, 1–0, and 1–1 results. Completed matches are treated as fixed outcomes — only
            unplayed fixtures are simulated.
          </Step>
          <Divider />
          <Step n="3" title="Bookmaker-odds blend">
            When a bookmaker API key is configured, the model is calibrated to the market: team
            strengths are nudged toward de-vigged outright-winner odds, and priced upcoming group
            fixtures take their goal rates from the de-vigged head-to-head market. Without a key,
            the app runs the pure model.
          </Step>
          <Divider />
          <Step n="4" title="Tens of thousands of simulations">
            Goals for every unplayed match are sampled simultaneously using vectorized NumPy
            Poisson draws — a full batch of tournaments per run (50,000 locally, 15,000 on the
            hosted instance). Each simulation runs the complete group stage (with FIFA tiebreakers
            including head-to-head), allocates the 8 best third-place teams to the round of 32 via
            FIFA's official 2026 bracket table, and plays out R32 → R16 → QF → SF → Final.
          </Step>
          <Divider />
          <Step n="5" title="Player awards">
            For each unplayed match, team goals are distributed among tracked players using each
            player's historical share of their team's scoring. Simulated future goals are stacked
            on top of current tournament tallies to estimate golden boot and top assists odds.
          </Step>
          <Divider />
          <Step n="6" title="Live updates">
            When a new result is detected — or while a match is in play — the simulator re-runs the
            full batch, folding the current score and time remaining into every live fixture, then
            pushes a server-sent event to all connected clients. Win probabilities update within
            seconds of a goal being recorded.
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
            { page: 'Path',       desc: 'Select any team to see their most likely opponents round by round. Enter hypothetical scores to run a scenario and see how their bracket path shifts.' },
            { page: 'Scenario',   desc: 'Set scores for any upcoming group stage matches and re-run the simulation to see how the championship odds change across all 48 teams.' },
            { page: 'About',      desc: 'This page.' },
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
            { label: 'Model',      value: 'Time-weighted Dixon-Coles · Poisson · bookmaker-odds blend' },
            { label: 'Data',       value: 'OpenFootball · ESPN API · The Odds API · eloratings.net' },
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
