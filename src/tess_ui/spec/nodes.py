"""The node model: a view file in the 0.5.0 syntax, read into validated `Node`s (spec sections 2, 3, 5 and 14; phase 3 of #209).

`parse_view(text, file)` reads one `*_View.tdl` (read into mappings with positions kept), checks every key of every node against the spec, checks each
property against its widget's declaration, compiles every slot (`<| expression |>`, a `tess_ui.tel.Parts`) and handler through `tess_ui.tel`, and gives every node a
stable id (its path from the root: the node's `name`, else `children[2]`). The first problem is a `LoadError` that names the file, line and
column, says what is wrong and, where it can, what to write instead.

This module only reads and checks. Composition (params, slots, `for:`, `if:`, `state:` at run time) is phase 4, and building the tree is the
existing builder until phase 5.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional


from tess_ui import a11y as a11y_module
from tess_ui.spec import placement, sizes
from tess_ui.tel import (Expr, ExprError, NestedTemplate, Origin, Parts, Statements, compile_expr, compile_statements, compile_template, is_action_name,
                         timer_handlers)
from tess_ui.spec import widgets as registry
from tess_ui.spec.widgets import Property, PropertyError, WidgetDecl, decl_from_params, is_expression, style_fields_of
from tess_ui.project import looks_like, tdl_wrong_kind, yaml_refused

__all__ = ["EVENTS", "ForSpec", "Handler", "LoadError", "Node", "ViewDoc", "parse_data", "parse_view", "read_marked"]

#: What `visible:` is when a widget does not declare a property of that name: a bool (or an expression), like any property.
VISIBLE = Property("bool", name="visible", doc="Shown while true; while false it is hidden and takes no room.")

#: Keys every node may have, besides its widget's properties (section 2).
#: What a `tooltip:` mapping may hold, and where it may sit against its node.
TOOLTIP_FIELDS = ("text", "title", "delay", "placement", "actions")
TOOLTIP_PLACEMENTS = placement.PLACEMENTS
UNIVERSAL_KEYS = ("widget", "name", "if", "for", "key", "slot", "state", "style", "classes", "handlers", "a11y", "interaction",
                  "window_region", "route", "focus_group", "tooltip", "children")
#: Keys only the root of a view file may have.
HEADER_KEYS = ("params", "expects")
#: The handler events (section 9.1): `view._EVENTS` plus `on_key`, `on_submit` and `on_press`. `tests/test_nodes.py` keeps the two in step.
EVENTS = ("on_click", "on_hover_enter", "on_hover_exit", "on_change", "on_focus_enter", "on_focus_exit", "on_tap", "on_long_press",
          "on_pan", "on_pinch", "on_touch_start", "on_touch_move", "on_touch_end", "on_touch_cancel", "on_file_hover",
          "on_file_hover_cancel", "on_file_drop", "on_link", "on_key", "on_submit", "on_press", "on_move", "on_release", "on_input", "on_dismiss")
A11Y_FIELDS = ("label", "role", "hidden", "live", "level", "set_size", "pos_in_set", "expanded", "selected", "checked", "value", "value_min", "value_max", "value_step", "focusable",
               "pressed", "invalid", "description", "describedby", "controls", "current", "value_now", "value_text", "busy")
WINDOW_REGIONS = ("drag", "none")
#: How arrow keys move focus among a `focus_group`'s items: along one axis, or both.
FOCUS_GROUPS = ("horizontal", "vertical", "both")
#: 0.4.x keys that no longer exist, and what to write.
OLD_KEYS = {
    "kind": "write 'widget: X'", "component": "write 'widget: X'", "view": "write 'widget: X' (a view is called by its name)",
    "include": "write 'widget: X' (a view is called by its name)", "id": "use 'name:' (and only where something addresses the node)",
    "with": "give the properties as plain keys", "repeat": "use 'for: item in items'", "when": "use 'if: expression'",
    "bindings": "write the expression in the property: text: \"{{ x }}\"",
    "two_way": "a model property given a bare reference is two-way: checked: \"{{ done }}\"",
    "component_of": "name the node and address it as a part",
}
MAX_DEPTH = 64

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FOR = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)\s+in\s+(.+?)\s*$", re.S)
_EVENT = re.compile(r"^on_[a-z][a-z_]*$")

Position = tuple[int, int]


# -- errors ----------------------------------------------------------------------------------------------------------------


class LoadError(ValueError):
    """A problem in a view file: `file:line:column: error: message (hint)`. `line` is 1-based, `column` 0-based."""

    def __init__(self, message: str, *, file: str = "<view>", line: int = 1, column: int = 0, hint: Optional[str] = None,
                 text: str = "") -> None:
        self.message, self.file, self.line, self.column, self.hint, self.text = message, file, line, column, hint, text
        super().__init__(f"{file}:{line}:{column + 1}: error: {message}" + (f" ({hint})" if hint else ""))

    def render(self) -> str:
        """The message with the offending line of the file and a caret under it."""
        lines = self.text.splitlines()
        if not 1 <= self.line <= len(lines):
            return str(self)
        return f"{self}\n    {self.line:>3} | {lines[self.line - 1]}\n        | {' ' * self.column}^"


def _near(text: Any, options: Any) -> Optional[str]:
    close = difflib.get_close_matches(str(text), [str(o) for o in options], n=3)
    return ("did you mean " + " or ".join(f"'{c}'" for c in close)) if close else None


def _describe(value: Any) -> str:
    if value is None:
        return "nothing"
    if isinstance(value, dict):
        return "a mapping"
    if isinstance(value, list):
        return "a list"
    return repr(value)


# -- mappings with positions ---------------------------------------------------------------------------------------------------


class PMap(dict):
    """A mapping that knows where it and its keys and values are: `at`, `key_at[key]`, `val_at[key]` as `(line, column)`."""

    at: Position
    key_at: dict[Any, Position]
    val_at: dict[Any, Position]


class PSeq(list):
    """A list that knows where it and its items are."""

    at: Position
    item_at: list[Position]


# -- the model -------------------------------------------------------------------------------------------------------------


@dataclass
class Handler:
    """One event's handler: an action name (`save`, `navigate.back`) or compiled statements."""

    source: str
    action: Optional[str] = None
    statements: Optional[Statements] = None
    at: Optional[Position] = None  # where it was written, for an error about the action it names


