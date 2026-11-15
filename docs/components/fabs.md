# Floating action buttons

*Actions*

## In Material Design 3

A floating action button (FAB) is the screen's most important action, as an icon in a prominent container.
There are four colours (primary, secondary, tertiary and surface) and three sizes: small (40dp), the
default (56dp) and large (96dp).

## In Tesserae

`Fab` is a view Tesserae ships (`Fab_View.tdl`): one widget for the four colours and three sizes, and for the extended form too (give it a
`Label`).

The glyph is 24 pixels, 36 on a large FAB, and the corners are 12, 16 and 28 pixels for the three sizes. A collapsed extended FAB shows only its icon, and its
label becomes its tooltip; the label is also the accessible name.

It rests at elevation level 3, lifts to 4 when hovered and settles to 3 when pressed. To collapse as a list scrolls down and extend as it scrolls up, bind
`Collapsed: "<| way == 'down' |>"` to the `Scroll_Direction` of the list. Not built: easing the collapse and the extend (the width goes between a number and `auto`,
which the engine does not animate, so the FAB changes shape at once), and the FAB menu.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Fab { ... }`. A file of the same name in your project replaces it.

### `Fab`

The Material 3 floating action button, and its extended form: an icon in a prominent container, with a label beside it when `Label` is given. In four colours (`Variant`: primary, secondary, tertiary, surface) and three sizes (`Size`: small 40, medium 56, large 96). An extended FAB collapses to just its icon when `Collapsed` is true; bind that to the way a list scrolls (`Collapsed: "<| way == 'down' |>"`) for the usual behaviour. `Label` names it for a screen reader and, when it is only an icon, is its tooltip. `Handlers: {On_Click: add}` on the call is what a press does. Colours, sizes and how it lifts are in Fab_Stylesheet.tdl.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Icon` | `str` |  | The icon. |
| `Label` | `str` |  | The text beside the icon (an extended FAB); also its accessible name. |
| `Variant` | `primary` or `secondary` or `tertiary` or `surface` | `primary` | The container colour. |
| `Size` | `small` or `medium` or `large` | `medium` | 40, 56 or 96 pixels. An extended FAB is 56 tall. |
| `Collapsed` | `bool` | `false` | An extended FAB shows only its icon. |
| `Disabled` | `bool` | `false` | Dimmed, not focusable, and it does not respond. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `icon` (Icon), `label` (Text).

Its look is in [`Fab_Stylesheet.tdl`](../stylesheets/fabs/fab.md).

## Using it

```tdl
Container {
  Name: inbox
  Style { Flex_Direction: vertical, Width: 360, Height: 480 }
  Children {
    ScrollView {
      Scroll_Direction: <| way |>
      Style { Height: 400 }
      Children {
        Text {
          Text: Messages
          Typography_Role: body_medium
          Style { Foreground: on_surface }
        }
      }
    }
    Fab {
      Icon: add
      Label: Compose
      Collapsed: <| way == 'down' |>
      Handlers {
        On_Click: compose
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import fab

add = fab(app.window, "add", size="default", variant="primary")
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Fab_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Fab
    Variant: primary
    Part: icon
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
