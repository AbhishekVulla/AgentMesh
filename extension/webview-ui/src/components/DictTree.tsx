import { useState } from "react";
import { useAgentMeshStore } from "../store";

function Node({
  name,
  value,
  depth = 0,
}: {
  name: string;
  value: unknown;
  depth?: number;
}) {
  const [open, setOpen] = useState(depth < 2);
  const isObj =
    value !== null && typeof value === "object" && !Array.isArray(value);

  if (!isObj) {
    return (
      <div className="node leaf" style={{ paddingLeft: depth * 10 }}>
        <span className="key">{name}</span>
        <span className="sep">: </span>
        <span className="val">{JSON.stringify(value)}</span>
      </div>
    );
  }

  const keys = Object.keys(value as object);
  return (
    <div className="node branch" style={{ paddingLeft: depth * 10 }}>
      <span className="toggle" onClick={() => setOpen(!open)}>
        {open ? "▼" : "▶"}
      </span>
      <span className="key">{name}</span>
      {open && (
        <div className="children">
          {keys.map((k) => (
            <Node
              key={k}
              name={k}
              value={(value as Record<string, unknown>)[k]}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function DictTree() {
  const agents = useAgentMeshStore((s) => s.agents);
  const list = Object.values(agents);
  if (list.length === 0) return null;

  return (
    <section className="dict-tree-grid">
      {list.map((a) => {
        const keys = Object.keys(a.dict);
        return (
          <div key={a.id} className="dict-tree">
            <h4>{a.role}</h4>
            {keys.length === 0 ? (
              <em className="empty">empty</em>
            ) : (
              keys.map((k) => <Node key={k} name={k} value={a.dict[k]} />)
            )}
          </div>
        );
      })}
    </section>
  );
}
