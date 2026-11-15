# TextField_Stylesheet.tdl

The look of TextField (Material 3). A state here is the state of the whole field: `focused` is true while anything inside it has the focus. A later rule wins a tie, so error comes after focused and hovered: a field in error keeps the error colour while it is used.

The look of [`TextField`](../../components/text-fields.md) (in [Text fields](../../components/text-fields.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: TextField
Tesserae: "0.6"
---
# The look of TextField (Material 3). A state here is the state of the whole field: `focused` is true while anything inside it has the focus.
# A later rule wins a tie, so error comes after focused and hovered: a field in error keeps the error colour while it is used.
Styles {
  Rule {
    Widget: TextField
    Style { Width: 280, Background: transparent }  # a fill, even a clear one, is what lets the pointer find the field
  }
  Rule {
    Widget: TextField
    State: disabled
    Style { Opacity: 0.38 }
  }

  # the box
  Rule {
    Widget: TextField
    Part: box
    Variant: filled
    Style { Background: surface_container_highest, Corner_Radius { Top: 4 } }  # square below: the line under it is its bottom edge
  }
  Rule {
    Widget: TextField
    Part: box
    Variant: outlined
    Style { Border_Width: 1, Border_Color: outline, Corner_Radius: 4 }
  }
  Rule {
    Widget: TextField
    Part: box
    Variant: outlined
    State: hovered
    Style { Border_Color: on_surface }
  }
  Rule {
    Widget: TextField
    Part: box
    Variant: outlined
    State: focused
    Style { Border_Width: 2, Border_Color: primary }
  }
  Rule {
    Widget: TextField
    Part: box
    Variant: outlined
    State: error
    Style { Border_Color: error }
  }

  # the line under a filled field
  Rule {
    Widget: TextField
    Part: indicator
    Style { Height: 1, Background: on_surface_variant }
  }
  Rule {
    Widget: TextField
    Part: indicator
    State: hovered
    Style { Background: on_surface }
  }
  Rule {
    Widget: TextField
    Part: indicator
    State: focused
    Style { Height: 2, Background: primary }
  }
  Rule {
    Widget: TextField
    Part: indicator
    State: error
    Style { Background: error }
  }

  # the label
  Rule {
    Widget: TextField
    Part: label
    Style { Foreground: on_surface_variant }
  }
  Rule {
    Widget: TextField
    Part: label
    State: focused
    Style { Foreground: primary }
  }
  Rule {
    Widget: TextField
    Part: label
    State: error
    Style { Foreground: error }
  }

  # the typing, and the text around it
  Rule {
    Widget: TextField
    Part: input
    Style { Foreground: on_surface, Background: transparent }  # the box around the typing is the field's own
  }
  Rule {
    Widget: TextField
    Part: prefix
    Style { Foreground: on_surface_variant }
  }
  Rule {
    Widget: TextField
    Part: suffix
    Style { Foreground: on_surface_variant }
  }
  Rule {
    Widget: TextField
    Part: supporting
    Style { Foreground: on_surface_variant }
  }
  Rule {
    Widget: TextField
    Part: supporting
    State: error
    Style { Foreground: error }
  }
  Rule {
    Widget: TextField
    Part: counter
    Style { Foreground: on_surface_variant }
  }

  # the icons
  Rule {
    Widget: TextField
    Part: leading_icon
    Style { Foreground: on_surface_variant }
  }
  Rule {
    Widget: TextField
    Part: trailing_icon
    Style { Foreground: on_surface_variant }
  }
  Rule {
    Widget: TextField
    Part: reveal_button
    Style { Background: transparent }
  }
  Rule {
    Widget: TextField
    Part: reveal_icon
    Style { Foreground: on_surface_variant }
  }
  Rule {
    Widget: TextField
    Part: error_icon
    Style { Foreground: error }
  }
}
```

## How it reaches the view

Each rule names `Widget: TextField` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `TextField` itself

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Width` | `280` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Background` | `transparent` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| state `disabled` | `Opacity` | `0.38` | From 0 (clear) to 1 (opaque). |

### `box` (Container)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| `Variant: filled` | `Background` | `surface_container_highest` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| `Variant: filled` | `Corner_Radius` | `{ Top: 4 }` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Variant: outlined` | `Border_Width` | `1` | The width of its border, in pixels. |
| `Variant: outlined` | `Border_Color` | `outline` | The colour of its border: a colour or a gradient. |
| `Variant: outlined` | `Corner_Radius` | `4` | Pixels, or a shape token (`none` to `extra_large`, or `full` for a pill or circle). Per corner: a list `[top_left, top_right, bottom_right, bottom_left]`, or a mapping of corners and edges (`Top`, `Right`, `Bottom`, `Left`) with the rest square. |
| `Variant: outlined`, state `hovered` | `Border_Color` | `on_surface` | The colour of its border: a colour or a gradient. |
| `Variant: outlined`, state `focused` | `Border_Width` | `2` | The width of its border, in pixels. |
| `Variant: outlined`, state `focused` | `Border_Color` | `primary` | The colour of its border: a colour or a gradient. |
| `Variant: outlined`, state `error` | `Border_Color` | `error` | The colour of its border: a colour or a gradient. |

### `indicator` (Rect)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Height` | `1` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| always | `Background` | `on_surface_variant` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| state `hovered` | `Background` | `on_surface` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| state `focused` | `Height` | `2` | Pixels, `auto` (its content's size, or stretched), `fit-content`, a percentage of the parent such as `50%`, or a sum such as `calc(100% - 16)` or `100% - 16` (a space each side of `+` and `-`; `16px` may be written inside a sum). |
| state `focused` | `Background` | `primary` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |
| state `error` | `Background` | `error` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |

### `label` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| state `focused` | `Foreground` | `primary` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| state `error` | `Foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `input` (TextInput)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| always | `Background` | `transparent` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |

### `prefix` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `suffix` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `supporting` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |
| state `error` | `Foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `counter` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `leading_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `trailing_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `reveal_button` (Rect)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Background` | `transparent` | Its fill: a theme role such as `surface`, `#RRGGBB`, any CSS colour, or a gradient such as `linear-gradient(90deg, primary, tertiary)`. |

### `reveal_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `error_icon` (Icon)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `error` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: TextField
    Style { Background: tertiary }
  }
}
```
