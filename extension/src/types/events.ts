// TypeScript types mirroring mesh/schemas/events.py (pydantic v2).
// Schema v1.1 — flat envelope, UPPERCASE agent states.
// Authoritative source: https://github.com/AbhishekVulla/AgentMesh/blob/p1-backend/mesh/schemas/events.py

export type AgentState = "IDLE" | "WORKING" | "BLOCKED" | "COMPLETED";
export type MessagePriority = "low" | "normal" | "high";
export type ChangeOp = "add" | "modify" | "delete";
export type SessionEndReason = "completed" | "aborted" | "error";

export interface AgentDescriptor {
  id: string;
  role: string;
  exposes: string[];
}

export interface DictChange {
  path: string;
  op: ChangeOp;
  old: unknown;
  new: unknown;
}

export interface ConflictParty {
  agent_id: string;
  value: unknown;
}

export interface DiffSummary {
  paths_changed: number;
  bytes: number;
}

export interface SessionTotals {
  events_emitted: number;
  messages_routed: number;
  conflicts: number;
  bytes_exchanged: number;
  duration_ms: number;
}

interface BaseEnvelope {
  seq: number;
  ts: string;
  session_id: string;
}

export interface MeshSessionStarted extends BaseEnvelope {
  event: "mesh.session.started";
  agents: AgentDescriptor[];
  config_path: string;
}

export interface MeshSessionEnded extends BaseEnvelope {
  event: "mesh.session.ended";
  reason: SessionEndReason;
  totals: SessionTotals;
}

export interface AgentStateChanged extends BaseEnvelope {
  event: "agent.state.changed";
  agent_id: string;
  from: AgentState;
  to: AgentState;
  current_task?: string | null;
}

export interface DictMutated extends BaseEnvelope {
  event: "dict.mutated";
  agent_id: string;
  version: number;
  changes: DictChange[];
}

export interface MessageSent extends BaseEnvelope {
  event: "message.sent";
  message_id: string;
  from: string;
  to: string;
  scope: string;
  diff_summary: DiffSummary;
  priority?: MessagePriority;
  correlation_id?: string | null;
}

export interface MessageDelivered extends BaseEnvelope {
  event: "message.delivered";
  message_id: string;
  from: string;
  to: string;
  latency_ms: number;
}

export interface ConflictDetected extends BaseEnvelope {
  event: "conflict.detected";
  conflict_id: string;
  path: string;
  parties: ConflictParty[];
  incoming_message_id: string;
}

export interface ConflictResolved extends BaseEnvelope {
  event: "conflict.resolved";
  conflict_id: string;
  winner: string;
  loser: string;
  reason: string;
  resolution_message_id: string;
}

export interface MetricsTick extends BaseEnvelope {
  event: "metrics.tick";
  messages_total: number;
  conflicts_total: number;
  bytes_exchanged_total: number;
  estimated_tokens_saved_pct: number; // 0..100
}

export type AgentMeshEvent =
  | MeshSessionStarted
  | MeshSessionEnded
  | AgentStateChanged
  | DictMutated
  | MessageSent
  | MessageDelivered
  | ConflictDetected
  | ConflictResolved
  | MetricsTick;
