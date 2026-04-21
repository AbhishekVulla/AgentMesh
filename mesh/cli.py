"""`agentmesh` CLI — the plugin surface.

Subcommands:

    agentmesh up          — start bus + static server + open overlay
    agentmesh bus         — bus only (what `python -m mesh.run` used to be)
    agentmesh serve       — static HTTP server for the overlay
    agentmesh attach      — blocking sidecar for a major agent (watches a
                            dict file, lets the caller write to it)
    agentmesh emit        — one-shot dict mutation (set/unset paths)
    agentmesh scenario    — drive the DEMO_SCENARIO against a running bus
    agentmesh status      — report bus liveness + last-session totals

All output is plain stdout so the command composes in shell pipelines.
Exit codes: 0 OK, 1 expected failure, 2 usage error.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any

from mesh.client import AgentMeshClient
from mesh.dict_store import atomic_write_json, utc_now_iso


DEFAULT_BUS_PORT = 9900
DEFAULT_WEB_PORT = 5173
DEFAULT_TEE = Path(".agentmesh/events/session.jsonl")
PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # mesh/cli.py -> repo root


# --------------------------------------------------------------------- helpers

def _port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_in_use(port):
            return True
        time.sleep(0.1)
    return False


def _default_config() -> Path:
    """Find a usable config.yaml: user's `demo/config.yaml` or packaged one."""
    cwd_candidate = Path.cwd() / "demo" / "config.yaml"
    if cwd_candidate.exists():
        return cwd_candidate
    pkg_candidate = PACKAGE_ROOT / "demo" / "config.yaml"
    if pkg_candidate.exists():
        return pkg_candidate
    raise SystemExit("error: no demo/config.yaml found. Pass --config explicitly.")


# ----------------------------------------------------------------- subcommands

def cmd_bus(args: argparse.Namespace) -> int:
    from mesh.run import main as run_main
    argv = ["--config", str(args.config or _default_config())]
    if args.duration is not None:
        argv += ["--duration", str(args.duration)]
    return run_main(argv)


