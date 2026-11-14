"""The only way the application talks to the shell: the `tesserae-shell` command, as a short-lived subprocess.

`schema --json`, `check --json --config-dir <folder>` and `status --json` (and later `reload`). There is no socket, no D-Bus and no import of
`tess_shell`. `ShellCommand` takes the executable and the timeout, and the function that starts the process, so a test can hand it a fake command
under `tmp_path` and never reaches a real shell. `Offload` runs a call on a worker thread and posts its answer to the event loop, so no command
runs on the UI thread's frame path.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tess_shell_config.schema import Schema

__all__ = ["DEFAULT_COMMAND", "DEFAULT_TIMEOUT", "ShellCommandError", "ShellNotFound", "ShellTimeout", "ShellFailed", "Finding", "CheckResult", "Status", "ReloadResult",
           "ShellCommand", "Offload", "InlineOffload"]

DEFAULT_COMMAND = "tesserae-shell"
#: `check` that does not answer within this many seconds is one message in the problems list (the spec's failure table).
DEFAULT_TIMEOUT = 10.0


class ShellCommandError(Exception):
    """The shell command could not give an answer. `str(error)` is the message for the person."""


class ShellNotFound(ShellCommandError):
    """The command is not on the path: the application stops with this message."""

    def __init__(self, command: str) -> None:
        self.command = command
        super().__init__(f"The command {command} was not found. Install Tesserae Shell and put {command} on the PATH; this application edits its configuration through that command and cannot start without it.")


class ShellTimeout(ShellCommandError):
    def __init__(self, command: str, what: str, seconds: float) -> None:
        super().__init__(f"{command} {what} did not answer within {seconds:g} seconds.")


class ShellFailed(ShellCommandError):
    """The command ran and its answer was not usable: it did not exit with JSON on its output."""


@dataclass(frozen=True)
class Finding:
    """One finding of `check`: where it is (`file` as the shell names it, 1-based `line` and `column`), how bad, which rule, and what to write instead."""

    file: str
    line: int
    column: int
    severity: str
    rule: str
    message: str
    hint: str

    @classmethod
    def read(cls, raw: Mapping[str, Any]) -> Finding:
        def number(name: str) -> int:
            value = raw.get(name)
            return value if isinstance(value, int) and not isinstance(value, bool) else 0

        return cls(file=str(raw.get("file") or ""), line=number("line"), column=number("column"), severity=str(raw.get("severity") or "error"),
                   rule=str(raw.get("rule") or ""), message=str(raw.get("message") or ""), hint=str(raw.get("hint") or ""))

    def __str__(self) -> str:
        where = f"{self.file}:{self.line}:{self.column}" if self.line else self.file
        return f"{where}: {self.message}" + (f" ({self.hint})" if self.hint else "")


@dataclass(frozen=True)
class CheckResult:
    """What `check --json` said: `ok`, how many `files` it read, the `findings`, how many it left out (`omitted`) and the folder it checked."""

    ok: bool
    files: int
    findings: tuple[Finding, ...]
    omitted: int
    config_dir: str | None


@dataclass(frozen=True)
class Status:
    """What `status --json` said, whole in `raw`. The shell names the folder it resolved in `config_dir` (a shell that does not yet says nothing: `None`)."""

    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def config_dir(self) -> str | None:
        value = self.raw.get("config_dir")
        return str(value) if isinstance(value, str) and value else None

    @property
    def running(self) -> bool | None:
        """Whether a shell is running. The recorded shapes: a running shell answers `{"state": "running", ...}`; no shell is `{"ok": false, "error": "...", "exit": 3}`. Anything else says nothing (`None`)."""
        state = self.raw.get("state")
        if isinstance(state, str):
            return state == "running"
        if self.raw.get("ok") is False:
            return False
        return None

    @property
    def error(self) -> str:
        """What the shell said when it is not running (`no shell is running (nobody owns the bus name)`), else empty."""
        value = self.raw.get("error")
        return str(value) if isinstance(value, str) else ""

    @property
    def surfaces(self) -> tuple[str, ...]:
        """The names of the surfaces a running shell shows (`shown` true), for the status line."""
        found = self.raw.get("surfaces")
        return tuple(str(x.get("name")) for x in found if isinstance(x, Mapping) and x.get("shown")) if isinstance(found, list) else ()


@dataclass(frozen=True)
class ReloadResult:
    """What `reload` said: it exits 0 after the shell applied the files, 1 with the errors it printed for a bad file, 3 when no shell is running. `message` is the last line it printed, for the status line."""

    exit: int
    output: str

    @property
    def ok(self) -> bool:
        return self.exit == 0

    @property
    def not_running(self) -> bool:
        return self.exit == 3

    @property
    def message(self) -> str:
        lines = [line.strip() for line in self.output.splitlines() if line.strip()]
        return lines[0] if lines else ("Reloaded." if self.ok else "The shell did not apply the files." if self.exit == 1 else "No shell is running." if self.not_running else f"reload exited with {self.exit}.")


Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class ShellCommand:
    """Runs `tesserae-shell` for the application. `executable` is a name looked up on the path or a path; `run` starts the process (`subprocess.run`)."""

    def __init__(self, executable: str = DEFAULT_COMMAND, timeout: float = DEFAULT_TIMEOUT, run: Runner = subprocess.run,
                 env: Mapping[str, str] | None = None) -> None:
        self.executable = executable
        self.timeout = timeout
        self._run = run
        self._env = dict(env) if env is not None else None

    # -- finding the command -----------------------------------------------------------------------------------------------------

    def resolve(self) -> str:
        """The command's full path; raises `ShellNotFound` naming the command when it is not there."""
        found = shutil.which(self.executable)
        if found is None:
            raise ShellNotFound(self.executable)
        return found

    # -- the commands -----------------------------------------------------------------------------------------------------------

    def schema(self) -> Schema:
        """`schema --json`, read into a `Schema`. Raises `UnsupportedSchemaVersion` (a `SchemaError`) for a major version this application does not know."""
        data = self._json(["schema", "--json"], "schema --json")
        return Schema.from_data(data)

    def check(self, config_dir: str | Path) -> CheckResult:
        """`check --json --config-dir <folder>`. Findings make the command exit non-zero; the JSON on its output is the answer either way."""
        data = self._json(["check", "--json", "--config-dir", str(config_dir)], "check --json")
        if not isinstance(data, Mapping):
            raise ShellFailed(f"{self.executable} check --json answered with something other than a table.")
        findings = tuple(Finding.read(f) for f in data.get("errors", ()) if isinstance(f, Mapping))
        files = data.get("files")
        omitted = data.get("omitted")
        folder = data.get("config_dir")
        return CheckResult(ok=bool(data.get("ok", not findings)), files=files if isinstance(files, int) else 0, findings=findings,
                           omitted=omitted if isinstance(omitted, int) else 0, config_dir=str(folder) if isinstance(folder, str) else None)

    def status(self) -> Status:
        """`status --json`: whole, as the shell says it."""
        data = self._json(["status", "--json"], "status --json")
        return Status(data if isinstance(data, Mapping) else {})

    def reload(self) -> ReloadResult:
        """`reload`: asks the running shell to apply the files now. Never raises for a non-zero exit (that is the answer); a missing command, a timeout or a command that cannot start is a `ShellCommandError`."""
        done = self._start(["reload"], "reload")
        return ReloadResult(done.returncode, "\n".join(part for part in (done.stdout, done.stderr) if part and part.strip()))

    # -- the process -------------------------------------------------------------------------------------------------------------

    def _start(self, arguments: Sequence[str], what: str) -> subprocess.CompletedProcess[str]:
        executable = self.resolve()
        try:
            return self._run([executable, *arguments], capture_output=True, text=True, timeout=self.timeout, env=self._env, check=False, stdin=subprocess.DEVNULL)
        except FileNotFoundError:
            raise ShellNotFound(self.executable) from None
        except subprocess.TimeoutExpired:
            raise ShellTimeout(self.executable, what, self.timeout) from None
        except OSError as error:
            raise ShellFailed(f"{self.executable} {what} could not run: {error}") from None

    def _json(self, arguments: Sequence[str], what: str) -> Any:
        done = self._start(arguments, what)
        try:
            return json.loads(done.stdout)
        except ValueError:
            reason = (done.stderr or done.stdout or "").strip().splitlines()
            detail = f": {reason[-1]}" if reason else ""
            raise ShellFailed(f"{self.executable} {what} exited with {done.returncode} and gave no JSON{detail}") from None


