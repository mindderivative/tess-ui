# Icon buttons

*Actions*

## In Material Design 3

An icon button is an action shown as a glyph alone. Like buttons it has four emphases: standard (no
container), filled, filled tonal and outlined. It is 40dp, with a 48dp touch target.

## In Tesserae

`IconButton` is a view Tesserae ships (`IconButton_View.tdl`): one widget for the four types, in five sizes and three widths. The `Label`
names it for a screen reader and is its tooltip. `Handlers { On_Click: ... }` on the call is what a press does.

The glyph is 20, 24, 24, 32 or 40 pixels for the five sizes. `Width_Kind` makes it as wide as it is tall (`default`), or narrower or wider (a 40 pixel button is 32
pixels wide when `narrow` and 52 when `wide`). A toggle (`Toggle: true`) flips `Selected` on a press, and the `Selected_Icon`, the colours and the shape show while it is on. The
glyph morphs into the other over 200 ms when the two are both closed shapes or both open lines (`add` and `remove` do); other pairs, such as `play` and `pause`, switch partway through
instead. `Tint` sets a standard button's icon colour to a colour role. A button with a `Label` shows it as a tooltip, and without one there is no tooltip.

The state layer, ripple and focus ring are the node's interaction; a pressed circle squares off. Not built: the 12% container of a disabled filled
button, and the 48 pixel touch target around a 40 pixel button.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `IconButton { ... }`. A file of the same name in your project replaces it.

### `IconButton`

The Material 3 icon button: standard, filled, tonal or outlined, in five sizes and three widths, round or square, with a toggle form that swaps its icon. `Label` is required in spirit: it names the button for a screen reader and is its tooltip, since an icon has no text. `Handlers: {On_Click: save}` on the call is what a press does. A toggle flips `Selected` (two-way, or held by the button when nothing is bound). Colours, sizes and shapes are in IconButton_Stylesheet.tdl.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Icon` | `str` |  | The icon. |
| `Selected_Icon` | `str` |  | For a toggle: the icon while it is on (the same icon when empty). |
| `Label` | `str` |  | What it does: its accessible name and its tooltip. |
| `Shortcut` | `str` |  | Its shortcut, written after the name in the tooltip (`Save (Ctrl+S)`); the accessible name stays the label. |
| `Variant` | `standard` or `filled` or `tonal` or `outlined` | `standard` | standard has no container; filled is the strongest; tonal is softer; outlined has a border. |
| `Size` | `xs` or `s` or `m` or `l` or `xl` | `s` | 32, 40, 56, 96 or 136 pixels tall. |
| `Width_Kind` | `narrow` or `default` or `wide` | `default` | narrow, as tall as it is, or wide. |
| `Shape` | `round` or `square` | `round` | A circle, or a rounded square. A toggle swaps to the other shape while selected. |
| `Disabled` | `bool` | `false` | Dimmed, not focusable, and it does not respond. |
| `Toggle` | `bool` | `false` | A press flips `Selected`. |
| `Selected` | `bool` | `false` | For a toggle: whether it is on. Two-way: give it a bare reference and the view writes it back. |
| `Tint` | `str` |  | A standard button's icon colour, a colour role such as on_primary_container (on_surface_variant when empty). |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `icon` (Icon).

Its look is in [`IconButton_Stylesheet.tdl`](../stylesheets/icon-buttons/icon-button.md).

## Using it

```tdl
Container {
  Name: toolbar
  Style { Flex_Direction: horizontal, Gap: 8, Padding: 16 }
  Children {
    IconButton {
      Icon: settings
      Label: Settings
      Handlers {
        On_Click: open_settings
      }
    }
    IconButton {
      Icon: home
      Selected_Icon: search
      Label: Favourite
      Variant: filled
      Toggle: true
      Selected: <| favourite |>
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import icon_button

settings = icon_button(app.window, "settings", 40, variant="standard")
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# IconButton_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: IconButton
    Variant: standard
    Part: icon
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
