"""Key chords as text: `Ctrl+Alt+Shift+Meta+Key`, as the `KeyChordField` widget writes and reads them.

A chord is its modifiers, always in the order Ctrl, Alt, Shift, Meta, and then one key, last, the parts joined by `+`: `Ctrl+Shift+F1`, `Alt+Left`, `Meta+Space`, `Ctrl+A`. A named key is in title
case (`Escape`, `Enter`, `Backspace`, `Tab`, `Space`, `Delete`, `Insert`, `Home`, `End`, `PageUp`, `PageDown`, `Left`, `Right`, `Up`, `Down`, and `Plus`, `Minus`, `Comma`, `Period` for the characters that
are hard to write in a `+`-joined text), a function key is `F1` to `F24`, a letter is a capital and any other single character is itself.

`normalise(text)` reads a chord written any way a person might (`ctrl+shift+f1`, `Control + Return`, `super+pgup`: any case, `Control`, `Option`, `Super`, `Win` and `Cmd` as modifier names, `Esc`, `Return`, `Del`,
`PgUp` and the engine's own `arrow_left` as key names, spaces around the `+`) and returns the canonical text, or `None` when it is not a chord. `from_event(key, ...)` builds the chord for a key press as the engine reports
it. Both use the one table below, so what is recorded and what is typed come out the same.
"""

from __future__ import annotations

__all__ = ["MODIFIERS", "canonical_key", "from_event", "is_modifier_key", "modifier_of", "normalise"]

#: The modifiers, in the order they are written.
MODIFIERS = ("Ctrl", "Alt", "Shift", "Meta")

_MODIFIER_NAMES = {
    "ctrl": "Ctrl", "control": "Ctrl", "ctl": "Ctrl",
    "alt": "Alt", "option": "Alt", "opt": "Alt",
    "shift": "Shift",
    "meta": "Meta", "super": "Meta", "win": "Meta", "windows": "Meta", "cmd": "Meta", "command": "Meta",
}

#: A key's name with no case and no `_`, `-` or space, and the canonical name it stands for.
_NAMED_KEYS = {
    "escape": "Escape", "esc": "Escape",
    "backspace": "Backspace", "bksp": "Backspace",
    "enter": "Enter", "return": "Enter",
    "tab": "Tab",
    "space": "Space", "spacebar": "Space",
    "delete": "Delete", "del": "Delete",
    "insert": "Insert", "ins": "Insert",
    "home": "Home", "end": "End",
    "pageup": "PageUp", "pgup": "PageUp", "prior": "PageUp",
    "pagedown": "PageDown", "pgdown": "PageDown", "pgdn": "PageDown", "next": "PageDown",
    "left": "Left", "arrowleft": "Left",
    "right": "Right", "arrowright": "Right",
    "up": "Up", "arrowup": "Up",
    "down": "Down", "arrowdown": "Down",
    "plus": "Plus", "minus": "Minus", "comma": "Comma", "period": "Period",
}

#: The names of keys that are only modifiers (or locks), which the engine reports as keys of their own: pressing one does not finish a chord. The `_left` and `_right` forms are the same keys.
_MODIFIER_KEYS = frozenset({"shift", "control", "ctrl", "alt", "altgr", "altgraph", "meta", "super", "hyper", "os", "capslock", "numlock", "scrolllock", "fn", "fnlock", "symbol", "symbollock"})


def _squash(name: str) -> str:
    return name.lower().replace("_", "").replace("-", "").replace(" ", "")


def is_modifier_key(name: str) -> bool:
    """Whether the engine's key `name` is a modifier or a lock, which is no key of a chord (`shift`, `control_left`, `alt_graph`, `caps_lock`, ...)."""
    squashed = _squash(name)
    for suffix in ("left", "right"):
        if squashed.endswith(suffix) and squashed[: -len(suffix)] in _MODIFIER_KEYS:
            return True
    return squashed in _MODIFIER_KEYS


def modifier_of(name: str) -> str | None:
    """The modifier (`Ctrl`, `Alt`, `Shift` or `Meta`) the engine's key `name` is, or `None` for any other key, a lock included (`control_left` is `Ctrl`, `caps_lock` is `None`)."""
    squashed = _squash(name)
    for suffix in ("left", "right"):
        if squashed.endswith(suffix):
            squashed = squashed[: -len(suffix)]
            break
    if squashed in ("shift",):
        return "Shift"
    if squashed in ("control", "ctrl"):
        return "Ctrl"
    if squashed in ("alt", "altgr", "altgraph"):
        return "Alt"
    if squashed in ("meta", "super", "hyper", "os"):
        return "Meta"
    return None


def canonical_key(name: str) -> str | None:
    """The canonical name of the key `name` (as typed or as the engine reports it), or `None` when it is not a key a chord can have."""
    if name == " ":
        return "Space"
    if name == "+":
        return "Plus"
    if len(name) == 1 and name.isprintable():
        return name.upper()
    squashed = _squash(name)
    if squashed in _NAMED_KEYS:
        return _NAMED_KEYS[squashed]
    if squashed.startswith("f") and squashed[1:].isdigit() and 1 <= int(squashed[1:]) <= 24 and squashed[1:] == str(int(squashed[1:])):
        return f"F{int(squashed[1:])}"
    return None


def _join(modifiers: set[str], key: str) -> str:
    return "+".join([*(m for m in MODIFIERS if m in modifiers), key])


def normalise(text: str) -> str | None:
    """`text` as the canonical chord, or `None` when it is not one: parts joined by `+` (spaces around them are fine), zero or more modifiers then exactly one key, a modifier named once at most.
    Any case is read. An empty text is not a chord (`None`): the empty shortcut is the caller's to allow."""
    parts = [part.strip() for part in text.split("+")]
    if len(parts) < 2 and not parts[0]:
        return None
    modifiers: set[str] = set()
    key: str | None = None
    for index, part in enumerate(parts):
        if not part:
            return None
        modifier = _MODIFIER_NAMES.get(part.lower())
        if modifier is not None and index < len(parts) - 1:
            if modifier in modifiers:
                return None
            modifiers.add(modifier)
        elif index == len(parts) - 1:
            key = canonical_key(part)
            if key is None:
                return None
        else:
            return None
    return _join(modifiers, key) if key is not None else None


def from_event(key: str, *, ctrl: bool = False, alt: bool = False, shift: bool = False, meta: bool = False) -> str | None:
    """The chord for the key press `key` (the engine's name for it) with the modifiers held, or `None` when `key` is a modifier of its own or a key a chord cannot have."""
    if is_modifier_key(key):
        return None
    name = canonical_key(key)
    if name is None:
        return None
    return _join({m for m, held in (("Ctrl", ctrl), ("Alt", alt), ("Shift", shift), ("Meta", meta)) if held}, name)
