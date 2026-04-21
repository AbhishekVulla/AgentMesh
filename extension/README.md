# extension — AgentMesh VS Code Visualizer

Owner: **P2 (Abhi)**

The VS Code extension that visualizes live AgentMesh sessions.

## UI strategy

**MVP — AgentMesh overlay (sidebar activity-bar view).** A custom TypeScript + React webview that connects to `ws://localhost:9900` and renders:

- **Agent strip** — one card per agent (backend, frontend, database) with state badge (IDLE/WORKING/BLOCKED/COMPLETED), current task, and token indicator
- **Dictionary store tree** per agent, live-updating on `dict.mutated`
- **Message flow** — animated courier orbs between agent cards on `message.sent`/`message.delivered`
- **Conflict panel** — slides in on `conflict.detected`, shows both values + priority-table rationale, clears green on `conflict.resolved`
- **Metrics bar** — messages, conflicts, bytes, estimated token-savings %

**Stretch — pixel-agents shim.** If Day 4 has buffer, P2 writes synthetic Claude Code JSONL records to the Claude Code project directory (`~/.claude/projects/{workspace-hash}/*.jsonl` on macOS/Linux, or the Windows equivalent under `%USERPROFILE%\.claude\`) so the separately-installed `pablodelucca/pixel-agents` extension renders 3 pixel characters in the bottom panel during the scenario. This is visual bonus, not a core demo dependency.

After reviewing pixel-agents v1.3.0 source: it uses a dual-mode detection (Claude Code Hooks API preferred, 500ms JSONL polling fallback) and expects real Claude Code transcript records (`type: 'assistant'` with `message.content` array containing `tool_use` blocks using recognized tool names like Read/Edit/Write/Bash/Grep/Task). The shim must produce that format exactly.

The extension **does not fork or modify pixel-agents.** If the shim is built, pixel-agents runs as shipped from the Marketplace.

## Layout

```
extension/
├── package.json            # vsce manifest + contributes.viewsContainers.activitybar
├── tsconfig.json
├── esbuild.mjs              # bundle extension.ts + webview
├── src/
│   ├── extension.ts         # activation, webview registration
│   ├── ws_client.ts         # WebSocket client, reconnect backoff
│   ├── session_store.ts     # event log → webview bridge
│   └── types/events.ts      # mirrors mesh/schemas/events.schema.json
├── webview-ui/              # React app, bundled separately
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── AgentStrip.tsx
│       ├── DictTree.tsx
│       ├── MessageFlow.tsx
│       ├── ConflictPanel.tsx
│       ├── MetricsBar.tsx
│       └── store.ts          # Zustand
└── media/
```

## References

- [../docs/WEBSOCKET_SCHEMA.md](../docs/WEBSOCKET_SCHEMA.md) — event contract (must match exactly)
- [../docs/DEMO_SCENARIO.md](../docs/DEMO_SCENARIO.md) — what the overlay must show
- [pablodelucca/pixel-agents](https://github.com/pablodelucca/pixel-agents) — upstream visualizer, stretch-integration target
