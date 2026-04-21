// BottomToolbar.jsx
function BottomToolbar({ onAddAgent, onCommand, agentsCount }) {
  return (
    <div style={{
      position: 'absolute', bottom: 14, left: 62, right: 14, zIndex: 20,
      display: 'flex', alignItems: 'center', gap: 8, pointerEvents: 'none',
    }}>
      <div style={{
        pointerEvents: 'auto',
        background: 'rgba(15,19,28,0.85)',
        backdropFilter: 'blur(12px) saturate(1.2)',
        border: '1px solid var(--am-border-strong)',
        borderRadius: 10,
        padding: 6,
        display: 'flex', gap: 6,
        boxShadow: 'var(--am-shadow-md)',
      }}>
        <Button variant="primary" icon="plus" onClick={onAddAgent}>Spawn agent</Button>
        <Button variant="secondary" icon="git-branch">Layout</Button>
        <Button variant="secondary" icon="settings">Settings</Button>
      </div>
      <div style={{ flex: 1 }} />
      <div style={{
        pointerEvents: 'auto',
        background: 'rgba(15,19,28,0.85)',
        backdropFilter: 'blur(12px) saturate(1.2)',
        border: '1px solid var(--am-border-strong)',
        borderRadius: 10,
        padding: '6px 10px',
        display: 'flex', alignItems: 'center', gap: 14,
        fontSize: 11, color: 'var(--am-fg-muted)',
        fontFamily: 'var(--am-font-mono)',
      }}>
        <span>{agentsCount} agents</span>
        <span style={{ color: 'var(--am-fg-subtle)' }}>·</span>
        <button onClick={onCommand} style={{
          background: 'transparent', border: 'none', color: 'var(--am-fg-muted)',
          fontFamily: 'var(--am-font-mono)', fontSize: 11, cursor: 'pointer',
          display: 'inline-flex', alignItems: 'center', gap: 6,
        }}>
          <Kbd>⌘</Kbd><Kbd>K</Kbd> command
        </button>
      </div>
    </div>
  );
}
Object.assign(window, { BottomToolbar });
