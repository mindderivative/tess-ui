"""tess-ui as a host of the behavior standard's `list` (the Selection behavior, SPEC 2.5b): a real `list_` (multiple or single) and a real `Tree`
(`Multiple`) driven through `window.simulate` and read back. See `search_bar_host.py` for the principles: what the widget reports is what the case sees, a difference is a
failed case (a conformance gap), what cannot be run or read raises `NotRun` with the reason.

Reported by the widget: `selection_change` (`list_` multiple: its `on_change`, which says detail `select` for every kind of change), and
`before_change` and `change` (`list_` single). The `Tree` reports no event at all. Derived here: only `focus_move`, from a row taking the focus with
the reason of the input, and `anchor` from the engine's `selection_anchor`."""

from __future__ import annotations

from typing import Any

import tess_re
from tess_behavior import (
    AdvanceInput,
    Event,
    FocusInput,
    Input,
    KeyInput,
    NotRun,
    Outcome,
    PointerInput,
    PressInput,
    SetOptionInput,
    Spec,
)

from tess_ui import App, Signal, ViewModel
from tess_ui.widgets import list_, list_item

#: The standard's key names -> the engine's.
KEYS = {"arrowdown": "arrow_down", "arrowup": "arrow_up", "space": "space", "escape": "escape", "enter": "enter", "home": "home", "end": "end"}
MODIFIERS = ("ctrl", "shift")


def _held(modifiers: tuple[str, ...]) -> dict[str, bool]:
    return {m: True for m in modifiers if m in MODIFIERS}


class _Host:
    """What the two hosts share: the inputs, the focus events, and the order in which what was heard comes."""

    ids: list[Any]
    window: Any
    single: bool

    def _row(self, item: Any) -> Any:
        raise NotImplementedError

    def _set_selection(self, value: list[Any]) -> None:
        raise NotImplementedError

    def _begin(self) -> None:
        self._heard: list[Event] = []
        self._focused: str | None = None
        self._reason = "keyboard"

    def _moved(self, to: str) -> None:
        """A row took the focus: `focus_move`, in the order the widget's own events came, with the reason of the input being driven."""
        if to != self._focused:
            self._heard.append(Event("focus_move", {"from": self._focused, "to": to, "reason": self._reason}))
            self._focused = to

    def present(self, name: str) -> bool:
        part, _, ident = name.partition("#")
        return part == "listbox" or (part == "option" and ident in [str(i) for i in self.ids])

    def _node(self, item: Any) -> Any:
        if item not in self.ids:
            raise NotRun(f"no row {item!r}")
        return self._row(item)

    def dispatch(self, event: Input) -> Outcome:
        self._heard.clear()
        self._focused = self.focus  # type: ignore[attr-defined]
        self._reason = "keyboard"
        match event:
            case PressInput(_, via, item, modifiers):
                self._reason = via
                if item is None:
                    raise NotRun("a press on the empty part of the list cannot be aimed at")
                if via != "pointer":
                    raise NotRun("a keyboard press on a row is Space or Enter: the case should send the key")
                self.window.simulate("click", node=self._node(item), **_held(modifiers))
            case PointerInput(_, kind, item, modifiers):
                self._reason = "pointer"
                if item is None or kind not in ("down", "up"):
                    raise NotRun("only a pointer press or release on a row can be driven")
                self.window.simulate(f"pointer_{kind}", node=self._node(item), **_held(modifiers))
            case KeyInput(_, key, modifiers, _):
                if key.lower() not in KEYS and len(key) != 1:
                    raise NotRun(f"no engine key for {key!r}")
                self.window.simulate("key_down", key=KEYS.get(key.lower(), key.lower()), **_held(modifiers))
            case FocusInput(_, via, item):
                self._reason = via
                if item is None:
                    raise NotRun("focus on the list itself")
                if via == "pointer":
                    raise NotRun("a pointer focus without a press cannot be driven")
                self._node(item).focus()
            case AdvanceInput(ms):
                self.window.advance(ms)
                raise NotRun("the announcement (the engine's `selection_announce`) cannot be read back from a headless window")
            case SetOptionInput(option, value):
                if option != "selection":
                    raise NotRun(f"there is no option {option!r} to change")
                self._reason = "api"
                self._set_selection(list(value))
            case _:
                raise NotRun("an input this widget does not take")
        for _ in range(3):
            self.window.advance(16)
        return Outcome(list(self._heard), consumed=bool(self._heard))