@dataclass
class ForSpec:
    """A `for: a, b in expr`: the names it binds and the compiled iterable."""

    targets: tuple[str, ...]
    iterable: Expr
    source: str


@dataclass
class Node:
    """One node of a view. `id` is its path from the view's root (assigned here, never authored); `props` holds each given property
    as its coerced literal, a `Template` for an expression, a `Node` for a `node` property or a list of them for `nodes`."""

    widget: str
    decl: WidgetDecl
    id: str
    at: Position
    name: Optional[str] = None
    props: dict[str, Any] = field(default_factory=dict)
    prop_at: dict[str, Position] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)
    when: Optional[Expr] = None
    loop: Optional[ForSpec] = None
    key: Optional[Expr] = None
    slot: Optional[str] = None
    state: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=dict)
    classes: list[str] = field(default_factory=list)
    handlers: dict[str, Handler] = field(default_factory=dict)
    a11y: dict[str, Any] = field(default_factory=dict)
    interaction: Any = None
    window_region: Optional[str] = None
    route: Optional[str] = None
    #: a route written as a mapping: `guard` (an `Expr`: a falsy value refuses the screen), `redirect` (a route to go to instead) and `lazy` (the view is built when first reached)
    route_options: dict[str, Any] = field(default_factory=dict)
    focus_group: Optional[str] = None
    #: `tooltip:` as `{text, title, delay, placement, actions}`, each text possibly a `Template`; `actions` is a list of (label, `Handler`)
    tooltip: dict[str, Any] = field(default_factory=dict)

    def subnodes(self) -> Iterator[tuple[str, int, "Node"]]:
        """The nodes directly under this one, as `(segment, index, node)`: the `node`/`nodes` properties, then the children."""
        for key, value in self.props.items():
            if isinstance(value, Node):
                yield key, -1, value
            elif isinstance(value, list):
                for i, sub in enumerate(value):
                    if isinstance(sub, Node):
                        yield key, i, sub
        for i, child in enumerate(self.children):
            yield "children", i, child

    def walk(self) -> Iterator["Node"]:
        """This node and every node under it, depth first."""
        yield self
        for _, _, sub in self.subnodes():
            yield from sub.walk()


