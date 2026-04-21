// Inspector.jsx — right panel for selected agent
function Inspector({ agent, onClose, onKill }) {
  if (!agent) return null;
  const ctxPct = agent.tokens / 200;
  const gaugeCls = ctxPct < 0.6 ? '#1fd08a' : ctxPct < 0.8 ? '#f5b84c' : '#ff5d6b';

  return (
    <div style={{
      width: 340, height: '100%',
      background: 'var(--am-ink-100)',
      borderLeft: '1px solid var(--am-border)',
      display: 'flex', flexDirection: 'column',
      flexShrink: 0,
    }}>
      {/* header */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--am-border)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <Avatar id={agent.id} size={36} status={agent.status} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--am-fg)' }}>{agent.name}</div>
          <div style={{ fontFamily: 'var(--am-font-mono)', fontSize: 11, color: 'var(--am-fg-subtle)' }}>
            agent-{String(agent.id).padStart(2,'0')} · {agent.model}
          </div>
        </div>
        <button onClick={onClose} style={{
          background: 'transparent', border: 'none', color: 'var(--am-fg-muted)',
          cursor: 'pointer', padding: 4, borderRadius: 4,
        }}><i data-lucide="x" style={{ width: 16, height: 16 }}/></button>
      </div>

      {/* status */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--am-border)', display: 'flex', gap: 8, alignItems: 'center' }}>
        <Badge tone={({idle:'neutral',thinking:'iris',working:'mint',waiting:'amber',error:'red'})[agent.status]} dot>
          {agent.status[0].toUpperCase() + agent.status.slice(1)}
        </Badge>
        {agent.tool && <span style={{ fontFamily: 'var(--am-font-mono)', fontSize: 11, color: 'var(--am-fg-muted)' }}>{agent.tool}</span>}
      </div>

      {/* context gauge */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--am-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontFamily: 'var(--am-font-mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--am-fg-subtle)' }}>Context</span>
          <span style={{ fontFamily: 'var(--am-font-mono)', fontSize: 11, color: 'var(--am-fg)', fontVariantNumeric: 'tabular-nums' }}>{agent.tokens}K / 200K</span>
        </div>
        <div style={{ height: 5, borderRadius: 999, background: 'var(--am-ink-200)', overflow: 'hidden' }}>
          <div style={{ width: `${ctxPct * 100}%`, height: '100%', background: gaugeCls, borderRadius: 999, transition: 'width 240ms' }} />
        </div>
      </div>

      {/* tool activity */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px' }}>
        <div style={{ fontFamily: 'var(--am-font-mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--am-fg-subtle)', marginBottom: 8, paddingLeft: 4 }}>Recent tool calls</div>
        {agent.tools.map((t, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px',
            borderRadius: 6, fontSize: 12, opacity: t.done ? 0.55 : 1,
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: 999,
              background: t.done ? '#1fd08a' : (t.wait ? '#f5b84c' : '#1fd08a'),
              animation: (!t.done) ? 'am-pulse 1.5s ease-in-out infinite' : 'none',
              flexShrink: 0,
            }} />
            <span style={{ color: t.wait ? '#f5b84c' : 'var(--am-fg)' }}>{t.name}</span>
            <code style={{ fontFamily: 'var(--am-font-mono)', fontSize: 11, color: 'var(--am-mint-200)', background: 'var(--am-ink-200)', padding: '1px 5px', borderRadius: 3 }}>{t.arg}</code>
            <span style={{ marginLeft: 'auto', fontFamily: 'var(--am-font-mono)', fontSize: 10, color: 'var(--am-fg-subtle)' }}>{t.time}</span>
          </div>
        ))}
      </div>

      {/* actions */}
      <div style={{ padding: 12, borderTop: '1px solid var(--am-border)', display: 'flex', gap: 8 }}>
        <Button variant="secondary" icon="terminal" style={{ flex: 1, justifyContent: 'center' }}>Focus terminal</Button>
        <Button variant="danger" icon="x" onClick={onKill}>Kill</Button>
      </div>
    </div>
  );
}
Object.assign(window, { Inspector });
