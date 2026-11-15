"""Component macro-expansion: a node `{id, component: Name, with: {...}}` expands to the fragment `Name`'s own kind-tree subtree (`id`/`kind`/`style`/
`text`/`children`, the shape `tess_ui.View(spec)` builds from). The fragments are Tesserae's own, plain data in `spec/fragments.py`: the Python widget
factories (`widgets.button()`, the overlays) build from them. An app's own views, stylesheets and themes are TDL and do not come through here.

What a fragment can use:

* `params:` -- names (required) or `{name: default}` (optional); a call gives them in `with:`. A value that is exactly one `{{ name }}` keeps the given
  value's own type (a number stays a number); a placeholder inside a longer string is interpolated as text.
* `{if: c, then: a, else: b}` as a value, and `when: c` on a `children:` entry -- expansion-time conditionals, decided once the params are in.
* `repeat: [...]` on a `component:` entry in `children:` -- one instance per entry (ids `<call id>.<index>`), the entry's keys on top of the shared `with:`.
* The component's `sheet`: the look of each part, put under the `style` the tree gives the part itself, with the same params filled in.

Ids are namespaced: the call's `id` is the root's, a part's is `<call id>.<part>`. The root is tagged `component_of: Name` (the theme's `components:`
entry for it). A call can also carry `handlers`, `bindings`, `two_way`, `a11y`, `interaction`, `classes` and `window_region` for the root.
"""

from __future__ import annotations

import re
from typing import Any

from tess_ui.spec.fragments import FRAGMENTS

__all__ = ["ComponentError", "expand_components_to_spec"]

_COMPONENT_KEY = "component"
_WITH_KEY = "with"
_ID_KEY = "id"
_CHILDREN_KEY = "children"
_REPEAT_KEY = "repeat"
_WHEN_KEY = "when"
_IF_KEYS = {"if", "then", "else"}

#: A guard against pathological nesting, not a depth any real component tree needs.
MAX_DEPTH = 16

_WHOLE_PARAM_RE = re.compile(r"^\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}$")
_PARAM_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class ComponentError(ValueError):
    """A `component:` reference that cannot be expanded, with the call chain that led to it. (The picture loaders raise it too.)"""


def _chain_text(chain: tuple[str, ...]) -> str:
    return " -> ".join(chain) if chain else "<root>"


def _plain(node: Any) -> Any:
    """A copy of `node` made of dicts and lists only (a tuple becomes a list), so no caller's object is shared with, or edited through, the spec."""
    if isinstance(node, dict):
        return {k: _plain(v) for k, v in node.items()}
    if isinstance(node, (list, tuple)):
        return [_plain(v) for v in node]
    return node


