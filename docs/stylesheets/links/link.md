# Link_Stylesheet.tdl

The look of Link: primary text, a different colour once it has been followed, dimmed while disabled. The underline is drawn by the renderer (while the pointer is over it or it has the keyboard focus, unless `Underline:` says otherwise).

The look of [`Link`](../../components/links.md) (in [Links](../../components/links.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Link
Tesserae: "0.6"
---
# The look of Link: primary text, a different colour once it has been followed, dimmed while disabled. The underline is drawn by the renderer
# (while the pointer is over it or it has the keyboard focus, unless `underline:` says otherwise).
Styles {
  Rule {
    Widget: Link
    Style { Foreground: primary }
  }
  Rule {
    Widget: Link
    State: visited
    Style { Foreground: secondary }
  }
  Rule {
    Widget: Link
    State: disabled
    Style { Foreground: on_surface, Opacity: 0.38 }
  }
}
```

## How it reaches the view

Each rule names `Widget: Link` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Link` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `primary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| state `visited` | `Foreground` | `secondary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| state `disabled` | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| state `disabled` | `Opacity` | `0.38` | From 0 (clear) to 1 (opaque). |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Link
    Style { Foreground: tertiary }
  }
}
```