@dataclass
class ViewDoc:
    """A parsed view file: its root node and the header."""

    root: Node
    file: str
    name: Optional[str] = None
    params: Any = None
    expects: Any = None
    decl: Optional[WidgetDecl] = None
    text: str = ""


def _assign_ids(node: Node, prefix: str) -> None:
    """Gives `node` and everything under it its id: the parent's id, then the node's `name`, else its place."""
    node.id = prefix
    for key, index, sub in node.subnodes():
        place = key if index < 0 else (f"{key}[{index}]")
        _assign_ids(sub, f"{prefix}.{sub.name or place}")


# -- parsing ---------------------------------------------------------------------------------------------------------------


class _Parser:
    def __init__(self, text: str, file: str, resolver: Optional[Callable[[str], Optional[WidgetDecl]]]) -> None:
        self.text, self.file, self.resolver = text, file, resolver
        self.names: list[tuple[str, Node, Position]] = []

    def fail(self, at: Position, message: str, hint: Optional[str] = None) -> LoadError:
        return LoadError(message, file=self.file, line=at[0], column=at[1], hint=hint, text=self.text)

    def expr_error(self, exc: ExprError) -> LoadError:
        return LoadError(exc.message, file=self.file, line=exc.line, column=exc.column, hint=exc.hint, text=self.text)

    def origin(self, at: Position) -> Origin:
        return Origin(self.file, at[0], at[1])

    def widget_decl(self, name: str, at: Position) -> WidgetDecl:
        decl = registry.lookup(name)
        if decl is None and self.resolver is not None:
            decl = self.resolver(name)
        if decl is None:
            raise self.fail(at, f"no widget named '{name}'", _near(name, registry.names()))
        return decl

    # values

    def template(self, value: Any) -> Any:
        """A `Parts` (a text with slots, as the TDL front end read it) as a `Template`; any other value unchanged. Each slot is compiled where it is written."""
        if isinstance(value, Parts):
            try:
                return compile_template(value)
            except ExprError as exc:
                raise self.expr_error(exc) from None
        return value

    def nested(self, value: Any) -> Any:
        """A list or mapping whose strings may be `Parts`: a `NestedTemplate` when any are, else the value itself."""
        found = False

        def work(item: Any) -> Any:
            nonlocal found
            if isinstance(item, Parts):
                found = True
                return self.template(item)
            if isinstance(item, list):
                return [work(sub) for sub in item]
            if isinstance(item, dict):
                return {key: work(sub) for key, sub in item.items()}
            return item

        worked = work(value)
        return NestedTemplate(worked) if found else value

    def expression(self, value: Any, at: Position, what: str, offset: int = 0, text: Optional[str] = None) -> Expr:
        if not isinstance(value, str) or not value.strip():
            raise self.fail(at, f"'{what}:' takes an expression")
        if "{{" in value:
            raise self.fail(at, f"'{what}:' is an expression, not a template", "write it without {{ }}")
        try:
            return compile_expr(value if text is None else text, origin=self.origin((at[0], at[1] + offset)))
        except ExprError as exc:
            raise self.expr_error(exc) from None

    # nodes

    def node(self, m: Any, depth: int, *, root: bool = False) -> Node:
        at: Position = getattr(m, "at", (1, 0))
        if depth > MAX_DEPTH:
            raise self.fail(at, f"nodes are nested more than {MAX_DEPTH} deep")
        if not isinstance(m, PMap):
            raise self.fail(at, f"a node is a mapping with a 'widget:' key, got {_describe(m)}")
        if "widget" not in m:
            old = next((k for k in ("kind", "component", "view", "include") if k in m), None)
            if old:
                raise self.fail(m.key_at[old], f"'{old}:' is not a key in 0.5.0", OLD_KEYS[old])
            keys = ", ".join(map(str, m)) or "none"
            kind_hint = looks_like(m, "view", self.file) if root else None
            raise self.fail(at, "a node needs a 'widget:'", f"its keys are: {keys}" + (f"; {kind_hint}" if kind_hint else ""))
        if not isinstance(m["widget"], str):
            raise self.fail(m.val_at["widget"], f"'widget:' takes a widget name, got {_describe(m['widget'])}")
        decl = self.widget_decl(m["widget"], m.val_at["widget"])
        node = Node(m["widget"], decl, "", at)

        for key, value in m.items():
            if key == "widget":
                continue
            where, vat = m.key_at[key], m.val_at[key]
            if key in HEADER_KEYS:
                if not root:
                    raise self.fail(where, f"'{key}:' is only valid at the top of a view file")
            elif key in OLD_KEYS and key not in decl.properties:
                raise self.fail(where, f"'{key}:' is not a key in 0.5.0", OLD_KEYS[key])
            elif key in UNIVERSAL_KEYS:
                self.universal(node, key, value, vat, where, depth)
            elif key in decl.properties:
                self.property(node, decl.properties[key], key, value, vat, depth)
            elif key == "visible":  # on any node, unless the widget declares a property of its own by the name (which keeps its meaning)
                self.property(node, VISIBLE, key, value, vat, depth)
            else:
                unknown = decl.check_properties([key])[0]
                raise self.fail(where, unknown[0], unknown[1] or _near(key, [*decl.properties, *UNIVERSAL_KEYS, "visible"]))
        for message, hint in decl.check_properties([k for k in m if k in decl.properties]):
            raise self.fail(at, message, hint)
        if node.key is not None and node.loop is None:
            raise self.fail(m.key_at["key"], "'key:' needs a 'for:' on the same node")
        if node.route is not None and not decl.view:
            raise self.fail(m.key_at["route"], "'route:' is for a view call", f"{decl.name} is not a view")
        if node.name is not None:
            self.names.append((node.name, node, m.val_at["name"]))
        return node

    def universal(self, node: Node, key: str, value: Any, vat: Position, where: Position, depth: int) -> None:
        if key == "name":
            if not isinstance(value, str) or not _NAME.match(value):
                raise self.fail(vat, f"a name is letters, digits and '_' and does not start with a digit, got {value!r}")
            node.name = value
        elif key == "slot":
            if not isinstance(value, str) or not _NAME.match(value):
                raise self.fail(vat, f"'slot:' takes a slot name, got {value!r}")
            node.slot = value
        elif key == "if":
            node.when = self.expression(value, vat, "if")
        elif key == "for":
            match = _FOR.match(value) if isinstance(value, str) else None
            if not match:
                raise self.fail(vat, f"'for:' reads 'item in items' or 'i, item in enumerate(items)', got {value!r}")
            targets = tuple(t.strip() for t in match.group(1).split(","))
            node.loop = ForSpec(targets, self.expression(value, vat, "for", match.start(2), match.group(2)), value)
        elif key == "key":
            node.key = self.expression(value, vat, "key")
        elif key == "state":
            if not isinstance(value, PMap):
                raise self.fail(vat, f"'state:' takes a mapping of names to starting values, got {_describe(value)}")
            for state_name, initial in value.items():
                if not isinstance(state_name, str) or not _NAME.match(state_name) or state_name.startswith("_"):
                    raise self.fail(value.key_at[state_name], f"a state name is a plain identifier, got {state_name!r}")
                node.state[state_name] = self.template(initial)
        elif key == "style":
            self.style(node, value, vat)
        elif key == "classes":
            if not isinstance(value, list) or not all(isinstance(c, str) for c in value):
                raise self.fail(vat, f"'classes:' takes a list of names, got {_describe(value)}")
            node.classes = list(value)
        elif key == "handlers":
            self.handlers(node, value, vat)
        elif key == "a11y":
            self.a11y(node, value, vat)
        elif key == "interaction":
            if isinstance(value, dict):
                raise self.fail(vat, "'interaction:' takes true, false or a colour role", "write interaction: <colour> instead of {color: ...}")
            if value is not None and not isinstance(value, (bool, str)):
                raise self.fail(vat, f"'interaction:' takes true, false or a colour role, got {_describe(value)}")
            # an expression is worked out once, when the view is composed (it may read the view's params, not a Signal)
            node.interaction = self.template(value)
        elif key == "window_region":
            if value not in WINDOW_REGIONS:
                raise self.fail(vat, f"'window_region:' is one of {', '.join(WINDOW_REGIONS)}, got {value!r}", _near(value, WINDOW_REGIONS))
            node.window_region = value
        elif key == "focus_group":
            if value not in FOCUS_GROUPS:
                raise self.fail(vat, f"'focus_group:' is one of {', '.join(FOCUS_GROUPS)}, got {value!r}", _near(value, FOCUS_GROUPS))
            node.focus_group = value
        elif key == "tooltip":
            self.tooltip(node, value, vat)
        elif key == "route":
            if isinstance(value, PMap):
                self.route_mapping(node, value, vat)
            elif not isinstance(value, str):
                raise self.fail(vat, f"'route:' takes a path (\"\" for the home screen) or {{path, guard, redirect, lazy}}, got {_describe(value)}")
            else:
                node.route = value
        elif key == "children":
            if not isinstance(value, PSeq):
                raise self.fail(vat, f"'children:' takes a list of nodes, got {_describe(value)}")
            if not node.decl.container:
                raise self.fail(where, f"{node.decl.name} takes no children")
            node.children = [self.node(child, depth + 1) for child in value]

    def route_mapping(self, node: Node, value: Any, vat: Position) -> None:
        unknown = [k for k in value if k not in ("path", "guard", "redirect", "lazy")]
        if unknown:
            raise self.fail(value.key_at[unknown[0]], f"'route:' takes path, guard, redirect and lazy, not '{unknown[0]}'", _near(unknown[0], ["path", "guard", "redirect", "lazy"]))
        if "path" not in value or not isinstance(value["path"], str):
            raise self.fail(vat, "'route:' as a mapping needs a 'path' (\"\" for the home screen)")
        node.route = value["path"]
        if "guard" in value:
            node.route_options["guard"] = self.expression(value["guard"], value.val_at["guard"], "route guard")
        if "redirect" in value:
            if not isinstance(value["redirect"], str) or "guard" not in value:
                raise self.fail(value.val_at["redirect"], "'redirect:' is a route to go to, and goes with a 'guard:'")
            node.route_options["redirect"] = value["redirect"]
        if "lazy" in value:
            if not isinstance(value["lazy"], bool):
                raise self.fail(value.val_at["lazy"], "'lazy:' is true or false")
            node.route_options["lazy"] = value["lazy"]

    def style(self, node: Node, value: Any, vat: Position) -> None:
        if isinstance(value, str):
            raise self.fail(vat, "'style:' takes a mapping of style fields; write the fields here, or give the node `classes:` and a rule in a stylesheet")
        if not isinstance(value, PMap):
            raise self.fail(vat, f"'style:' takes a mapping of style fields, got {_describe(value)}")
        allowed = style_fields_of(node.decl)
        for key, item in value.items():
            if key not in allowed:
                hint = None
                if key == "foreground":
                    users = sorted(n for n in registry.names() if "foreground" in (registry.lookup(n).extras or ()))
                    hint = f"widgets that accept it: {', '.join(users)}"
                raise self.fail(value.key_at[key], f"{node.decl.name}: style '{key}' is not valid here", hint or _near(key, allowed))
            problem = None if not isinstance(item, (str, int, float)) or isinstance(item, Parts) else sizes.size_problem(key, item)
            if problem is None and key in placement.ANCHOR_FIELDS and not isinstance(item, Parts):
                problem = placement.style_problem(key, item.unwrap() if hasattr(item, "unwrap") else item)
            if problem:  # a size or an inset that tess_re would refuse, found where it is written (an expression is checked when it is worked out)
                raise self.fail(value.val_at[key], f"{node.decl.name}: {problem}")
            node.style[key] = self.template(item)
        for edge, others in _EDGES.items():  # two ways to place one edge in one mapping leave one unheard
            if edge in value and value[edge] is not None:
                for other in others:
                    if other in value and value[other] is not None:
                        raise self.fail(value.key_at[other], f"{node.decl.name}: style.{edge} and style.{other} both place the node; say one of them ({edge} is the same as {_SAME_AS[edge]})")

    def handlers(self, node: Node, value: Any, vat: Position) -> None:
        if not isinstance(value, PMap):
            raise self.fail(vat, f"'handlers:' takes a mapping of events to actions, got {_describe(value)}")
        for event, action in value.items():
            if event not in EVENTS:
                raise self.fail(value.key_at[event], f"no event '{event}'" if _EVENT.match(str(event)) else f"'{event}' is not an event name",
                                _near(event, EVENTS))
            avat = value.val_at[event]
            if not isinstance(action, str) or not action.strip():
                raise self.fail(avat, f"a handler is an action name or statements, got {_describe(action)}")
            if is_action_name(action):
                node.handlers[event] = Handler(action.strip(), action=action.strip(), at=avat)
                continue
            try:
                statements = compile_statements(action, origin=self.origin(avat))
                for later in timer_handlers(statements):
                    if not is_action_name(later):
                        compile_statements(later, origin=self.origin(avat))
                node.handlers[event] = Handler(action, statements=statements)
            except ExprError as exc:
                raise self.expr_error(exc) from None

    def tooltip(self, node: Node, value: Any, vat: Position) -> None:
        """`tooltip: text`, or `tooltip: {text, title, delay, placement, actions}` for a rich one."""
        if isinstance(value, str):
            node.tooltip = {"text": self.template(value)}
            return
        if not isinstance(value, PMap):
            raise self.fail(vat, f"'tooltip:' takes text, or a mapping of text, title, delay, placement and actions, got {_describe(value)}")
        for key, item in value.items():
            if key not in TOOLTIP_FIELDS:
                raise self.fail(value.key_at[key], f"no tooltip field '{key}'", _near(key, TOOLTIP_FIELDS))
            iat = value.val_at[key]
            if key == "placement":
                if item not in TOOLTIP_PLACEMENTS:
                    raise self.fail(iat, f"tooltip placement is one of {', '.join(TOOLTIP_PLACEMENTS)}, got {_describe(item)}")
                node.tooltip[key] = item
            elif key == "actions":
                node.tooltip[key] = self.tooltip_actions(item, iat)
            elif key == "delay":
                if isinstance(item, bool) or not isinstance(item, (int, float)) or item < 0:
                    raise self.fail(iat, f"tooltip delay is milliseconds, 0 or more, got {_describe(item)}")
                node.tooltip[key] = item
            elif not isinstance(item, str):
                raise self.fail(iat, f"tooltip {key} is text, got {_describe(item)}")
            else:
                node.tooltip[key] = self.template(item)
        if "text" not in node.tooltip:
            raise self.fail(vat, "a tooltip needs text", "write tooltip: {text: ..., title: ...}")

    def tooltip_actions(self, value: Any, vat: Position) -> list[tuple[Any, Handler]]:
        """The text buttons of a rich tooltip: up to two of `{label, on_click}`, `on_click` an action name or statements as a handler is."""
        if not isinstance(value, list) or not 1 <= len(value) <= 2:
            raise self.fail(vat, f"tooltip actions are a list of one or two {{label, on_click}}, got {_describe(value)}")
        actions = []
        for item in value:
            if not isinstance(item, PMap) or set(item) - {"label", "on_click"} or not {"label", "on_click"} <= set(item):
                raise self.fail(getattr(item, "at", vat), "a tooltip action is {label: ..., on_click: ...}")
            label, click = item["label"], item["on_click"]
            if not isinstance(label, str) or not isinstance(click, str) or not click.strip():
                raise self.fail(item.val_at["label"], "a tooltip action's label is text and its on_click an action name or statements")
            if is_action_name(click):
                handler = Handler(click.strip(), action=click.strip(), at=item.val_at["on_click"])
            else:
                try:
                    handler = Handler(click, statements=compile_statements(click, origin=self.origin(item.val_at["on_click"])))
                except ExprError as exc:
                    raise self.expr_error(exc) from None
            actions.append((self.template(label), handler))
        return actions

    def a11y(self, node: Node, value: Any, vat: Position) -> None:
        if not isinstance(value, PMap):
            raise self.fail(vat, f"'a11y:' takes a mapping, got {_describe(value)}")
        for key, item in value.items():
            if key not in A11Y_FIELDS:
                raise self.fail(value.key_at[key], f"no a11y field '{key}'", _near(key, A11Y_FIELDS))
            iat = value.val_at[key]
            if is_expression(item):
                if key == "role":  # a role cannot change while a view is open, but it may be worked out from the view's params (checked when composing)
                    node.a11y[key] = self.template(item)
                    continue
                if key not in a11y_module.BINDABLE:
                    raise self.fail(iat, f"a11y '{key}' cannot be bound", f"bindable: {', '.join(a11y_module.BINDABLE)}")
                node.a11y[key] = self.template(item)
                continue
            try:
                a11y_module.check({key: item})
            except ValueError as exc:
                raise self.fail(iat, str(exc)) from None
            node.a11y[key] = item

    def property(self, node: Node, prop: Property, key: str, value: Any, vat: Position, depth: int) -> None:
        node.prop_at[key] = vat
        if {key, *node.props} >= {"text", "runs"} and node.decl.name == "Text":  # the runs are the text
            raise self.fail(vat, "Text: `runs:` is the text, so there is no `text:` with it", "give one or the other")
        if prop.type == "node":
            node.props[key] = self.node(value, depth + 1)
        elif prop.type == "nodes":
            if not isinstance(value, PSeq):
                raise self.fail(vat, f"'{key}' takes a list of nodes, got {_describe(value)}")
            node.props[key] = [self.node(v, depth + 1) for v in value]
        else:
            try:
                coerced = prop.coerce(value)
            except PropertyError as exc:
                raise self.fail(vat, f"{node.decl.name}: {exc.message}", exc.hint) from None
            node.props[key] = self.nested(coerced) if key == "runs" and node.decl.name == "Text" else self.template(coerced)


