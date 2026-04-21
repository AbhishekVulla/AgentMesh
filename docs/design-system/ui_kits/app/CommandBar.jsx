// CommandBar.jsx — ⌘K palette
function CommandBar({ open, onClose, onRun }) {
  const [query, setQuery] = React.useState('');
  const items = [
    { id: 'spawn', label: 'Spawn agent', hint: 'sonnet-4-5', icon: 'plus' },
    { id: 'spawn-haiku', label: 'Spawn agent (haiku)', hint: 'haiku-4-5', icon: 'zap' },
    { id: 'focus', label: 'Focus next waiting agent', hint: 'needs approval', icon: 'arrow-right' },
    { id: 'kill', label: 'Kill idle agents', hint: 'stopped > 5m', icon: 'x' },
    { id: 'layout', label: 'Reset mesh layout', hint: '', icon: 'git-branch' },
    { id: 'logs', label: 'Open logs', hint: '', icon: 'terminal' },
  ];
  const filtered = items.filter(i => i.label.toLowerCase().includes(query.toLowerCase()));
  const inputRef = React.useRef(null);
  React.useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 50); }, [open]);
  React.useEffect(() => { if (!open) setQuery(''); }, [open]);
  if (!open) return null;
  return (
    <div onClick={onClose} style={{
      position: 'absolute', inset: 0, zIndex: 50,
      background: 'rgba(0,0,0,.6)', display: 'flex', alignItems: 'flex-start',
      justifyContent: 'center', paddingTop: 90,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: 520, background: 'var(--am-ink-150)',
        border: '1px solid var(--am-border-strong)',
        borderRadius: 14,
        boxShadow: 'var(--am-shadow-lg)',
        overflow: 'hidden',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', borderBottom: '1px solid var(--am-border)' }}>
          <i data-lucide="search" style={{ width: 16, height: 16, color: 'var(--am-fg-muted)' }} />
          <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)} placeholder="Type a command…" style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            color: 'var(--am-fg)', fontSize: 14, fontFamily: 'var(--am-font-sans)',
          }}/>
          <Kbd>esc</Kbd>
        </div>
        <div style={{ padding: 6, maxHeight: 340, overflowY: 'auto' }}>
          {filtered.map((it, i) => (
            <button key={it.id} onClick={() => { onRun(it.id); onClose(); }} style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 10px', borderRadius: 8,
              background: i === 0 ? 'var(--am-ink-200)' : 'transparent',
              border: '1px solid ' + (i === 0 ? 'var(--am-border-strong)' : 'transparent'),
              color: 'var(--am-fg)', cursor: 'pointer', fontFamily: 'var(--am-font-sans)',
              fontSize: 13, textAlign: 'left',
            }}>
              <i data-lucide={it.icon} style={{ width: 14, height: 14, color: 'var(--am-fg-muted)' }} />
              <span>{it.label}</span>
              {it.hint && <span style={{ marginLeft: 'auto', fontFamily: 'var(--am-font-mono)', fontSize: 10, color: 'var(--am-fg-subtle)' }}>{it.hint}</span>}
            </button>
          ))}
          {filtered.length === 0 && <div style={{ padding: 20, textAlign: 'center', fontSize: 12, color: 'var(--am-fg-subtle)' }}>No matches.</div>}
        </div>
      </div>
    </div>
  );
}
Object.assign(window, { CommandBar });
