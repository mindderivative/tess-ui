"""A test-only converter from a shipped YAML view to TDL (the seed of piece 2's `tesserae migrate-tdl`), and the one rule it has to bend.

`yaml_to_tdl(text, name)` writes the view as TDL the front end (`tess_ui.spec.tdl`) reads back to the same mapping: keys `Title_Case`, a node a block
headed by its widget, `If`/`For` wrappers, handlers as `Set`/`Call` step blocks, slots `<| expr |>`. It keeps no comments and no layout (the real
converter will). It refuses what it cannot write back exactly instead of writing something near it.

The one bent rule: **a `for:` with a pair target (`i, it in enumerate(items)`) has no TDL form yet** (a TDL `For` has one variable). The helper writes
the loop with one variable named by joining the pair (`i_it`) over the same expression and returns each one it did that to; the body's references to
`i` and `it` are NOT rewritten (that is piece 2's decision). `with_single_variable(data)` makes the YAML mapping say the same, so the two can be compared.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from tess_ui.expr import _closing, is_action_name
from tess_ui.spec import marker
from tess_ui.spec.nodes import PMap, load_marked
from tess_ui.spec.tdl import snake_case, title_case

_FOR = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)\s+in\s+(.+?)\s*$", re.S)
_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*$")
_NUMBER = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
_RESERVED = {"If", "Else", "For", "In", "Key"}
#: What a node's mapping has that is not a property or a map of its own.
_WRAPPER_KEYS = ("widget", "if", "for", "key")


def single_variable(target: str) -> str:
    """The one variable a pair target is written with: `i, it` -> `i_it`."""
    return "_".join(t.strip() for t in target.split(","))


def with_single_variable(data: Any) -> list[str]:
    """Rewrites every pair-target `for:` in the YAML mapping `data` in place to the form `yaml_to_tdl` writes; returns the original texts."""
    found: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            value = item.get("for")
            match = _FOR.match(value) if isinstance(value, str) else None
            if match and "," in match.group(1):
                found.append(value)
                item["for"] = f"{single_variable(match.group(1))} in {match.group(2)}"
            for sub in item.values():
                walk(sub)
        elif isinstance(item, list):
            for sub in item:
                walk(sub)

    walk(data)
    return found


# -- values ----------------------------------------------------------------------------------------------------------------


def key_of(snake: str) -> str:
    key = title_case(snake)
    if snake_case(key) != snake or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key) or key in _RESERVED:
        raise ValueError(f"the key '{snake}' has no TDL form ({key!r})")
    return key


def slot(expr: str) -> str:
    text = expr.strip()
    if "|>" in text or "\n" in text:
        raise ValueError(f"an expression that cannot sit in a slot: {expr!r}")
    return f"<| {text} |>"


def split_template(text: str) -> list[tuple[bool, str]]:
    """`(is_slot, text)` parts: a slot's text is exactly what lies between `{{` and `}}`."""
    parts: list[tuple[bool, str]] = []
    i, literal = 0, 0
    while i < len(text):
        if text.startswith("{{", i):
            end = _closing(text, i + 2)
            if end is None:
                raise ValueError(f"a '{{{{' is never closed: {text!r}")
            if literal < i:
                parts.append((False, text[literal:i]))
            parts.append((True, text[i + 2:end]))
            i = literal = end + 2
        else:
            i += 1
    if literal < len(text):
        parts.append((False, text[literal:]))
    return parts


def scalar(v: Any) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        text = repr(v)
        if not _NUMBER.match(text):
            raise ValueError(f"a number TDL reads differently: {text}")
        return text
    assert isinstance(v, str), v
    if "{{" in v:
        parts = split_template(v)
        if len(parts) == 1 and parts[0][0]:
            return f"<|{parts[0][1]}|>"
        text = "".join(f"<|{t}|>" if is_slot else t for is_slot, t in parts)
        literal = "".join(t for is_slot, t in parts if not is_slot)
        if (text != text.strip() or "\n" in text or text[0] in "\"'[#" or any(c in literal for c in "{},]") or " #" in literal or "<|" in literal
                or any(any(c in t for c in "\r") for _, t in parts)):
            raise ValueError(f"text with a slot that cannot be written unquoted: {v!r}")
        return text
    if _WORD.match(v) and v not in ("true", "false", "null"):
        return v
    out = json.dumps(v, ensure_ascii=False)
    if re.search(r"\\[bfr/]", out):
        raise ValueError(f"a string with a control character: {v!r}")
    return out


