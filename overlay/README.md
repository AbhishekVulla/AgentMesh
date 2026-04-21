# AgentMesh overlay — live frontend

The bridge between the `mesh/` backend protocol and the `docs/design-system/` UI kit.

## What it is

A single-page HTML app that:

1. Opens a WebSocket to `ws://localhost:9900` (the event bus served by `mesh.run`)
2. Reduces the typed event stream into live UI state (agents, edges, metrics, conflicts)
3. Renders it through the design system's own components (`MeshCanvas`, `Inspector`, `BottomToolbar`, etc.)

No build step. React + Babel-in-the-browser, same as the design system kit.

## Run the end-to-end demo

```bash
# Terminal 1 — protocol backend + event bus
python -m mesh.run --config demo/config.yaml

# Terminal 2 — drive the DEMO_SCENARIO
python demo/run_scenario.py

# Browser — open overlay/index.html (file:// or served)
# The mesh canvas populates from mesh.session.started, nodes flip
# status on agent.state.changed, edges flash on message.sent, and the
# conflict card slides in at T+17s.
```

Pass `?ws=ws://host:port` on the overlay URL to point at a different bus.

## Files

| File | What |
|---|---|
| `index.html` | Loads React + Babel, the design-system UI components, and boots `live_app.jsx`. |
| `ws_client.js` | Plain-JS WebSocket client + pure-function reducer over the 9 event types. |
| `live_app.jsx` | React app that mirrors `docs/design-system/ui_kits/app/App.jsx` but state comes from the live bus. |

## Design system compliance

- Imports `../docs/design-system/colors_and_type.css` directly — no token duplication.
- Reuses `MeshCanvas`, `Inspector`, `BottomToolbar`, `CommandBar`, `LeftRail`, `Primitives` verbatim.
- Follows the operator-tone copy rules: sentence case, no emoji, `·` separators, uppercase mono for eyebrows.
