# Toolbar_Stylesheet.tdl

The look of Toolbar (Material 3): a docked one is a 64 pixel surface_container strip with 16 pixels of padding; a floating one is a pill at elevation level 3 with 8 pixels of padding. Vibrant uses primary_container. The buttons stand 4 pixels apart.

The look of [`Toolbar`](../../components/toolbars.md) (in [Toolbars](../../components/toolbars.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Toolbar
Tesserae: "0.6"
---
# The look of Toolbar (Material 3): a docked one is a 64 pixel surface_container strip with 16 pixels of padding; a floating one is a pill at elevation level 3 with 8 pixels of padding.
# Vibrant uses primary_container. The buttons stand 4 pixels apart.
Styles {
  Rule {
    Widget: Toolbar
    Style {
      Background: <| 'primary_container' if vibrant else 'surface_container' |>
    }
  }
  Rule { Widget: Toolbar, Variant: docked, Style { Padding { Left: 16, Right: 16, Top: 0, Bottom: 0 }, Gap: 8 } }
  Rule { Widget: Toolbar, Variant: floating, Style { Padding: 8, Gap: 8, Corner_Radius: full, Elevation: 3 } }
  Rule { Widget: Toolbar, Part: group, Style { Gap: 4 } }
}
```

## How it reaches the view

Each rule names `Widget: Toolbar` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Toolbar` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `<\| 'primary_container' if vibrant else 'surface_container' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: docked` | `Padding` | `{ Left: 16, Right: 16, Top: 0, Bottom: 0 }` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| `Variant: docked` | `Gap` | `8` | Space between its children. |
| `Variant: floating` | `Padding` | `8` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| `Variant: floating` | `Gap` | `8` | Space between its children. |
| `Variant: floating` | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Variant: floating` | `Elevation` | `3` | A shadow level, 0 to 5. |

### `group` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Gap` | `4` | Space between its children. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Toolbar
    Style { Background: tertiary }
  }
}
```
