# Button_Stylesheet.tdl

The look of Button (Material 3, with the Expressive sizes). Sizes set the height, the padding (by size: 12 for `xs`, 24 for `s` and `m` (16 on the side with an icon on `s`), 48 for `l`, 64 for `xl`) and the gap; variants set the colours; the shape is a pill or a rounded square, and a toggle that is on, or a press, takes the other. A state layer and a ripple come from the node's interaction; a filled, tonal or elevated button lifts when hovered.

The look of [`Button`](../../components/buttons.md) (in [Buttons](../../components/buttons.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Button
Tesserae: "0.6"
---
# The look of Button (Material 3, with the Expressive sizes). Sizes set the height, the padding (by size: 12 for `xs`, 24 for `s` and `m` (16 on the side with an icon on `s`), 48 for `l`, 64 for `xl`) and the gap; variants set the colours; the shape is a pill or a rounded square, and a toggle that is on, or a press, takes the other.
# A state layer and a ripple come from the node's interaction; a filled, tonal or elevated button lifts when hovered.
Styles {
  Rule {
    Widget: Button
    Style {
      Height: <| 40 if density == '' else density_token(density, 'control_height') |>
      Transition { Corner_Radius: 200, Elevation: 200, Background: 150 }
    }
  }
  # sizes
  Rule { Widget: Button, Size: xs, Style { Height: <| (32 if density == '' else min(32, density_token(density, 'icon_button_container'))) |>, Gap: 4 } }
  Rule { Widget: Button, Size: s, Style { Height: <| 40 if density == '' else density_token(density, 'control_height') |>, Gap: 8 } }
  Rule { Widget: Button, Size: m, Style { Height: 56, Gap: 8 } }
  Rule { Widget: Button, Size: l, Style { Height: 96, Gap: 12 } }
  Rule { Widget: Button, Size: xl, Style { Height: 136, Gap: 16 } }
  Rule {
    Widget: Button
    Style {
      Padding: <| {'left': (({'xs': 12, 's': 16, 'm': 24, 'l': 48, 'xl': 64}[size]) if (icon != '' or loading) else ({'xs': 12, 's': 24, 'm': 24, 'l': 48, 'xl': 64}[size])) if variant != 'text' else 12, 'right': (({'xs': 12, 's': 16, 'm': 24, 'l': 48, 'xl': 64}[size]) if trailing_icon != '' else ({'xs': 12, 's': 24, 'm': 24, 'l': 48, 'xl': 64}[size])) if variant != 'text' else 12, 'top': 0, 'bottom': 0} |>
    }
  }
  # shapes: a pill, or a rounded square; a toggle that is on (and a press) takes the other
  Rule {
    Widget: Button
    Shape: round
    Style { Corner_Radius: full }
  }
  Rule {
    Widget: Button
    Shape: square
    Style { Corner_Radius: <| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] |> }
  }
  Rule {
    Widget: Button
    Shape: round
    State: selected
    Style { Corner_Radius: <| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] |> }
  }
  Rule {
    Widget: Button
    Shape: square
    State: selected
    Style { Corner_Radius: full }
  }
  Rule {
    Widget: Button
    Shape: round
    State: pressed
    Style { Corner_Radius: <| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] |> }
  }
  # variants
  Rule {
    Widget: Button
    Variant: filled
    Style { Background: <| 'primary' if (not toggle or selected) else 'surface_container_highest' |> }
  }
  Rule {
    Widget: Button
    Variant: tonal
    Style { Background: <| 'secondary_container' if (not toggle or not selected) else 'secondary' |> }
  }
  Rule {
    Widget: Button
    Variant: elevated
    Style { Background: <| 'surface_container_low' if (not toggle or not selected) else 'primary' |>, Elevation: 1 }
  }
  Rule {
    Widget: Button
    Variant: outlined
    Style {
      Background: <| 'transparent' if (not toggle or not selected) else 'inverse_surface' |>
      Border_Width: <| 1 if (not toggle or not selected) else 0 |>
      Border_Color: outline
    }
  }
  Rule {
    Widget: Button
    Variant: text
    Style { Background: transparent }
  }
  # lifting
  Rule { Widget: Button, Variant: filled, State: hovered, Style { Elevation: 1 } }
  Rule { Widget: Button, Variant: tonal, State: hovered, Style { Elevation: 1 } }
  Rule { Widget: Button, Variant: elevated, State: hovered, Style { Elevation: 2 } }
  Rule { Widget: Button, Variant: elevated, State: pressed, Style { Elevation: 1 } }
  # content colours
  Rule {
    Widget: Button
    Variant: filled
    Part: label
    Style { Foreground: <| 'on_primary' if (not toggle or selected) else 'on_surface_variant' |> }
  }
  Rule {
    Widget: Button
    Variant: tonal
    Part: label
    Style { Foreground: <| 'on_secondary_container' if (not toggle or not selected) else 'on_secondary' |> }
  }
  Rule {
    Widget: Button
    Variant: elevated
    Part: label
    Style { Foreground: <| 'primary' if (not toggle or not selected) else 'on_primary' |> }
  }
  Rule {
    Widget: Button
    Variant: outlined
    Part: label
    Style { Foreground: <| 'primary' if not toggle else ('inverse_on_surface' if selected else 'on_surface_variant') |> }
  }
  Rule {
    Widget: Button
    Variant: text
    Part: label
    Style { Foreground: primary }
  }
  Rule { Widget: Button, Variant: filled, Part: icon, Style { Foreground: <| 'on_primary' if (not toggle or selected) else 'on_surface_variant' |> } }
  Rule {
    Widget: Button
    Variant: tonal
    Part: icon
    Style { Foreground: <| 'on_secondary_container' if (not toggle or not selected) else 'on_secondary' |> }
  }
  Rule { Widget: Button, Variant: elevated, Part: icon, Style { Foreground: <| 'primary' if (not toggle or not selected) else 'on_primary' |> } }
  Rule {
    Widget: Button
    Variant: outlined
    Part: icon
    Style { Foreground: <| 'primary' if not toggle else ('inverse_on_surface' if selected else 'on_surface_variant') |> }
  }
  Rule { Widget: Button, Variant: text, Part: icon, Style { Foreground: primary } }
  Rule {
    Widget: Button
    Variant: filled
    Part: trailing
    Style { Foreground: <| 'on_primary' if (not toggle or selected) else 'on_surface_variant' |> }
  }
  Rule {
    Widget: Button
    Variant: tonal
    Part: trailing
    Style { Foreground: <| 'on_secondary_container' if (not toggle or not selected) else 'on_secondary' |> }
  }
  Rule { Widget: Button, Variant: elevated, Part: trailing, Style { Foreground: <| 'primary' if (not toggle or not selected) else 'on_primary' |> } }
  Rule {
    Widget: Button
    Variant: outlined
    Part: trailing
    Style { Foreground: <| 'primary' if not toggle else ('inverse_on_surface' if selected else 'on_surface_variant') |> }
  }
  Rule { Widget: Button, Variant: text, Part: trailing, Style { Foreground: primary } }
  # icon sizes
  Rule {
    Widget: Button
    Part: icon
    Style { Width: <| {'xs': 20, 's': 18, 'm': 24, 'l': 32, 'xl': 40}[size] |>, Height: <| {'xs': 20, 's': 18, 'm': 24, 'l': 32, 'xl': 40}[size] |> }
  }
  Rule {
    Widget: Button
    Part: trailing
    Style { Width: <| {'xs': 20, 's': 18, 'm': 24, 'l': 32, 'xl': 40}[size] |>, Height: <| {'xs': 20, 's': 18, 'm': 24, 'l': 32, 'xl': 40}[size] |> }
  }
}
```

## How it reaches the view

Each rule names `Widget: Button` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Button` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Height` | `<\| 40 if density == '' else density_token(density, 'control_height') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Transition` | `{ Corner_Radius: 200, Elevation: 200, Background: 150 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |
| `Size: xs` | `Height` | `<\| (32 if density == '' else min(32, density_token(density, 'icon_button_container'))) \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: xs` | `Gap` | `4` | Space between its children. |
| `Size: s` | `Height` | `<\| 40 if density == '' else density_token(density, 'control_height') \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: s` | `Gap` | `8` | Space between its children. |
| `Size: m` | `Height` | `56` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: m` | `Gap` | `8` | Space between its children. |
| `Size: l` | `Height` | `96` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: l` | `Gap` | `12` | Space between its children. |
| `Size: xl` | `Height` | `136` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| `Size: xl` | `Gap` | `16` | Space between its children. |
| always | `Padding` | `<\| {'left': (({'xs': 12, 's': 16, 'm': 24, 'l': 48, 'xl': 64}[size]) if (icon != '' or loading) else ({'xs': …` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| `Shape: round` | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Shape: square` | `Corner_Radius` | `<\| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Shape: round`, state `selected` | `Corner_Radius` | `<\| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Shape: square`, state `selected` | `Corner_Radius` | `full` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Shape: round`, state `pressed` | `Corner_Radius` | `<\| {'xs': 12, 's': 12, 'm': 16, 'l': 28, 'xl': 28}[size] \|>` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Variant: filled` | `Background` | `<\| 'primary' if (not toggle or selected) else 'surface_container_highest' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: tonal` | `Background` | `<\| 'secondary_container' if (not toggle or not selected) else 'secondary' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: elevated` | `Background` | `<\| 'surface_container_low' if (not toggle or not selected) else 'primary' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: elevated` | `Elevation` | `1` | A shadow level, 0 to 5. |
| `Variant: outlined` | `Background` | `<\| 'transparent' if (not toggle or not selected) else 'inverse_surface' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: outlined` | `Border_Width` | `<\| 1 if (not toggle or not selected) else 0 \|>` | The width of its border, in pixels. |
| `Variant: outlined` | `Border_Color` | `outline` | The colour of its border: a colour or a gradient. |
| `Variant: text` | `Background` | `transparent` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: filled`, state `hovered` | `Elevation` | `1` | A shadow level, 0 to 5. |
| `Variant: tonal`, state `hovered` | `Elevation` | `1` | A shadow level, 0 to 5. |
| `Variant: elevated`, state `hovered` | `Elevation` | `2` | A shadow level, 0 to 5. |
| `Variant: elevated`, state `pressed` | `Elevation` | `1` | A shadow level, 0 to 5. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| `Variant: filled` | `Foreground` | `<\| 'on_primary' if (not toggle or selected) else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: tonal` | `Foreground` | `<\| 'on_secondary_container' if (not toggle or not selected) else 'on_secondary' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: elevated` | `Foreground` | `<\| 'primary' if (not toggle or not selected) else 'on_primary' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: outlined` | `Foreground` | `<\| 'primary' if not toggle else ('inverse_on_surface' if selected else 'on_surface_variant') \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: text` | `Foreground` | `primary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| `Variant: filled` | `Foreground` | `<\| 'on_primary' if (not toggle or selected) else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: tonal` | `Foreground` | `<\| 'on_secondary_container' if (not toggle or not selected) else 'on_secondary' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: elevated` | `Foreground` | `<\| 'primary' if (not toggle or not selected) else 'on_primary' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: outlined` | `Foreground` | `<\| 'primary' if not toggle else ('inverse_on_surface' if selected else 'on_surface_variant') \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: text` | `Foreground` | `primary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `<\| {'xs': 20, 's': 18, 'm': 24, 'l': 32, 'xl': 40}[size] \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| {'xs': 20, 's': 18, 'm': 24, 'l': 32, 'xl': 40}[size] \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

### `trailing` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| `Variant: filled` | `Foreground` | `<\| 'on_primary' if (not toggle or selected) else 'on_surface_variant' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: tonal` | `Foreground` | `<\| 'on_secondary_container' if (not toggle or not selected) else 'on_secondary' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: elevated` | `Foreground` | `<\| 'primary' if (not toggle or not selected) else 'on_primary' \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: outlined` | `Foreground` | `<\| 'primary' if not toggle else ('inverse_on_surface' if selected else 'on_surface_variant') \|>` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| `Variant: text` | `Foreground` | `primary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Width` | `<\| {'xs': 20, 's': 18, 'm': 24, 'l': 32, 'xl': 40}[size] \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Height` | `<\| {'xs': 20, 's': 18, 'm': 24, 'l': 32, 'xl': 40}[size] \|>` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Button
    Variant: filled
    Style { Background: tertiary }
  }
}
```