#: `x` is `left` and `y` is `top`, and `inset` is all four: a mapping that gives an edge twice says what it means only once.
_EDGES = {"x": ("left", "inset"), "y": ("top", "inset")}
_SAME_AS = {"x": "left", "y": "top"}


def _check_names(parser: _Parser) -> None:
    """A name is unique in a view, except that a node and one under it may share one (section 5)."""
    seen: dict[str, list[Node]] = {}
    for name, node, at in parser.names:
        for other in seen.get(name, []):
            if not (node.id.startswith(other.id + ".") or other.id.startswith(node.id + ".")):
                raise parser.fail(at, f"the name '{name}' is already used in this view (by {other.id})", "names are unique in a view")
        seen.setdefault(name, []).append(node)


def read_marked(text: str, file: str = "<view>", *, resolver: Optional[Callable[[str], Optional[WidgetDecl]]] = None) -> Any:
    """The mapping with positions of the TDL view file `text` (`resolver` as `parse_view`'s). A file named `*.yaml` is refused, saying that YAML is no longer
    read; a TDL file whose root says it is a stylesheet or a theme is refused with the hint that names the file to give it."""
    gone = yaml_refused(file)
    if gone is not None:
        raise LoadError(gone, file=file, line=1, column=0, text=text)
    from tess_ui.spec.tdl import load_marked_tdl

    wrong = tdl_wrong_kind(text, "view", file)
    if wrong is not None:
        raise LoadError("a view's root block is a widget, and this file's is not", file=file, line=wrong[1], column=wrong[2], hint=wrong[0], text=text)
    return load_marked_tdl(text, file, resolver=resolver)


