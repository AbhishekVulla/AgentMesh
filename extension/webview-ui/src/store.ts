import { create } from "zustand";
import type { AgentMeshEvent, AgentState, ConflictSide } from "./types/events";

interface AgentInfo {
  id: string;
  domain: string;
  display_name: string;
  state: AgentState;
  current_task?: string;
  dict: Record<string, unknown>;
}

interface MessageInfo {
  id: string;
  from: string;
  to: string;
  scope: string;
  summary: string;
  ts: string;
  delivered: boolean;
}

interface ConflictInfo {
  conflict_id: string;
  key_path: string;
  agents: string[];
  values: Record<string, ConflictSide>;
  resolved?: { winner: string; loser: string; rationale: string };
}

interface Metrics {
  messages_sent: number;
  messages_delivered: number;
  conflicts_resolved_total: number;
  bytes_exchanged: number;
  estimated_tokens_saved_pct: number;
}

interface State {
  sessionId: string | null;
  agents: Record<string, AgentInfo>;
  messages: MessageInfo[];
  activeConflict: ConflictInfo | null;
  metrics: Metrics;
  ended: boolean;
  applyEvent: (e: AgentMeshEvent) => void;
}

const emptyMetrics: Metrics = {
  messages_sent: 0,
  messages_delivered: 0,
  conflicts_resolved_total: 0,
  bytes_exchanged: 0,
  estimated_tokens_saved_pct: 0,
};

function splitPath(path: string): string[] {
  // Dot-separated segments. Route paths like "/api/users" are preserved because
  // they don't contain a dot at the segment-boundary position.
  return path.split(".");
}

function setPath(obj: Record<string, unknown>, path: string, val: unknown) {
  const parts = splitPath(path);
  let cur: Record<string, unknown> = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const p = parts[i];
    const existing = cur[p];
    if (typeof existing !== "object" || existing === null || Array.isArray(existing)) {
      cur[p] = {};
    }
    cur = cur[p] as Record<string, unknown>;
  }
  cur[parts[parts.length - 1]] = val;
}

function deletePath(obj: Record<string, unknown>, path: string) {
  const parts = splitPath(path);
  let cur: Record<string, unknown> = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const p = parts[i];
    const existing = cur[p];
    if (typeof existing !== "object" || existing === null || Array.isArray(existing)) return;
    cur = existing as Record<string, unknown>;
  }
  delete cur[parts[parts.length - 1]];
}

export const useAgentMeshStore = create<State>((set, get) => ({
  sessionId: null,
  agents: {},
  messages: [],
  activeConflict: null,
  metrics: emptyMetrics,
  ended: false,
  applyEvent: (e) => {
    switch (e.event) {
      case "mesh.session.started":
        set({
          sessionId: e.session_id,
          agents: Object.fromEntries(
            e.data.agents.map((a) => [
              a.id,
              {
                id: a.id,
                domain: a.domain,
                display_name: a.display_name,
                state: "idle" as AgentState,
                dict: {},
              },
            ]),
          ),
          messages: [],
          activeConflict: null,
          metrics: emptyMetrics,
          ended: false,
        });
        break;

      case "mesh.session.ended":
        set({ ended: true });
        break;

      case "agent.state.changed": {
        const a = get().agents[e.data.agent_id];
        if (!a) return;
        set({
          agents: {
            ...get().agents,
            [e.data.agent_id]: {
              ...a,
              state: e.data.new_state,
              current_task: e.data.current_task ?? a.current_task,
            },
          },
        });
        break;
      }

      case "dict.mutated": {
        const a = get().agents[e.data.agent_id];
        if (!a) return;
        const newDict = structuredClone(a.dict);
        for (const ch of e.data.changes) {
          if (ch.op === "delete") deletePath(newDict, ch.path);
          else setPath(newDict, ch.path, ch.new);
        }
        set({ agents: { ...get().agents, [e.data.agent_id]: { ...a, dict: newDict } } });
        break;
      }

      case "message.sent":
        set({
          messages: [
            {
              id: e.data.message_id,
              from: e.data.from,
              to: e.data.to,
              scope: e.data.scope,
              summary: e.data.summary,
              ts: e.ts,
              delivered: false,
            },
            ...get().messages,
          ].slice(0, 50),
        });
        break;

      case "message.delivered":
        set({
          messages: get().messages.map((m) =>
            m.id === e.data.message_id ? { ...m, delivered: true } : m,
          ),
        });
        break;

      case "conflict.detected":
        set({
          activeConflict: {
            conflict_id: e.data.conflict_id,
            key_path: e.data.key_path,
            agents: e.data.agents,
            values: e.data.values,
          },
        });
        break;

      case "conflict.resolved": {
        const c = get().activeConflict;
        if (c && c.conflict_id === e.data.conflict_id) {
          set({
            activeConflict: {
              ...c,
              resolved: {
                winner: e.data.winner,
                loser: e.data.loser,
                rationale: e.data.rationale,
              },
            },
          });
          // Auto-dismiss 2s after resolution.
          setTimeout(() => {
            const cur = get().activeConflict;
            if (cur && cur.conflict_id === e.data.conflict_id) {
              set({ activeConflict: null });
            }
          }, 2000);
        }
        break;
      }

      case "metrics.tick":
        set({
          metrics: {
            messages_sent: e.data.messages_sent,
            messages_delivered: e.data.messages_delivered,
            conflicts_resolved_total: e.data.conflicts_resolved_total,
            bytes_exchanged: e.data.bytes_exchanged,
            estimated_tokens_saved_pct: e.data.estimated_tokens_saved_pct,
          },
        });
        break;
    }
  },
}));
