import { useAgentMeshStore } from "../store";

export function ConflictPanel() {
  const c = useAgentMeshStore((s) => s.activeConflict);
  if (!c) return null;

  const resolved = !!c.resolved;

  return (
    <section className={`conflict-panel ${resolved ? "resolved" : "active"}`}>
      <h4>
        {resolved ? "Resolved" : "Conflict"}: <code>{c.key_path}</code>
      </h4>
      <div className="values">
        {Object.entries(c.values).map(([agent, v]) => (
          <div
            key={agent}
            className={
              resolved
                ? c.resolved!.winner === agent
                  ? "side winner"
                  : "side loser"
                : "side"
            }
          >
            <strong>{agent}</strong>
            <span className="val">{JSON.stringify(v.value)}</span>
            <span className="reason">{v.reason}</span>
          </div>
        ))}
      </div>
      {resolved && (
        <div className="resolution">
          <strong>{c.resolved!.winner}</strong> wins — {c.resolved!.rationale}
        </div>
      )}
    </section>
  );
}
