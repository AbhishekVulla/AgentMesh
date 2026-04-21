// TypeScript types mirroring docs/WEBSOCKET_SCHEMA.md v1.0.
// Keep in sync with mesh/schemas/events.py. Manual mirror — no codegen in MVP.

export type AgentState = "idle" | "working" | "blocked" | "completed";
export type MessageType = "state_update" | "request" | "response" | "signal";
export type MessagePriority = "blocking" | "high" | "normal" | "low";
export type ChangeOp = "add" | "modify" | "delete";

export interface AgentDescriptor {
  id: string;
  domain: string;
  display_name: string;
}

export interface SessionStartedData {
  agents: AgentDescriptor[];
  dependency_map_hash: string;
}

export interface SessionEndedData {
  duration_ms: number;
  totals: {
    messages: number;
    conflicts_detected: number;
    conflicts_resolved: number;
    dict_mutations: number;
    bytes_exchanged: number;
    estimated_tokens_saved_pct: number;
  };
}

export interface AgentStateChangedData {
  agent_id: string;
  old_state: AgentState;
  new_state: AgentState;
  current_task?: string;
}

export interface DictChange {
  path: string;
  op: ChangeOp;
  old: unknown;
  new: unknown;
}

export interface DictMutatedData {
  agent_id: string;
  version_from: number;
  version_to: number;
  changes: DictChange[];
}

export interface MessageSentData {
  message_id: string;
  from: string;
  to: string;
  type: MessageType;
  priority: MessagePriority;
  scope: string;
  summary: string;
  size_bytes: number;
}

export interface MessageDeliveredData {
  message_id: string;
  to: string;
  processing_ms: number;
}

export interface ConflictSide {
  value: unknown;
  version: number;
  reason: string;
}

export interface ConflictDetectedData {
  conflict_id: string;
  key_path: string;
  agents: string[];
  values: Record<string, ConflictSide>;
  strategy: string;
}

export interface ConflictResolvedData {
  conflict_id: string;
  winner: string;
  loser: string;
  applied_value: unknown;
  follow_up_message_id: string;
  rationale: string;
}

export interface MetricsTickData {
  messages_sent: number;
  messages_delivered: number;
  conflicts_open: number;
  conflicts_resolved_total: number;
  dict_mutations_total: number;
  bytes_exchanged: number;
  estimated_tokens_saved_pct: number;
}

interface Envelope<T extends string, D> {
  event: T;
  v: "1.0";
  seq: number;
  ts: string;
  session_id: string;
  data: D;
}

export type AgentMeshEvent =
  | Envelope<"mesh.session.started", SessionStartedData>
  | Envelope<"mesh.session.ended", SessionEndedData>
  | Envelope<"agent.state.changed", AgentStateChangedData>
  | Envelope<"dict.mutated", DictMutatedData>
  | Envelope<"message.sent", MessageSentData>
  | Envelope<"message.delivered", MessageDeliveredData>
  | Envelope<"conflict.detected", ConflictDetectedData>
  | Envelope<"conflict.resolved", ConflictResolvedData>
  | Envelope<"metrics.tick", MetricsTickData>;
