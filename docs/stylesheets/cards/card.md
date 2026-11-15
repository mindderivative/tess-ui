# Card_Stylesheet.tdl

The look of Card (Material 3): 12 pixel corners, 16 pixels of padding around the text. Elevated is surface_container_low at level 1 (2 when an actionable one is hovered), filled is surface_container_highest, outlined is surface with a 1 pixel outline_variant border. A selected outlined card has an outline border; a selected filled or elevated one is secondary_container.

The look of [`Card`](../../components/cards.md) (in [Cards](../../components/cards.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: Card
Tesserae: "0.6"
---
# The look of Card (Material 3): 12 pixel corners, 16 pixels of padding around the text. Elevated is surface_container_low at level 1 (2 when an
# actionable one is hovered), filled is surface_container_highest, outlined is surface with a 1 pixel outline_variant border. A selected outlined card has
# an outline border; a selected filled or elevated one is secondary_container.
Styles {
  Rule {
    Widget: Card
    Style {
      Corner_Radius: 12
      Transition { Elevation: 200, Background: 150 }
    }
  }
  Rule {
    Widget: Card
    Variant: elevated
    Style { Background: <| 'secondary_container' if selected else 'surface_container_low' |>, Elevation: 1 }
  }
  Rule { Widget: Card, Variant: elevated, State: hovered, Style { Elevation: <| 2 if actionable else 1 |> } }
  Rule { Widget: Card, Variant: filled, Style { Background: <| 'secondary_container' if selected else 'surface_container_highest' |> } }
  Rule {
    Widget: Card
    Variant: outlined
    Style {
      Background: surface
      Border_Width: 1
      Border_Color: <| 'outline' if selected else 'outline_variant' |>
    }
  }
  Rule { Widget: Card, Part: body, Style { Padding: 16, Gap: 4 } }
  Rule { Widget: Card, Part: headline, Style { Foreground: on_surface } }
  Rule { Widget: Card, Part: subhead, Style { Foreground: on_surface_variant } }
  Rule { Widget: Card, Part: text, Style { Foreground: on_surface_variant } }
}
```

## How it reaches the view

Each rule names `Widget: Card` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `Card` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Corner_Radius` | `12` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| always | `Transition` | `{ Elevation: 200, Background: 150 }` | Which style changes ease to their new value: a duration in milliseconds, or `{Duration, easing, bounce}`. `all` covers every one that can. A node is where it says when first drawn; only a change eases. |
| `Variant: elevated` | `Background` | `<\| 'secondary_container' if selected else 'surface_container_low' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: elevated` | `Elevation` | `1` | A shadow level, 0 to 5. |
| `Variant: elevated`, state `hovered` | `Elevation` | `<\| 2 if actionable else 1 \|>` | A shadow level, 0 to 5. |
| `Variant: filled` | `Background` | `<\| 'secondary_container' if selected else 'surface_container_highest' \|>` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: outlined` | `Background` | `surface` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: outlined` | `Border_Width` | `1` | The width of its border, in pixels. |
| `Variant: outlined` | `Border_Color` | `<\| 'outline' if selected else 'outline_variant' \|>` | The colour of its border: a colour or a gradient. |

### `body` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Padding` | `16` | Space inside it: one number, or `{Left, Right, Top, Bottom}`. |
| always | `Gap` | `4` | Space between its children. |

### `headline` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `subhead` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: Card
    Variant: elevated
    Style { Background: tertiary }
  }
}
```
