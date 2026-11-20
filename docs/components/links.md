# Links

*Navigation*

## In Material Design 3

A link takes the user somewhere else, or opens a related page. It is text, in the primary colour.

## In Tesserae

`Link` is text that takes focus, and that Enter or a click activates. It is `primary`, in `body_medium` unless you name another type role.

The `text` also names the link for a screen reader. Its `Href` is opened in the OS's browser or mail program when the link is activated: `http`, `https`, `mailto` and `tel` only,
anything else is refused. Opening it sets a bound `Visited`, and `State: visited` in a rule colours it (`secondary` by default). A disabled link is dimmed, out of the Tab order,
and does nothing. It is underlined while the pointer is over it or keyboard focus is on it (`Underline: hover`, the default), always, or never. `Handlers { On_Click: ... }` runs
as well as the `Href` opens; a link with no `Href` just runs its handler.

The type properties of `Text` (`Typography_Role`, `Wrap`, `Overflow`, `Max_Lines`, ...) apply. A link inside a longer text is a `link` run of a `Text` (`Runs`, [Rich Text & Links](../guide/rich-text.md)); a `Link` is for a whole line.

## How it is built

### `Link`

Text that can be activated.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Text` | `str` |  | The link's text, which names it for a screen reader. |
| `Typography_Role` | `str` |  | A type role of the theme, such as body_large or title_large. |
| `Font_Family` | `str` |  |  |
| `Font_Size` | `float` |  |  |
| `Font_Weight` | `any` |  |  |
| `Wrap` | `word` or `none` | `word` | 'word' breaks a long line; 'none' never does. |
| `Overflow` | `clip` or `ellipsis` | `clip` |  |
| `Text_Align` | `start` or `center` or `end` | `start` |  |
| `Max_Lines` | `int` |  | The most lines shown, from 1; a longer text is cut (with `Overflow: ellipsis`, an ellipsis ends the last line). |
| `Letter_Spacing` | `float` |  | Extra space between letters, in pixels (tracking). |
| `Href` | `str` |  | A web or mail link (http, https, mailto, tel) opened in the OS's browser or mail program when it is activated. |
| `Visited` | `bool` |  | Whether it has been followed; opening its href sets it, and a rule can show it with `State: visited`. Two-way. |
| `Disabled` | `bool` |  | Dimmed, and not activated. |
| `Underline` | `hover` or `always` or `never` | `hover` | When the text is underlined: while the pointer is over it or it has the keyboard focus, always, or never. |

Its `Style` also takes `Foreground`.

Its look is in [`Link_Stylesheet.tdl`](../stylesheets/links/link.md).

## Using it

```tdl
Container {
  Name: help
  Style { Flex_Direction: vertical, Gap: 8, Width: 300, Height: 100 }
  Children {
    Link {
      Text: "Read the docs"
      Href: "https://example.com/docs"
      Visited: <| docs_seen |>
    }
    Link {
      Text: "Not now"
      Disabled: true
    }
    Link {
      Text: "Sign in"
      Handlers {
        On_Click: sign_in
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import link

help_link = link(app.window, "Read the docs", 160, on_click=viewmodel.open_docs)
```

## See also

- [Rich Text](../guide/rich-text.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
