# IconButton_Stylesheet.tdl

The look of IconButton (Material 3, with the Expressive sizes, widths and shapes). The icon is 20, 24, 24, 32 or 40 pixels for the five sizes. A toggle that is on takes the selected colours and the other shape; a press squares a round button off.

The look of [`IconButton`](../../components/icon-buttons.md) (in [Icon buttons](../../components/icon-buttons.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: IconButton
Tesserae: "0.6"
---
# The look of IconButton (Material 3, with the Expressive sizes, widths and shapes). The icon is 20, 24, 24, 32 or 40 pixels for the five sizes. A toggle
# that is on takes the selected colours and the other shape; a press squares a round button off.
Styles {
  Rule {
    Widget: IconButton
    Style {
      Height: <| 40 if app_density() == '' else density_token(app_density(), 'icon_button_container') |>
      Width: <| 40 if app_density() == '' else density_token(app_density(), 'icon_button_container') |>
      Transition { Corner_Radius: 200, Background: 150 }
    }
  }
  Rule { Widget: IconButton, Size: xs, Style { Height: 32 } }
  Rule { Widget: IconButton, Size: s, Style { Height: <| 40 if app_density() == '' else density_token(app_density(), 'icon_button_container') |> } }
  Rule { Widget: IconButton, Size: m, Style { Height: 56 } }
  Rule { Widget: IconButton, Size: l, Style { Height: 96 } }
  Rule { Widget: IconButton, Size: xl, Style { Height: 136 } }
  Rule {
    Widget: IconButton
    Style {
      Width: <| {'xs': {'narrow': 28, 'default': 32, 'wide': 40}, 's': {'narrow': 32, 'default': (40 if app_density() == '' else density_token(app_density(), 'icon_button_container')), 'wide': 52}, 'm': {'narrow': 48, 'default': 56, 'wide': 72}, 'l': {'narrow': 64, 'default': 96, 'wide': 128}, 'xl': {'narrow': 104, 'default': 136, 'wide': 184}}[size][width_kind] |>
    }
  }
  # shapes
  Rule { Widget: IconButton, Shape: round, Style { Corner_Radius: full } }
  Rule { Widget: IconButton, Shape: square, Style { Corner_Radius: <| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] |> } }
  Rule { Widget: IconButton, Shape: round, State: selected, Style { Corner_Radius: <| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] |> } }
  Rule { Widget: IconButton, Shape: square, State: selected, Style { Corner_Radius: full } }
  Rule { Widget: IconButton, Shape: round, State: pressed, Style { Corner_Radius: <| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] |> } }
  # variants
  Rule { Widget: IconButton, Variant: standard, Style { Background: transparent } }
  Rule { Widget: IconButton, Variant: filled, Style { Background: <| 'primary' if (not toggle or selected) else 'surface_container_highest' |> } }
  Rule { Widget: IconButton, Variant: tonal, Style { Background: <| 'secondary_container' if (not toggle or not selected) else 'secondary' |> } }
  Rule {
    Widget: IconButton
    Variant: outlined
    Style {
      Background: <| 'transparent' if (not toggle or not selected) else 'inverse_surface' |>
      Border_Width: <| 1 if (not toggle or not selected) else 0 |>
      Border_Color: outline
    }
  }
  # the icon
  Rule { Widget: IconButton, Part: icon, Style { Transition { Icon: 200 } } }
  Rule {
    Widget: IconButton
    Part: icon
    Style { Width: <| {'xs': 20, 's': (24 if app_density() == '' else density_token(app_density(), 'icon_button_icon')), 'm': 24, 'l': 32, 'xl': 40}[size] |>, Height: <| {'xs': 20, 's': (24 if app_density() == '' else density_token(app_density(), 'icon_button_icon')), 'm': 24, 'l': 32, 'xl': 40}[size] |> }
  }
  Rule {
    Widget: IconButton
    Variant: standard
    Part: icon
    Style { Foreground: <| tint if tint != '' else ('primary' if (toggle and selected) else 'on_surface_variant') |> }
  }
  Rule {
    Widget: IconButton
    Variant: filled
    Part: icon
    Style { Foreground: <| 'on_primary' if (not toggle or selected) else 'on_surface_variant' |> }
  }
  Rule {
    Widget: IconButton
    Variant: tonal
    Part: icon
    Style { Foreground: <| 'on_secondary_container' if (not toggle or not selected) else 'on_secondary' |> }
  }
  Rule {
    Widget: IconButton
    Variant: outlined
    Part: icon
    Style { Foreground: <| 'on_surface_variant' if (not toggle or not selected) else 'inverse_on_surface' |> }
  }
}
```

## How it reaches the view

Each rule names `Widget: IconButton` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `IconButton` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Height` | `<\| 40 if app_density() == '' else density_token(app_density(), 'icon_button_container') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Width` | `<\| 40 if app_density() == '' else density_token(app_density(), 'icon_button_container') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Transition` | `{ Corner_Radius: 200, Background: 150 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |
| `Size: xs` | `Height` | `32` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: s` | `Height` | `<\| 40 if app_density() == '' else density_token(app_density(), 'icon_button_container') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: m` | `Height` | `56` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: l` | `Height` | `96` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: xl` | `Height` | `136` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Width` | `<\| {'xs': {'narrow': 28, 'default': 32, 'wide': 40}, 's': {'narrow': 32, 'default': (40 if app_density() == '…` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Shape: round` | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Shape: square` | `Corner_Radius` | `<\| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Shape: round`, state `selected` | `Corner_Radius` | `<\| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Shape: square`, state `selected` | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Shape: round`, state `pressed` | `Corner_Radius` | `<\| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Variant: standard` | `Background` | `transparent` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: filled` | `Background` | `<\| 'primary' if (not toggle or selected) else 'surface_container_highest' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: tonal` | `Background` | `<\| 'secondary_container' if (not toggle or not selected) else 'secondary' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: outlined` | `Background` | `<\| 'transparent' if (not toggle or not selected) else 'inverse_surface' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: outlined` | `Border_Width` | `<\| 1 if (not toggle or not selected) else 0 \|>` | The width of its border, in pixels. |
| `Variant: outlined` | `Border_Color` | `outline` | The colour of its border: a colour or a gradient. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Transition` | `{ Icon: 200 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |
| always | `Width` | `<\| {'xs': 20, 's': (24 if app_density() == '' else density_token(app_density(), 'icon_button_icon')), 'm': 24…` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| {'xs': 20, 's': (24 if app_density() == '' else density_token(app_density(), 'icon_button_icon')), 'm': 24…` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Variant: standard` | `Foreground` | `<\| tint if tint != '' else ('primary' if (toggle and selected) else 'on_surface_variant') \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: filled` | `Foreground` | `<\| 'on_primary' if (not toggle or selected) else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: tonal` | `Foreground` | `<\| 'on_secondary_container' if (not toggle or not selected) else 'on_secondary' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: outlined` | `Foreground` | `<\| 'on_surface_variant' if (not toggle or not selected) else 'inverse_on_surface' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: IconButton
    Variant: standard
    Style { Background: tertiary }
  }
}
```
