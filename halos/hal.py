"""hal — unified entry point for the halos ecosystem.

Usage:
    hal                         # list all modules
    hal <module> [args...]      # run a module command
    hal secrets vaults          # == secretctl vaults
    hal night add --title ...   # == nightctl add --title ...
    hal track add zazen ...     # == trackctl add zazen ...
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

AGENT_DIR = Path.home() / "code" / "halo" / "agent"

# Module registry: alias -> (command, description)
MODULES = {
    "mem":       ("memctl",       "Structured memory governance"),
    "night":     ("nightctl",     "Work tracker / Eisenhower matrix"),
    "cron":      ("cronctl",      "Cron job definitions and crontab generation"),
    "log":       ("logctl",       "Structured log reader and search"),
    "report":    ("reportctl",    "Periodic digests"),
    "agent":     ("agentctl",     "LLM session tracking / spin detection"),
    "brief":     ("hal-briefing", "Daily digests (morning/nightly)"),
    "fleet":     ("halctl",       "MicroHAL fleet management"),
    "track":     ("trackctl",     "Personal metrics tracker"),
    "dash":      ("dashctl",      "TUI dashboard"),
    "mail":      ("mailctl",      "Gmail operations via himalaya"),
    "cal":       ("calctl",       "Calendar operations"),
    "status":    ("statusctl",    "System status checks"),
    "backup":    ("backupctl",    "Backup management"),
    "blog":      ("blogctl",      "Blog management"),
    "ledger":    ("ledgerctl",    "Finance ledger"),
    "doc":       ("docctl",       "Documentation management"),
    "watch":     ("watchctl",     "YouTube channel monitor"),
    "secrets":   ("secretctl",    "1Password secret access"),
}

# Agent tools: dispatched separately (not halos console_scripts)
AGENT_MODULES = {
    "steer":     ("steer",                  "GUI automation — see, ocr, click, type, hotkey"),
    "drive":     ("drive",                  "Tmux terminal control for agent sessions"),
    "listen":    ("just listen",            "Start agent job server on :7600"),
    "send":      ("just send",              "Send a prompt to the agent server"),
    "sendi":     ("just sendi",             "Send prompt (interactive mode — visible TUI)"),
    "sendf":     ("just sendf",             "Send prompt from file"),
    "sendfi":    ("just sendfi",            "Send prompt from file (interactive mode)"),
    "jobs":      ("just jobs",              "List agent jobs"),
    "job":       ("just job",               "Show agent job detail"),
    "latest":    ("just latest",            "Show latest agent job(s)"),
    "stop":      ("just stop",              "Stop a running agent job"),
}


class _HalHelpAction(argparse.Action):
    """Custom help that shows the module table instead of argparse default."""
    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, **kwargs):
        super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        _print_modules()
        parser.exit()


def _print_modules() -> None:
    print(f"usage: hal [-h] module [args ...]\n")
    print(f"hal — unified entry point for the halos ecosystem\n")
    print(f"modules:")
    for alias, (cmd, desc) in MODULES.items():
        print(f"    {alias:<12} {cmd:<16} {desc}")
    print(f"\nagent tools:")
    for alias, (cmd, desc) in AGENT_MODULES.items():
        print(f"    {alias:<12} {cmd:<16} {desc}")
    print(f"\noptions:")
    print(f"  -h, --help            show this help message and exit")
    print(f"\nexamples:")
    print(f"  hal secrets vaults")
    print(f"  hal night add --title 'fix bug' --quadrant q1")
    print(f"  hal track add zazen --duration 25")
    print(f"  hal steer ocr --app Chrome")
    print(f"  hal send 'research topic X and write summary'")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help", "list"):
        _print_modules()
        return

    module = sys.argv[1]

    args = sys.argv[2:]

    # Check halos modules first
    if module in MODULES:
        cmd, _ = MODULES[module]
        os.execvp(cmd, [cmd] + args)

    # Check agent modules
    if module in AGENT_MODULES:
        cmd_str, _ = AGENT_MODULES[module]
        parts = cmd_str.split()

        if parts[0] == "just":
            # just commands run from agent/ dir
            os.chdir(AGENT_DIR)
            full_cmd = ["just"] + parts[1:] + args
            os.execvp("just", full_cmd)
        elif module == "steer":
            os.execvp("steer", ["steer"] + args)
        elif module == "drive":
            # drive is a uv script in agent/drive/
            os.chdir(AGENT_DIR / "drive")
            drive_cmd = ["uv", "run", "python", "main.py"] + args
            os.execvp("uv", drive_cmd)

    # Fuzzy match: full command name or stripped ctl suffix
    for alias, (cmd, _) in MODULES.items():
        if cmd == module or cmd.replace("ctl", "") == module:
            os.execvp(cmd, [cmd] + args)

    print(f"hal: unknown module '{module}'")
    print(f"Run 'hal --help' to see available modules.")
    sys.exit(1)
