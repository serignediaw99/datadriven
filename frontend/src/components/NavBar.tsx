import { NavLink, Link } from 'react-router-dom'

const links = [
  { to: '/groups',   label: 'Groups' },
  { to: '/knockout', label: 'Knockout' },
  { to: '/awards',   label: 'Awards' },
  { to: '/matches',  label: 'Matches' },
  { to: '/bracket',  label: 'Bracket' },
  { to: '/path',     label: 'Path' },
  { to: '/scenario', label: 'Scenario' },
  { to: '/about',    label: 'About' },
]

export default function NavBar() {
  return (
    <nav style={{
      background: 'rgba(250,245,238,0.92)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid var(--border)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
    }}>
      <div style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        height: 48,
        gap: 4,
        overflowX: 'auto',
      }}>
        <Link to="/" style={{ textDecoration: 'none', marginRight: 20, flexShrink: 0 }}>
          <span style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 800,
            fontSize: 18,
            letterSpacing: '-0.03em',
            color: 'var(--accent)',
          }}>
            datadriven
          </span>
        </Link>

        {links.map(l => (
          <NavLink
            key={l.to}
            to={l.to}
            style={({ isActive }) => ({
              position: 'relative',
              color: isActive ? 'var(--accent)' : 'var(--text-2)',
              fontWeight: isActive ? 600 : 400,
              fontSize: 13,
              textDecoration: 'none',
              padding: '0 10px',
              height: 48,
              display: 'flex',
              alignItems: 'center',
              whiteSpace: 'nowrap',
              transition: 'color .15s',
              borderBottom: isActive ? '2px solid var(--accent)' : '2px solid transparent',
              flexShrink: 0,
            })}
          >
            {l.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
