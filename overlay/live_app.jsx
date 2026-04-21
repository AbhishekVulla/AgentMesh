// live_app.jsx — AgentMesh overlay wired to the real event bus.
//
// Mirrors the structure of docs/design-system/ui_kits/app/App.jsx but the
// state comes from AgentMeshLive.connect() instead of a SEED constant.
// Depends on the same UI primitives: LeftRail, BottomToolbar, MeshCanvas,
// Inspector, CommandBar.

const { useState, useEffect, useMemo, useCallback } = React;

function useMeshLive(url) {
  const [state, setState] = useState(() => window.AgentMeshLive.initialState());
  useEffect(() => {
    const client = window.AgentMeshLive.connect(url, setState);
    return () => client.close();
  }, [url]);
  return state;
}

function StatusDot({ connected }) {
  const color = connected ? "#1fd08a" : "#ff5d6b";
  const label = connected ? "Live" : "Disconnected";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{
        width: 8, height: 8, borderRadius: 999, background: color,
        boxShadow: connected ? `0 0 0 3px ${color}22` : "none",
        animation: connected ? "am-pulse 1.5s ease-in-out infinite" : "none",
      }} />
      <span style={{ color: "var(--am-fg-subtle)", fontSize: 11, fontFamily: "var(--am-font-mono)", textTransform: "uppercase", letterSpacing: ".08em" }}>
        {label}
      </span>
    </span>
  );
}

function MetricsBar({ metrics, sessionId, connected }) {
  return (
    <div style={{
      position: "absolute", top: 14, left: 14, zIndex: 10,
      background: "rgba(15,19,28,0.85)", backdropFilter: "blur(12px) saturate(1.2)",
      border: "1px solid var(--am-border-strong)", borderRadius: 10,
      padding: "8px 12px", display: "flex", gap: 14, alignItems: "center",
      fontFamily: "var(--am-font-mono)", fontSize: 11,
      boxShadow: "var(--am-shadow-sm)",
    }}>
      <StatusDot connected={connected} />
      <span style={{ color: "var(--am-fg-subtle)" }}>·</span>
      <span style={{ color: "#1fd08a" }}>{metrics.messages} messages</span>
      <span style={{ color: "#f5b84c" }}>{metrics.conflicts} conflicts</span>
      <span style={{ color: "#7a8cff" }}>{metrics.bytes}B</span>
      <span style={{ color: "var(--am-fg-subtle)" }}>·</span>
      <span style={{ color: "#1fd08a" }}>{metrics.saved ? metrics.saved.toFixed(1) : "0.0"}% saved</span>
      <span style={{ color: "var(--am-fg-subtle)" }}>·</span>
      <span style={{ color: "var(--am-fg-subtle)" }}>{sessionId ? sessionId.slice(0, 16) : "no session"}</span>
    </div>
  );
}

function ConflictCard({ conflict, resolution }) {
  if (!conflict) return null;
  const resolved = conflict.resolved;
  const winner = resolved ? conflict.winner : null;
  return (
    <div style={{
      position: "absolute", top: 60, right: 14, zIndex: 10,
      width: 320,
      background: "rgba(15,19,28,0.95)",
      border: `1px solid ${resolved ? "#1fd08a" : "#f5b84c"}`,
      borderRadius: 10, padding: 14,
      boxShadow: "var(--am-shadow-md)", fontSize: 12,
    }}>
      <div style={{
        fontFamily: "var(--am-font-mono)", fontSize: 10,
        letterSpacing: ".08em", textTransform: "uppercase",
        color: resolved ? "#1fd08a" : "#f5b84c", marginBottom: 6,
      }}>
        {resolved ? "Resolved" : "Conflict detected"}
      </div>
      <div style={{ fontFamily: "var(--am-font-mono)", fontSize: 11, marginBottom: 8, color: "var(--am-fg)" }}>
        {conflict.path}
      </div>
      <div style={{ display: "grid", gap: 6 }}>
        {conflict.parties.map(p => (
          <div key={p.agent_id} style={{
            display: "flex", justifyContent: "space-between",
            padding: "6px 8px", borderRadius: 6,
            background: winner === p.agent_id ? "#1b2a24" : "rgba(255,255,255,0.02)",
            border: winner === p.agent_id ? "1px solid #1fd08a" : "1px solid transparent",
          }}>
            <span style={{ fontFamily: "var(--am-font-mono)" }}>{p.agent_id}</span>
            <span style={{ fontFamily: "var(--am-font-mono)", color: "var(--am-fg-subtle)" }}>
              {JSON.stringify(p.value)}
            </span>
          </div>
        ))}
      </div>
      {resolved && (
        <div style={{ marginTop: 8, fontSize: 11, color: "var(--am-fg-subtle)" }}>
          {conflict.reason}
        </div>
      )}
    </div>
  );
}

