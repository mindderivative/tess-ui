"""The `tesserae-shell-config` command: start the window on the shell's configuration folder.

The folder is the one given with `--config-dir`, else the one `tesserae-shell status --json` names, else the shell's own default place. Without the `tesserae-shell` command, or with a schema whose
major version this application does not know, it says so on standard error and stops (it bundles no schema of its own).
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from collections.abc import Sequence

from tess_shell_config import __version__
from tess_shell_config.files import state_dir
from tess_shell_config.folder import resolve_config_dir
from tess_shell_config.schema import SchemaError
from tess_shell_config.session import ConfigSession
from tess_shell_config.shell import DEFAULT_COMMAND, ShellCommand, ShellCommandError

__all__ = ["main", "start"]

#: The exit status of "cannot start": a missing command, a schema it cannot read.
CANNOT_START = 3


def start(config_dir: str | None = None, command: str = DEFAULT_COMMAND, state: str | None = None, shell: ShellCommand | None = None) -> ConfigSession:
    """Everything the window needs before it opens: the command found, the schema read and checked, the folder resolved. Raises `ShellCommandError` or `SchemaError` (their text is the message for the person)."""
    shell = shell or ShellCommand(command)
    shell.resolve()
    schema = shell.schema()
    status_dir = None
    if not config_dir:  # the folder the shell names, when it says one; no shell running (or one that cannot say) leaves the discovery rule
        with contextlib.suppress(ShellCommandError):
            status_dir = shell.status().config_dir
    folder = resolve_config_dir(config_dir, status_dir)
    return ConfigSession(folder, schema, shell, state_dir=state if state is not None else state_dir())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tesserae-shell-config", description="Edit the configuration of Tesserae Shell.")
    parser.add_argument("--config-dir", help="the configuration folder to open (default: the one the shell names, else the shell's own default place)")
    parser.add_argument("--shell-command", default=DEFAULT_COMMAND, help=f"the shell command to run (default: {DEFAULT_COMMAND})")
    parser.add_argument("--state-dir", help="the application's own state folder, for backups and settings (default: under XDG_STATE_HOME)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    try:
        session = start(args.config_dir, args.shell_command, args.state_dir)
    except (ShellCommandError, SchemaError) as error:
        print(f"tesserae-shell-config: {error}", file=sys.stderr)
        return CANNOT_START
    from tess_shell_config.app import build

    built = build(session, live=True)
    try:
        built.app.run()
    finally:
        built.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
