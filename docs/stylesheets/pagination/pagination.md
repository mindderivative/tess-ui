# Pagination_Stylesheet.tdl

The look of Pagination: the ellipsis and the "3 of 12" in on_surface_variant and on_surface.

The look of [`Pagination`](../../components/pagination.md) (in [Pagination](../../components/pagination.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Pagination
Tesserae: "0.6"
---
# The look of Pagination: the ellipsis and the "3 of 12" in on_surface_variant and on_surface.
Styles {
  Rule { Widget: Pagination, Part: gap, Style { Foreground: on_surface_variant } }
  Rule { Widget: Pagination, Part: summary, Style { Foreground: on_surface } }
}
```

## How it reaches the view

Each rule names `Widget: Pagination` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `gap` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `summary` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Pagination
    Part: gap
    Style { Foreground: tertiary }
  }
}
```
