import { useAgentMeshStore } from "../store";

export function MetricsBar() {
  const m = useAgentMeshStore((s) => s.metrics);
  const saved = Math.round(m.estimated_tokens_saved_pct); // already 0..100

  return (
    <footer className="metrics-bar">
      <div className="metric">
        <span className="label">msgs</span>
        <span className="value">{m.messages_total}</span>
      </div>
      <div className="metric">
        <span className="label">conflicts</span>
        <span className="value">{m.conflicts_total}</span>
      </div>
      <div className="metric">
        <span className="label">bytes</span>
        <span className="value">{m.bytes_exchanged_total.toLocaleString()}</span>
      </div>
      <div className="metric saved">
        <span className="label">tokens saved</span>
        <span className="value">{saved}%</span>
      </div>
    </footer>
  );
}
