# MenuItem_Stylesheet.tdl

The look of MenuItem (Material 3): 12 pixels each side and between the parts, the label in on_surface, the icon and the trailing text in on_surface_variant.

The look of [`MenuItem`](../../components/menus.md) (in [Menus](../../components/menus.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: MenuItem
Tesserae: "0.6"
---
# The look of MenuItem (Material 3): 12 pixels each side and between the parts, the label in on_surface, the icon and the trailing text in on_surface_variant.
Styles {
  Rule {
    Widget: MenuItem
    Style {
      Padding: <| {'left': 12 if density == '' else density_token(density, 'row_padding_x'), 'right': 12 if density == '' else density_token(density, 'row_padding_x'), 'top': 0, 'bottom': 0} |>
      Gap: <| 12 if density == '' else density_token(density, 'icon_label_gap') |>
    }
  }
  Rule { Widget: MenuItem, Part: label, Style { Foreground: on_surface } }
  Rule { Widget: MenuItem, Part: lead, Style { Width: 24, Height: 24, Foreground: on_surface_variant } }
  Rule { Widget: MenuItem, Part: trailing, Style { Foreground: on_surface_variant } }
  Rule { Widget: MenuItem, Part: chevron, Style { Width: 24, Height: 24, Foreground: on_surface_variant } }
}
```

## How it reaches the view

Each rule names `Widget: MenuItem` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `MenuItem` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `<\| {'left': 12 if density == '' else density_token(density, 'row_padding_x'), 'right': 12 if density == '' el…` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `<\| 12 if density == '' else density_token(density, 'icon_label_gap') \|>` | Space between its children. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `lead` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `trailing` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `chevron` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: MenuItem
    Part: label
    Style { Foreground: tertiary }
  }
}
```
