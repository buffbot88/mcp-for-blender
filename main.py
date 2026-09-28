"""Launcher for the MCP for Blender server.

The usual way to start the server is the installed `mcp-for-blender` console
script (`pipx`, `uvx`, or `pip install .`). This file handles being pointed at
directly by an MCP client, which is how this checkout is wired up:

    python C:\\...\\TWOR\\blender_mcp\\main.py

Two things can go wrong with that command, and both are handled here:

1. **The package is not importable.** Python puts the *script's own directory*
   on `sys.path`, not the directory above it, so `from blender_mcp.server
   import ...` fails with `ModuleNotFoundError: No module named 'blender_mcp'`
   on a fresh clone. The `src/` directory is prepended to `sys.path` below.

2. **The interpreter called `python` has no dependencies.** A system Python
   without `mcp` and `httpx` cannot run the server, so if that import fails this
   process hands itself over to the checkout's own virtualenv interpreter
   (`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere). The
   MCP client's stdio pipes are inherited, so the hand-off is invisible to it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

_SRC = _HERE / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _venv_python() -> Path | None:
    """Return this checkout's virtualenv interpreter, if one exists."""
    for candidate in (
        _HERE / ".venv" / "Scripts" / "python.exe",
        _HERE / ".venv" / "bin" / "python",
    ):
        if candidate.is_file():
            return candidate
    return None


def _reexec_in_venv(reason: str) -> None:
    """Restart this script under the virtualenv interpreter.

    Returns only when the hand-off is impossible, so the caller can report the
    original problem.
    """
    venv_python = _venv_python()
    if venv_python is None:
        return
    if Path(sys.executable).resolve() == venv_python.resolve():
        return  # already running inside the venv: do not loop

    print(
        f"blender_mcp/main.py: {reason}; restarting with {venv_python}",
        file=sys.stderr,
        flush=True,
    )
    argv = [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]]
    try:
        # Replaces this process, keeping the client's stdio pipes attached.
        os.execv(str(venv_python), argv)
    except OSError:
        # Fallback for platforms where exec does not preserve the pipes; the
        # child inherits stdin/stdout/stderr from this process by default.
        completed = subprocess.run(argv, check=False)
        raise SystemExit(completed.returncode)


try:
    from blender_mcp.server import main as server_main
except ModuleNotFoundError as exc:
    missing = exc.name or ""
    if not missing.startswith("blender_mcp"):
        # A dependency, not the package itself: the bundled venv can fix it.
        _reexec_in_venv(f"this interpreter is missing the '{missing}' module")

    _VENV_PYTHON = _HERE / ".venv" / "Scripts" / "python.exe"
    print(f"blender_mcp/main.py: cannot start the server: {exc}", file=sys.stderr)
    print(
        "This checkout needs its dependencies installed, e.g.:\n"
        f"  python -m venv {_HERE / '.venv'}\n"
        f"  {_VENV_PYTHON} -m pip install -e {_HERE}",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def main():
    """Entry point for the mcp-for-blender package."""
    server_main()


if __name__ == "__main__":
    main()