def _substitute(node: Any, values: dict[str, Any]) -> Any:
    """Replaces every `{{ name }}` in `node` with its supplied value: the value itself when the string is exactly one placeholder, else interpolated."""
    if isinstance(node, str):
        whole = _WHOLE_PARAM_RE.match(node)
        if whole:
            name = whole.group(1)
            return values.get(name, node)
        return _PARAM_RE.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), node)
    if isinstance(node, dict):
        return {k: _substitute(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [_substitute(v, values) for v in node]
    return node


def _truthy(value: Any) -> bool:
    """A condition after substitution: `None`, `""`, `false`, `0`, an empty list or mapping, and the strings "false"/"no"/"null"/"none" (any case) are
    false; everything else is true."""
    if isinstance(value, str):
        return value.strip().lower() not in ("", "false", "no", "null", "none", "0")
    return bool(value)


#: A conditional with no `else:` that isn't taken: its key is left out.
_DROP = object()


def _resolve_conditionals(node: Any, where: str) -> Any:
    """A fragment's expansion-time conditionals, once its params are substituted: `{if: c, then: a, else: b}` becomes `a` when `c` is truthy, else `b` (or
    is left out, with no `else:`); a `children:` entry with `when: c` is kept only when `c` is truthy, and loses the `when:` key."""
    if isinstance(node, list):
        out = []
        for item in node:
            if isinstance(item, dict) and _WHEN_KEY in item:
                keep = _truthy(item[_WHEN_KEY])
                item = {k: v for k, v in item.items() if k != _WHEN_KEY}
                if not keep:
                    continue
            out.append(_resolve_conditionals(item, where))
        return [v for v in out if v is not _DROP]
    if isinstance(node, dict):
        if "if" in node:
            extra = set(node) - _IF_KEYS
            if extra or "then" not in node:
                raise ComponentError(f"{where}: a conditional value is {{if: ..., then: ..., else: ...}} "
                                     f"(`else:` optional); got keys {sorted(node)}")
            chosen = node["then"] if _truthy(node["if"]) else node.get("else", _DROP)
            return _DROP if chosen is _DROP else _resolve_conditionals(chosen, where)
        out_map = {}
        for key, value in node.items():
            resolved = _resolve_conditionals(value, where)
            if resolved is not _DROP:
                out_map[key] = resolved
        return out_map
    return node


def _declared_params(declared: Any, name: str) -> tuple[list[str], dict[str, Any]]:
    """`params:` as names and defaults: each entry is a name (a required param) or a one-key mapping `{name: default}` (optional)."""
    if not isinstance(declared, list):
        raise ComponentError(f"{name}: `params:` must be a list of names")
    names: list[str] = []
    defaults: dict[str, Any] = {}
    for entry in declared:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict) and len(entry) == 1 and isinstance(next(iter(entry)), str):
            param, default = next(iter(entry.items()))
            names.append(param)
            defaults[param] = default
        else:
            raise ComponentError(f"{name}: a `params:` entry is a name or {{name: default}}, got {entry!r}")
    return names, defaults


def _namespace_ids(node: Any, prefix: str) -> Any:
    """Prefixes every `id:` inside `node` with `prefix.`, except the fragment's own root `id:`, which the caller renames to `prefix` itself."""
    if isinstance(node, list):
        return [_namespace_ids(v, prefix) for v in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == _ID_KEY and isinstance(value, str):
            out[key] = f"{prefix}.{value}"
        else:
            out[key] = _namespace_ids(value, prefix)
    return out


def _parts_of(node: Any) -> set[str]:
    """Every `id:` in a fragment's tree: its parts."""
    found: set[str] = set()
    if isinstance(node, dict):
        if isinstance(node.get(_ID_KEY), str):
            found.add(node[_ID_KEY])
        for child in node.get(_CHILDREN_KEY) or []:
            found |= _parts_of(child)
    return found


def _apply_sheet(node: Any, rules: dict[str, dict[str, Any]], where: str) -> None:
    """Puts each part's sheet rule under the style the fragment gives it itself."""
    if not isinstance(node, dict):
        return
    part = node.get(_ID_KEY)
    if part in rules:
        if _COMPONENT_KEY in node:
            raise ComponentError(f"{where}: {part!r} is a `component:` call: style it through its own `with:`")
        node["style"] = {**rules[part], **(node.get("style") or {})}
    for child in node.get(_CHILDREN_KEY) or []:
        _apply_sheet(child, rules, where)


def _expand_component(node: dict[str, Any], chain: tuple[str, ...]) -> list[dict[str, Any]]:
    """Replaces one `{component: Name, with: {...}}` node with the fragment(s) it names, fully expanded and namespaced: one element normally, or one per
    `repeat:` entry."""
    if len(chain) >= MAX_DEPTH:
        raise ComponentError(f"{_chain_text(chain)}: components nested more than {MAX_DEPTH} deep")

    name = node[_COMPONENT_KEY]
    if not isinstance(name, str):
        raise ComponentError(f"{_chain_text(chain)}: `component:` must be a string, got {name!r}")
    if name in chain:
        raise ComponentError(f"component cycle: {_chain_text((*chain, name))}")

    call_id = node.get(_ID_KEY)
    if not isinstance(call_id, str):
        raise ComponentError(
            f"{_chain_text((*chain, name))}: a `component:` entry needs its own `id:` "
            "(used to namespace the fragment's own internal ids)"
        )

    entry = FRAGMENTS.get(name)
    if entry is None:
        raise ComponentError(f"unknown component {name!r} -- the built-in ones are {', '.join(sorted(FRAGMENTS))}")
    template = entry["tree"]
    sheet = entry.get("sheet") or {}
    unknown_parts = set(sheet) - _parts_of(template)
    if unknown_parts:
        raise ComponentError(f"{_chain_text((*chain, name))}: the sheet of {name} styles {sorted(unknown_parts)}, "
                             f"which {name} has no part of (its parts are {sorted(_parts_of(template))})")
    declared, defaults = _declared_params(entry.get("params") or [], name)

    with_supplied = node.get(_WITH_KEY) or {}
    if not isinstance(with_supplied, dict):
        raise ComponentError(f"{_chain_text((*chain, name))}: `with:` must be a mapping")

    extra = set(node) - {_COMPONENT_KEY, _WITH_KEY, _ID_KEY, _REPEAT_KEY} - set(_CALL_KEYS)
    if extra:
        raise ComponentError(
            f"{_chain_text((*chain, name))}: a `component:` node takes `id:`, `with:`, `repeat:`, and "
            f"{', '.join(f'`{k}:`' for k in _CALL_KEYS)} for its root; got {sorted(extra)}. "
            "Pass configuration as parameters."
        )
    call_keys = _call_keys(node, (*chain, name))

    # `repeat:`: one iteration per entry, each a mapping of per-item values on top of the shared `with:` values. A key given in both is rejected rather
    # than letting one win.
    repeat_items = node.get(_REPEAT_KEY)
    if repeat_items is None:
        iterations = [(call_id, dict(with_supplied))]
    else:
        if not isinstance(repeat_items, list):
            raise ComponentError(
                f"{_chain_text((*chain, name))}: `repeat:` must be a list of mappings, got {type(repeat_items).__name__}"
            )
        iterations = []
        for index, item in enumerate(repeat_items):
            if not isinstance(item, dict):
                raise ComponentError(
                    f"{_chain_text((*chain, name))}: `repeat:` entry {index} must be a mapping, got {type(item).__name__}"
                )
            overlap = set(item) & set(with_supplied)
            if overlap:
                raise ComponentError(
                    f"{_chain_text((*chain, name))}: `repeat:` entry {index} repeats "
                    f"key(s) {sorted(overlap)} already given in `with:` -- a value "
                    "that varies per item belongs in `repeat:`, a shared one in `with:`, "
                    "not both"
                )
            iterations.append((f"{call_id}.{index}", {**with_supplied, **item}))

    results = []
    for local_call_id, supplied in iterations:
        supplied = _plain({**defaults, **supplied})
        missing = [p for p in declared if p not in supplied]
        if missing:
            raise ComponentError(
                f"{_chain_text((*chain, name))}: missing parameter(s) {missing} for {local_call_id!r}; {name} declares {declared}"
            )
        unknown = [k for k in supplied if k not in declared]
        if unknown:
            raise ComponentError(
                f"{_chain_text((*chain, name))}: unknown parameter(s) {unknown} for "
                f"{local_call_id!r}; {name} declares {declared or '[]'}"
            )

        fragment = _resolve_conditionals(_substitute(template, supplied), f"{name} ({local_call_id!r})")
        if sheet:  # the component's sheet, with the same parameters filled in
            _apply_sheet(fragment, _resolve_conditionals(_substitute(sheet, supplied), f"the sheet of {name}"),
                         f"the sheet of {name}")

        # A `component:` inside the fragment is expanded before namespacing: its ids get the OUTER call's id too, once.
        fragment = _walk(fragment, (*chain, name))

        local_id = fragment.get(_ID_KEY)
        fragment = _namespace_ids(fragment, local_call_id)
        if isinstance(local_id, str):
            fragment[_ID_KEY] = local_call_id  # the root gets the call's id itself, not a prefixed one
        if isinstance(fragment, dict):
            fragment.setdefault("component_of", name)  # its theme `components:` entry
            _apply_call_keys(fragment, call_keys)
        results.append(fragment)

    return results


#: What a `component:` call puts on the fragment's root: the view's own wiring and naming, not the fragment's look (that's its params).
_CALL_KEYS = ("handlers", "bindings", "two_way", "a11y", "interaction", "classes", "window_region")
_CALL_MAPPINGS = ("handlers", "bindings", "a11y", "interaction")


def _call_keys(node: dict[str, Any], chain: tuple[str, ...]) -> dict[str, Any]:
    """The call's root keys, checked. They're the view's: their `{{ }}` are its bindings, so they aren't substituted with the fragment's params."""
    keys = {k: _plain(node[k]) for k in _CALL_KEYS if k in node}
    for key in _CALL_MAPPINGS:
        if key in keys and not isinstance(keys[key], dict):
            raise ComponentError(f"{_chain_text(chain)}: `{key}:` on a `component:` node must be a mapping")
    if "two_way" in keys and not isinstance(keys["two_way"], str):
        raise ComponentError(f"{_chain_text(chain)}: `two_way:` on a `component:` node must be a property name")
    classes = keys.get("classes")
    if classes is not None and not (isinstance(classes, list) and all(isinstance(c, str) for c in classes)):
        raise ComponentError(f"{_chain_text(chain)}: `classes:` on a `component:` node must be a list of names")
    return keys


def _apply_call_keys(root: dict[str, Any], keys: dict[str, Any]) -> None:
    """Puts a call's keys on the fragment's root: mappings merged key by key (the call's win), `two_way:` replaced, `classes:` added."""
    for key, value in keys.items():
        if key in _CALL_MAPPINGS:
            root[key] = {**(root.get(key) or {}), **value}
        elif key == "classes":
            root[key] = [*(root.get(key) or []), *(c for c in value if c not in (root.get(key) or []))]
        else:
            root[key] = value


def _walk(node: Any, chain: tuple[str, ...]) -> Any:
    if isinstance(node, list):
        out: list[Any] = []
        for item in node:
            if isinstance(item, dict) and _COMPONENT_KEY in item:
                out.extend(_expand_component(dict(item), chain))
            else:
                out.append(_walk(item, chain))
        return out
    if not isinstance(node, dict):
        return node
    if _COMPONENT_KEY in node:
        results = _expand_component(dict(node), chain)
        if len(results) != 1:
            raise ComponentError(
                f"{_chain_text(chain)}: `repeat:` produced {len(results)} nodes, but this "
                "position needs exactly one -- `repeat:` is only valid on a `component:` "
                "entry inside a `children:` list"
            )
        return results[0]
    return {k: (_walk(v, chain) if k == _CHILDREN_KEY else v) for k, v in node.items()}


def expand_components_to_spec(spec: dict[str, Any]) -> Any:
    """Expands every `component:` entry in `spec` (a node, or a tree with such nodes in its `children:`), returning the finished kind-tree dict with no
    `component:`/`with:`/`params:`/`repeat:` keys remaining, ready for `tess_ui.View(spec)`. `spec` itself is not changed."""
    return _walk(_plain(spec), ())
