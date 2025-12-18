"""Helper module for bootstrapping MCP servers."""

from __future__ import annotations

import atexit
import os
import platform
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from colorama import Fore, Style  # type: ignore[import-untyped]

MCP_PROCESSES: list[subprocess.Popen] = []


def cleanup_mcp_processes() -> None:
    """Kill all started MCP processes."""
    if not MCP_PROCESSES:
        return

    print(f"\n{Fore.YELLOW}Shutting down MCP servers...{Style.RESET_ALL}")
    for p in MCP_PROCESSES:
        if p.poll() is None:  # If still running
            try:
                if platform.system() == "Windows":
                    p.terminate()
                else:
                    os.kill(p.pid, signal.SIGTERM)
            except Exception as e:
                print(f"{Fore.RED}Error killing process {p.pid}: {e}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}MCP Servers terminated.{Style.RESET_ALL}")


def start_mcp_server(script_name: str) -> None:
    """Start an MCP server in a new terminal window."""
    # wheatley_V2/helper/mcp_bootstrapper.py -> wheatley_V2/MCP
    script_path = Path(__file__).parent.parent / "MCP" / script_name

    if not script_path.exists():
        print(
            f"{Fore.RED}Error: Could not find {script_name} at {script_path}{Style.RESET_ALL}"
        )
        return

    cmd = [sys.executable, str(script_path)]
    system = platform.system()
    process = None

    try:
        if system == "Windows":
            # CREATE_NEW_CONSOLE = 0x00000010
            # Use getattr to avoid mypy errors on non-Windows systems
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 16)
            process = subprocess.Popen(cmd, creationflags=creation_flags)
        elif system == "Linux":
            # Only use lxterminal as requested
            if shutil.which("lxterminal"):
                process = subprocess.Popen(
                    ["lxterminal", "-e", sys.executable, str(script_path)]
                )
            else:
                print(
                    f"{Fore.YELLOW}lxterminal not found. Running {script_name} in background.{Style.RESET_ALL}"
                )
                process = subprocess.Popen(cmd)

        if process:
            MCP_PROCESSES.append(process)
            print(
                f"{Fore.GREEN}Started {script_name} (PID: {process.pid}){Style.RESET_ALL}"
            )

    except Exception as e:
        print(f"{Fore.RED}Failed to start {script_name}: {e}{Style.RESET_ALL}")


# Register cleanup on module import
atexit.register(cleanup_mcp_processes)
