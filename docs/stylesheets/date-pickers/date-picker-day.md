# DatePickerDay_Stylesheet.tdl

The look of DatePickerDay: the selected day is a primary circle with on_primary text; today a 1 pixel primary outline with primary text; a day outside the month is on_surface_variant; the rest on_surface.

The look of [`DatePickerDay`](../../components/date-pickers.md) (in [Date picker](../../components/date-pickers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: DatePickerDay
Tesserae: "0.6"
---
# The look of DatePickerDay: the selected day is a primary circle with on_primary text; today a 1 pixel primary outline with primary text; a day outside the month is
# on_surface_variant; the rest on_surface.
Styles {
  Rule {
    Widget: DatePickerDay
    Part: circle
    Style {
      Background: <| 'primary' if selected else 'transparent' |>
      Border_Width: <| 1 if (today and not selected) else 0 |>
      Border_Color: primary
    }
  }
  Rule {
    Widget: DatePickerDay
    Part: number
    Style { Foreground: <| 'on_primary' if selected else ('primary' if today else ('on_surface_variant' if outside else 'on_surface')) |> }
  }
}
```

## How it reaches the view

Each rule names `Widget: DatePickerDay` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `circle` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'primary' if selected else 'transparent' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Border_Width` | `<\| 1 if (today and not selected) else 0 \|>` | The width of its border, in pixels. |
| always | `Border_Color` | `primary` | The colour of its border: a colour or a gradient. |

### `number` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `<\| 'on_primary' if selected else ('primary' if today else ('on_surface_variant' if outside else 'on_surface')…` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: DatePickerDay
    Part: circle
    Style { Background: tertiary }
  }
}
```
