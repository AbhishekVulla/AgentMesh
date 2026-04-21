import { useAgentMeshStore } from "../store";

export function AgentStrip() {
  const agents = useAgentMeshStore((s) => s.agents);
  const list = Object.values(agents);

  if (list.length === 0) {
    return <div className="empty">Waiting for a session…</div>;
  }

  return (
    <section className="agent-strip">
      {list.map((a) => (
        <div key={a.id} className={`agent-card state-${a.state.toLowerCase()}`}>
          <div className="agent-head">
            <span className="agent-name">{a.role}</span>
            <span className={`state-badge ${a.state.toLowerCase()}`}>{a.state}</span>
          </div>
          <div className="agent-domain">{a.id}</div>
          {a.current_task && <div className="current-task">{a.current_task}</div>}
        </div>
      ))}
    </section>
  );
}
