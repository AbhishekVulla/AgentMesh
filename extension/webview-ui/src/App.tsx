import { useEffect } from "react";
import { useAgentMeshStore } from "./store";
import { AgentStrip } from "./components/AgentStrip";
import { DictTree } from "./components/DictTree";
import { MessageFlow } from "./components/MessageFlow";
import { ConflictPanel } from "./components/ConflictPanel";
import { MetricsBar } from "./components/MetricsBar";

export function App() {
  const applyEvent = useAgentMeshStore((s) => s.applyEvent);
  const sessionId = useAgentMeshStore((s) => s.sessionId);

  useEffect(() => {
    function handler(e: MessageEvent) {
      const msg = e.data as { kind?: string; evt?: unknown };
      if (msg && msg.kind === "event" && msg.evt) {
        applyEvent(msg.evt as Parameters<typeof applyEvent>[0]);
      }
    }
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [applyEvent]);

  return (
    <div className="agentmesh-app">
      <header className="app-header">
        <span className="app-title">AgentMesh</span>
        <span className="session-id">{sessionId ?? "waiting for session"}</span>
      </header>
      <AgentStrip />
      <MessageFlow />
      <DictTree />
      <ConflictPanel />
      <MetricsBar />
    </div>
  );
}
