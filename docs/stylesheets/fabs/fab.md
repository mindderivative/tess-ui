# Fab_Stylesheet.tdl

The look of Fab (Material 3): a container at elevation level 3 that lifts to 4 when hovered and settles back when pressed. The container colour is the variant's, the icon and label its "on" colour. The extended form (with a label that shows) is 56 tall with 16 pixels of padding before the icon and 20 after the label.

The look of [`Fab`](../../components/fabs.md) (in [Floating action buttons](../../components/fabs.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Fab
Tesserae: "0.6"
---
# The look of Fab (Material 3): a container at elevation level 3 that lifts to 4 when hovered and settles back when pressed. The container colour is the
# variant's, the icon and label its "on" colour. The extended form (with a label that shows) is 56 tall with 16 pixels of padding before the icon and 20
# after the label.
Styles {
  Rule {
    Widget: Fab
    Style {
      Elevation: 3
      Transition { Elevation: 200, Corner_Radius: 200 }
      Height: 56
      Width: auto
      Corner_Radius: 16
    }
  }
  Rule { Widget: Fab, Size: small, Style { Height: 40, Corner_Radius: 12 } }
  Rule { Widget: Fab, Size: medium, Style { Height: 56, Corner_Radius: 16 } }
  Rule { Widget: Fab, Size: large, Style { Height: 96, Corner_Radius: 28 } }
  # the shape: a square one for an icon alone, otherwise as wide as it needs
  Rule {
    Widget: Fab
    Style {
      Width: <| {'small': 40, 'medium': 56, 'large': 96}[size] if (label == '' or collapsed) else 'auto' |>
      Height: <| 56 if (label != '' and not collapsed) else {'small': 40, 'medium': 56, 'large': 96}[size] |>
      Padding: <| {'left': 16, 'right': 20, 'top': 0, 'bottom': 0} if (label != '' and not collapsed) else 0 |>
      Gap: 8
    }
  }
  Rule { Widget: Fab, State: hovered, Style { Elevation: 4 } }
  Rule { Widget: Fab, State: pressed, Style { Elevation: 3 } }
  # colours
  Rule { Widget: Fab, Variant: primary, Style { Background: primary_container } }
  Rule { Widget: Fab, Variant: secondary, Style { Background: secondary_container } }
  Rule { Widget: Fab, Variant: tertiary, Style { Background: tertiary_container } }
  Rule { Widget: Fab, Variant: surface, Style { Background: surface_container_high } }
  Rule { Widget: Fab, Variant: primary, Part: icon, Style { Foreground: on_primary_container } }
  Rule { Widget: Fab, Variant: secondary, Part: icon, Style { Foreground: on_secondary_container } }
  Rule { Widget: Fab, Variant: tertiary, Part: icon, Style { Foreground: on_tertiary_container } }
  Rule { Widget: Fab, Variant: surface, Part: icon, Style { Foreground: primary } }
  Rule { Widget: Fab, Variant: primary, Part: label, Style { Foreground: on_primary_container } }
  Rule { Widget: Fab, Variant: secondary, Part: label, Style { Foreground: on_secondary_container } }
  Rule { Widget: Fab, Variant: tertiary, Part: label, Style { Foreground: on_tertiary_container } }
  Rule { Widget: Fab, Variant: surface, Part: label, Style { Foreground: primary } }
  # icon sizes
  Rule { Widget: Fab, Part: icon, Style { Width: <| 36 if size == 'large' else 24 |>, Height: <| 36 if size == 'large' else 24 |> } }
}
```

## How it reaches the view

Each rule names `Widget: Fab` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Fab` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Elevation` | `3` | A shadow level, 0 to 5. |
| always | `Transition` | `{ Elevation: 200, Corner_Radius: 200 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |
| always | `Height` | `56` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Width` | `auto` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Corner_Radius` | `16` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Size: small` | `Height` | `40` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: small` | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Size: medium` | `Height` | `56` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: medium` | `Corner_Radius` | `16` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Size: large` | `Height` | `96` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: large` | `Corner_Radius` | `28` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Width` | `<\| {'small': 40, 'medium': 56, 'large': 96}[size] if (label == '' or collapsed) else 'auto' \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| 56 if (label != '' and not collapsed) else {'small': 40, 'medium': 56, 'large': 96}[size] \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Padding` | `<\| {'left': 16, 'right': 20, 'top': 0, 'bottom': 0} if (label != '' and not collapsed) else 0 \|>` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `8` | Space between its children. |
| state `hovered` | `Elevation` | `4` | A shadow level, 0 to 5. |
| state `pressed` | `Elevation` | `3` | A shadow level, 0 to 5. |
| `Variant: primary` | `Background` | `primary_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: secondary` | `Background` | `secondary_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: tertiary` | `Background` | `tertiary_container` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: surface` | `Background` | `surface_container_high` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| `Variant: primary` | `Foreground` | `on_primary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: secondary` | `Foreground` | `on_secondary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: tertiary` | `Foreground` | `on_tertiary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: surface` | `Foreground` | `primary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `<\| 36 if size == 'large' else 24 \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| 36 if size == 'large' else 24 \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| `Variant: primary` | `Foreground` | `on_primary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: secondary` | `Foreground` | `on_secondary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: tertiary` | `Foreground` | `on_tertiary_container` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: surface` | `Foreground` | `primary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Fab
    Variant: primary
    Style { Background: tertiary }
  }
}
```