def parse_view(text: str, file: str = "<view>", *, resolver: Optional[Callable[[str], Optional[WidgetDecl]]] = None,
               view_name: Optional[str] = None) -> ViewDoc:
    """Reads the TDL view in `text`. `resolver` maps a widget name that is not built in to its declaration (a view with
    `params:`)."""
    return parse_data(read_marked(text, file, resolver=resolver), text, file, resolver=resolver, view_name=view_name)


def parse_data(data: Any, text: str, file: str = "<view>", *, resolver: Optional[Callable[[str], Optional[WidgetDecl]]] = None,
               view_name: Optional[str] = None) -> ViewDoc:
    """Reads a view that is already a mapping with positions: what `tdl.load_marked_tdl` makes of TDL text.
    `text` is only the file's text, for error messages."""
    parser = _Parser(text, file, resolver)
    if not isinstance(data, PMap):
        raise parser.fail((1, 0), "a view file is a mapping: its root node", "start with 'widget: Container'")
    root = parser.node(data, 0, root=True)
    _assign_ids(root, "root")
    _check_names(parser)
    doc = ViewDoc(root=root, file=file, name=root.name, params=data.get("params"), expects=data.get("expects"), text=text)
    if "params" in data:
        try:
            doc.decl = decl_from_params(view_name or root.name or file, data["params"])
        except ValueError as exc:
            raise parser.fail(data.val_at["params"], str(exc)) from None
    return doc
