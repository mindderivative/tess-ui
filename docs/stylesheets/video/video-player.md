# VideoPlayer_Stylesheet.tdl

The look of VideoPlayer: the picture sits on a dark stage; the time labels are on_surface_variant; the subtitle band is white on a darkened scrim.

The look of [`VideoPlayer`](../../components/video.md) (in [Video](../../components/video.md)). [How component stylesheets work](../index.md).

## The stylesheet

```tdl
---
TDL: 0.2
Name: VideoPlayer
Tesserae: "0.6"
---
# The look of VideoPlayer: the picture sits on a dark stage; the time labels are on_surface_variant; the subtitle band is white on a darkened scrim.
Styles {
  Rule { Widget: VideoPlayer, Part: elapsed, Style { Foreground: on_surface_variant } }
  Rule { Widget: VideoPlayer, Part: total, Style { Foreground: on_surface_variant } }
  Rule { Widget: VideoPlayer, Part: caption_text, Style { Foreground: "#ffffff" } }
}
```

## How it reaches the view

Each rule names `Widget: VideoPlayer` and may add the properties the view declares (a `Variant`, a `Size`, a `Shape`), `Classes`, a node `Name`, a `Part` (one of the view's named nodes) and a `State` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). A rule's values may be expressions over the view's parameters. The most specific rule wins: a `Name`, then the number of properties matched (all the `Classes` count as one more), then a `State`, then the widget alone; a later rule wins a tie. These rules are the lowest layer: your app's stylesheet goes over them, and a node's own `Style` beats every rule for the fields it sets.

## The rules

### `elapsed` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `total` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `on_surface_variant` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

### `caption_text` (Text)

| When | Field | Value | What it does |
| --- | --- | --- | --- |
| always | `Foreground` | `"#ffffff"` | Its text or glyph colour: a theme role, `#RRGGBB`, any CSS colour, or a gradient. |

## Changing it

Write a rule of your own; it goes over this file's, field by field:

```tdl
Styles {
  Rule {
    Widget: VideoPlayer
    Part: elapsed
    Style { Foreground: tertiary }
  }
}
```
