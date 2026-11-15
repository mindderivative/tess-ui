# Text

*Content*

## In Material Design 3

Text is set in Material Design 3's type scale: 15 styles in five groups (display, headline, title, body and
label), each large, medium or small, with a font, size, weight, line height and tracking.

## In Tesserae

`Text`. Name a `Typography_Role` (or a `Font_Family`) and Tesserae fills in the rest; a theme's `Typography` can change
what a role means. A `Text` needs one of them and a `Style.Foreground`: without either the view does not build, and the error says which.

`Text` can be an expression, and follows the Signals it reads. `Font_Family`, `Font_Size` and `Font_Weight` replace what the role gives. `Wrap` is `word` or `none`,
`Runs` gives pieces of one text their own style and links ([Rich Text & Links](../guide/rich-text.md)). `Overflow` is `clip` or `ellipsis`, `Text_Align` is `start`, `center` or `end`, and `Max_Lines` cuts a longer text to that many lines (with `Overflow: ellipsis` the last
one ends in an ellipsis). `Letter_Spacing` adds space between letters, in pixels. `Selectable: true` lets the text be selected and copied, and `Heading: 1` to `6` makes it a heading of that level for a screen reader.

The colour is `Style.Foreground` (required). Tracking: the roles are drawn with none, as the engine draws them; Material 3's per-role values are
`tokens.MD3_TRACKING`, and a theme turns them on with `Typography: tokens.MD3_TRACKING_TYPOGRAPHY` (or one role at a time:
`Typography { Body_Large { Tracking: 0.5 } }`). A node's own `Letter_Spacing` wins.

## How it is built

### `Text`

A run of text.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Text` | `str` |  | The text shown. |
| `Typography_Role` | `str` |  | A type role of the theme, such as body_large or title_large. |
| `Font_Family` | `str` |  |  |
| `Font_Size` | `float` |  |  |
| `Font_Weight` | `any` |  |  |
| `Wrap` | `word` or `none` | `word` | 'word' breaks a long line; 'none' never does. |
| `Overflow` | `clip` or `ellipsis` | `clip` |  |
| `Text_Align` | `start` or `center` or `end` | `start` |  |
| `Max_Lines` | `int` |  | The most lines shown, from 1; a longer text is cut (with `Overflow: ellipsis`, an ellipsis ends the last line). |
| `Letter_Spacing` | `float` |  | Extra space between letters, in pixels (tracking). |
| `Selectable` | `bool` |  | The text can be selected and copied. |
| `Runs` | `list` |  | Pieces of one text in different styles, instead of `Text`: each a string, or `{Text, color, weight, italic, Underline, strikethrough, Font_Size, Font_Family, link}`. A piece with a `link` is the theme's `primary` and underlined, and `On_Link` runs with `event.href` when it is pressed. |
| `Heading` | `1` or `2` or `3` or `4` or `5` or `6` |  | Makes it a heading of this level for a screen reader. |

Its `Style` also takes `Foreground`.

## Using it

```tdl
Container {
  Name: article
  Style { Flex_Direction: vertical, Gap: 8, Width: 360, Height: 200 }
  Children {
    Text {
      Text: Notes
      Typography_Role: headline_medium
      Heading: 1
      Style { Foreground: on_surface }
    }
    Text {
      Text: <| summary |>
      Typography_Role: body_large
      Max_Lines: 3
      Overflow: ellipsis
      Selectable: true
      Style { Foreground: on_surface_variant }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import text

heading = text(app.window, "Notes", typography_role="headline_medium")
```

## See also

- [Index](../themes/index.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
