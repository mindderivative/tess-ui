# MenuBar_Stylesheet.tdl

The look of MenuBar (ux spec Menu Bar): the bar and its titles are as high as a control of the density (40, 32, 28), a title has the field padding at each side and the extra-small corner, the bar is `surface` and a title `on_surface`; the bar has no elevation.

The look of [`MenuBar`](../../components/menu-bars.md) (in [Menu bars](../../components/menu-bars.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: MenuBar
Tesserae: "0.6"
---
# The look of MenuBar (ux spec Menu Bar): the bar and its titles are as high as a control of the density (40, 32, 28), a title has the field padding at each side and the extra-small corner, the
# bar is `surface` and a title `on_surface`; the bar has no elevation.
Styles {
  Rule { Widget: MenuBar, Style { Background: surface, Padding: <| {'left': 4, 'right': 4, 'top': 0, 'bottom': 0} |> } }
  Rule {
    Widget: MenuBar
    Part: title
    Style {
      Height: <| 40 if density == '' else density_token(density, 'control_height') |>
      Padding: <| {'left': 12 if density == '' else density_token(density, 'field_padding_x'), 'right': 12 if density == '' else density_token(density, 'field_padding_x'), 'top': 0, 'bottom': 0} |>
      Align_Content: center
      Corner_Radius: 4
    }
  }
  Rule { Widget: MenuBar, Part: label, Style { Foreground: on_surface } }
}
```

## How it reaches the view

Each rule names `Widget: MenuBar` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `MenuBar` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `surface` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Padding` | `<\| {'left': 4, 'right': 4, 'top': 0, 'bottom': 0} \|>` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |

### `title` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Height` | `<\| 40 if density == '' else density_token(density, 'control_height') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Padding` | `<\| {'left': 12 if density == '' else density_token(density, 'field_padding_x'), 'right': 12 if density == '' …` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Align_Content` | `center` | Where its children sit: `top_left`, `Top`, `top_right`, `Left`, `center`, `Right`, `bottom_left`, `Bottom` or `bottom_right`. Not set, they fill the space across the layout. |
| always | `Corner_Radius` | `4` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: MenuBar
    Style { Background: tertiary }
  }
}
```
