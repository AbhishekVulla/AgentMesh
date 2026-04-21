// Primitives.jsx — small shared UI atoms

function Button({ variant = 'secondary', size = 'md', children, icon, ...rest }) {
  const variants = {
    primary:   { background: 'var(--am-mint-400)', color: '#05070b', border: '1px solid var(--am-mint-400)' },
    secondary: { background: 'var(--am-ink-200)',  color: 'var(--am-fg)', border: '1px solid var(--am-border-strong)' },
    ghost:     { background: 'transparent',        color: 'var(--am-fg-muted)', border: '1px solid transparent' },
    danger:    { background: '#2a1418',             color: '#ff8c96', border: '1px solid rgba(255,93,107,.3)' },
  };
  const sizes = {
    sm: { padding: '4px 10px', fontSize: 12 },
    md: { padding: '7px 14px', fontSize: 13 },
    lg: { padding: '10px 20px', fontSize: 14 },
    icon: { padding: 6, width: 30, height: 30 },
  };
  return (
    <button
      {...rest}
      style={{
        ...variants[variant],
        ...sizes[size],
        fontFamily: 'var(--am-font-sans)',
        fontWeight: 500,
        borderRadius: 6,
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        transition: 'all 120ms var(--am-ease-out)',
        ...rest.style,
      }}
    >
      {icon && <i data-lucide={icon} style={{ width: 14, height: 14 }} />}
      {children}
    </button>
  );
}

function Badge({ tone = 'neutral', children, dot = false }) {
  const tones = {
    neutral: { bg: 'var(--am-bg-card)', fg: 'var(--am-fg-muted)', bd: 'var(--am-border-strong)', dotC: '#5a6072' },
    mint:    { bg: 'rgba(31,208,138,.12)', fg: 'var(--am-mint-300)', bd: 'rgba(31,208,138,.25)', dotC: '#1fd08a' },
    iris:    { bg: 'rgba(122,140,255,.12)', fg: 'var(--am-iris-300)', bd: 'rgba(122,140,255,.25)', dotC: '#7a8cff' },
    amber:   { bg: 'rgba(245,184,76,.1)', fg: '#ffca6b', bd: 'rgba(245,184,76,.25)', dotC: '#f5b84c' },
    red:     { bg: 'rgba(255,93,107,.1)', fg: '#ff8c96', bd: 'rgba(255,93,107,.25)', dotC: '#ff5d6b' },
  };
  const t = tones[tone];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '3px 9px', borderRadius: 999,
      fontSize: 11, fontWeight: 500,
      background: t.bg, color: t.fg, border: `1px solid ${t.bd}`,
      fontFamily: 'var(--am-font-sans)',
    }}>
      {dot && <span style={{ width: 6, height: 6, borderRadius: 999, background: t.dotC }} />}
      {children}
    </span>
  );
}

function Kbd({ children }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      minWidth: 18, height: 18, padding: '0 5px',
      fontFamily: 'var(--am-font-mono)', fontSize: 10, fontWeight: 500,
      color: 'var(--am-fg-muted)',
      background: 'var(--am-ink-200)',
      border: '1px solid var(--am-ink-400)',
      borderBottomWidth: 2,
      borderRadius: 3,
    }}>{children}</span>
  );
}

// Deterministic 2-color gradient from an agent id — procedural avatar
function avatarColors(id) {
  const h1 = (id * 97) % 360;
  const h2 = (h1 + 40) % 360;
  return [`oklch(70% 0.15 ${h1})`, `oklch(55% 0.15 ${h2})`];
}

function Avatar({ id, size = 28, status = 'idle' }) {
  const [c1, c2] = avatarColors(id);
  const ringColors = {
    idle: 'var(--am-ink-400)',
    thinking: 'var(--am-iris-400)',
    working: 'var(--am-mint-400)',
    waiting: '#f5b84c',
    error: '#ff5d6b',
  };
  const pulse = status === 'working' || status === 'thinking';
  return (
    <span style={{
      width: size, height: size, borderRadius: size * 0.28,
      background: `linear-gradient(135deg, ${c1}, ${c2})`,
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'var(--am-font-mono)', fontSize: size * 0.4, fontWeight: 600,
      color: 'rgba(0,0,0,.7)',
      boxShadow: `0 0 0 2px ${ringColors[status]}`,
      animation: pulse ? 'am-pulse 1.6s ease-in-out infinite' : 'none',
      flexShrink: 0,
    }}>{String(id).padStart(2, '0')}</span>
  );
}

Object.assign(window, { Button, Badge, Kbd, Avatar, avatarColors });
