# Snackbars

*Communication*

## In Material Design 3

A snackbar briefly tells the user about a process that has happened or will happen, at the bottom of the
window, and may offer one action. It goes away by itself.

## In Tesserae

Two views Tesserae ships: `Snackbar` (one message) and `SnackbarHost` (several, one after another).

A `Snackbar` shows while `Open` is true and writes `false` back when it closes. It closes itself after `Duration` milliseconds (4000 by default; 0 keeps it until it is closed),
and the pointer over it holds the time off. The `Action` is a text button after the message: pressing it runs `On_Action` and closes the snackbar. `Closable` adds a close
button, and `On_Close` is called when it closes however it closes. It is 344 to 560 pixels wide (`Width`), 16 from the window's edge (`Margin`), at the start or `Centered`.

It is `inverse_surface` at level 3 with 4 pixel corners, 48 pixels tall (68 for two lines), over the content, not modal, and takes no focus; a screen reader hears it
as a polite alert. A `SnackbarHost` takes `Messages` (`{Message}` and optionally `{Action, Value, id, Duration}`), shows the first, drops it when it closes
and shows the next; add to the list from anywhere that can write it; `Chosen` is the `Value` of the action pressed. An `Overlay` has a `Timeout`
and an `on_dismiss` handler, which is how this is made. Not built: swipe to dismiss, and lifting above a FAB or a bottom bar.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Snackbar { ... }`. A file of the same name in your project replaces it.

### `Snackbar`

The Material 3 snackbar: a short message near the bottom of the window, over the content, that goes by itself. It is not modal, takes no focus and blocks nothing. `Open` shows it (and is written false when it closes); it closes `Duration` milliseconds after it opens (4000 by default; 0 keeps it up) unless the pointer is over it, when the action or the close button is pressed, and calls `On_Close` then. An `Action` is a text button after the message: pressing it runs `On_Action`, then closes. Announced politely. `SnackbarHost` shows several one after another.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Open` | `bool` | `false` | Whether it is showing; it writes false when it closes. Two-way: give it a bare reference and the view writes it back. |
| `Message` | `str` |  | What to say. |
| `Action` | `str` |  | The label of a text button after the message. |
| `On_Action` | `handler` |  | What the action button does. |
| `On_Close` | `handler` |  | Called when it closes, however it closes. |
| `Closable` | `bool` | `false` | A close button after the message. |
| `Duration` | `float` | `4000` | Milliseconds before it closes itself; 0 keeps it until it is closed. |
| `Margin` | `float` | `16` | The space between it and the window's edge. |
| `Centered` | `bool` | `false` | In the middle of the window instead of at the start. |
| `Width` | `float` | `344` | How wide it is, from 344 to 560 pixels; a message longer than fits goes onto a second line. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `bar` (Container), `message` (Text), `action` (Container), `action_text` (Text), `close` (Container), `close_icon` (Icon).

Its look is in [`Snackbar_Stylesheet.tdl`](../stylesheets/snackbars/snackbar.md).

### `SnackbarHost`

Several snackbars, one after another (Material 3 shows one at a time). `Messages` is a list of {message} and optionally {action, value, id, duration}; the first shows, and when it closes it is taken off the list and the next one shows. Add to the list (`messages = messages + [{'message': 'Saved'}]`) from anywhere that can write it. The `Value` of an action that was pressed goes to `Chosen`. It takes no room where it is written.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Messages` | `list` | `[]` | The waiting messages, each {message} and optionally {action, value, id, duration}. The first is showing. Two-way: give it a bare reference and the view writes it back. |
| `Chosen` | `any` |  | The value of the action last pressed. Two-way: give it a bare reference and the view writes it back. |
| `Closable` | `bool` | `false` | A close button on each. |
| `Centered` | `bool` | `false` | In the middle of the window instead of at the start. |
| `Margin` | `float` | `16` | The space between a snackbar and the window's edge. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `current` (Snackbar).

## Using it

```tdl
Container {
  Name: notes
  Style { Width: 480, Height: 320 }
  Children {
    SnackbarHost {
      Messages: <| toasts |>
      Chosen: <| undo |>
    }
    Snackbar {
      Open: <| saved |>
      Message: "Note saved"
      Action: Undo
      On_Action: undo_save
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import snackbar

bar = snackbar(app.window, "Saved", 280, action_label="Undo", on_action=viewmodel.undo)
bar.open()
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# Snackbar_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: Snackbar
    Part: message
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
