import { useAgentMeshStore } from "../store";

export function MessageFlow() {
  const messages = useAgentMeshStore((s) => s.messages);
  if (messages.length === 0) return null;

  return (
    <section className="message-flow">
      <h4>Recent messages</h4>
      <ul>
        {messages.slice(0, 8).map((m) => (
          <li key={m.id} className={m.delivered ? "delivered" : "pending"}>
            <span className="from">{m.from}</span>
            <span className="arrow">→</span>
            <span className="to">{m.to}</span>
            <span className="scope">{m.scope}</span>
            <span className="summary">
              {m.paths_changed} change{m.paths_changed === 1 ? "" : "s"} · {m.bytes}B
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
