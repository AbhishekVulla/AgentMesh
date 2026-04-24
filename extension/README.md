# extension — AgentMesh VS Code Visualizer

VS Code extension that visualizes live AgentMesh sessions. Connects to `ws://localhost:9900` and renders a sidebar activity-bar webview with the protocol state.

## UI

- **Agent strip** — one card per agent with state badge (IDLE/WORKING/BLOCKED/COMPLETED), current task, and dictionary tree
- **Recent messages feed** — routed diffs showing `from → to`, scope path, change count, byte size
- **Conflict panel** — slides in on `conflict.detected`, shows both values + resolution rule, clears green on `conflict.resolved`
- **Metrics strip** — messages, conflicts, bytes exchanged, estimated token-savings %

## Layout

```
extension/
├── package.json              # manifest + contributes.viewsContainers.activitybar
├── tsconfig.json
├── esbuild.mjs               # bundle extension.ts + webview
├── src/
│   ├── extension.ts          # activation, webview registration
│   ├── ws_client.ts          # WebSocket client with reconnect backoff
│   ├── session_store.ts      # event log → webview bridge
│   └── types/events.ts       # mirrors mesh/schemas/events.schema.json
├── webview-ui/               # React app, bundled separately (Vite)
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

## Running (development)

```bash
cd extension
npm install
npm run build
```

Open the `extension/` folder in VS Code and press **F5** to launch the Extension Development Host. In the host window, open the AgentMesh activity-bar view; it connects to `ws://localhost:9900` automatically (set `agentmesh.source` to `live` in user settings if you need to force it).

## References

- [../docs/WEBSOCKET_SCHEMA.md](../docs/WEBSOCKET_SCHEMA.md) — event contract (must match the pydantic models)
- [../docs/DEMO_SCENARIO.md](../docs/DEMO_SCENARIO.md) — reference scenario timeline
