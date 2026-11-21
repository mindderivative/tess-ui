# ListItem_Stylesheet.tdl

The look of ListItem (Material 3): 16 pixels of padding each side, 16 between the parts; the headline in on_surface, the supporting text and the small text in on_surface_variant; a selected item is secondary_container.

The look of [`ListItem`](../../components/lists.md) (in [Lists](../../components/lists.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: ListItem
Tesserae: "0.6"
---
# The look of ListItem (Material 3): 16 pixels of padding each side, 16 between the parts; the headline in on_surface, the supporting text and the
# small text in on_surface_variant; a selected item is secondary_container.
Styles {
  Rule {
    Widget: ListItem
    Style {
      Padding: <| {'left': 16 if app_density() == '' else density_token(app_density(), 'row_padding_x'), 'right': 16 if app_density() == '' else density_token(app_density(), 'row_padding_x'), 'top': 8 if app_density() == '' else (density_token(app_density(), 'row_height') - 20) / 2, 'bottom': 8 if app_density() == '' else (density_token(app_density(), 'row_height') - 20) / 2} |>
      Gap: <| 16 if app_density() == '' else density_token(app_density(), 'icon_label_gap') |>
      Background: <| 'secondary_container' if selected else 'transparent' |>
    }
  }
  Rule { Widget: ListItem, Part: headline, Style { Foreground: on_surface } }
  Rule { Widget: ListItem, Part: supporting, Style { Foreground: on_surface_variant } }
  Rule { Widget: ListItem, Part: overline, Style { Foreground: on_surface_variant } }
  Rule { Widget: ListItem, Part: trailing_text, Style { Foreground: on_surface_variant } }
  Rule { Widget: ListItem, Part: leading_icon, Style { Foreground: on_surface_variant, Width: 24, Height: 24 } }
  Rule { Widget: ListItem, Part: trailing_icon, Style { Foreground: on_surface_variant, Width: 24, Height: 24 } }
  Rule {
    Widget: ListItem
    Part: avatar
    Style { Width: 40, Height: 40, Corner_Radius: full, Background: primary_container, Align_Content: center }
  }
  Rule { Widget: ListItem, Part: avatar_text, Style { Foreground: on_primary_container } }
  Rule { Widget: ListItem, Part: picture, Style { Width: 56, Height: 56, Corner_Radius: 4 } }
}
```

## How it reaches the view

Each rule names `Widget: ListItem` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `ListItem` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `<\| {'left': 16 if app_density() == '' else density_token(app_density(), 'row_padding_x'), 'right': 16 if app_…` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `<\| 16 if app_density() == '' else density_token(app_density(), 'icon_label_gap') \|>` | Space between its children. |
| always | `Background` | `<\| 'secondary_container' if selected else 'transparent' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |

### `headline` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `supporting` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `overline` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `trailing_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `leading_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `trailing_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `avatar` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Background` | `primary_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |

### `avatar_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_primary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `picture` (Image)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `56` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `56` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `4` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: ListItem
    Style { Background: tertiary }
  }
}
```
