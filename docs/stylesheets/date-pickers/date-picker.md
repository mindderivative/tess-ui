# DatePicker_Stylesheet.tdl

The look of DatePicker (Material 3): a surface_container_high dialog with 28 pixel corners and 24 pixels of padding; the heading in on_surface_variant, the date in on_surface, the weekday initials and the month in on_surface_variant / on_surface.

The look of [`DatePicker`](../../components/date-pickers.md) (in [Date picker](../../components/date-pickers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: DatePicker
Tesserae: "0.6"
---
# The look of DatePicker (Material 3): a surface_container_high dialog with 28 pixel corners and 24 pixels of padding; the heading in on_surface_variant, the date in on_surface,
# the weekday initials and the month in on_surface_variant / on_surface.
Styles {
  Rule {
    Widget: DatePicker
    Part: panel
    Style {
      Background: surface_container_high
      Corner_Radius: 28
      Padding: 24
      Elevation: 3
    }
  }
  Rule { Widget: DatePicker, Part: heading, Style { Foreground: on_surface_variant } }
  Rule { Widget: DatePicker, Part: chosen, Style { Foreground: on_surface } }
  Rule { Widget: DatePicker, Part: month, Style { Foreground: on_surface } }
  Rule { Widget: DatePicker, Part: initial, Style { Foreground: on_surface } }
}
```

## How it reaches the view

Each rule names `Widget: DatePicker` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `panel` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface_container_high` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Corner_Radius` | `28` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Padding` | `24` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Elevation` | `3` | A shadow level, 0 to 5. |

### `heading` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `chosen` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `month` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `initial` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: DatePicker
    Part: panel
    Style { Background: tertiary }
  }
}
```
