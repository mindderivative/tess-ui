# Cards

*Containment*

## In Material Design 3

A card holds content and actions about one subject. It comes **elevated** (a shadow), **filled** (a
higher surface) or **outlined** (a border). All have a medium (12dp) corner radius.

## In Tesserae

`Card` is a view Tesserae ships (`Card_View.tdl`): a surface with 12 pixel corners that is as tall as what is in it.

The `Variant` is a shadow (`elevated`, level 1), a higher surface (`filled`) or a 1 pixel `outline_variant` border (`outlined`). The `Headline` is `title_large`, the `Subhead`
`title_small` and the `Text` `body_medium`, with 16 pixels around them. A `Media` picture runs across the top, clipped to the corners (160 pixels tall unless `Media_Height` says
otherwise). An `Actionable` card is one pressable surface: a state layer, a ripple, Enter, and a lift to level 2 for the elevated one when hovered. A `Selected` card is
`secondary_container` (an outlined one gets an `outline` border instead); the caller decides when, as in `On_Click: "picked = not picked"`. A `Disabled` card is dimmed.

Your own content goes in the default slot, after the text, and buttons in the `Actions` slot (a row at the end). `Handlers { On_Click: ... }` on the call is
what a press of an actionable card does. A plain card is a group and takes no focus. Not built: dragging and swiping a card, and the dragged state.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Card { ... }`. A file of the same name in your project replaces it.

### `Card`

The Material 3 card: a surface that holds content about one subject. `Variant` is elevated, filled or outlined. It can have a `Media` picture across the top, a `Headline`, a `Subhead` and supporting `Text`; your own content goes in the default slot, and a row of `Actions` (buttons) in the `Actions` slot. An `Actionable` card is one pressable surface (a state layer, a ripple, Enter, a lift for the elevated one): `Handlers: {On_Click: open}` on the call is what a press does, and the buttons inside one are a conflict MD3 asks you to avoid. `Selected` shows a chosen card; the caller decides when (`On_Click: "picked = not picked"`). Colours, corners and how it lifts are in Card_Stylesheet.tdl.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Variant` | `elevated` or `filled` or `outlined` | `elevated` | elevated has a shadow, filled a higher surface, outlined a border. |
| `Headline` | `str` |  | The title. |
| `Subhead` | `str` |  | A line under the title. |
| `Text` | `str` |  | Supporting text. |
| `Media` | `str` |  | A picture across the top, relative to the view. |
| `Media_Height` | `float` | `160` | How tall the picture is. |
| `Actionable` | `bool` | `false` | The whole card is one pressable surface. |
| `Selected` | `bool` | `false` | Whether the card is chosen (the caller decides when). |
| `Bare` | `bool` | `false` | Only the surface: no picture and no body, and nothing is clipped, so a Python widget's own nodes can be added straight into the card. |
| `Disabled` | `bool` | `false` | Dimmed, and an actionable card does not respond. |

Children go in the default slot, the `actions` slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `picture` (Image), `body` (Container), `headline` (Text), `subhead` (Text), `text` (Text), `actions` (Container).

Its look is in [`Card_Stylesheet.tdl`](../stylesheets/cards/card.md).

## Using it

```tdl
Container {
  Name: trips
  Style { Flex_Direction: horizontal, Gap: 16, Padding: 16, Width: 560, Height: 360 }
  Children {
    Card {
      Headline: Paris
      Subhead: "Three days"
      Text: "Flights and a hotel."
      Media: paris.png
      Style { Width: 240 }
      Children {
        Button {
          Label: Book
          Variant: text
          Slot: actions
        }
      }
    }
    Card {
      Variant: outlined
      Headline: Rome
      Actionable: true
      Selected: <| picked |>
      Style { Width: 240 }
      Handlers {
        On_Click: pick
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import card

summary = card(app.window, 240, 120, variant="elevated")
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Card_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Card
    Part: headline
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
