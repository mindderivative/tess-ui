# SearchBar_Stylesheet.tdl

The look of SearchBar (Material 3): a surface_container_high pill, 56 tall, at level 3; 4 pixels in from the edge, the icons 24 pixels in a 48 pixel button, the text in on_surface and the placeholder dimmed, the avatar a 30 pixel circle in primary_container.

The look of [`SearchBar`](../../components/search.md) (in [Search](../../components/search.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: SearchBar
Tesserae: "0.6"
---
# The look of SearchBar (Material 3): a surface_container_high pill, 56 tall, at level 3; 4 pixels in from the edge, the icons 24 pixels in a 48 pixel button, the text
# in on_surface and the placeholder dimmed, the avatar a 30 pixel circle in primary_container.
Styles {
  Rule {
    Widget: SearchBar
    Style {
      Background: <| 'surface_container_high@72%' if frosted else 'surface_container_high' |>
      Backdrop_Blur: <| 20 if frosted else 0 |>
      Corner_Radius: full
      Elevation: 3
      Padding { Left: 4, Right: 12, Top: 0, Bottom: 0 }
      Gap: 4
    }
  }
  Rule {
    Widget: SearchBar
    Part: back
    Style { Width: 48, Height: 48, Corner_Radius: 24, Align_Content: center }
  }
  Rule {
    Widget: SearchBar
    Part: leading
    Style { Width: 48, Height: 48, Corner_Radius: 24, Align_Content: center }
  }
  Rule {
    Widget: SearchBar
    Part: clear
    Style { Width: 48, Height: 48, Corner_Radius: 24, Align_Content: center }
  }
  Rule {
    Widget: SearchBar
    Part: trailing
    Style { Width: 48, Height: 48, Corner_Radius: 24, Align_Content: center }
  }
  Rule { Widget: SearchBar, Part: back_icon, Style { Width: 24, Height: 24, Foreground: on_surface } }
  Rule { Widget: SearchBar, Part: leading_glyph, Style { Width: 24, Height: 24, Foreground: on_surface } }
  Rule { Widget: SearchBar, Part: clear_icon, Style { Width: 24, Height: 24, Foreground: on_surface_variant } }
  Rule { Widget: SearchBar, Part: trailing_glyph, Style { Width: 24, Height: 24, Foreground: on_surface_variant } }
  Rule {
    Widget: SearchBar
    Part: input
    Style { Foreground: on_surface, Background: transparent }
  }
  Rule {
    Widget: SearchBar
    Part: avatar
    Style { Width: 30, Height: 30, Corner_Radius: full, Background: primary_container, Align_Content: center }
  }
  Rule { Widget: SearchBar, Part: avatar_text, Style { Foreground: on_primary_container } }
}
```

## How it reaches the view

Each rule names `Widget: SearchBar` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `SearchBar` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'surface_container_high@72%' if frosted else 'surface_container_high' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Backdrop_Blur` | `<\| 20 if frosted else 0 \|>` | Blurs what is behind it, by this many pixels: with a translucent `Background`, a frosted surface. |
| always | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Elevation` | `3` | A shadow level, 0 to 5. |
| always | `Padding` | `{ Left: 4, Right: 12, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `4` | Space between its children. |

### `back` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `48` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `48` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `24` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `leading` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `48` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `48` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `24` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `clear` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `48` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `48` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `24` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `trailing` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `48` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `48` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `24` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `back_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `leading_glyph` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `clear_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `trailing_glyph` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `input` (TextInput)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Background` | `transparent` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |

### `avatar` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `30` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `30` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Background` | `primary_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `avatar_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_primary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: SearchBar
    Style { Background: tertiary }
  }
}
```