function EmptyState({ connected }) {
  return (
    <div style={{
      position: "absolute", inset: 0, display: "flex",
      alignItems: "center", justifyContent: "center",
      flexDirection: "column", gap: 10, pointerEvents: "none",
    }}>
      <div style={{
        fontFamily: "'Instrument Serif', serif", fontStyle: "italic",
        fontSize: 34, color: "var(--am-fg)",
      }}>
        Waiting for agents
      </div>
      <div style={{ color: "var(--am-fg-subtle)", fontSize: 13 }}>
        {connected
          ? "Connected — no session has started yet."
          : "Not connected. Start: python -m mesh.run --config demo/config.yaml"}
      </div>
    </div>
  );
}

// Default OfficeCanvas settings (mirrors docs/design-system/ui_kits/app/App.jsx TWEAK_DEFAULTS).
const DEFAULT_SETTINGS = {
  movement: true,
  chatiness: 0.6,
  speed: 1.0,
  showDesks: true,
};

const DEMO_ROLES = ["researcher", "tests", "formatter", "reviewer", "orchestrator"];
const DEMO_STATUSES = ["working", "thinking", "waiting", "idle"];
const DEMO_MODELS = ["sonnet-4-5", "haiku-4-5"];
const DEMO_TOOLS = [
  { name: "Read", arg: "README.md" },
  { name: "Grep", arg: "useEffect" },
  { name: "Edit", arg: "src/App.tsx:42" },
  { name: "Bash", arg: "npm test" },
  { name: "Write", arg: ".prettierrc" },
];

function LiveCounter({ agents, selected }) {
  const working = agents.filter(a => a.status === "working").length;
  const thinking = agents.filter(a => a.status === "thinking").length;
  const waiting = agents.filter(a => a.status === "waiting").length;
  return (
    <div style={{
      position: "absolute", top: 14, right: selected ? 354 : 14, zIndex: 10,
      background: "rgba(15,19,28,0.85)", backdropFilter: "blur(12px) saturate(1.2)",
      border: "1px solid var(--am-border-strong)", borderRadius: 10,
      padding: "8px 12px", display: "flex", gap: 14, alignItems: "center",
      fontFamily: "var(--am-font-mono)", fontSize: 11,
      boxShadow: "var(--am-shadow-sm)",
    }}>
      <span style={{ color: "var(--am-fg-subtle)", letterSpacing: ".08em", textTransform: "uppercase", fontSize: 10 }}>Live</span>
      <span style={{ color: "#1fd08a" }}>{working} working</span>
      <span style={{ color: "#7a8cff" }}>{thinking} thinking</span>
      <span style={{ color: "#f5b84c" }}>{waiting} waiting</span>
    </div>
  );
}

