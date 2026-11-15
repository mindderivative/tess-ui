# Dividers

*Containment*

## In Material Design 3

A divider is a thin line that groups and separates content in lists and containers. It spans the whole length (**full-width**), starts
16 dp in from the start (**inset**), or is 16 dp in from both ends (**middle inset**), and is horizontal or vertical.

## In Tesserae

`Divider` is a view Tesserae ships (`Divider_View.tdl`) with its look as rules (`Divider_Stylesheet.tdl`): a line in the
`outline_variant` colour that fills the length it is in, and is a `separator` to a screen reader.

The `Variant` says how much of the ends it keeps clear (`full` by default; `inset` leaves 16 pixels at the start, `middle` 16 at both ends). A `horizontal` divider fills the
width it is in and a `vertical` one the height (in a container that does not set `Align_Content`, which would size it to its content, and so to nothing); it is 1 pixel thick unless `Thickness` says.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Divider { ... }`. A file of the same name in your project replaces it.

### `Divider`

The Material 3 divider: a thin line that separates content. `Variant: full | inset | middle`, `Orientation: horizontal | vertical`. What it looks like (the colour, the thickness, the insets) is in Divider_Stylesheet.tdl; this file is its structure. A screen reader hears it as a `separator`.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Variant` | `full` or `inset` or `middle` | `full` | full spans the whole length; inset starts 16 in from the start; middle is 16 in from both ends. |
| `Orientation` | `horizontal` or `vertical` | `horizontal` | Horizontal separates rows and fills the width it is in; vertical separates columns and fills the height. |
| `Thickness` | `float` | `1` | How thick the line is. |

Its look is in [`Divider_Stylesheet.tdl`](../stylesheets/dividers/divider.md).

## Using it

```tdl
Container {
  Name: settings
  Style { Flex_Direction: vertical, Width: 320, Height: 160 }
  Children {
    Text {
      Text: Wi-Fi
      Typography_Role: body_large
      Style { Foreground: on_surface }
    }
    Divider {
      Variant: inset
    }
    Text {
      Text: Bluetooth
      Typography_Role: body_large
      Style { Foreground: on_surface }
    }
    Divider { }
  }
}
```

## Changing its look

Write rules for `Divider` in your app's stylesheet; they sit above the shipped ones, and a `Style:` on the node beats every rule for the
fields it sets.

```tdl
Styles {
  Rule {
    Widget: Divider
    Style { Background: outline }
  }
}
```

A view named `Divider_View.tdl` in your project replaces the shipped divider, and its shipped look with it.

## Using it in Python

```python
from tess_ui.widgets import divider

rule = divider(app.window, 240)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Divider_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Divider
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
