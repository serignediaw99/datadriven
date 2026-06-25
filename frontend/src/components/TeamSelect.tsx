import { useEffect, useRef, useState } from 'react'
import { FlagImg } from '../lib/FlagImg'

interface TeamSelectProps {
  teams: string[]
  value: string
  onChange: (team: string) => void
  placeholder?: string
}

/**
 * Custom team dropdown with image-based flags.
 *
 * A native <select> can only render text in its <option>s, so emoji flags get
 * used there — and those don't render on Windows. This replaces the native
 * control with an accessible button + listbox so flags use <FlagImg> (PNG)
 * everywhere, including Windows.
 */
export function TeamSelect({ teams, value, onChange, placeholder = 'Select…' }: TeamSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const select = (t: string) => { onChange(t); setOpen(false) }

  return (
    <div ref={ref} style={{ position: 'relative', width: '100%' }}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        style={{
          width: '100%', padding: '10px 12px',
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 8, fontSize: 14, color: value ? 'var(--text-1)' : 'var(--text-3)',
          fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
          display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left',
        }}
      >
        {value && (
          <span style={{ width: 22, flexShrink: 0, display: 'inline-flex', alignItems: 'center' }}>
            <FlagImg team={value} size={20} />
          </span>
        )}
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {value || placeholder}
        </span>
        <span aria-hidden style={{ flexShrink: 0, color: 'var(--text-3)', fontSize: 10 }}>▼</span>
      </button>

      {open && (
        <ul
          role="listbox"
          style={{
            position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 50,
            margin: 0, padding: 4, listStyle: 'none',
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 8, maxHeight: 320, overflowY: 'auto',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)',
          }}
        >
          {teams.map(t => {
            const selected = t === value
            return (
              <li
                key={t}
                role="option"
                aria-selected={selected}
                onClick={() => select(t)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 14,
                  color: 'var(--text-1)',
                  background: selected ? 'var(--surface-hi)' : 'transparent',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--surface-hi)' }}
                onMouseLeave={e => { e.currentTarget.style.background = selected ? 'var(--surface-hi)' : 'transparent' }}
              >
                <span style={{ width: 22, flexShrink: 0, display: 'inline-flex', alignItems: 'center' }}>
                  <FlagImg team={t} size={20} />
                </span>
                <span>{t}</span>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