def cmd_serve(args: argparse.Namespace) -> int:
    """Static HTTP server over the repo root so the overlay can load."""
    import http.server
    import socketserver

    root = args.root or PACKAGE_ROOT
    os.chdir(root)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"[agentmesh] serving {root} on http://127.0.0.1:{args.port}/overlay/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    """Start bus + static server together. Blocks until Ctrl-C."""
    cfg = args.config or _default_config()

    if _port_in_use(args.bus_port):
        print(f"[agentmesh] bus already listening on :{args.bus_port}")
        bus_proc: subprocess.Popen | None = None
    else:
        bus_cmd = [
            sys.executable, "-m", "mesh.cli", "bus",
            "--config", str(cfg),
        ]
        if args.duration is not None:
            bus_cmd += ["--duration", str(args.duration)]
        env = {**os.environ, "PYTHONPATH": str(PACKAGE_ROOT)}
        bus_proc = subprocess.Popen(bus_cmd, env=env)
        if not _wait_for_port(args.bus_port):
            print(f"[agentmesh] error: bus did not come up on :{args.bus_port}",
                  file=sys.stderr)
            bus_proc.terminate()
            return 1
        print(f"[agentmesh] bus -> ws://localhost:{args.bus_port}")

    if _port_in_use(args.web_port):
        print(f"[agentmesh] http server already on :{args.web_port}")
        web_proc: subprocess.Popen | None = None
    else:
        web_cmd = [
            sys.executable, "-m", "mesh.cli", "serve",
            "--port", str(args.web_port),
            "--root", str(PACKAGE_ROOT),
        ]
        env = {**os.environ, "PYTHONPATH": str(PACKAGE_ROOT)}
        web_proc = subprocess.Popen(web_cmd, env=env)
        if not _wait_for_port(args.web_port):
            print(f"[agentmesh] error: static server did not come up on :{args.web_port}",
                  file=sys.stderr)
            if bus_proc:
                bus_proc.terminate()
            web_proc.terminate()
            return 1

    url = f"http://localhost:{args.web_port}/overlay/"
    print(f"[agentmesh] overlay -> {url}")
    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        if bus_proc:
            bus_proc.wait()
        elif web_proc:
            web_proc.wait()
        else:
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        for p in (bus_proc, web_proc):
            if p and p.poll() is None:
                p.terminate()
    return 0


def cmd_attach(args: argparse.Namespace) -> int:
    """Run a blocking sidecar for the given agent_id.

    Major agents (Claude Code, Codex, scripted producers) call this to join
    the mesh. The sidecar seeds `.agentmesh/agents/<id>/dictionary.json`
    and `input.json` and blocks until Ctrl-C.
    """
    client = AgentMeshClient(
        agent_id=args.agent_id,
        base_dir=Path(args.base_dir),
    )
    client.register(role=args.role or args.agent_id)
    print(f"[agentmesh] attached as '{args.agent_id}' — dir={client.agent_dir}")
    print(f"[agentmesh] edit {client.dict_path} or use `agentmesh emit` to mutate.")
    print("[agentmesh] Ctrl-C to detach.")
    try:
        while True:
            time.sleep(0.5)
            # Drain any incoming messages and print them so the caller can
            # react in-stream. MVP: just print.
            incoming = client.drain_input()
            for msg in incoming:
                print(f"[in] {msg['from']} scope={msg['scope']} "
                      f"changes={len(msg.get('changes', []))}")
    except KeyboardInterrupt:
        print("\n[agentmesh] detached")
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    """Mutate the given agent's dictionary from the shell.

    Each --set is `path=<json>`. Paths use dot-notation with '/'-prefixed
    URL segments preserved: `routes./api/users.auth_required=true`.
    """
    client = AgentMeshClient(
        agent_id=args.agent_id,
        base_dir=Path(args.base_dir),
    )
    client.register(role=args.agent_id)
    for expr in args.set or []:
        if "=" not in expr:
            print(f"error: --set expects path=value, got {expr!r}", file=sys.stderr)
            return 2
        path, raw = expr.split("=", 1)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw  # treat as literal string
        client.set(path, value)
        print(f"[agentmesh] {args.agent_id}:{path} <- {json.dumps(value)}")
    for path in args.unset or []:
        client.unset(path)
        print(f"[agentmesh] {args.agent_id}:{path} deleted")
    print(f"[agentmesh] {args.agent_id} version -> {client.version}")
    return 0


def cmd_scenario(args: argparse.Namespace) -> int:
    """Run the packaged DEMO_SCENARIO.md timeline."""
    scenario_path = PACKAGE_ROOT / "demo" / "run_scenario.py"
    if not scenario_path.exists():
        print(f"error: demo/run_scenario.py not found at {scenario_path}",
              file=sys.stderr)
        return 1
    env = {**os.environ, "PYTHONPATH": str(PACKAGE_ROOT)}
    return subprocess.call([sys.executable, str(scenario_path)], env=env)


def cmd_status(args: argparse.Namespace) -> int:
    tee = Path(args.tee or DEFAULT_TEE)
    bus_up = _port_in_use(args.bus_port)
    web_up = _port_in_use(args.web_port)
    print(f"bus   (:{args.bus_port}): {'UP' if bus_up else 'down'}")
    print(f"http  (:{args.web_port}): {'UP' if web_up else 'down'}")
    if not tee.exists():
        print(f"tee   ({tee}): missing")
        return 0
    events: list[dict[str, Any]] = []
    with tee.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    counts: dict[str, int] = {}
    for e in events:
        counts[e["event"]] = counts.get(e["event"], 0) + 1
    print(f"tee   ({tee}): {len(events)} events")
    for k in sorted(counts):
        print(f"  {counts[k]:4d}  {k}")
    if events:
        last = events[-1]
        print(f"last: seq={last.get('seq')} {last.get('event')} {last.get('ts', '')}")
    return 0


# ---------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agentmesh", description="AgentMesh — plugin CLI.")
    p.add_argument("--version", action="version", version="agentmesh 0.1.0")
    sub = p.add_subparsers(dest="cmd", required=True)

    # up
    up = sub.add_parser("up", help="Start bus + static server; open overlay.")
    up.add_argument("--bus-port", type=int, default=DEFAULT_BUS_PORT)
    up.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT)
    up.add_argument("--config", type=Path, default=None)
    up.add_argument("--duration", type=int, default=None, help="Bus auto-stop seconds.")
    up.add_argument("--no-open", dest="open", action="store_false", default=True)
    up.set_defaults(fn=cmd_up)

    # bus
    bus = sub.add_parser("bus", help="Run the event bus only.")
    bus.add_argument("--config", type=Path, default=None)
    bus.add_argument("--duration", type=int, default=None)
    bus.set_defaults(fn=cmd_bus)

    # serve
    serve = sub.add_parser("serve", help="Static HTTP server for the overlay.")
    serve.add_argument("--port", type=int, default=DEFAULT_WEB_PORT)
    serve.add_argument("--root", type=Path, default=None)
    serve.set_defaults(fn=cmd_serve)

    # attach
    attach = sub.add_parser("attach", help="Register a major agent and block.")
    attach.add_argument("--agent-id", required=True)
    attach.add_argument("--role", default=None)
    attach.add_argument("--base-dir", default=".agentmesh/agents")
    attach.set_defaults(fn=cmd_attach)

    # emit
    emit = sub.add_parser("emit", help="One-shot mutation to an agent's dict.")
    emit.add_argument("--agent-id", required=True)
    emit.add_argument("--base-dir", default=".agentmesh/agents")
    emit.add_argument("--set", action="append", metavar="path=json",
                      help="Set a path; value is JSON (use quotes for strings).")
    emit.add_argument("--unset", action="append", metavar="path",
                      help="Delete a path.")
    emit.set_defaults(fn=cmd_emit)

    # scenario
    sc = sub.add_parser("scenario", help="Drive the DEMO_SCENARIO timeline.")
    sc.set_defaults(fn=cmd_scenario)

    # status
    st = sub.add_parser("status", help="Show bus/http liveness + event totals.")
    st.add_argument("--bus-port", type=int, default=DEFAULT_BUS_PORT)
    st.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT)
    st.add_argument("--tee", type=Path, default=None)
    st.set_defaults(fn=cmd_status)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
