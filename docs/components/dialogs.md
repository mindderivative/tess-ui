# Dialogs

*Containment*

## In Material Design 3

A dialog interrupts to ask for a decision or give needed information. It has a headline, supporting text and
up to two actions, on a raised surface over a scrim, and blocks what is behind it.

## In Tesserae

`Dialog` is a view Tesserae ships (`Dialog_View.tdl`): a modal [`Overlay`](../guide/view-language.md#overlays) holding a raised panel (28 pixel
corners, 24 of padding) with an optional icon, a headline, supporting text, your own content and text-button actions.

`Open` is two-way: Escape and a press on the scrim write `false` back, unless `Dismissible` is off, when only an action closes it. Each of the `Actions` is `{Label, Value}`
and optionally `{Variant}` (a text button unless it says otherwise); pressing one closes the dialog and writes its `Value` to `Result`, which stays empty when the dialog was
dismissed. The panel is `Width` wide, held between 280 and 560 pixels (312 by default), and the content scrolls beyond `Max_Height` (480). `Fullscreen` is the full-screen
form: the panel fills the window on `surface`, with a close button, the headline and the actions in a 56 pixel bar along the top, and the content scrolling under it.

Children are the content, after the supporting text. When the content scrolls, a line shows above the actions. Actions stack when they do not fit
one row. A screen reader hears a `dialog` named by the headline (tess_re has no `alertdialog` role). In the full-screen form the close button writes
`false` to `Open` with no result, the actions sit in the bar instead of under the content (MD3 has one confirming action there), and a line shows under
the bar once the content has scrolled; use it where the window is `Compact` (`Fullscreen: "<| app.width_class == 'compact' |>"`). Not built: focusing a
form dialog's first field.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Dialog { ... }`. A file of the same name in your project replaces it.

### `Dialog`

The Material 3 dialog, basic or (`Fullscreen: true`) full-screen: a modal panel over a scrim, with an optional icon, a headline, supporting text or your own content, and up to a few text button actions. `Open` is two-way (Escape and a press on the scrim close it, unless `Dismissible: false`); pressing an action closes it and writes the action's value to `Result`, so the caller can tell which was chosen. A screen reader hears a `dialog` named by the headline (tess_re has no `alertdialog` role, so an alert is a `dialog` with `Dismissible: false`). The content scrolls when it is taller than the dialog, and a line shows above the actions then. Children are the content: they follow the supporting text. Actions stack when they do not fit the width on one row.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Open` | `bool` | `false` | Whether it is showing. Two-way: give it a bare reference and the view writes it back. |
| `Headline` | `str` |  | The title. |
| `Text` | `str` |  | Supporting text. |
| `Icon` | `str` |  | An icon above the headline. |
| `Actions` | `list` | `[]` | Text buttons, each {label, value} and optionally {variant}. Pressing one closes the dialog and sets `Result` to its value. |
| `Result` | `any` |  | The value of the action last pressed; empty when it was dismissed. Two-way: give it a bare reference and the view writes it back. |
| `Dismissible` | `bool` | `true` | Escape and a press on the scrim close it. Off, it is an alert dialog: only an action closes it. |
| `Width` | `float` | `312` | From 280 to 560 pixels. |
| `Max_Height` | `float` | `480` | The content scrolls beyond this. |
| `Fullscreen` | `bool` | `false` | The full-screen form: it fills the window, with a close button, the headline and the actions along the top, and the content scrolling under them. |

Children go in the default slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `panel` (Container), `bar` (Container), `close` (IconButton), `bar_title` (Text), `bar_action` (Button), `bar_line` (Divider), `icon` (Icon), `headline` (Text), `content` (ScrollView), `body` (Text), `line` (Divider), `actions` (Container), `action` (Button).

Its look is in [`Dialog_Stylesheet.tdl`](../stylesheets/dialogs/dialog.md).

## Using it

```tdl
Container {
  Name: files
  Style { Flex_Direction: vertical, Width: 480, Height: 360 }
  Children {
    Dialog {
      Open: <| confirming |>
      Result: <| choice |>
      Headline: "Discard draft?"
      Text: "This cannot be undone."
      Icon: home
      Actions {
        Item { Label: Cancel, Value: cancel }
        Item { Label: Discard, Value: discard }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import dialog

confirm = dialog(app.window, "Discard changes?", "Your edits will be lost.", 320, 200,
                 actions=[("Cancel", None), ("Discard", viewmodel.discard)])
confirm.open()
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Dialog_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Dialog
    Part: panel
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