function App() {
  const url = new URLSearchParams(location.search).get("ws") || "ws://localhost:9900";
  const live = useMeshLive(url);
  const [selectedId, setSelectedId] = useState(null);
  const [localAgents, setLocalAgents] = useState([]);
  // "office" = pixel-desk canvas (default — matches the design-system demo).
  // "mesh"   = force-directed graph (legacy dots view).
  const [view, setView] = useState("office");
  const [commandOpen, setCommandOpen] = useState(false);
  const [tweaksOn, setTweaksOn] = useState(false);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);

  const updateSettings = useCallback((partial) => {
    setSettings(prev => ({ ...prev, ...partial }));
  }, []);

  // Merge live (backend-driven) agents with locally-spawned demo agents.
  const allAgents = useMemo(
    () => [...live.agents, ...localAgents],
    [live.agents, localAgents]
  );

  const spawnLocalAgent = useCallback(() => {
    setLocalAgents(prev => {
      const idx = prev.length;
      const role = DEMO_ROLES[idx % DEMO_ROLES.length];
      const status = DEMO_STATUSES[idx % DEMO_STATUSES.length];
      const model = DEMO_MODELS[idx % DEMO_MODELS.length];
      const tool = DEMO_TOOLS[idx % DEMO_TOOLS.length];
      return [...prev, {
        id: `local-${Date.now()}-${idx}`,
        name: role,
        role,
        model,
        status,
        tool: `${tool.name} ${tool.arg}`,
        tokens: Math.floor(20 + Math.random() * 120),
        tools: [
          { name: tool.name, arg: tool.arg, time: `${(0.2 + Math.random()).toFixed(1)}s`, done: false },
        ],
      }];
    });
  }, []);

  const killAgent = useCallback((id) => {
    const target = id ?? selectedId;
    if (!target) return;
    setLocalAgents(prev => prev.filter(a => a.id !== target));
    setSelectedId(curr => (curr === target ? null : curr));
  }, [selectedId]);

  const handleCommand = useCallback((cmd) => {
    if (cmd === "spawn" || cmd === "spawn-haiku") {
      spawnLocalAgent();
    } else if (cmd === "focus") {
      const w = allAgents.find(a => a.status === "waiting");
      if (w) setSelectedId(w.id);
    } else if (cmd === "kill") {
      setLocalAgents(prev => prev.filter(a => a.status !== "idle"));
    }
  }, [allAgents, spawnLocalAgent]);

  // pick the selected agent by agent.id string (design system uses numeric
  // ids; we use the string id directly).
  const selected = useMemo(
    () => allAgents.find(a => a.id === selectedId) || null,
    [allAgents, selectedId]
  );

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); setCommandOpen(v => !v); }
      if ((e.metaKey || e.ctrlKey) && e.key === ",") { e.preventDefault(); setTweaksOn(v => !v); }
      if (e.key === "Escape") { setCommandOpen(false); setSelectedId(null); setTweaksOn(false); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => { if (window.lucide) window.lucide.createIcons(); });

  // Adapt live state to the shape MeshCanvas expects (numeric id).
  const agentsForCanvas = useMemo(() => allAgents.map((a, i) => ({
    ...a,
    id: i + 1,
    _meshId: a.id,
    parentId: null,
  })), [allAgents]);

  const onSelectCanvas = useCallback((numericId) => {
    const a = agentsForCanvas.find(x => x.id === numericId);
    if (a) setSelectedId(a._meshId);
  }, [agentsForCanvas]);

  const canvasSelectedId = selected ? agentsForCanvas.findIndex(a => a._meshId === selected.id) + 1 : null;

  return (
    <div style={{ display: "flex", width: "100vw", height: "100vh", background: "var(--am-bg)" }}>
      <LeftRail view={view} onView={setView} />
      <div style={{ flex: 1, position: "relative" }}>
        {view === "office" ? (
          <OfficeCanvas
            agents={agentsForCanvas}
            selectedId={canvasSelectedId}
            onSelect={onSelectCanvas}
            settings={settings}
          />
        ) : (
          <MeshCanvas
            agents={agentsForCanvas}
            selectedId={canvasSelectedId}
            onSelect={onSelectCanvas}
          />
        )}
        {allAgents.length === 0 && <EmptyState connected={live.connected} />}
        <MetricsBar metrics={live.metrics} sessionId={live.sessionId} connected={live.connected} />
        <LiveCounter agents={allAgents} selected={selected} />
        <ConflictCard conflict={live.conflict} resolution={live.recentResolution} />
        <BottomToolbar
          onAddAgent={spawnLocalAgent}
          onCommand={() => setCommandOpen(true)}
          agentsCount={allAgents.length}
        />
        <CommandBar open={commandOpen} onClose={() => setCommandOpen(false)} onRun={handleCommand} />
        <TweaksPanel visible={tweaksOn} settings={settings} onChange={updateSettings} />
      </div>
      {selected && (
        <Inspector
          agent={{
            id: selected.id,
            name: selected.name,
            model: selected.model || selected.role || "mesh",
            status: selected.status,
            tool: selected.tool || "",
            tokens: selected.tokens || 0,
            tools: (selected.tools || []).map(t => ({
              name: t.name, arg: t.arg, time: t.time || "now", done: !!t.done,
            })),
          }}
          onClose={() => setSelectedId(null)}
          onKill={() => killAgent(selected.id)}
        />
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
