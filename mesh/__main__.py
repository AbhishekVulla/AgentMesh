"""Allow `python -m mesh` to dispatch to the run entry point."""
from mesh.run import main

if __name__ == "__main__":
    raise SystemExit(main())
