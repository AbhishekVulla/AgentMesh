"""Session bootstrapper: parse config, start Mini Agents + WebSocket server.

Day-1 skeleton only. Day-2 wires up mini_agent + ws_server; until then
``main()`` validates the config and prints a registration summary.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mesh", description="Start an AgentMesh session.")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to demo/config.yaml (agents + paths + WebSocket port).",
    )
    args = parser.parse_args(argv)

    if not args.config.exists():
        print(f"error: config not found: {args.config}", file=sys.stderr)
        return 2

    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    agents = config.get("agents", [])
    port = config.get("websocket", {}).get("port", 9900)

    print(f"[mesh] loaded config: {args.config}")
    print(f"[mesh] agents: {[a['id'] for a in agents]}")
    print(f"[mesh] websocket: ws://localhost:{port}")
    print("[mesh] Day-1 skeleton — Mini Agents and WebSocket server land on Day 2 (G3).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
