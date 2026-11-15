# Snackbar_Stylesheet.tdl

The look of Snackbar (Material 3): inverse_surface at level 3 with 4 pixel corners, 16 pixels in from the edge on the left and 8 on the right of the buttons; the message in inverse_on_surface, the action in inverse_primary.

The look of [`Snackbar`](../../components/snackbars.md) (in [Snackbars](../../components/snackbars.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Snackbar
Tesserae: "0.6"
---
# The look of Snackbar (Material 3): inverse_surface at level 3 with 4 pixel corners, 16 pixels in from the edge on the left and 8 on the right of the buttons;
# the message in inverse_on_surface, the action in inverse_primary.
Styles {
  Rule {
    Widget: Snackbar
    Style {
      Background: inverse_surface
      Corner_Radius: 4
      Elevation: 3
    }
  }
  Rule {
    Widget: Snackbar
    Part: bar
    Style { Padding { Left: 16, Right: 8, Top: 0, Bottom: 0 } }
  }
  Rule {
    Widget: Snackbar
    Part: message
    Style { Foreground: inverse_on_surface, Flex: expand_horizontal, Padding { Left: 0, Right: 0, Top: 14, Bottom: 14 } }
  }
  Rule {
    Widget: Snackbar
    Part: action
    Style { Padding { Left: 8, Right: 8, Top: 8, Bottom: 8 }, Corner_Radius: 16 }
  }
  Rule { Widget: Snackbar, Part: action_text, Style { Foreground: inverse_primary } }
  Rule {
    Widget: Snackbar
    Part: close
    Style { Width: 40, Height: 40, Corner_Radius: 20, Align_Content: center }
  }
  Rule { Widget: Snackbar, Part: close_icon, Style { Foreground: inverse_on_surface, Width: 24, Height: 24 } }
}
```

## How it reaches the view

Each rule names `Widget: Snackbar` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Snackbar` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `inverse_surface` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Corner_Radius` | `4` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Elevation` | `3` | A shadow level, 0 to 5. |

### `bar` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `{ Left: 16, Right: 8, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `message` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `inverse_on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Flex` | `expand_horizontal` | How it takes room in its parent: `none` (the default) is as big as its content and never squeezed, `expand_horizontal` and `expand_vertical` take the room left over in that direction, `fill` both. |
| always | `Padding` | `{ Left: 0, Right: 0, Top: 14, Bottom: 14 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `action` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `{ Left: 8, Right: 8, Top: 8, Bottom: 8 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Corner_Radius` | `16` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

### `action_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `inverse_primary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `close` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `20` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `close_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `inverse_on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Snackbar
    Style { Background: tertiary }
  }
}
```