class Offload:
    """Runs a call on a worker thread and hands its answer to `post`, a function that runs a callable on the event-loop thread (`app.thread_handle().call_soon`).

    `submit(fn, on_result, on_error)` returns at once; `on_result(value)` or `on_error(error)` runs on the loop thread. `on_error` gets the exception the call raised.
    """

    def __init__(self, post: Callable[[Callable[[], None]], Any]) -> None:
        self._post = post

    def submit(self, fn: Callable[[], Any], on_result: Callable[[Any], None], on_error: Callable[[BaseException], None]) -> threading.Thread:
        def work() -> None:
            try:
                value = fn()
            except BaseException as error:  # the loop thread is told; a worker never dies silently
                self._post(lambda error=error: on_error(error))  # type: ignore[misc]
            else:
                self._post(lambda: on_result(value))

        thread = threading.Thread(target=work, name="tess-shell-config-command", daemon=True)
        thread.start()
        return thread


class InlineOffload:
    """The same `submit`, run on the calling thread at once: for a window that is not running (a test, a script), where there is no loop to post to. Never used by the running application."""

    def submit(self, fn: Callable[[], Any], on_result: Callable[[Any], None], on_error: Callable[[BaseException], None]) -> None:
        try:
            value = fn()
        except BaseException as error:  # same contract as `Offload`: the error goes to `on_error`
            on_error(error)
        else:
            on_result(value)
