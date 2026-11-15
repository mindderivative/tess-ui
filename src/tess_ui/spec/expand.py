"""Component macro-expansion: `component: Name` / `with: {...}` in a spec expands to the referenced `*_Component.yaml` fragment's own
`WidgetSpec`-shaped subtree. The fragments are the ones Tesserae ships in `spec/components/` (the Python widget factories, `widgets.button()` and the
overlays, build from them); an app's own views, stylesheets and themes are TDL and do not come through here. Modeled directly on pyCopper's own real,
proven `source:`/`with:`/`params:` design (`pycopper/spec/include.py`), adapted to `tess_re`'s real schema (`id`/`kind`/`style`/`text`/`children`, confirmed
against `engine-spec/src/spec.rs` -- no `anchor:`-style cross-reference field exists, so only `id:` needs namespacing, unlike pyCopper's own `name:`+
`anchor:` pair).

M28: `repeat:` lets one `component:` entry expand to N sibling
instances from a literal, static list of per-item overrides -- real,
deliberately narrow scope, confirmed against `tess_re`'s own imperative
`add_list` first: it takes pre-built `Node`s and does pure layout
composition (`window_factory.rs`, no `NodeKind::List` primitive at
all), meaning "a list" is *already* expressible today as a plain
`kind: Container` with N `ListItem` children -- the real, missing
capability isn't a primitive, it's repeating a fragment call without
hand-duplicating N near-identical `component:` blocks. Deliberately
NOT reactive -- `repeat:`'s own items are known at macro-expansion
time, before `tess_re` ever sees the spec, so an app wanting
runtime-changing content (items added/removed, live reordering) uses a `For` in its view, not this. Checked
`pyCopper` directly (M26/M28's own scoping) -- no repeat/loop construct
exists there at all, confirming this is genuinely new design territory,
not a port.

Real, load-bearing design point: `{{ param }}` substitution preserves
the supplied value's own real Python type (int/float/bool/str) when a
string is *exactly* one placeholder with nothing else around it --
verified necessary directly: PyYAML's `safe_dump` quotes a numeric-
looking Python `str`, which would turn `width: "{{ width }}"` into
`width: '120'` after substitution -- a quoted string `tess_re`'s own
`serde_yaml_ng` parser rejects for an `f32` field. Only genuinely mixed
strings (a placeholder embedded in surrounding text) fall back to plain
string interpolation, where stringifying is correct. This same
whole-value rule is what lets `with: {label: "{{ some_signal.get() }}"}`
forward a live `tess_re` binding expression through untouched -- the
supplied value is itself the string `"{{ some_signal.get() }}"`, so a
whole-value substitution reproduces it exactly, for `tess_re`'s own
`binding.rs` to resolve later at `View._attach()` time.
"""

from __future__ import annotations

import contextvars
import datetime
import re
from pathlib import Path
from typing import Any

import yaml

__all__ = ["ComponentError", "expand_components", "expand_components_to_spec"]

_COMPONENT_KEY = "component"
_WITH_KEY = "with"
_PARAMS_KEY = "params"
_ID_KEY = "id"
_CHILDREN_KEY = "children"
_REPEAT_KEY = "repeat"
_WHEN_KEY = "when"
_IF_KEYS = {"if", "then", "else"}

#: A guard against pathological/adversarial nesting, not a real depth
#: any legitimate component tree needs: it allows real component-
#: composing-component nesting (e.g. a `Card` fragment using `component:
#: Button` inside it) some real headroom without being unbounded.
MAX_DEPTH = 16

_WHOLE_PARAM_RE = re.compile(r"^\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}$")
_PARAM_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class ComponentError(ValueError):
    """A `component:` reference that cannot be expanded, with the call
    chain that led to it."""


def _chain_text(chain: tuple[str, ...]) -> str:
    return " -> ".join(chain) if chain else "<root>"


