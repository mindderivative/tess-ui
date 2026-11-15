# PeriodSelector_Stylesheet.tdl

The look of PeriodSelector: an outlined frame with 8 pixel corners. The halves' colours are in the view, because a rule cannot see the loop variable that says which half is which.

The look of [`PeriodSelector`](../../components/time-pickers.md) (in [Time picker](../../components/time-pickers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: PeriodSelector
Tesserae: "0.6"
---
# The look of PeriodSelector: an outlined frame with 8 pixel corners. The halves' colours are in the view, because a rule cannot see the loop variable that
# says which half is which.
Styles {
  Rule {
    Widget: PeriodSelector
    Style { Corner_Radius: 8, Border_Width: 1, Border_Color: outline }
  }
}
```

## How it reaches the view

Each rule names `Widget: PeriodSelector` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `PeriodSelector` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `8` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Border_Width` | `1` | The width of its border, in pixels. |
| always | `Border_Color` | `outline` | The colour of its border: a colour or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: PeriodSelector
    Style { Corner_Radius: tertiary }
  }
}
```
