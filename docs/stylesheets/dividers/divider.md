# Divider_Stylesheet.tdl

The look of Divider (Material 3): a line in outline_variant that fills the length it is in (in a container that does not set `Align_Content`). The insets are margins at the ends it keeps clear.

The look of [`Divider`](../../components/dividers.md) (in [Dividers](../../components/dividers.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Divider
Tesserae: "0.6"
---
# The look of Divider (Material 3): a line in outline_variant that fills the length it is in (in a container that does not set `align_content`). The insets are margins at the ends it keeps clear.
Styles {
  Rule {
    Widget: Divider
    Style {
      Background: outline_variant
      Width: <| thickness if orientation == 'vertical' else 'auto' |>
      Height: <| thickness if orientation == 'horizontal' else 'auto' |>
    }
  }

  Rule {
    Widget: Divider
    Variant: inset
    Style {
      Margin: <| {'left': 16} if orientation == 'horizontal' else {'top': 16} |>
    }
  }

  Rule {
    Widget: Divider
    Variant: middle
    Style {
      Margin: <| {'left': 16, 'right': 16} if orientation == 'horizontal' else {'top': 16, 'bottom': 16} |>
    }
  }
}
```

## How it reaches the view

Each rule names `Widget: Divider` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Divider` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `outline_variant` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| always | `Width` | `<\| thickness if orientation == 'vertical' else 'auto' \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| thickness if orientation == 'horizontal' else 'auto' \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Variant: inset` | `Margin` | `<\| {'left': 16} if orientation == 'horizontal' else {'top': 16} \|>` | Space outside it: one number, or `{Left, Right, Top, Bottom}`. |
| `Variant: middle` | `Margin` | `<\| {'left': 16, 'right': 16} if orientation == 'horizontal' else {'top': 16, 'bottom': 16} \|>` | Space outside it: one number, or `{Left, Right, Top, Bottom}`. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Divider
    Style { Background: tertiary }
  }
}
```
