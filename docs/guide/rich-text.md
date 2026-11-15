# Rich Text & Links

A `Text` is text in one style: one `Typography_Role`, one `Foreground`, one weight. For text that is partly bold, struck through, coloured
or a link, give it `Runs`: the pieces of one text, each with its own style. A whole line that opens a page is a [`Link`](#links).

```tdl
Text {
  Name: offer
  Typography_Role: body_large
  Style { Foreground: on_surface, Width: 360 }
  Runs {
    Item { Text: "Sale: " }
    Item { Text: <| was |>, Strikethrough: true, Color: on_surface_variant }
    Item { Text: " $9", Weight: 700, Color: error }
    Item { Text: " ends Friday. " }
    Item { Text: "Read the terms", Link: terms }
  }
  Handlers { On_Link { Call { Action: open_terms, Args: [<| event.href |>] } } }
}
```

A run is an `Item` with its `Text` and any of the keys below. (Runs of plain text only can be written as a list of strings, `Runs: ["Sale: ", "now"]`; a list cannot mix strings and `Item` blocks.)

| Key | What it does |
| --- | --- |
| `Color` | A theme role or a CSS colour. |
| `Weight` | A font weight, 1 to 1000 (`700` is bold). |
| `Italic`, `Underline`, `Strikethrough` | `true` for the style. |
| `Font_Size`, `Font_Family` | A size in pixels, a family. |
| `Link` | A name for the link; the run is the theme's `primary` and underlined unless it says otherwise. |

`Runs` is the text, so a `Text` has `Runs` or `Text`, not both. The pieces are joined into one text that wraps as one (give it a `Width`),
and the text of a run may be an expression (`Text: <| was |>`), so the pieces follow your data. A mistake is refused with the node named: an empty
list, a run with no `Text`, an unknown key, a `Weight` that is not a number. Only a `Text` has `Runs` (a `Link` is one piece, and what is typed in
a `TextInput` is one style).

## Pieces that need their own layout

When the pieces must be separate nodes (each with its own `Handlers`, padding or alignment), lay `Text` and `Link` nodes out in a row:

```tdl
Container {
  Style { Flex_Direction: horizontal, Align_Content: left, Width: 360, Padding: 16, Background: surface }
  Children {
    Text {
      Name: was
      Text: "$12"
      Typography_Role: body_large
      Style { Foreground: on_surface_variant }
    }
    Text {
      Name: now
      Text: " $9"
      Typography_Role: body_large
      Font_Weight: 700
      Style { Foreground: error }
    }
    Link {
      Name: terms
      Text: Read the terms
      Handlers { On_Click: open_terms }
    }
  }
}
```

Each piece takes its own `Typography_Role`, `Font_Size`, `Font_Family` and `Font_Weight`, and its own `Foreground`. The row keeps
its pieces on one line; for a paragraph that wraps, use one `Text` with `Runs` and a `Width`.

## Links

A `Link` is text that takes focus and that a click or Enter activates. It is the theme's `primary`, underlined
while the pointer is over it or it has the keyboard focus.

| Property | What it does |
| --- | --- |
| `Text` | What it says; it also names the link for a screen reader. |
| `Href` | A link the OS opens in the browser or mail program when it is activated: `http`, `https`, `mailto` and `tel` only. Anything else is not opened: activating it logs a warning. |
| `Visited` | Whether it has been followed. Opening its `Href` sets a bound one, and a stylesheet rule with `State: visited` can colour it. |
| `Underline` | `hover` (the default), `always` or `never`. |
| `Disabled` | Dimmed, out of the Tab order, and does nothing. |

`Handlers { On_Click: ... }` runs as well as the `Href` opens. A link that goes somewhere inside the app has no `Href`, only a
handler; the handler decides what it means:

```tdl
Link {
  Text: Settings
  Handlers { On_Click: open_settings }
}
```

To open an address from any other node, a handler calls `open_url('https://example.com')`
([Opening a link](view-language.md#opening-a-link)). The pointer is a hand over a link.

`On_Link` is the event of a link run inside one `Text`, with the run's `Link` in `event.href`: `On_Link { Call { Action: open_terms, Args: [<| event.href |>] } }`. A handler named
without brackets is called with no event, so write the call to get `event.href`.

## Sizing

A `Text` with no `Width` is measured to fit its text on one line. Give it a `Width` and it wraps, and is as tall as
its lines. `Max_Lines` and `Overflow: ellipsis` end a long text with an ellipsis; see
[Text in a box](layout.md#text-in-a-box).

## Selectable text

`Selectable: true` on a `Text` lets the user select it with the pointer, and copy it with Ctrl+C. Double-click
selects a word, triple-click a line, and a drag from one selectable text into another selects across them. Only a
`Text` can be selectable.

```tdl
Text {
  Name: help
  Text: "Press and drag to select this."
  Typography_Role: body_medium
  Selectable: true
  Style { Foreground: on_surface, Width: 240 }
}
```

To copy from a handler instead, `copy(text)` puts text on the clipboard ([The clipboard](view-language.md#the-clipboard)).
