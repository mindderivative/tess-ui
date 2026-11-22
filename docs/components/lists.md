# Lists

*Containment*

## In Material Design 3

A list is a column of rows, each a headline with optional leading and trailing content and supporting text.

## In Tesserae

`ListItem` is a view Tesserae ships (`ListItem_View.tdl`): a row as wide as its place, 56, 72 or 88 pixels tall by its lines. A list is a
container of them (or a `For:`, or a `VirtualList`, over your data).

The `Headline` is the first line, `Supporting` the line under it and `Overline` a small line above it; they set the height (56 for one line, 72 for two, 88 for three) unless
`Lines` says. Before the text goes a 24 pixel `Leading_Icon`, a 40 pixel circle holding the letters of `Leading_Text`, or a 56 pixel `Leading_Image`; after it a `Trailing_Text` or a
`Trailing_Icon`. With `Selectable` a press flips `Selected`, and a selected row is `secondary_container`. `Divider` draws a line along the bottom edge.

Your own content goes in the `Leading` and `Trailing` slots (`Slot: trailing` on a child): a switch, a checkbox, a button. `Handlers { On_Click: ... }` on
the call is what a press does. A section's header can hold the top of a `ScrollView` while its rows scroll past: give it `Style { Sticky: 0 }`. Not built: swipe actions, drag to
reorder, and the dragged state.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `ListItem { ... }`. A file of the same name in your project replaces it.

### `ListItem`

The Material 3 list item: one, two or three lines of text with something before it and something after it. `Headline` is the first line, `Supporting` the second, and an `Overline` goes above the headline; the item is 56, 72 or 88 pixels tall by how many of those it has (`Lines` overrides). Before the text: a `Leading_Icon`, a `Leading_Text` in a circle (an avatar), a `Leading_Image` (56 pixels), or your own content in the `Leading` slot. After it: a `Trailing_Text`, a `Trailing_Icon`, or your own content in the `Trailing` slot (a switch, a checkbox, a button). It is pressable (a state layer, a ripple, Enter); `Handlers: {On_Click: open}` on the call is what a press does. With `Selectable` a press flips `Selected`, and a selected item is `secondary_container`. `Divider` draws a line along its bottom edge.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Headline` | `str` |  | The first line. |
| `Supporting` | `str` |  | The line under the headline. |
| `Overline` | `str` |  | A small line above the headline. |
| `Leading_Icon` | `str` |  | An icon before the text. |
| `Leading_Text` | `str` |  | One or two letters in a circle before the text (an avatar). |
| `Leading_Image` | `str` |  | A picture before the text, 56 pixels, relative to the view. |
| `Trailing_Text` | `str` |  | Small text after it. |
| `Trailing_Icon` | `str` |  | An icon after it. |
| `Lines` | `int` | `0` | 1, 2 or 3 lines; 0 works it out from the text it has. |
| `Selectable` | `bool` | `false` | A press flips `Selected`. |
| `Selected` | `bool` | `false` | Whether it is selected. Two-way: give it a bare reference and the view writes it back. |
| `Pickable` | `bool` | `false` | The row is a choice in a list that does the selecting (a selectable `list_` sets it): it tells assistive technology whether it is selected, and a press does not flip `Selected` itself. |
| `Disabled` | `bool` | `false` | Dimmed, not focusable, and it does not respond. |
| `Divider` | `bool` | `false` | A line along the bottom edge. |
| `Actionable` | `bool` | `true` | Whether the row is a Tab stop that a press and Enter act on. False for a row that only shows something (a plain list's row): it takes no focus (Focus none). |

Children go in the `leading` slot, the `trailing` slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `leading_icon` (Icon), `avatar` (Container), `avatar_text` (Text), `picture` (Image), `text` (Container), `overline` (Text), `headline` (Text), `supporting` (Text), `trailing_text` (Text), `trailing_icon` (Icon), `line` (Divider).

Its look is in [`ListItem_Stylesheet.tdl`](../stylesheets/lists/list-item.md).

## Using it

```tdl
Container {
  Name: mail
  Style { Flex_Direction: vertical, Width: 360, Height: 300 }
  Children {
    ListItem {
      Headline: Inbox
      Supporting: "12 unread"
      Leading_Icon: home
      Trailing_Text: "5m"
      Divider: true
      Handlers {
        On_Click: open_inbox
      }
    }
    ListItem {
      Headline: Wi-Fi
      Supporting: Connected
      Children {
        Switch {
          Slot: trailing
          Selected: <| wifi |>
        }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import list_, list_item

rows = list_(app.window, [list_item(app.window, name) for name in ("Inbox", "Sent", "Drafts")], width=320)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# ListItem_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: ListItem
    Part: headline
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Lists](../guide/lists.md)
- [Effects](../guide/effects.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