def _require(given: dict[str, Any], what: str, controlled: bool) -> None:
    if controlled:
        raise NotRun(f"{what}'s selection is not controlled by the host")
    if any(entry.get("unselectable") for entry in given["items"]):
        raise NotRun(f"{what} has no unselectable rows")
    if given["select_on_focus"]:
        raise NotRun(f"{what} never selects on focus")
    if given["select_all_key"] is not True and given["selection_mode"] == "multiple":
        raise NotRun(f"{what} always has Ctrl+A")


DEFAULTS = {"items": [], "selection": [], "selection_mode": "multiple", "select_all_key": True, "select_on_focus": False}


class ListHost(_Host):
    """A `list_` in a headless window."""

    def __init__(self, spec: Spec, options: dict[str, Any] | None, controlled: bool, responses: list[str]) -> None:
        given = {**DEFAULTS, **(options or {})}
        _require(given, "list_", controlled)
        if any(entry.get("disabled") for entry in given["items"]):
            raise NotRun("a list_item has no disabled state")
        self.single = given["selection_mode"] == "single"
        self.ids = [entry["id"] for entry in given["items"]]
        self.window = tess_re.Window(width=600, height=600)
        self.window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start", flex_direction="vertical")
        self.rows = [list_item(self.window, entry["label"]) for entry in given["items"]]
        start = [self.ids.index(i) for i in given["selection"]]
        self.box = list_(self.window, self.rows, selectable="single" if self.single else "multiple",
                         selected=(start[0] if start else None) if self.single else start, announce="{count} selected")
        self._begin()
        if self.single:
            self.box.on_before_change(lambda change: self._heard.append(Event("before_change", self._fields(change), cancelable=True)))
            self.box.on_change(lambda change: self._heard.append(Event("change", self._fields(change))))
        else:
            self.box.on_change(self._changed)
        for ident, row in zip(self.ids, self.rows, strict=True):
            self.box.view._listen(row.node, "focus", lambda event, ident=ident: self._moved(f"option#{ident}"))
        for _ in range(3):
            self.window.advance(16)

    def _row(self, item: Any) -> Any:
        return self.rows[self.ids.index(item)].node

    def _set_selection(self, value: list[Any]) -> None:
        if self.single:
            self.box.selected.set(self.ids.index(value[0]) if value else None)
        else:
            self.box.selection.set(tuple(sorted(self.ids.index(i) for i in value)))

    def _ids(self, value: Any) -> list[Any]:
        indices = [] if value is None else [value] if isinstance(value, int) else list(value)
        return [self.ids[i] for i in indices]

    def _fields(self, change: Any) -> dict[str, Any]:
        return {"reason": change.reason, "detail": change.detail, "previous": self._ids(change.previous), "value": self._ids(change.value)}

    def _changed(self, change: Any) -> None:
        self._heard.append(Event("selection_change", {"count": len(change.value), "anchor": self._anchor(), "reason": change.reason, "detail": change.detail}))

    def _anchor(self) -> Any:
        if self.single:
            return None  # the single list does not expose one
        held = self.box.node.get("selection_anchor")
        return None if held is None else self.ids[next(i for i, row in enumerate(self.rows) if row.node == held)]

    @property
    def state(self) -> dict[str, Any]:
        chosen = self.box.selected.get() if self.single else self.box.selection.get()
        return {"selection": self._ids(chosen), "anchor": self._anchor()}

    @property
    def focus(self) -> str | None:
        return next((f"option#{i}" for i, row in zip(self.ids, self.rows, strict=True) if row.node.get("focused")), None)

    def tree(self) -> list[dict[str, Any]]:
        selected = self.state["selection"]
        options = [{"role": "option", "name": row.node.get("label"), "props": {"selected": i in selected, "disabled": False}, "children": []}
                   for i, row in zip(self.ids, self.rows, strict=True)]
        return [{"role": "listbox", "name": self.box.node.get("label"), "props": {"multiselectable": not self.single}, "children": options}]


