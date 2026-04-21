// LeftRail.jsx — narrow vertical icon rail
function LeftRail({ view, onView }) {
  const items = [
    { id: 'mesh', icon: 'network', label: 'Mesh' },
    { id: 'agents', icon: 'bot', label: 'Agents' },
    { id: 'logs', icon: 'terminal', label: 'Logs' },
    { id: 'files', icon: 'file-code', label: 'Files' },
  ];
  return (
    <div style={{
      width: 48, height: '100%',
      background: 'var(--am-ink-100)',
      borderRight: '1px solid var(--am-border)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '10px 0', gap: 4,
    }}>
      <div style={{ padding: '6px 0 12px' }}>
        <img src={window.__resources.logoGlyph} width="22" />
      </div>
      {items.map(it => (
        <button key={it.id} title={it.label} onClick={() => onView(it.id)} style={{
          width: 32, height: 32, borderRadius: 8,
          background: view === it.id ? 'var(--am-bg-active)' : 'transparent',
          border: view === it.id ? '1px solid var(--am-mint-400)' : '1px solid transparent',
          color: view === it.id ? 'var(--am-mint-300)' : 'var(--am-fg-muted)',
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <i data-lucide={it.icon} style={{ width: 16, height: 16 }} />
        </button>
      ))}
      <div style={{ flex: 1 }} />
      <button title="Settings" style={{
        width: 32, height: 32, borderRadius: 8, background: 'transparent',
        border: '1px solid transparent', color: 'var(--am-fg-muted)', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}><i data-lucide="settings" style={{ width: 16, height: 16 }} /></button>
    </div>
  );
}
Object.assign(window, { LeftRail });
