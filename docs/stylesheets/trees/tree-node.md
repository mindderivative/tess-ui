# TreeNode_Stylesheet.tdl

The look of TreeNode (Material 3 list terms): 16 pixels in plus 24 for each level on the left, 16 on the right, 8 between the parts; a selected row is secondary_container.

The look of [`TreeNode`](../../components/trees.md) (in [Trees](../../components/trees.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: TreeNode
Tesserae: "0.6"
---
# The look of TreeNode (Material 3 list terms): 16 pixels in plus 24 for each level on the left, 16 on the right, 8 between the parts; a selected row is
# secondary_container.
Styles {
  Rule {
    Widget: TreeNode
    Style {
      Padding: <| {'left': (16 + 24 * level) if density == '' else density_token(density, 'row_padding_x') + density_token(density, 'tree_indent') * level, 'right': 16 if density == '' else density_token(density, 'row_padding_x'), 'top': 0, 'bottom': 0} |>
      Gap: <| 8 if density == '' else density_token(density, 'icon_label_gap') |>
      Background: <| 'secondary_container' if selected else 'transparent' |>
      Transition { Background: 150 }
    }
  }
  Rule { Widget: TreeNode, Part: label, Style { Flex: expand_horizontal, Min_Width: 0 } }  # a long label ends in an ellipsis instead of being cut (AC-TRN-07)
  Rule { Widget: TreeNode, Part: chevron, Style { Width: <| 24 if density == '' else density_token(density, 'chevron_box') |>, Height: <| 24 if density == '' else density_token(density, 'chevron_box') |>, Foreground: on_surface_variant } }
  Rule {
    Widget: TreeNode
    Part: icon
    Style { Width: 24, Height: 24, Foreground: <| 'on_secondary_container' if selected else 'on_surface_variant' |> }
  }
  Rule { Widget: TreeNode, Part: label, Style { Foreground: <| 'on_secondary_container' if selected else 'on_surface' |> } }
}
```

## How it reaches the view

Each rule names `Widget: TreeNode` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `TreeNode` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `<\| {'left': (16 + 24 * level) if density == '' else density_token(density, 'row_padding_x') + density_token(d…` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `<\| 8 if density == '' else density_token(density, 'icon_label_gap') \|>` | Space between its children. |
| always | `Background` | `<\| 'secondary_container' if selected else 'transparent' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Transition` | `{ Background: 150 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Flex` | `expand_horizontal` | How it takes room in its parent: `none` (the default) is as big as its content and never squeezed, `expand_horizontal` and `expand_vertical` take the room left over in that direction, `fill` both. |
| always | `Min_Width` | `0` | The least width it can take. |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `chevron` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `<\| 24 if density == '' else density_token(density, 'chevron_box') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| 24 if density == '' else density_token(density, 'chevron_box') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `24` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Foreground` | `<\| 'on_secondary_container' if selected else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: TreeNode
    Style { Background: tertiary }
  }
}
```
