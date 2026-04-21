import * as vscode from "vscode";
import * as fs from "node:fs";
import * as path from "node:path";
import WebSocket from "ws";
import type { AgentMeshEvent } from "./types/events";

export type EventHandler = (e: AgentMeshEvent) => void;
type SourceMode = "auto" | "live" | "mock";

const BACKOFF_MS = [1000, 2000, 4000, 8000];

export class EventSource {
  private ws?: WebSocket;
  private reconnectAttempts = 0;
  private reconnectTimer?: NodeJS.Timeout;
  private handlers: EventHandler[] = [];
  private mockAbort = false;
  private disposed = false;

  private mode: SourceMode;
  private wsUrl: string;
  private mockPath: string;

  constructor(private ctx: vscode.ExtensionContext) {
    const cfg = vscode.workspace.getConfiguration("agentmesh");
    this.mode = (cfg.get<string>("source", "auto") as SourceMode) ?? "auto";
    this.wsUrl = cfg.get<string>("websocketUrl", "ws://localhost:9900");
    const rel = cfg.get<string>("mockEventsPath", "../mesh/mock_events.jsonl");
    const workspaceRoot =
      vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? ctx.extensionPath;
    this.mockPath = path.resolve(workspaceRoot, rel);
  }

  onEvent(h: EventHandler): void {
    this.handlers.push(h);
  }

  private emit(e: AgentMeshEvent): void {
    for (const h of this.handlers) {
      try {
        h(e);
      } catch (err) {
        console.warn("[AgentMesh] handler error", err);
      }
    }
  }

  async start(): Promise<void> {
    this.mockAbort = false;
    if (this.mode === "mock") {
      void this.runMockReplay();
      return;
    }
    this.connectLive();
  }

  private connectLive(): void {
    if (this.disposed) return;
    try {
      console.log(`[AgentMesh] WS connecting to ${this.wsUrl}`);
      this.ws = new WebSocket(this.wsUrl);
    } catch (err) {
      console.error("[AgentMesh] WS construct failed", err);
      this.onLiveFailed();
      return;
    }

    this.ws.on("open", () => {
      console.log("[AgentMesh] WS connected");
      this.reconnectAttempts = 0;
    });

    this.ws.on("message", (raw: WebSocket.RawData) => {
      try {
        const evt = JSON.parse(raw.toString("utf-8")) as AgentMeshEvent;
        this.emit(evt);
      } catch (err) {
        console.warn("[AgentMesh] malformed event", err);
      }
    });

    this.ws.on("close", () => {
      if (this.disposed || this.mode === "mock") return;
      if (this.mode === "auto" && this.reconnectAttempts === 0) {
        console.log("[AgentMesh] live unavailable, falling back to mock");
        void this.runMockReplay();
        return;
      }
      this.scheduleReconnect();
    });

    this.ws.on("error", (err: Error) => {
      console.log(`[AgentMesh] WS error: ${err.message}`);
    });
  }

  private onLiveFailed(): void {
    if (this.mode === "auto") {
      console.log("[AgentMesh] live setup failed, falling back to mock");
      void this.runMockReplay();
    } else {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.disposed) return;
    const d = BACKOFF_MS[Math.min(this.reconnectAttempts, BACKOFF_MS.length - 1)];
    this.reconnectAttempts++;
    console.log(`[AgentMesh] WS reconnect in ${d}ms (attempt ${this.reconnectAttempts})`);
    this.reconnectTimer = setTimeout(() => this.connectLive(), d);
  }

  private async runMockReplay(): Promise<void> {
    if (!fs.existsSync(this.mockPath)) {
      console.warn(`[AgentMesh] mock file not found at ${this.mockPath}`);
      return;
    }
    console.log(`[AgentMesh] replaying mock events from ${this.mockPath}`);
    let events: AgentMeshEvent[] = [];
    try {
      events = fs
        .readFileSync(this.mockPath, "utf-8")
        .split(/\r?\n/)
        .filter((l) => l.trim().length > 0)
        .map((l) => JSON.parse(l) as AgentMeshEvent);
    } catch (err) {
      console.error("[AgentMesh] failed to parse mock file", err);
      return;
    }
    if (events.length === 0) return;

    const startEventTs = new Date(events[0].ts).getTime();
    const startWall = Date.now();

    for (const evt of events) {
      if (this.mockAbort || this.disposed) return;
      const scenarioDelta = new Date(evt.ts).getTime() - startEventTs;
      const waitMs = Math.max(0, scenarioDelta - (Date.now() - startWall));
      if (waitMs > 0) {
        await new Promise((r) => setTimeout(r, waitMs));
      }
      if (this.mockAbort || this.disposed) return;
      this.emit(evt);
    }
    console.log("[AgentMesh] mock replay complete");
  }

  stop(): void {
    this.mockAbort = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = undefined;
    try {
      this.ws?.close();
    } catch {
      /* noop */
    }
    this.ws = undefined;
  }

  dispose(): void {
    this.disposed = true;
    this.stop();
  }
}
