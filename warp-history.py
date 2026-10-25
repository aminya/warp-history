#!/usr/bin/python3

import argparse
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from collections import OrderedDict
from datetime import datetime
from itertools import chain
from os import getenv
from os.path import expanduser
from pathlib import Path

db_globs = [
    "~/.local/state/warp-terminal/warp.sqlite",
    "~/.config/Warp/warp.sqlite",
    "~/.local/share/warp-terminal/warp.sqlite",
    "~/.config/Warp/warp.db",
    "~/Library/Application Support/Warp/warp.sqlite",
    "~/Library/Application Support/Warp/warp.db",
    "~/Library/Application Support/Warp/databases/warp.sqlite",
    "/Users/*/Library/Group Containers/*.dev.warp/Library/Application Support/dev.warp.Warp-Stable/warp.sqlite",
]


def find_path_in_globs(globs: list[str]):
    paths = chain.from_iterable([glob.glob(expanduser(g)) for g in globs])
    return [Path(p) for p in paths]


def get_warp_db_paths():
    return find_path_in_globs(db_globs)


def merge_warp_history(history: OrderedDict[str, datetime], db_path: Path):
    # Connect to the SQLite database
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Execute the query to select unique commands and their start timestamps
        cursor.execute("SELECT DISTINCT command, start_ts FROM commands")
        commands = cursor.fetchall()

    # Parse the start_ts and store in the history dictionary
    for command, start_ts in commands:
        try:
            if start_ts is None:
                start_ts = "1970-01-01 00:00:00.000000"

            # Truncate nanoseconds to microseconds
            start_ts = start_ts[:26]
            start_ts_dt = datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S.%f")
            history[command] = start_ts_dt
        except Exception as e:
            print(f"Failed to parse timestamp {start_ts}: {e}")
            continue


def merge_warp_histories(history: OrderedDict[str, datetime]):
    db_paths = get_warp_db_paths()
    for db_path in db_paths:
        merge_warp_history(history, db_path)


def populate_mcfly_history(history_path: Path) -> None:
    # Check if the `mcfly` command is available
    if not shutil.which("mcfly"):
        # print("The `mcfly` command is not available.")
        return

    # set MCFLY_HISTFILE to the history file path
    os.environ["MCFLY_HISTFILE"] = str(history_path)

    # Create a temporary file for McFly history
    mcfly_history = getenv("MCFLY_HISTORY")
    if not mcfly_history:
        with tempfile.NamedTemporaryFile(
            delete=False, prefix="mcfly.", dir="/tmp"
        ) as tmpfile:
            mcfly_history = tmpfile.name
        os.environ["MCFLY_HISTORY"] = mcfly_history

    # Populate McFly's temporary history file from recent commands in the shell's primary HISTFILE
    with (
        history_path.open("r") as histfile,
        Path(mcfly_history).open("w") as mcfly_file,
    ):
        lines = histfile.readlines()
        mcfly_file.writelines(lines)


def merge_mcfly_history(
    history_path: Path, history: OrderedDict[str, datetime]
) -> None:
    # Check if the `mcfly` command is available
    if not shutil.which("mcfly"):
        # print("The `mcfly` command is not available.")
        return

    stdout: str = "[]"
    try:
        populate_mcfly_history(history_path)

        # Run the `mcfly dump` command and capture the output
        result = subprocess.run(
            ["mcfly", "dump"], stdout=subprocess.PIPE, text=True, check=True
        )
        stdout = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to read McFly history: {e}")
        return

    # Parse the JSON output
    commands_json = json.loads(stdout)

    # Extract the `cmd` and `when_run` properties and store them in the given history dictionary
    for command in commands_json:
        when_run = datetime.fromisoformat(command["when_run"])
        history[command["cmd"]] = when_run


def write_history_to_shell_history(
    history_path: Path, history: OrderedDict[str, datetime]
) -> None:

    # Append the commands to the shell history file
    with open(history_path, "w") as history_file:
        for command in history:
            history_file.write(command)
            history_file.write("\n")


def write_this_script_to_rc_file(shell: str) -> None:
    # Define the path to the shell RC file
    rc_path = Path(expanduser(f"~/.{shell}rc"))

    # if the script is already appended, do not append it again
    with open(rc_path, "r") as f:
        if __file__ in f.read():
            return

    # Append this script to the shell RC file
    with rc_path.open("a") as rc_file:
        rc_file.write("\n# Append Warp and McFly history to shell history\n")
        interactivity = '[[ "$-" == *i* ]]'
        existence = f"test -f {__file__}"
        rc_file.write(f"{interactivity} && {existence} && python3 {__file__}\n")


def create_shell_history(args):
    # Define the path to the shell history file
    history_path = Path(expanduser(f"~/.{args.shell}_history"))

    # Backup the existing shell history file
    if history_path.exists():
        metadata = history_path.stat()
        history_path.rename(str(history_path) + ".bak")
        history_path.touch()
    else:
        history_path.touch()
        metadata = history_path.stat()

    modified_datetime = datetime.fromtimestamp(metadata.st_mtime)

    history: OrderedDict[str, datetime] = OrderedDict()
    with (
        history_path.open("r") as histfile,
    ):
        shell_lines = histfile.readlines()
        for line in shell_lines:
            if not line in history:
                history[line] = modified_datetime
    return history_path, history


def get_shell():
    env_shell = getenv("SHELL", "bash").split("/")[-1]

    try:
        # Method 1: Check the SHELL environment variable
        shell_path = env_shell
        if shell_path.endswith("zsh"):
            return "zsh"

        if getenv("ZSH_VERSION"):
            return "zsh"

        # Method 2: Check parent process name (more reliable)
        # Works on Unix-like systems
        if sys.platform != "win32":
            try:
                parent_pid = os.getppid()
                proc_name = subprocess.check_output(
                    ["ps", "-p", str(parent_pid), "-o", "comm="], text=True
                ).strip()
                if proc_name.lower() == "zsh":
                    return "zsh"
            except Exception:
                pass

        return env_shell
    except Exception as e:
        print(f"Error detecting shell: {e}")
        return env_shell


def parse_args():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Write Warp and McFly history to shell history."
    )

    parser.add_argument(
        "--shell",
        type=str,
        default=get_shell(),
        help="Specify the shell type (automatically detected).",
    )
    return parser.parse_args()


def main():
    # Parse command-line arguments
    args = parse_args()

    # Write this script to the shell RC file
    write_this_script_to_rc_file(args.shell)

    history_path, history = create_shell_history(args)

    # Get commands from Warp
    merge_warp_histories(history)
    if not history:
        return

    # Get commands from McFly
    merge_mcfly_history(history_path, history)

    # Write the combined history to the specified shell history
    write_history_to_shell_history(history_path, history)


if __name__ == "__main__":
    main()
