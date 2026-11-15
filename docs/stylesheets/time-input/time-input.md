# TimeInput_Stylesheet.tdl

The look of TimeInput: the colon in on_surface, centred on the fields.

The look of [`TimeInput`](../../components/time-input.md) (in [Time input](../../components/time-input.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: TimeInput
Tesserae: "0.6"
---
# The look of TimeInput: the colon in on_surface, centred on the fields.
Styles {
  Rule { Widget: TimeInput, Part: colon, Style { Foreground: on_surface } }
}
```

## How it reaches the view

Each rule names `Widget: TimeInput` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `colon` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: TimeInput
    Part: colon
    Style { Foreground: tertiary }
  }
}
```