def value(v: Any) -> str:
    if isinstance(v, list):
        if any(isinstance(i, (dict, list)) for i in v):
            raise ValueError("a list of containers has no property form")
        return "[" + ", ".join(scalar(i) for i in v) + "]"
    return scalar(v)


# -- handlers --------------------------------------------------------------------------------------------------------------


def steps(text: str) -> list[str]:
    """A handler's statements as `Set` and `Call` step blocks (one line each)."""
    out: list[str] = []
    for s in ast.parse(text.strip()).body:
        if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name):
            out.append(f"Set {{ Target: {s.targets[0].id}, Value: {slot(ast.unparse(s.value))} }}")
        elif isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name):
            out.append(f"Set {{ Target: {s.target.id}, Value: {slot(ast.unparse(ast.BinOp(ast.Name(s.target.id, ast.Load()), s.op, s.value)))} }}")
        elif isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and not any(isinstance(a, ast.Starred) for a in s.value.args):
            args = ", ".join(slot(ast.unparse(a)) for a in s.value.args)
            kw = "".join(f", {key_of(k.arg)}: {slot(ast.unparse(k.value))}" for k in s.value.keywords if k.arg)
            out.append(f'Call {{ Action: {json.dumps(ast.unparse(s.value.func))}{", Args: [" + args + "]" if args else ""}{kw} }}')
        else:
            raise ValueError(f"a statement with no step form: {ast.unparse(s)}")
    return out


def handlers(d: dict[str, Any], ind: str) -> list[str]:
    lines = [f"{ind}Handlers {{"]
    for event, text in d.items():
        if isinstance(text, str) and is_action_name(text):
            lines.append(f"{ind}  {key_of(event)}: {value(text.strip())}")
        else:
            lines += [f"{ind}  {key_of(event)} {{", *[f"{ind}    {s}" for s in steps(text)], f"{ind}  }}"]
    lines.append(f"{ind}}}")
    return lines


# -- nodes -----------------------------------------------------------------------------------------------------------------


def mapping(key: str, d: dict[str, Any], ind: str) -> list[str]:
    lines = [f"{ind}{key_of(key)} {{"]
    for k, v in d.items():
        if isinstance(v, dict):
            lines += mapping(k, v, ind + "  ")
        else:
            lines.append(f"{ind}  {key_of(k)}: {value(v)}")
    lines.append(f"{ind}}}")
    return lines


def node(n: dict[str, Any], ind: str) -> list[str]:
    lines = [f"{ind}{n['widget']} {{"]
    for k, v in n.items():
        if k in _WRAPPER_KEYS:
            continue
        if k == "children":
            lines.append(f"{ind}  Children {{")
            for c in v:
                lines += node(c, ind + "    ")
            lines.append(f"{ind}  }}")
        elif k == "handlers":
            lines += handlers(v, ind + "  ")
        elif isinstance(v, dict):
            lines += mapping(k, v, ind + "  ")
        else:
            lines.append(f"{ind}  {key_of(k)}: {value(v)}")
    lines.append(f"{ind}}}")
    if "if" in n:
        lines = [f"{ind}If {slot(n['if'])} {{", *["  " + line for line in lines], f"{ind}}}"]
    if "for" in n:
        match = _FOR.match(n["for"])
        assert match, n["for"]
        variable = single_variable(match.group(1))
        lines = [f"{ind}For {variable} In {slot(match.group(2))} Key {slot(n.get('key', 'None'))} {{", *["  " + line for line in lines], f"{ind}}}"]
    elif "key" in n:
        raise ValueError("a key: without a for:")
    return lines


def yaml_to_tdl(text: str, name: str) -> str:
    """The TDL text for the YAML view in `text`; `name` is the file's `Name`. Pair-target loops are written with one variable (see the module)."""
    data = load_marked(text)
    assert isinstance(data, PMap)
    series = marker.scan(text).value
    d = dict(data)
    head = ["---", "TDL: 0.1", f"Name: {name}"] + ([f'Tesserae: "{series}"'] if series else []) + ["---", ""]
    return "\n".join([*head, *node(d, "")]) + "\n"
