"""TDL text for the values a form writes, and what a value already in a file says to a widget.

A form writes one value as one line of TDL (`Block.with_property(key, value_text)`). The helpers here make that text for a typed value (a quoted string with its escapes, a number without
a stray `.0`, a percentage, a quoted colour) and read the other way (a colour in any of the forms TDL takes, a number's text). Nothing here knows a key: the schema says which key takes which.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from functools import cache

import tess_dl
from tess_dl import Document, Value

__all__ = ["value_text", "key_problem", "quote", "parse_number", "normal_colour", "colour_text", "format_number", "is_reference", "EXPRESSION_STUB"]

#: What an expression's field holds before the person types inside it.
EXPRESSION_STUB = "{{  }}"

_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t"}
_NUMBER = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)$")
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_REFERENCE = re.compile(r"^\$[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")


def value_text(document: Document, value: Value) -> str:
    """The text of `value` exactly as the file has it (a list, a call or an expression included)."""
    return document.text[value.start:value.end]


@cache
def key_problem(name: str) -> str:
    """Why `tess_dl` will not write a property called `name` (a word the language reserves, a name that is not one), or `''` when it will. Asked of `tess_dl` itself, once for each name."""
    root = tess_dl.loads("---\nTDL: 0.1\nName: Probe\n---\nProbe { }\n").root
    try:
        root.with_property(name, "0")
    except (ValueError, tess_dl.TDLError) as error:
        return str(getattr(error, "message", error))
    return ""


def quote(text: str) -> str:
    """`text` as a TDL string: double quotes, with the backslash, the quote, the new line and the tab escaped."""
    return '"' + "".join(_ESCAPES.get(c, c) for c in text) + '"'


def is_reference(text: str) -> bool:
    """`$group.name`: a theme token."""
    return bool(_REFERENCE.match(text.strip()))


def parse_number(text: str) -> Decimal | None:
    """The number a person typed, or `None` when it is not one (a trailing unit word or a stray character is not a number)."""
    text = text.strip()
    if not _NUMBER.match(text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:  # pragma: no cover - the pattern keeps these out
        return None


def format_number(value: Decimal) -> str:
    """A number as TDL writes it: `12`, `-1.5`, `0.25` (no exponent, no trailing zeros)."""
    text = format(value.normalize(), "f")
    return "0" if text in ("-0", "") else text


def normal_colour(text: str) -> str | None:
    """A TDL colour string's content (`#RGB`, `#RGBA`, `#RRGGBB`, `#RRGGBBAA`) as the picker's `#rrggbb` or `#rrggbbaa`; `None` when it is not one of those forms."""
    text = text.strip()
    if not _HEX.match(text):
        return None
    digits = text[1:].lower()
    if len(digits) in (3, 4):
        digits = "".join(c * 2 for c in digits)
    if len(digits) == 8 and digits.endswith("ff"):
        digits = digits[:6]
    return "#" + digits


def colour_text(picker_value: str) -> str:
    """The picker's `#rrggbb` (or `#rrggbbaa`) as the quoted upper-case colour the shell's own files use: `"#4682B4"`."""
    return quote("#" + picker_value.lstrip("#").upper())