def _substitute(node: Any, values: dict[str, Any]) -> Any:
    """Replace every `{{ name }}` in `node` with its supplied value.

    A string that is *exactly* one placeholder (optionally surrounded by
    whitespace, nothing else) is replaced with the supplied value's own
    real type -- required so a numeric param round-trips as a real YAML
    number, not a quoted string. A placeholder embedded in a larger
    string is replaced via plain string interpolation instead.
    """
    if isinstance(node, str):
        whole = _WHOLE_PARAM_RE.match(node)
        if whole:
            name = whole.group(1)
            return values[name] if name in values else node
        return _PARAM_RE.sub(
            lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), node
        )
    if isinstance(node, dict):
        return {k: _substitute(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [_substitute(v, values) for v in node]
    return node


def _truthy(value: Any) -> bool:
    """A condition after substitution: `None`, `""`, `false`, `0`,
    an empty list or mapping, and the strings "false"/"no"/"null"/"none"
    (any case) are false; everything else is true."""
    if isinstance(value, str):
        return value.strip().lower() not in ("", "false", "no", "null", "none", "0")
    return bool(value)


def _resolve_conditionals(node: Any, where: str) -> Any:
    """M55: a fragment's expansion-time conditionals, once its params are
    substituted. A value `{if: c, then: a, else: b}` becomes `a` when `c`
    is truthy, else `b` (or is left out, with no `else:`); a `children:`
    entry with `when: c` is kept only when `c` is truthy, and loses the
    `when:` key."""
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


#: A conditional with no `else:` that isn't taken: its key is left out.
_DROP = object()


def _declared_params(declared: Any, path: Path) -> tuple[list[str], dict[str, Any]]:
    """`params:` as names and defaults: each entry is a name (a
    required param) or a one-key mapping `{name: default}` (optional)."""
    if not isinstance(declared, list):
        raise ComponentError(f"{path}: `params:` must be a list of names")
    names: list[str] = []
    defaults: dict[str, Any] = {}
    for entry in declared:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict) and len(entry) == 1 and isinstance(next(iter(entry)), str):
            name, default = next(iter(entry.items()))
            names.append(name)
            defaults[name] = default
        else:
            raise ComponentError(f"{path}: a `params:` entry is a name or {{name: default}}, got {entry!r}")
    return names, defaults


def _namespace_ids(node: Any, prefix: str) -> Any:
    """Prefix every `id:` inside `node` with `prefix.`, except the
    fragment's own root `id:`, which the caller already renamed to
    `prefix` directly (mirrors pyCopper's own `_namespace_names`,
    adapted from `name:`/`anchor:` to `tess_re`'s single `id:` field --
    `WidgetSpec` has no cross-reference field an id-rename could break).
    """
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


#: Tesserae's own fragments and their stylesheets.
COMPONENTS = Path(__file__).parent / "components"
STYLESHEET_SUFFIX = "_Stylesheet.yaml"


#: The folders fragments are searched in, in order: Tesserae's own, unless a caller of `expand_components_to_spec` gave its own list.
_DIRS: contextvars.ContextVar[list[Path]] = contextvars.ContextVar("tesserae_component_dirs", default=[COMPONENTS])


def _find_component_file(name: str) -> tuple[Path, int]:
    """The fragment's file, and the index of the folder it was found in."""
    dirs = _DIRS.get()
    for index, directory in enumerate(dirs):
        candidate = directory / f"{name}_Component.yaml"
        if candidate.is_file():
            return candidate, index
    raise ComponentError(f"unknown component {name!r} -- searched {', '.join(str(d) for d in dirs)}")


def _parts_of(node: Any) -> set[str]:
    """Every `id:` in a fragment: its parts."""
    found: set[str] = set()
    if isinstance(node, dict):
        if isinstance(node.get(_ID_KEY), str):
            found.add(node[_ID_KEY])
        for child in node.get(_CHILDREN_KEY) or []:
            found |= _parts_of(child)
    return found


def _component_sheet(name: str, found_in: int) -> dict[str, dict[str, Any]]:
    """A component's stylesheet: `<name>_Stylesheet.yaml` rules, `{part id: style}`.

    The look of a component lives in its stylesheet, the fragment holding only its structure. The sheet is read from the fragment's own folder and from
    each folder searched before it, field by field over the later one's. A folder after the fragment's is not read: the fragment shadows the whole
    component."""
    rules: dict[str, dict[str, Any]] = {}
    for directory in reversed(_DIRS.get()[: found_in + 1]):
        path = directory / f"{name}{STYLESHEET_SUFFIX}"
        if not path.is_file():
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ComponentError(f"{path}: invalid YAML: {exc}") from exc
        except OSError as exc:
            raise ComponentError(f"cannot read {path}: {exc}") from exc
        listed = raw.get("styles") if isinstance(raw, dict) and set(raw) <= {"styles"} else None
        if not isinstance(listed, list):
            raise ComponentError(f"{path}: a component's stylesheet is `styles:`, a list of `{{id: <part>, style: {{...}}}}` rules")
        for rule in listed:
            if not (isinstance(rule, dict) and set(rule) == {"id", "style"} and isinstance(rule["id"], str)
                    and isinstance(rule["style"], dict)):
                raise ComponentError(f"{path}: each rule is `{{id: <part>, style: {{...}}}}`, got {rule!r}")
            rules[rule["id"]] = {**rules.get(rule["id"], {}), **rule["style"]}
    return rules


def _apply_sheet(node: Any, rules: dict[str, dict[str, Any]], where: str) -> None:
    """Puts each part's stylesheet rule under the style the fragment gives it itself."""
    if not isinstance(node, dict):
        return
    part = node.get(_ID_KEY)
    if part in rules:
        if _COMPONENT_KEY in node:
            raise ComponentError(f"{where}: {part!r} is a `component:` call: style it through its own `with:`")
        node["style"] = {**rules[part], **(node.get("style") or {})}
    for child in node.get(_CHILDREN_KEY) or []:
        _apply_sheet(child, rules, where)


def _load_fragment(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ComponentError(f"{path}: invalid YAML: {exc}") from exc
    except OSError as exc:
        raise ComponentError(f"cannot read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ComponentError(f"{path}: a component fragment must be a mapping, got {type(raw).__name__}")
    return raw



def _normalize_scalars(node: Any) -> Any:
    """PyYAML's `safe_load` turns an unquoted `2026-09-24` into a
    `datetime.date`, which `tess_re`'s `spec=` depythonizer can't read into a
    string field. The old text round-trip (`safe_dump` then `tess_re`'s own
    `serde_yaml_ng` parse) turned it back into the string `"2026-09-24"`;
    `str()` gives that exact same string, so `spec=` sees what the text
    path used to."""
    if isinstance(node, list):
        return [_normalize_scalars(v) for v in node]
    if isinstance(node, dict):
        return {k: _normalize_scalars(v) for k, v in node.items()}
    if isinstance(node, (datetime.date, datetime.datetime)):
        return str(node)
    return node


def _expand_component(
    node: dict[str, Any],
    chain: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Replace one `{component: Name, with: {...}}` node with the
    fragment(s) it names, fully expanded and namespaced -- one element
    normally, or one per real `repeat:` entry."""
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

    path, found_in = _find_component_file(name)
    fragment_template = _load_fragment(path)
    sheet = _component_sheet(name, found_in)
    unknown_parts = set(sheet) - _parts_of(fragment_template)
    if unknown_parts:
        raise ComponentError(f"{_chain_text((*chain, name))}: {name}{STYLESHEET_SUFFIX} styles "
                             f"{sorted(unknown_parts)}, which {name} has no part of (its parts are {sorted(_parts_of(fragment_template))})")
    declared, defaults = _declared_params(fragment_template.pop(_PARAMS_KEY, []) or [], path)

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

    # M28: `repeat:` -- one iteration per entry, each a mapping of
    # per-item values merged on top of the shared `with:` values. A
    # real key given in both is rejected rather than silently letting
    # one win, matching this module's own "fail loudly on ambiguity"
    # convention every other real check here already follows.
    repeat_items = node.get(_REPEAT_KEY)
    if repeat_items is None:
        iterations = [(call_id, dict(with_supplied))]
    else:
        if not isinstance(repeat_items, list):
            raise ComponentError(
                f"{_chain_text((*chain, name))}: `repeat:` must be a list of mappings, "
                f"got {type(repeat_items).__name__}"
            )
        iterations = []
        for index, item in enumerate(repeat_items):
            if not isinstance(item, dict):
                raise ComponentError(
                    f"{_chain_text((*chain, name))}: `repeat:` entry {index} must be a "
                    f"mapping, got {type(item).__name__}"
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
        supplied = {**defaults, **supplied}
        missing = [p for p in declared if p not in supplied]
        if missing:
            raise ComponentError(
                f"{_chain_text((*chain, name))}: missing parameter(s) {missing} for "
                f"{local_call_id!r}; {name} declares {declared}"
            )
        unknown = [k for k in supplied if k not in declared]
        if unknown:
            raise ComponentError(
                f"{_chain_text((*chain, name))}: unknown parameter(s) {unknown} for "
                f"{local_call_id!r}; {name} declares {declared or '[]'}"
            )

        fragment = _resolve_conditionals(_substitute(fragment_template, supplied), f"{path.name} ({local_call_id!r})")
        if sheet:  # the component's stylesheet, with the same parameters filled in
            _apply_sheet(fragment, _resolve_conditionals(_substitute(sheet, supplied), f"{name}{STYLESHEET_SUFFIX}"),
                         f"{name}{STYLESHEET_SUFFIX}")

        # Resolve any `component:` usage inside the fragment itself
        # before namespacing -- a nested fragment's own ids get
        # namespaced by the OUTER call site's id too, once, not twice.
        fragment = _walk(fragment, (*chain, name))

        local_id = fragment.get(_ID_KEY)
        fragment = _namespace_ids(fragment, local_call_id)
        if isinstance(local_id, str):
            # The fragment's own root gets the call site's id directly,
            # not a further "local_call_id.local_call_id"-prefixed one.
            fragment[_ID_KEY] = local_call_id
        if isinstance(fragment, dict):
            # its theme `components:` entry (M57): the fragment's own, if it names one
            fragment.setdefault("component_of", name)
            _apply_call_keys(fragment, call_keys)
        results.append(fragment)

    return results


#: What a `component:` call puts on the fragment's root (M69): the view's
#: own wiring and naming, not the fragment's look (that's its params).
_CALL_KEYS = ("handlers", "bindings", "two_way", "a11y", "interaction", "classes",
              "window_region")  # 0.3.0 M3: a fragment can be (part of) the title bar
_CALL_MAPPINGS = ("handlers", "bindings", "a11y", "interaction")


def _call_keys(node: dict[str, Any], chain: tuple[str, ...]) -> dict[str, Any]:
    """The call's root keys, checked. They're the view's: their `{{ }}` are
    its bindings, so they aren't substituted with the fragment's params."""
    keys = {k: node[k] for k in _CALL_KEYS if k in node}
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
    """Puts a call's keys on the fragment's root: mappings merged key by key
    (the call's win), `two_way:` replaced, `classes:` added."""
    for key, value in keys.items():
        if key in _CALL_MAPPINGS:
            root[key] = {**(root.get(key) or {}), **value}
        elif key == "classes":
            root[key] = [*(root.get(key) or []), *(c for c in value if c not in (root.get(key) or []))]
        else:
            root[key] = value


def _expand_list_item(item: Any, chain: tuple[str, ...]) -> list[Any]:
    """One `children:` entry expands to 0+ real nodes -- 1 for an
    ordinary node (component or not), N for a real `repeat:`."""
    if isinstance(item, dict) and _COMPONENT_KEY in item:
        return _expand_component(dict(item), chain)
    return [_walk(item, chain)]


def _walk(node: Any, chain: tuple[str, ...]) -> Any:
    if isinstance(node, list):
        out: list[Any] = []
        for item in node:
            out.extend(_expand_list_item(item, chain))
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
    return {
        k: (_walk(v, chain) if k == _CHILDREN_KEY else v) for k, v in node.items()
    }


def expand_components_to_spec(yaml_text: str, *, component_dirs: list[Path] | None = None) -> Any:
    """Expands every `component:` entry in `yaml_text` (a node with the fragment it names), returning the finished `WidgetSpec`-shaped dict with no
    `component:`/`with:`/`params:`/`repeat:` keys remaining -- ready for `tess_ui.View(spec)`, with no YAML-text round-trip.

    The fragments are Tesserae's own (`spec/components/`); `component_dirs` is a list of folders to search instead, in order."""
    token = _DIRS.set(component_dirs if component_dirs is not None else [COMPONENTS])
    try:
        return _normalize_scalars(_walk(yaml.safe_load(yaml_text), ()))
    finally:
        _DIRS.reset(token)


def expand_components(yaml_text: str, *, component_dirs: list[Path] | None = None) -> str:
    """`expand_components_to_spec`, dumped back to YAML text -- for inspecting an expansion."""
    return yaml.safe_dump(expand_components_to_spec(yaml_text, component_dirs=component_dirs), sort_keys=False)
