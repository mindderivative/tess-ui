"""The font families installed on the machine, as the `FontList` widget lists them.

`families()` is the sorted, de-duplicated list the *provider* gives; the default provider runs `fc-list : family` (fontconfig's own list, a read-only subprocess, given
`TIMEOUT` seconds) and reads what it prints: one line for each font, each line holding the family and its other names in other languages, separated by commas. A machine with no
`fc-list`, or one that fails, takes too long or prints nothing, is a `FontListError`: the widget then offers a text field in place of the list. The answer is kept for the life of the
process (`refresh()` asks again), so the subprocess runs once.

A test, or an app that knows better where its fonts are, swaps the provider with `use(fn)`: `fn()` returns the family names (in any order, with repeats) or raises `FontListError`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterable

__all__ = ["FontListError", "default_provider", "families", "parse", "refresh", "use"]

#: Seconds `fc-list` is given.
TIMEOUT = 5.0


class FontListError(Exception):
    """The installed families cannot be listed: `str(error)` says why."""


def parse(text: str) -> list[str]:
    """The families in the output of `fc-list : family`: split on newlines and commas, trimmed, with the empty ones and the repeats left out (a family differing only in case is a repeat),
    sorted without regard to case. A comma or a backslash inside a name is escaped by `fc-list` with a backslash and is kept."""
    seen: dict[str, str] = {}
    for line in text.splitlines():
        for name in _split(line):
            name = name.strip()
            if name and name.casefold() not in seen:
                seen[name.casefold()] = name
    return [seen[key] for key in sorted(seen)]


def _split(line: str) -> list[str]:
    """`line` split at the commas that are not escaped, the escapes removed."""
    names, current, escaped = [], "", False
    for char in line:
        if escaped:
            current, escaped = current + char, False
        elif char == "\\":
            escaped = True
        elif char == ",":
            names.append(current)
            current = ""
        else:
            current += char
    return [*names, current]


def default_provider() -> list[str]:
    """Runs `fc-list : family` and returns its families (see `parse`). Raises `FontListError` when there is no `fc-list`, it fails, it takes more than `TIMEOUT` seconds or it lists none."""
    try:
        done = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except FileNotFoundError:
        raise FontListError("fc-list is not installed") from None
    except subprocess.TimeoutExpired:
        raise FontListError(f"fc-list took more than {TIMEOUT:g} seconds") from None
    except OSError as error:
        raise FontListError(f"fc-list could not run: {error.strerror or error}") from None
    if done.returncode != 0:
        raise FontListError(f"fc-list failed (exit {done.returncode})")
    found = parse(done.stdout)
    if not found:
        raise FontListError("fc-list lists no fonts")
    return found


_provider: Callable[[], Iterable[str]] = default_provider
_cache: list[str] | FontListError | None = None


def use(provider: Callable[[], Iterable[str]] | None) -> Callable[[], Iterable[str]]:
    """Makes `provider` the one `families()` asks (`None` puts `fc-list` back), forgets the kept answer, and returns the provider it replaced so a test can put that back."""
    global _provider, _cache
    previous = _provider
    _provider = provider if provider is not None else default_provider
    _cache = None
    return previous


def refresh() -> None:
    """Forgets the kept answer: the next `families()` asks the provider again."""
    global _cache
    _cache = None


def families() -> list[str]:
    """The installed families, sorted without regard to case, each once. Raises `FontListError` when the provider cannot say (the failure is kept as well, so a machine without `fc-list` is not asked again)."""
    global _cache
    if _cache is None:
        try:
            found = _clean(_provider())
            _cache = found if found else FontListError("the provider lists no fonts")
        except FontListError as error:
            _cache = error
        except OSError as error:
            _cache = FontListError(f"the provider failed: {error.strerror or error}")
    if isinstance(_cache, FontListError):
        raise _cache
    return list(_cache)


def _clean(names: Iterable[str]) -> list[str]:
    """What a provider gave, made the way `parse` makes its answer: trimmed, no empty name, no repeat, sorted without regard to case."""
    seen: dict[str, str] = {}
    for name in names:
        name = str(name).strip()
        if name and name.casefold() not in seen:
            seen[name.casefold()] = name
    return [seen[key] for key in sorted(seen)]
