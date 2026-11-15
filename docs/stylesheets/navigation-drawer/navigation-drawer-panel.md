# NavigationDrawerPanel_Stylesheet.tdl

The look of the inside of a drawer: 12 pixels in from the edge, section headings in on_surface_variant, a little space above the first destination.

The look of [`NavigationDrawerPanel`](../../components/navigation-drawer.md) (in [Navigation drawer](../../components/navigation-drawer.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: NavigationDrawerPanel
Tesserae: "0.6"
---
# The look of the inside of a drawer: 12 pixels in from the edge, section headings in on_surface_variant, a little space above the first destination.
Styles {
  Rule {
    Widget: NavigationDrawerPanel
    Style {
      Padding { Left: 12, Right: 12, Top: 12, Bottom: 12 }
    }
  }
  Rule {
    Widget: NavigationDrawerPanel
    Part: heading
    Style { Foreground: on_surface_variant, Padding { Left: 16, Right: 16, Top: 18, Bottom: 18 } }
  }
}
```

## How it reaches the view

Each rule names `Widget: NavigationDrawerPanel` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `NavigationDrawerPanel` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `{ Left: 12, Right: 12, Top: 12, Bottom: 12 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `heading` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Padding` | `{ Left: 16, Right: 16, Top: 18, Bottom: 18 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: NavigationDrawerPanel
    Part: heading
    Style { Foreground: tertiary }
  }
}
```
