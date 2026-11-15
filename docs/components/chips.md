# Chips

*Selection and input*

## In Material Design 3

Chips are compact elements for an action, a filter, a piece of input, or a suggestion. **Assist** chips
start an action, **filter** chips narrow results (and show a check when selected), **input** chips are
things the user entered, and **suggestion** chips offer a reply or next step.

## In Tesserae

`Chip` is a view Tesserae ships (`Chip_View.tdl`): 32 pixels tall with 8 pixel corners, as wide as its label. `ChipGroup` is a wrapping row of
them.

A chip has a leading 18 pixel `Icon`, or `Avatar_Text`: letters in a 24 pixel circle. A filter or input chip that is `Selected` is `secondary_container` with no outline, and
a filter chip also shows a check in place of its icon. `elevated` swaps the outline for a raised surface. A `Removable` chip (an input chip) has a close button: pressing it
sets `Removed` to true and runs `On_Remove`. A filter chip is a checkbox to a screen reader and the others are buttons; a disabled chip is dimmed and not focusable.

A filter chip flips `Selected` itself (`Flip: false` leaves that to you); `Handlers { On_Click: ... }` on the call is what a press does. A `ChipGroup` takes
`Chips` (`{Value, Label}` and optionally `{Icon, Avatar_Text, Disabled}`) and a `Mode`: `none` (assist or suggestion chips; the last pressed goes to
`Chosen`), `single` or `multiple` (filter chips; `Selected` is the value or the list of values), or `input` (chips with a close, and a field: Enter adds a
chip, the close removes one, and `Chips` is two-way; `Entry` is what is typed and `Placeholder` its hint). In `none` mode `Variant` is `assist` or `suggestion`, and
`elevated` raises every chip. The group is one Tab stop and the arrow keys move the focus along the chips (in `single` mode the focus carries the choice with it). Not built:
dragging chips to reorder, and a chip group that scrolls sideways.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Chip { ... }`. A file of the same name in your project replaces it.

### `Chip`

The Material 3 chip: assist (an action), filter (a toggle), input (a piece of what the user entered, with a close) or suggestion (a suggested reply or query). 32 pixels tall with 8 pixel corners, a `label_large` label and an optional 18 pixel leading `Icon` or 24 pixel avatar (`Avatar_Text`, letters in a circle). A filter chip flips `Selected` on a press, and while it is on it is `secondary_container` with a check in place of its icon. An input chip has a close button, `Removable`, which sets `Removed` to true. `Elevated` swaps the outline for a raised surface. `Handlers: {On_Click: ...}` on the call is what a press does. Colours and shapes are in Chip_Stylesheet.tdl.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Label` | `str` |  | The text. |
| `Variant` | `assist` or `filter` or `input` or `suggestion` | `assist` | assist runs an action; filter toggles; input is what the user entered; suggestion offers a reply or a query. |
| `Icon` | `str` |  | A leading icon. |
| `Avatar_Text` | `str` |  | Letters in a circle before the label (an avatar). |
| `Selected` | `bool` | `false` | For a filter or input chip: whether it is on. Two-way: give it a bare reference and the view writes it back. |
| `Elevated` | `bool` | `false` | A raised surface instead of an outline. |
| `Removable` | `bool` | `false` | A close button after the label (an input chip). |
| `Removed` | `bool` | `false` | Set to true when the close button is pressed. Two-way: give it a bare reference and the view writes it back. |
| `On_Remove` | `handler` |  | What to do when the close button is pressed, written as a handler (an action name or statements). |
| `Flip` | `bool` | `true` | For a filter chip: whether a press flips `Selected` itself. Off, the caller decides (a chip group does). |
| `Disabled` | `bool` | `false` | Dimmed, not focusable, and it does not respond. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `avatar` (Container), `avatar_text` (Text), `icon` (Icon), `label` (Text), `close` (Container), `close_icon` (Icon).

Its look is in [`Chip_Stylesheet.tdl`](../stylesheets/chips/chip.md).

### `ChipGroup`

A group of chips, wrapping onto new rows. `Chips` is a list of {value, label} and optionally {icon, avatar_text, disabled}. `Mode` says how they behave: `none` suggestion/assist chips that act (the last one pressed goes to `Chosen`); `single` and `Multiple` filter chips (`Selected` is the chosen value, or the list of them); `input` chips with a close button and a text field after them, so typing and pressing Enter adds a chip, and the close removes one (`Chips` is two-way: the list the user has built). One Tab stop; the arrows move the focus along the chips (and, for `single`, the choice).

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Chips` | `list` | `[]` | The chips, each {value, label} and optionally {icon, avatar_text, disabled}. In input mode adding and removing write it back. Two-way: give it a bare reference and the view writes it back. |
| `Mode` | `none` or `single` or `multiple` or `input` | `none` | none: actions; single or multiple: filters; input: what the user entered. |
| `Selected` | `any` |  | single: the chosen value; multiple: the list of chosen values. Two-way: give it a bare reference and the view writes it back. |
| `Chosen` | `any` |  | none: the value of the chip last pressed. Two-way: give it a bare reference and the view writes it back. |
| `Variant` | `assist` or `suggestion` | `assist` | The look of the chips in `none` mode. |
| `Elevated` | `bool` | `false` | Raised chips instead of outlined ones. |
| `Placeholder` | `str` | `Add` | Input mode: the hint in the text field. |
| `Entry` | `str` |  | Input mode: what is typed in the field. Two-way: give it a bare reference and the view writes it back. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `chip` (Chip), `entry` (TextField).

## Using it

```tdl
Container {
  Name: filters
  Style { Flex_Direction: vertical, Gap: 16, Width: 420, Height: 240 }
  Children {
    Chip {
      Label: Share
      Icon: home
      Handlers {
        On_Click: share
      }
    }
    ChipGroup {
      Mode: multiple
      Selected: <| filters |>
      Chips {
        Item { Value: open, Label: Open }
        Item { Value: mine, Label: Mine }
        Item { Value: late, Label: Overdue }
      }
    }
    ChipGroup {
      Mode: input
      Chips: <| tags |>
      Entry: <| typed |>
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import chip

shipped = chip(app.window, "Shipped", 96, variant="filter", selected=True)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Chip_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Chip
    Part: label
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
