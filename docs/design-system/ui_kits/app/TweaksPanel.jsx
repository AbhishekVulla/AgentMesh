// TweaksPanel.jsx

function TweaksPanel({ visible, settings, onChange }) {
  if (!visible) return null;
  const row = (label, child) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px' }}>
      <span style={{ flex: 1, fontSize: 12, color: 'var(--am-fg-muted)' }}>{label}</span>
      {child}
    </div>
  );
  return (
    <div style={{
      position: 'absolute', bottom: 72, right: 14, zIndex: 40,
      width: 260,
      background: 'rgba(15,19,28,0.95)',
      backdropFilter: 'blur(14px)',
      border: '1px solid var(--am-border-strong)',
      borderRadius: 12,
      boxShadow: 'var(--am-shadow-lg)',
      fontFamily: 'var(--am-font-sans)',
    }}>
      <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--am-border)', fontSize: 11, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--am-fg-subtle)', fontFamily: 'var(--am-font-mono)' }}>
        Tweaks
      </div>
      {row('Movement', (
        <button onClick={() => onChange({ movement: !settings.movement })} style={toggleStyle(settings.movement)}>
          {settings.movement ? 'on' : 'off'}
        </button>
      ))}
      {row('Chattiness', (
        <input type="range" min="0" max="1" step="0.05" value={settings.chatiness}
          onChange={e => onChange({ chatiness: parseFloat(e.target.value) })} style={{ width: 110 }} />
      ))}
      {row('Walk speed', (
        <input type="range" min="0.3" max="3" step="0.1" value={settings.speed}
          onChange={e => onChange({ speed: parseFloat(e.target.value) })} style={{ width: 110 }} />
      ))}
      {row('Show desks', (
        <button onClick={() => onChange({ showDesks: !settings.showDesks })} style={toggleStyle(settings.showDesks)}>
          {settings.showDesks ? 'on' : 'off'}
        </button>
      ))}
    </div>
  );
}

function toggleStyle(on) {
  return {
    padding: '4px 10px', borderRadius: 999,
    background: on ? 'var(--am-mint-500, #1fd08a)' : 'var(--am-ink-200)',
    border: '1px solid ' + (on ? 'var(--am-mint-400, #1fd08a)' : 'var(--am-border-strong)'),
    color: on ? '#0a1412' : 'var(--am-fg-muted)',
    fontSize: 11, fontFamily: 'var(--am-font-mono)', cursor: 'pointer',
    minWidth: 42,
  };
}

Object.assign(window, { TweaksPanel });
