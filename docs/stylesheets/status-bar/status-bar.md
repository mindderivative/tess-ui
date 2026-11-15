# StatusBar_Stylesheet.tdl

The look of StatusBar: a thin surface_container strip with label_small text in on_surface_variant; an item that can be pressed has a state layer.

The look of [`StatusBar`](../../components/status-bar.md) (in [Status bar](../../components/status-bar.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: StatusBar
Tesserae: "0.6"
---
# The look of StatusBar: a thin surface_container strip with label_small text in on_surface_variant; an item that can be pressed has a state layer.
Styles {
  Rule {
    Widget: StatusBar
    Style {
      Background: surface_container
      Padding { Left: 8, Right: 8, Top: 0, Bottom: 0 }
    }
  }
  Rule { Widget: StatusBar, Part: text, Style { Foreground: on_surface_variant } }
  Rule { Widget: StatusBar, Part: note_text, Style { Foreground: on_surface_variant } }
  Rule { Widget: StatusBar, Part: icon, Style { Foreground: on_surface_variant, Width: 16, Height: 16 } }
  Rule { Widget: StatusBar, Part: note_icon, Style { Foreground: on_surface_variant, Width: 16, Height: 16 } }
}
```

## How it reaches the view

Each rule names `Widget: StatusBar` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `StatusBar` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Padding` | `{ Left: 8, Right: 8, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `note_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `16` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `16` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `note_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `16` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `16` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: StatusBar
    Style { Background: tertiary }
  }
}
```
