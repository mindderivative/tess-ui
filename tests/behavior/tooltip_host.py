"""tess-ui as a host of the behavior standard's `tooltip`: a real `Tooltip:` on a button in a scrolling pane, driven through `window.simulate`
and read back (its open state is whether the view shows a tip layer). See `search_bar_host.py` for the principles.

The tooltip's own events are read from the view (`on_tooltip_before_change`, `on_tooltip_change`: reason and detail as the standard names
them); only `focus_move` is derived, from the focused part changing, with the reason of the input that caused it."""

from __future__ import annotations

from typing import Any

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
    ScrollInput,
    SetOptionInput,
    Spec,
    TextInput,
    WindowInput,
)

from tess_ui import App, Signal, ViewModel

VIEW = """---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 300, Height: 300 }
  Children {
    ScrollView {
      Name: pane
      Style { Width: 300, Height: 120 }
      Children {
        Container {
          Name: tall
          Style { Flex_Direction: vertical, Width: 100%, Height: 600 }
          Children {
            Container {
              Name: trigger
              Tooltip: "Save the file"
              A11y { Label: Save }
              Style { Width: 80, Height: 40, Background: primary }
              Handlers { On_Click { Set { Target: clicks, Value: <| clicks + 1 |> } } }
            }
            Container { Name: other, Style { Width: 80, Height: 40, Background: secondary }, Handlers { On_Click { Set { Target: clicks, Value: <| clicks + 1 |> } } } }
          }
        }
      }
    }
  }
}
"""

#: The tooltip's delay and grace are the toolkit's constants (500 and 150 ms); a case that sets other values cannot run.
DEFAULTS = {"label": "Save", "text": "Save the file", "open_delay": 500, "grace": 150}


class _Model(ViewModel):
    views = "main"

    def __init__(self) -> None:
        super().__init__()
        self.clicks = Signal(0)


class TooltipHost:
    """A button with a `Tooltip:` in a view, as a host of `tooltip`."""

    def __init__(self, root: Any, spec: Spec, options: dict[str, Any] | None, controlled: bool, responses: list[str]) -> None:
        given = {**DEFAULTS, **(options or {})}
        if controlled:
            raise NotRun("a tooltip has no controlled value")
        for name, default in DEFAULTS.items():
            if given[name] != default:
                raise NotRun(f"the tooltip's {name} is fixed by the toolkit ({default!r})")
        (root / "Views").mkdir(parents=True, exist_ok=True)
        (root / "Views" / "Main_View.tdl").write_text(VIEW)
        self.app = App(root=root)
        self.app.bind(_Model)
        self.view = self.app.open_view("Main")
        self.app.show("main")
        self.window = self.view.window
        self.window.advance(16)
        self._away()
        self._settle()
        self._heard: list[Event] = []
        self.view.on_tooltip_before_change(lambda change: self._heard.append(Event("before_change", _fields(change), cancelable=True)))
        self.view.on_tooltip_change(lambda change: self._heard.append(Event("change", _fields(change))))

    # -- geometry --------------------------------------------------------------------------------------------------

    def _node(self, name: str) -> Any:
        return self.view.node(f"root.pane.tall.{name}")

    def _inside(self, node: Any) -> tuple[float, float]:
        return node.get("layout_x") + 8, node.get("layout_y") + 8

    def _away(self) -> None:
        self.window.simulate("pointer_move", x=290, y=290)  # off the trigger and off any tip

    def _tip_layer(self) -> Any:
        layers = [layer[0] for layer in self.view._tips.values()]
        return layers[0] if layers else None

    def _settle(self) -> None:
        self.window.advance(0)  # the engine runs what an input queued, without moving time

    # -- observing -------------------------------------------------------------------------------------------------

    @property
    def state(self) -> dict[str, Any]:
        return {"open": bool(self.view._tips)}

    @property
    def focus(self) -> str | None:
        return "trigger" if self._node("trigger").get("focused") else None

    def present(self, name: str) -> bool:
        return name == "trigger" or (name == "tip" and bool(self.view._tips))

    def tree(self) -> list[dict[str, Any]]:
        trigger = self._node("trigger")
        nodes = [{"role": trigger.get("role"), "name": trigger.get("label"), "props": {"description": trigger.get("description")},
                  "children": []}]
        layer = self._tip_layer()
        if layer is not None:
            nodes.append({"role": layer.get("role"), "name": layer.get("label") or layer.get("description") or self._text(layer),
                          "props": {"hidden": bool(layer.get("a11y_hidden"))}, "children": []})
        return nodes

    @staticmethod
    def _text(layer: Any) -> Any:
        return next((child.get("text") for child in layer.children() if child.get("text")), None)

    # -- input -----------------------------------------------------------------------------------------------------

    def dispatch(self, event: Input) -> Outcome:
        before = self.focus
        self._heard.clear()
        w = self.window
        match event:
            case PointerInput(part, kind):
                node = self._node("trigger") if part == "trigger" else self._tip_layer()
                if node is None:
                    raise NotRun(f"the part {part!r} is not there")
                if kind == "enter":
                    w.simulate("pointer_move", x=self._inside(node)[0], y=self._inside(node)[1])
                elif kind == "leave":
                    self._away()
                elif kind == "down":
                    w.simulate("pointer_move", x=self._inside(node)[0], y=self._inside(node)[1])
                    w.simulate("pointer_down", x=self._inside(node)[0], y=self._inside(node)[1])
                else:
                    raise NotRun(f"pointer {kind} is not driven")
            case FocusInput(part, via):
                if part == "trigger" and via == "keyboard":
                    w.simulate("key_down", key="shift")  # the keyboard was the last input, so focus that arrives is shown (focus_visible)
                    self._node("trigger").focus()
                elif part is None and self.focus == "trigger":
                    w.simulate("key_down", key="tab")  # on to the next Tab stop: out of the trigger
                else:
                    raise NotRun("focus by pointer without a press is not drivable here")
            case KeyInput(part, key):
                w.simulate("key_down", key=key.lower())
            case ScrollInput():
                w.simulate("wheel", node=self.view._built.outer["root.pane"], delta_x=0.0, delta_y=40.0)
            case WindowInput(kind):
                if kind != "focus_lost":
                    raise NotRun(f"window {kind} is not driven")
                w.simulate("active", active=True)  # an event only fires on a change; a headless window starts inactive
                w.simulate("active", active=False)
            case AdvanceInput(ms):
                w.advance(ms)
            case TextInput() | PressInput() | SetOptionInput():
                raise NotRun("not an input of a tooltip")
        self._settle()
        events = list(self._heard)  # what the tooltip reported itself
        if self.focus != before:
            moved = Event("focus_move", {"from": before, "to": self.focus, "reason": self._focus_reason(event)})
            # the standard's order: a focus input moves focus and then its handlers answer; a pointer down runs its handlers first (SPEC 3.0)
            events = [moved, *events] if isinstance(event, FocusInput) else [*events, moved]
        return Outcome(events, consumed=False)

    @staticmethod
    def _focus_reason(event: Input) -> str:
        """The reason of the input that moved focus: a pointer press is the pointer's, a focus input says its own, anything else the keyboard's."""
        if isinstance(event, PointerInput):
            return "pointer"
        return event.via if isinstance(event, FocusInput) else "keyboard"


def _fields(change: Any) -> dict[str, Any]:
    return {"reason": change.reason, "detail": change.detail, "previous": change.previous, "value": change.value}