class _VM(ViewModel):
    views = "main"

    def __init__(self) -> None:
        super().__init__()
        self.picked = Signal([])
        self.chosen = Signal("")
        self.open = Signal([])


def _item(entry: dict[str, Any]) -> str:
    return f"Item {{ Value: {entry['id']}, Label: \"{entry['label']}\"{', Disabled: true' if entry.get('disabled') else ''} }}"


class TreeHost(_Host):
    """A `Tree` (flat rows, `Multiple` for the multiple mode) in a headless window."""

    def __init__(self, tmp_path: Any, spec: Spec, options: dict[str, Any] | None, controlled: bool, responses: list[str]) -> None:
        given = {**DEFAULTS, **(options or {})}
        _require(given, "the Tree", controlled)
        self.single = given["selection_mode"] == "single"
        self.ids = [entry["id"] for entry in given["items"]]
        (tmp_path / "Views").mkdir(exist_ok=True)
        nodes = "\n".join(_item(entry) for entry in given["items"])
        multiple = "" if self.single else "Multiple: true\n      Selection: <| picked |>"
        (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 800 }}
  Children {{
    Tree {{
      Name: t
      Label: Items
      Nodes {{ {nodes} }}
      Selected: <| chosen |>
      {multiple}
    }}
  }}
}}
""")
        self.app = App(root=tmp_path, width=400, height=800)
        self.app.bind(_VM)
        self.view = self.app.open_view("Main")
        self.app.show("main")
        self.window = self.view.window
        self.vm = self.app.bindings.viewmodel_for("main")
        (self.vm.chosen if self.single else self.vm.picked).set(given["selection"][0] if self.single and given["selection"] else
                                                                 "" if self.single else list(given["selection"]))
        self._begin()
        for ident in self.ids:
            self.view._listen(self._row(ident), "focus", lambda event, ident=ident: self._moved(f"option#{ident}"))
        for _ in range(8):
            self.window.advance(16)

    def _row(self, item: Any) -> Any:
        return self.view.node(f"root.t.row[{item}]")

    def _set_selection(self, value: list[Any]) -> None:
        if self.single:
            self.vm.chosen.set(value[0] if value else "")
        else:
            self.vm.picked.set(list(value))

    @property
    def state(self) -> dict[str, Any]:
        chosen = [self.vm.chosen.get()] if self.single and self.vm.chosen.get() != "" else [] if self.single else self.vm.picked.get()
        order = {i: n for n, i in enumerate(self.ids)}
        held = None if self.single else self.view.node("root.t").get("selection_anchor")
        anchor = None if held is None else next(i for i in self.ids if self._row(i) == held)
        return {"selection": sorted(chosen, key=order.__getitem__), "anchor": anchor}

    @property
    def focus(self) -> str | None:
        return next((f"option#{i}" for i in self.ids if self._row(i).get("focused")), None)

    def tree(self) -> list[dict[str, Any]]:
        selected = self.state["selection"]
        options = [{"role": "option" if self._row(i).get("role") == "option" else self._row(i).get("role"), "name": self._row(i).get("label"),
                    "props": {"selected": i in selected, "disabled": bool(self._row(i).get("disabled"))}, "children": []} for i in self.ids]
        return [{"role": self.view.node("root.t").get("role"), "name": self.view.node("root.t").get("label"),
                 "props": {"multiselectable": not self.single}, "children": options}]
