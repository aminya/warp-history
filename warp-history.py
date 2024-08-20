#!/usr/bin/env python3

from datetime import datetime
import shutil
import sqlite3
import os
import subprocess
import json
from collections import OrderedDict
import argparse


def get_warp_history(history: OrderedDict[str, datetime]) -> None:
    try:
        # Define the paths
        db_path = os.path.expanduser("~/.local/state/warp-terminal/warp.sqlite")

        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute the query to select unique commands and their start timestamps
        cursor.execute("SELECT DISTINCT command, start_ts FROM commands")
        commands = cursor.fetchall()

        # Close the database connection
        conn.close()

    except Exception as e:
        print(f"Failed to read Warp history from {db_path}: {e}")
        return

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


def get_mcfly_history(history: OrderedDict[str, datetime]):
    # Check if the `mcfly` command is available
    if not shutil.which("mcfly"):
        print("The `mcfly` command is not available.")
        return

    stdout: str = "[]"
    try:
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
    history: OrderedDict[str, datetime], shell: str
) -> None:
    # Define the path to the shell history file
    history_path = os.path.expanduser(f"~/.{shell}_history")

    # Backup the existing shell history file
    if os.path.exists(history_path):
        os.rename(history_path, history_path + ".bak")

    # Append the commands to the shell history file
    with open(history_path, "a") as history_file:
        for command in history.keys():
            history_file.write(command)
            history_file.write("\n")


def parse_args():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Write Warp and McFly history to shell history."
    )
    parser.add_argument(
        "--shell",
        type=str,
        default="bash",
        choices=["bash", "zsh"],
        help="Specify the shell type (bash or zsh).",
    )
    return parser.parse_args()


def main():
    # Parse command-line arguments
    args = parse_args()

    # History
    history = OrderedDict()

    # Get commands from Warp
    get_warp_history(history)

    # Get commands from McFly
    get_mcfly_history(history)

    # Write the combined history to the specified shell history
    write_history_to_shell_history(history, args.shell)

    print(
        f"""
Number of commands written to {args.shell} history: {len(history)}
Please restart your shell to apply the changes.
"""
    )


if __name__ == "__main__":
    main()
