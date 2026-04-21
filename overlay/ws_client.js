// AgentMesh WebSocket client + event reducer.
//
// Connects to the mesh.run event bus on ws://localhost:9900 and maintains
// a derived UI state: agents[], edges[], metrics, conflict, log.
//
// Plain JS (no bundler). Loaded as a <script> in overlay/index.html and
// exposed on window.AgentMeshLive.

(function () {
  const DEFAULT_URL = "ws://localhost:9900";

  // Map schema `AgentState` -> design-system `status` token.
  const STATE_TO_STATUS = {
    IDLE: "idle",
    WORKING: "working",
    BLOCKED: "waiting",
    COMPLETED: "idle",
  };

  function initialState() {
    return {
      sessionId: null,
      connected: false,
      agents: [],            // [{id, name, model, status, tool, tokens, parentId, tools, version}]
      edges: [],             // active/in-flight edges [{from, to, id, born, kind}]
      metrics: { messages: 0, conflicts: 0, bytes: 0, saved: 0 },
      conflict: null,        // latest unresolved conflict card
      recentResolution: null,
      log: [],               // last 50 events for inspector timeline
      dict: {},              // agent_id -> current known dict (for inspector)
    };
  }

  function reduce(state, ev) {
    const next = { ...state, log: trim([ev, ...state.log], 50) };

    switch (ev.event) {
      case "mesh.session.started":
        next.sessionId = ev.session_id;
        next.agents = ev.agents.map((a, i) => ({
          id: a.id,
          name: a.id,
          role: a.role,
          model: "mesh",
          status: "idle",
          tool: "",
          tokens: 0,
          parentId: null,
          exposes: a.exposes || [],
          tools: [],
          version: 0,
        }));
        next.dict = Object.fromEntries(next.agents.map(a => [a.id, {}]));
        return next;

      case "mesh.session.ended":
        next.agents = next.agents.map(a => ({ ...a, status: "idle" }));
        return next;

      case "agent.state.changed": {
        next.agents = next.agents.map(a =>
          a.id === ev.agent_id
            ? {
                ...a,
                status: STATE_TO_STATUS[ev.to] || "idle",
                rawState: ev.to,
                tool: ev.current_task || a.tool,
              }
            : a
        );
        return next;
      }

      case "dict.mutated": {
        // update version, tool label, and a local dict mirror by path
        const aid = ev.agent_id;
        const patch = applyChanges(next.dict[aid] || {}, ev.changes);
        next.dict = { ...next.dict, [aid]: patch };
        next.agents = next.agents.map(a =>
          a.id === aid
            ? {
                ...a,
                version: ev.version,
                tokens: estimateTokens(patch),
                tools: trim(
                  [
                    ...(ev.changes || []).map(c => ({
                      name: c.op,
                      arg: c.path,
                      time: "now",
                      done: true,
                    })),
                    ...(a.tools || []),
                  ],
                  6
                ),
              }
            : a
        );
        return next;
      }

      case "message.sent": {
        next.metrics = {
          ...next.metrics,
          messages: next.metrics.messages + 1,
          bytes: next.metrics.bytes + (ev.diff_summary?.bytes || 0),
        };
        next.edges = [
          ...next.edges.filter(e => e.id !== ev.message_id),
          {
            id: ev.message_id,
            from: ev.from,
            to: ev.to,
            scope: ev.scope,
            priority: ev.priority,
            born: Date.now(),
            kind: "send",
          },
        ];
        return next;
      }

      case "message.delivered": {
        next.edges = next.edges.map(e =>
          e.id === ev.message_id ? { ...e, kind: "delivered", born: Date.now() } : e
        );
        // decay after 1.2s — we mark for cleanup in the animation loop
        return next;
      }

      case "conflict.detected": {
        next.metrics = { ...next.metrics, conflicts: next.metrics.conflicts + 1 };
        next.conflict = {
          id: ev.conflict_id,
          path: ev.path,
          parties: ev.parties,
          incomingMessageId: ev.incoming_message_id,
          resolved: false,
        };
        return next;
      }

      case "conflict.resolved": {
        next.conflict =
          next.conflict && next.conflict.id === ev.conflict_id
            ? { ...next.conflict, resolved: true, winner: ev.winner, reason: ev.reason }
            : next.conflict;
        next.recentResolution = {
          conflictId: ev.conflict_id,
          winner: ev.winner,
          loser: ev.loser,
          reason: ev.reason,
          ts: Date.now(),
        };
        return next;
      }

      case "metrics.tick": {
        next.metrics = {
          messages: ev.messages_total,
          conflicts: ev.conflicts_total,
          bytes: ev.bytes_exchanged_total,
          saved: ev.estimated_tokens_saved_pct,
        };
        return next;
      }

      default:
        return next;
    }
  }

  // -------------------------------------------------------------- helpers

  function trim(arr, n) {
    return arr.length > n ? arr.slice(0, n) : arr;
  }

  function applyChanges(dict, changes) {
    const out = JSON.parse(JSON.stringify(dict || {}));
    for (const c of changes || []) {
      const segs = tokenize(c.path);
      if (!segs.length) continue;
      if (c.op === "delete") {
        removeAt(out, segs);
      } else {
        setAt(out, segs, c.new);
      }
    }
    return out;
  }

  function tokenize(path) {
    // Matches mesh.dict_store.tokenize_dotpath: split on '.' but keep
    // '/'-prefixed URL segments whole.
    const out = [];
    let buf = "";
    for (let i = 0; i < path.length; i++) {
      const ch = path[i];
      if (ch === "." && !(buf.startsWith("/") && path[i + 1] === "/")) {
        if (buf) out.push(buf);
        buf = "";
      } else {
        buf += ch;
      }
    }
    if (buf) out.push(buf);
    return out.filter(Boolean);
  }

  function setAt(obj, segs, value) {
    let cur = obj;
    for (let i = 0; i < segs.length - 1; i++) {
      const k = segs[i];
      if (typeof cur[k] !== "object" || cur[k] === null) cur[k] = {};
      cur = cur[k];
    }
    cur[segs[segs.length - 1]] = value;
  }

  function removeAt(obj, segs) {
    let cur = obj;
    for (let i = 0; i < segs.length - 1; i++) {
      const k = segs[i];
      if (typeof cur[k] !== "object" || cur[k] === null) return;
      cur = cur[k];
    }
    delete cur[segs[segs.length - 1]];
  }

  function estimateTokens(dict) {
    return Math.min(200, JSON.stringify(dict).length >> 3);
  }

  // ---------------------------------------------------------------- client

  function connect(url, onState) {
    url = url || DEFAULT_URL;
    let state = initialState();
    let ws;
    let retry = 0;

    const push = (s) => {
      state = s;
      try { onState(state); } catch (e) { console.error("onState failed", e); }
    };

    const open = () => {
      ws = new WebSocket(url);

      ws.onopen = () => {
        retry = 0;
        push({ ...state, connected: true });
      };

      ws.onmessage = (msg) => {
        try {
          const ev = JSON.parse(msg.data);
          push(reduce(state, ev));
        } catch (e) {
          console.error("bad event", e, msg.data);
        }
      };

      ws.onclose = () => {
        push({ ...state, connected: false });
        retry = Math.min(retry + 1, 6);
        setTimeout(open, 400 * retry);
      };

      ws.onerror = () => {
        try { ws.close(); } catch (e) {}
      };
    };

    open();

    return {
      get state() { return state; },
      close: () => { try { ws && ws.close(); } catch (e) {} },
    };
  }

  window.AgentMeshLive = { connect, reduce, initialState, tokenize };
})();
