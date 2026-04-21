import { useAgentMeshStore } from "../store";

export function ConflictPanel() {
  const c = useAgentMeshStore((s) => s.activeConflict);
  if (!c) return null;

  const resolved = !!c.resolved;

  return (
    <section className={`conflict-panel ${resolved ? "resolved" : "active"}`}>
      <h4>
        {resolved ? "Resolved" : "Conflict"}: <code>{c.path}</code>
      </h4>
      <div className="values">
        {c.parties.map((p) => (
          <div
            key={p.agent_id}
            className={
              resolved
                ? c.resolved!.winner === p.agent_id
                  ? "side winner"
                  : "side loser"
                : "side"
            }
          >
            <strong>{p.agent_id}</strong>
            <span className="val">{JSON.stringify(p.value)}</span>
          </div>
        ))}
      </div>
      {resolved && (
        <div className="resolution">
          <strong>{c.resolved!.winner}</strong> wins — {c.resolved!.reason}
        </div>
      )}
    </section>
  );
}
