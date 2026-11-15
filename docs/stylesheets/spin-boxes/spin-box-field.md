# SpinBoxField_Stylesheet.tdl

The look of SpinBoxField: the label in on_surface_variant, the supporting text in on_surface_variant and an error in error; 16 pixels in from the edge, as a text field's are.

The look of [`SpinBoxField`](../../components/spin-boxes.md) (in [Spin box](../../components/spin-boxes.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: SpinBoxField
Tesserae: "0.6"
---
# The look of SpinBoxField: the label in on_surface_variant, the supporting text in on_surface_variant and an error in error; 16 pixels in from the edge, as a
# text field's are.
Styles {
  Rule { Widget: SpinBoxField, Part: label, Style { Foreground: <| 'error' if error != '' else 'on_surface_variant' |>, Margin { Left: 4 } } }
  Rule { Widget: SpinBoxField, Part: help, Style { Foreground: <| 'error' if error != '' else 'on_surface_variant' |>, Margin { Left: 4 } } }
}
```

## How it reaches the view

Each rule names `Widget: SpinBoxField` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `<\| 'error' if error != '' else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Margin` | `{ Left: 4 }` | Space outside it: one number, or `{Left, Right, Top, Bottom}`. |

### `help` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `<\| 'error' if error != '' else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Margin` | `{ Left: 4 }` | Space outside it: one number, or `{Left, Right, Top, Bottom}`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: SpinBoxField
    Part: label
    Style { Foreground: tertiary }
  }
}
```
