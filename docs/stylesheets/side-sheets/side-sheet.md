# SideSheet_Stylesheet.tdl

The look of the standard side sheet: a `surface` column.

The look of [`SideSheet`](../../components/side-sheets.md) (in [Side sheets](../../components/side-sheets.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: SideSheet
Tesserae: "0.6"
---
# The look of the standard side sheet: a `surface` column.
Styles {
  Rule {
    Widget: SideSheet
    Style {
      Background: surface
    }
  }
}
```

## How it reaches the view

Each rule names `Widget: SideSheet` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `SideSheet` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: SideSheet
    Style { Background: tertiary }
  }
}
```
