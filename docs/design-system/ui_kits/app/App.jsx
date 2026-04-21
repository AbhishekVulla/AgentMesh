// App.jsx — AgentMesh top-level

const { useState, useEffect, useCallback } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "movement": true,
  "chatiness": 0.5,
  "speed": 1.0,
  "showDesks": true
}/*EDITMODE-END*/;

const SEED = [
  { id: 1, name: 'orchestrator', model: 'sonnet-4-5', status: 'working', tool: 'Edit App.tsx', tokens: 92, parentId: null,
    tools: [
      { name: 'Read', arg: 'src/App.tsx', time: '1.2s', done: true },
      { name: 'Grep', arg: 'useEffect', time: '0.9s', done: true },
      { name: 'Edit', arg: 'src/App.tsx:42', time: '3.8s', done: false },
    ] },
  { id: 2, name: 'researcher', model: 'haiku-4-5', status: 'thinking', tool: '', tokens: 44, parentId: 1,
    tools: [ { name: 'Read', arg: 'docs/guide.md', time: '0.3s', done: true } ] },
  { id: 3, name: 'tests', model: 'sonnet-4-5', status: 'waiting', tool: 'Bash npm test', tokens: 128, parentId: null,
    tools: [
      { name: 'Read', arg: 'package.json', time: '0.4s', done: true },
      { name: 'Bash', arg: 'npm test', time: 'waiting', done: false, wait: true },
    ] },
  { id: 4, name: 'formatter', model: 'haiku-4-5', status: 'idle', tool: '', tokens: 12, parentId: null,
    tools: [ { name: 'Write', arg: '.prettierrc', time: '0.2s', done: true } ] },
  { id: 5, name: 'reviewer', model: 'sonnet-4-5', status: 'working', tool: 'Grep', tokens: 76, parentId: 1,
    tools: [
      { name: 'Read', arg: 'src/hooks/', time: '0.8s', done: true },
      { name: 'Grep', arg: 'TODO|FIXME', time: '0.5s', done: false },
    ] },
];

function App() {
  const [agents, setAgents] = useState(SEED);
  const [selectedId, setSelectedId] = useState(1);
  const [view, setView] = useState('mesh');
  const [commandOpen, setCommandOpen] = useState(false);
  const [tweaksOn, setTweaksOn] = useState(false);
  const [settings, setSettings] = useState(TWEAK_DEFAULTS);

  const updateSettings = useCallback((partial) => {
    setSettings(prev => {
      const next = { ...prev, ...partial };
      try {
        window.parent.postMessage({ type: '__edit_mode_set_keys', edits: partial }, '*');
      } catch {}
      return next;
    });
  }, []);

  const selected = agents.find(a => a.id === selectedId);

  const addAgent = useCallback(() => {
    setAgents(prev => {
      const id = Math.max(...prev.map(a => a.id)) + 1;
      return [...prev, {
        id, name: `agent-${id}`, model: 'sonnet-4-5',
        status: 'thinking', tool: '', tokens: 8, parentId: null,
        tools: [{ name: 'Read', arg: 'README.md', time: '0.3s', done: false }],
      }];
    });
  }, []);

  const killAgent = useCallback(() => {
    setAgents(prev => prev.filter(a => a.id !== selectedId));
    setSelectedId(null);
  }, [selectedId]);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); setCommandOpen(v => !v); }
      if (e.key === 'Escape') setCommandOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    const onMsg = (e) => {
      const d = e.data;
      if (!d || !d.type) return;
      if (d.type === '__activate_edit_mode') setTweaksOn(true);
      if (d.type === '__deactivate_edit_mode') setTweaksOn(false);
    };
    window.addEventListener('message', onMsg);
    try { window.parent.postMessage({ type: '__edit_mode_available' }, '*'); } catch {}
    return () => window.removeEventListener('message', onMsg);
  }, []);

  useEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  const handleCommand = (cmd) => {
    if (cmd === 'spawn' || cmd === 'spawn-haiku') addAgent();
    if (cmd === 'focus') {
      const w = agents.find(a => a.status === 'waiting');
      if (w) setSelectedId(w.id);
    }
    if (cmd === 'kill') setAgents(prev => prev.filter(a => a.status !== 'idle'));
  };

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', background: 'var(--am-bg)' }}>
      <LeftRail view={view} onView={setView} />
      <div style={{ flex: 1, position: 'relative' }}>
        <OfficeCanvas agents={agents} selectedId={selectedId} onSelect={setSelectedId} settings={settings} />
        <BottomToolbar onAddAgent={addAgent} onCommand={() => setCommandOpen(true)} agentsCount={agents.length} />
        <CommandBar open={commandOpen} onClose={() => setCommandOpen(false)} onRun={handleCommand} />
        <TweaksPanel visible={tweaksOn} settings={settings} onChange={updateSettings} />
        {/* Top-right live counter */}
        <div style={{
          position: 'absolute', top: 14, right: selected ? 354 : 14, zIndex: 10,
          background: 'rgba(15,19,28,0.85)', backdropFilter: 'blur(12px) saturate(1.2)',
          border: '1px solid var(--am-border-strong)', borderRadius: 10,
          padding: '8px 12px', display: 'flex', gap: 14, alignItems: 'center',
          fontFamily: 'var(--am-font-mono)', fontSize: 11,
          boxShadow: 'var(--am-shadow-sm)',
        }}>
          <span style={{ color: 'var(--am-fg-subtle)', letterSpacing: '.08em', textTransform: 'uppercase', fontSize: 10 }}>Live</span>
          <span style={{ color: '#1fd08a' }}>{agents.filter(a=>a.status==='working').length} working</span>
          <span style={{ color: '#7a8cff' }}>{agents.filter(a=>a.status==='thinking').length} thinking</span>
          <span style={{ color: '#f5b84c' }}>{agents.filter(a=>a.status==='waiting').length} waiting</span>
        </div>
      </div>
      {selected && <Inspector agent={selected} onClose={() => setSelectedId(null)} onKill={killAgent} />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
