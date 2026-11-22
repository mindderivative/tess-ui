"""tess-ui as a host of the Tesserae behavior standard: a real `search_bar` driven through `window.simulate` and read back, so the corpus of
`search_field` runs against the widget a user gets, not against a model of it.

What the widget cannot do or does not report is not hidden: a case it cannot run raises `NotRun` (with the reason), and a difference is a
failed case, which is a conformance gap of the widget. The adapter derives only what it can observe: `change` (the query changed) and
`focus_move` (the focused part changed), with the reason of the input it sent and the detail the spec names for that input. The widget emits no
`before_change`, so no case that expects one can pass until it does."""

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
    PressInput,
    SetOptionInput,
    Spec,
    TextInput,
)

from tess_ui.widgets import search_bar

#: The corpus part name -> the widget's part name.
PARTS = {"input": "field", "clear": "clear"}
#: Options the widget takes, and what each does; any other option at a non-default value is a case this widget cannot run.
DEFAULTS = {"value": "", "disabled": False, "label": "Search", "clear_label": "Clear", "clear_on_escape": True}


class SearchBarHost:
    """A `search_bar` in a headless window, as a host of `search_field`."""

    def __init__(self, spec: Spec, options: dict[str, Any] | None, controlled: bool, responses: list[str]) -> None:
        if controlled:
            raise NotRun("search_bar has no controlled value: its query is the widget's own Signal and nothing can veto a change")
        given = {**DEFAULTS, **(options or {})}
        for name in ("disabled", "clear_label"):
            if given[name] != DEFAULTS[name]:
                raise NotRun(f"search_bar has no {name} option (the helper takes no such argument)")
        self.spec = spec
        self.window = tess_re.Window(width=600, height=200)
        self.window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start")
        self.bar = search_bar(self.window, given["label"], 360)
        self.bar.query.set(given["value"])
        self._settle()

    # -- observing -------------------------------------------------------------------------------------------------

    @property
    def state(self) -> dict[str, Any]:
        return {"value": self.bar.query.get()}

    @property
    def focus(self) -> str | None:
        return next((name for name in PARTS if self.present(name) and self._node(name).get("focused")), None)

    def present(self, name: str) -> bool:
        try:
            self.bar.part(PARTS[name])
        except ValueError:
            return False
        return True

    def tree(self) -> list[dict[str, Any]]:
        nodes = []
        for name in PARTS:
            if self.present(name):
                node = self._node(name)
                role = node.get("role")
                props: dict[str, Any] = {"disabled": bool(node.get("disabled"))}
                if name == "input":
                    props["value"] = node.get("text")
                nodes.append({"role": "searchbox" if role == "textbox" else role, "name": node.get("label"), "props": props, "children": []})
        return nodes

    # -- input -----------------------------------------------------------------------------------------------------

    def dispatch(self, event: Input) -> Outcome:
        before = (self.state["value"], self.focus)
        reason = "keyboard"
        match event:
            case TextInput(part, text):
                self._require(part)
                self.window.simulate("input", text=text)
            case KeyInput(part, key):
                self._require(part)
                self.window.simulate("key_down", key=key.lower())
            case PressInput(part, via):
                reason = via
                node = self._require(part)
                if via == "pointer":
                    self.window.simulate("click", node=node)
                else:
                    node.focus()
                    self.window.simulate("key_down", key="enter")
            case FocusInput(part, via):
                reason = via
                node = self._require(part)
                if via == "pointer" and part != "input":
                    raise NotRun("a pointer on a button of the widget presses it: it cannot take focus by pointer without acting")
                node.focus()
            case AdvanceInput(ms):
                self.window.advance(ms)
            case SetOptionInput():
                raise NotRun("search_bar's options are fixed when it is built")
        self._settle()
        return self._outcome(before, reason, event)

    # -- helpers ---------------------------------------------------------------------------------------------------

    def _settle(self) -> None:
        for _ in range(3):
            self.window.advance(16)

    def _node(self, name: str) -> Any:
        return self.bar.part(PARTS[name])

    def _require(self, name: str) -> Any:
        if not self.present(name):
            raise NotRun(f"the part {name!r} is not there")
        return self._node(name)

    def _outcome(self, before: tuple[str, str | None], reason: str, event: Input) -> Outcome:
        events: list[Event] = []
        value, focus = self.state["value"], self.focus
        if value != before[0]:
            events.append(Event("change", {"reason": reason, "detail": self._detail(event), "previous": before[0], "value": value}))
        if focus != before[1]:
            events.append(Event("focus_move", {"from": before[1], "to": focus, "reason": reason}))
        # the widget does not say whether it used an input: an input that changed something was used
        return Outcome(events, consumed=bool(events))

    def _detail(self, event: Input) -> str:
        """The name the spec gives the action that input runs (what the cause is called, not something the widget reports)."""
        match event:
            case TextInput(part, _):
                handler = next((h for h in self.spec.part(part).on if h.event == "input"), None)
                return self.spec.action(handler.do).detail if handler else ""
            case KeyInput(part, key):
                handler = next((h for h in self.spec.part(part).on if h.event == "key_down" and (h.key or "").lower() == key.lower()), None)
                return self.spec.action(handler.do).detail if handler else ""
            case PressInput(part, _):
                press = self.spec.part(part).press
                return self.spec.action(press.do).detail if press else ""
        return ""
