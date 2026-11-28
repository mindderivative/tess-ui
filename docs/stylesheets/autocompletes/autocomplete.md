# Autocomplete_Stylesheet.tdl

The look of Autocomplete (ux spec Autocomplete): the popup is a `surface_container` surface at level 2 with 4 pixel corners and 4 pixels (8 at the default density) above and below the rows, as Menu; a row has the padding of a menu row, a selected row is `secondary_container` with a check at its end, the active row `surface_container_highest`.

The look of [`Autocomplete`](../../components/autocompletes.md) (in [Autocomplete](../../components/autocompletes.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Autocomplete
Tesserae: "0.6"
---
# The look of Autocomplete (ux spec Autocomplete): the popup is a `surface_container` surface at level 2 with 4 pixel corners and 4 pixels (8 at the default density) above and below the rows, as Menu; a row has
# the padding of a menu row, a selected row is `secondary_container` with a check at its end, the active row `surface_container_highest`.
Styles {
  Rule { Widget: Autocomplete, Part: surface, Style { Background: surface_container, Corner_Radius: 4, Elevation: 2, Padding: <| {'left': 0, 'right': 0, 'top': 8 if density in ('', 'default') else 4, 'bottom': 8 if density in ('', 'default') else 4} |> } }
  Rule { Widget: Autocomplete, Part: row, Style { Corner_Radius: 0 } }
}
```

## How it reaches the view

Each rule names `Widget: Autocomplete` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `surface` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Corner_Radius` | `4` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Elevation` | `2` | A shadow level, 0 to 5. |
| always | `Padding` | `<\| {'left': 0, 'right': 0, 'top': 8 if density in ('', 'default') else 4, 'bottom': 8 if density in ('', 'def…` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `row` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `0` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Autocomplete
    Part: surface
    Style { Background: tertiary }
  }
}
```
