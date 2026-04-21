import { create } from "zustand";
import type { AgentMeshEvent, AgentState, ConflictParty } from "./types/events";

interface AgentInfo {
  id: string;
  role: string;
  exposes: string[];
  state: AgentState;
  current_task?: string | null;
  dict: Record<string, unknown>;
}

interface MessageInfo {
  id: string;
  from: string;
  to: string;
  scope: string;
  bytes: number;
  paths_changed: number;
  ts: string;
  delivered: boolean;
}

interface ConflictInfo {
  conflict_id: string;
  path: string;
  parties: ConflictParty[];
  incoming_message_id: string;
  resolved?: {
    winner: string;
    loser: string;
    reason: string;
  };
}

interface Metrics {
  messages_total: number;
  conflicts_total: number;
  bytes_exchanged_total: number;
  estimated_tokens_saved_pct: number; // 0..100
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
  messages_total: 0,
  conflicts_total: 0,
  bytes_exchanged_total: 0,
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
            e.agents.map((a) => [
              a.id,
              {
                id: a.id,
                role: a.role,
                exposes: a.exposes,
                state: "IDLE" as AgentState,
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
        const a = get().agents[e.agent_id];
        if (!a) return;
        set({
          agents: {
            ...get().agents,
            [e.agent_id]: {
              ...a,
              state: e.to,
              current_task: e.current_task ?? a.current_task,
            },
          },
        });
        break;
      }

      case "dict.mutated": {
        const a = get().agents[e.agent_id];
        if (!a) return;
        const newDict = structuredClone(a.dict);
        for (const ch of e.changes) {
          if (ch.op === "delete") deletePath(newDict, ch.path);
          else setPath(newDict, ch.path, ch.new);
        }
        set({ agents: { ...get().agents, [e.agent_id]: { ...a, dict: newDict } } });
        break;
      }

      case "message.sent":
        set({
          messages: [
            {
              id: e.message_id,
              from: e.from,
              to: e.to,
              scope: e.scope,
              bytes: e.diff_summary.bytes,
              paths_changed: e.diff_summary.paths_changed,
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
            m.id === e.message_id ? { ...m, delivered: true } : m,
          ),
        });
        break;

      case "conflict.detected":
        set({
          activeConflict: {
            conflict_id: e.conflict_id,
            path: e.path,
            parties: e.parties,
            incoming_message_id: e.incoming_message_id,
          },
        });
        break;

      case "conflict.resolved": {
        const c = get().activeConflict;
        if (c && c.conflict_id === e.conflict_id) {
          set({
            activeConflict: {
              ...c,
              resolved: {
                winner: e.winner,
                loser: e.loser,
                reason: e.reason,
              },
            },
          });
          setTimeout(() => {
            const cur = get().activeConflict;
            if (cur && cur.conflict_id === e.conflict_id) {
              set({ activeConflict: null });
            }
          }, 2500);
        }
        break;
      }

      case "metrics.tick":
        set({
          metrics: {
            messages_total: e.messages_total,
            conflicts_total: e.conflicts_total,
            bytes_exchanged_total: e.bytes_exchanged_total,
            estimated_tokens_saved_pct: e.estimated_tokens_saved_pct,
          },
        });
        break;
    }
  },
}));
