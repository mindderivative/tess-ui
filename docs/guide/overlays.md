# Overlays

An overlay is a layer over the window: a dialog, a menu, a snackbar, a side sheet. There are two ways to make one.
In a view, an `Overlay` shows its children while its `Open` is true. From Python, `tess_ui.overlays` has MD3's
dialogs, menus, snackbars, tooltips, popovers, side sheets and modal navigation drawers, ready made, built from Tesserae's
fragments and shown with `tess_re`'s layers.

## An Overlay in a view

An `Overlay` takes no room where it is written. Its children are drawn in a layer over the window while `Open` is
true. Bind `Open` to a Signal (or a `State` name) and the layer follows it, and the user's Escape or outside press writes
`false` back:

```tdl
Container {
  Name: page
  State { Confirm: false }
  Style { Flex_Direction: vertical, Width: 400, Height: 300, Padding: 20 }
  Children {
    Button {
      Name: delete
      Label: Delete
      Handlers { On_Click { Set { Target: confirm, Value: <| True |> } } }
    }
    Overlay {
      Open: <| confirm |>
      Modal: true
      Children {
        Container {
          Name: dialog
          Style { Flex_Direction: vertical, Gap: 16, Padding: 24, Width: 312, Background: surface_container_high, Corner_Radius: 28 }
          A11y { Role: dialog, Label: "Delete this file" }
          Children {
            Text { Text: "Delete this file?", Typography_Role: headline_small, Style { Foreground: on_surface } }
            Container {
              Style { Flex_Direction: horizontal, Gap: 8, Align_Content: right }
              Children {
                Button {
                  Name: cancel
                  Label: Cancel
                  Variant: text
                  Handlers { On_Click { Set { Target: confirm, Value: <| False |> } } }
                }
                Button {
                  Name: confirm_it
                  Label: Delete
                  Variant: text
                  Handlers {
                    On_Click {
                      Set { Target: confirm, Value: <| False |> }
                      Call { Action: delete_file }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

| Property | What it does |
| --- | --- |
| `Open` | Whether it is showing. Two-way. With an `Open` that is not a Signal, a layer the user closed stays closed until `Open` goes false. |
| `Anchor` | The `Name` of a node in this view to sit against, or `parent` for the node it is written inside. |
| `Placement` | `below` (the default), `above`, `start` or `end` of the anchor, or a corner: `top_start`, `top_end`, `bottom_start`, `bottom_end`, `center`. The sides flip or shift to fit; the corners do not, and a corner puts the middle of the overlay on that point of the anchor (use `Offset` to move it). |
| `Offset` | `[dx, dy]` in pixels from the placement. |
| `Flip` | `true` (the default) moves a side placement to the other side when it does not fit; `false` keeps it. |
| `Modal` | A scrim (the `scrim` colour at 32%) over the whole window, blocking input to what is under it and keeping Tab inside. It follows the window's size and centres its children unless the style places them (`Align_Content`). A press on the scrim closes a dismissible modal; a press on its content does not. |
| `Dismissible` | `true` (the default): Escape and a press outside close it. `false` turns both off. |
| `Focus_First` | When it opens, the focus moves to the first thing in it that can take it (a menu's first row). |
| `Timeout` | Closes it that many milliseconds after it opens, unless the pointer is over it. 0, the default, never. |
| `Handlers` | `On_Dismiss` runs when Escape, a press outside, its `Timeout` or `surface.dismiss` closes it; writing `false` to `Open` from code does not run it. |

Without an `Anchor` and not modal, the layer sits at its own `X` and `Y` in the window (the top left unless its style says).
Focus goes back to where it was when the layer closes. To close it from inside, write `false` to the Signal `Open` is bound
to, as the Cancel button does. The `Style` of the Overlay sizes and paints the layer; put the dialog itself in a child with
its own size and background.

A menu against a button, closed by the same Signal:

```tdl
Container {
  State { Menu_Open: false }
  Style { Flex_Direction: vertical, Padding: 20, Width: 300, Height: 240 }
  Children {
    Button {
      Name: trigger
      Label: Options
      Handlers { On_Click { Set { Target: menu_open, Value: <| not menu_open |> } } }
    }
    Overlay {
      Open: <| menu_open |>
      Anchor: trigger
      Placement: below
      Focus_First: true
      Style { Width: 160, Background: surface_container }
      Children {
        Container {
          Name: rename
          Style { Height: 40, Padding: 12, Align_Content: left }
          Handlers {
            On_Click {
              Set { Target: menu_open, Value: <| False |> }
              Call { Action: rename }
            }
          }
          Children {
            Text { Text: Rename, Typography_Role: label_large, Style { Foreground: on_surface } }
          }
        }
        Container {
          Name: remove
          Style { Height: 40, Padding: 12, Align_Content: left }
          Handlers {
            On_Click {
              Set { Target: menu_open, Value: <| False |> }
              Call { Action: remove }
            }
          }
          Children {
            Text { Text: Delete, Typography_Role: label_large, Style { Foreground: on_surface } }
          }
        }
      }
    }
  }
}
```

[The View Language](view-language.md#overlays) has the rest, and a `Tooltip` on any node is the lighter way to show a hint
([Tooltips](view-language.md#tooltips)).

## Overlays from Python

For a dialog, menu or snackbar that code opens, `tess_ui.overlays` makes them:

```python
from tess_ui.overlays import Dialog, Menu, Snackbar, Tooltip

confirm = Dialog(app.window, "Discard draft?", "It won't be saved.",
                 actions=[("Cancel", None), ("Discard", viewmodel.discard)])
confirm.open()                      # modal: focus moves into it
confirm.on_close(lambda: print("closed"))
```

Made on the app's window with no `theme=`, an overlay takes the app's
theme and follows it, light and dark included. Give `theme=` to pin
it to a theme instead.

Components such as dialogs, menus and snackbars have their own pages under
[Components](../components/index.md); the signatures are in the
[Python API](../api/python.md). This page covers how they open, close and behave.

Every overlay has `open()`, `close()`, `is_open`, `on_close(fn)` and
`set_theme(theme)`. When it closes, focus goes back to where it was.

## A dialog with a view of its own

`ViewDialog(window, "Settings_View.yaml", width=480, height=320)` is a `Dialog` whose content is a view file: its
file, or its name in a project, with its ViewModel if it has one (`arguments={"who": "Ada"}` goes to the constructor) and without one
if it hasn't. `dialog.content` is the view and `dialog.viewmodel` its ViewModel. A `TitleBar` with `Buttons: [dismiss]` at
the top of the view is a header with a close button, and a `surface.dismiss` handler on anything closes the dialog.

`ViewDialog` is for a view in the older syntax (`kind:`), read with the older loader, and given a TDL view it refuses it
with a message that says what to write instead. A dialog written in TDL is a modal `Overlay` in a view, as above: its content is the
view you call by name, `Open` is bound to a Signal, and a `surface.dismiss` handler closes it. A called view has no ViewModel of its own, so
the `arguments` that `ViewDialog` hands to a ViewModel's constructor are the Overlay's content's params, or names the view's ViewModel serves.

`surface.dismiss` closes the nearest overlay the widget is in. In a view that is the nearest `Overlay` up the tree, closed as a press outside it
would: the layer hides, a bound `Open` goes false, and `On_Dismiss` runs. A button in a view the Overlay calls dismisses it too, and in nested
Overlays it is the inner one. With no `Overlay` around, it closes the overlay made by `tess_ui.overlays` that the view is in, as its `close()`
does (`dismiss_surface(node)` is the same from Python), and does nothing if there is none. Writing `false` to `Open` still closes an Overlay.

## Which closes how

| Overlay | Where it opens | Outside press | Escape | Modal |
| --- | --- | --- | --- | --- |
| `Menu` | below its anchor (flipped above if it won't fit), or at a point | closes | closes | no |
| `Dialog` | centred over a scrim | -- | closes | yes |
| `ViewDialog` | centred over a scrim, showing a view | -- | closes | yes |
| `FileDialog` (a view) | centred over a scrim, a panel for choosing files and folders | closes | closes | yes |
| `SideSheet` | the window's end, over a scrim, sliding in | -- | closes | yes |
| `NavigationDrawer` | the window's start, over a scrim, sliding in | -- | closes | yes |
| `Snackbar` | 24 px in, 72 px from the bottom | no | no | no |
| `Tooltip` | below its anchor | closes | closes | no |
| `Popover` | below its anchor | closes | closes | no |
| `SearchView` | below its search bar | closes | closes | no |

A modal overlay's scrim (black at 32%) fills the window, even as the
window resizes while it's open, and edge sheets and snackbars keep to
their edge. A press
outside the panel lands on the scrim, and Escape is what closes it. A
modal overlay keeps Tab inside it.

## Each one

- **`Dialog(window, headline, text, *, width=312, height=200, actions=[(label, fn)])`:**
  MD3's basic dialog, with text-button actions on the right. An action
  calls its `fn` and closes the dialog.
- **`Menu(window, items, *, width=200)`:** `items` are `(label, fn)` pairs or
  `tess_ui.widgets.menu_item(...)` widgets. It opens with
  `open(anchor)`, `open_at(x, y)`, or on a right-click with
  `attach_context(node)`. Focus moves to the first item; the up and down
  arrows move between items; a click or Enter calls the item and closes
  the menu.
- **`Snackbar(window, text, *, action=None, on_action=None, closable=False, duration=4000, width=344)`:**
  it hides itself after `duration` ms, as MD3's does (`None` keeps it
  until closed). The action button calls `on_action` and closes it. It's
  announced politely.
- **`Tooltip(window, text)`:** `attach(anchor)` shows it 500 ms after the
  anchor is hovered, or at once when the anchor gets keyboard focus, and
  hides it when the pointer or focus leaves. It gives the anchor its text
  as a label, since screen readers can't reach a tooltip.
- **`Popover(window, supporting_text, *, subhead=None, width=312, actions=[(label, fn)])`:**
  MD3's rich tooltip, `tess_re`'s popover: a `surface_container` panel with
  an optional subhead, the text wrapped to the width, and optional text
  buttons. Unlike a plain tooltip it stays open until an outside press,
  Escape or an action closes it, and with actions, focus moves to the
  first. `open(anchor)` shows it below `anchor`; `attach(anchor)` opens
  and closes it on the anchor's click.
- **`SideSheet(window, *, width=360, label=None)`:** a modal side sheet. Put
  its content in `.panel`. A standard (non-modal) side sheet isn't an
  overlay: use `tess_ui.widgets.side_sheet(modal=False)`.
- **`NavigationDrawer(window, labels, icons, *, selected=None, width=360)`:** the modal
  navigation drawer. `.drawer` is the drawer widget (`.drawer.selected`,
  `.drawer.on_change`), and choosing an item closes it.
- **`SearchView(window, *, bar=None, width=360, max_height=336, results=None, max_results=8)`:**
  MD3's docked search view, the results under a `search_bar`. Given the
  `bar`, it opens below it when the field has focus or is typed in and
  there are results. The down arrow in the field moves into the rows, up
  from the first row goes back, and a click or Enter calls the row's
  `fn` and closes it. `set_results([(text, fn)])` replaces the rows, and
  `on_query(fn)` hears the bar's typing.

`tess_ui.widgets`' `dialog`, `snackbar`, `side_sheet(modal=True)`,
`menu`, `tooltip`, `popover` and `search_view` return these.

## A dialog for choosing files

A `FileDialog` is a view Tesserae ships: a modal `Overlay` for choosing a file to open, a folder and a name to save under, or a folder, inside the app and with
no window of the operating system. It is opened and closed like the `Dialog` above, by a Signal bound to `Open`:

```tdl
FileDialog {
  Open: <| choosing |>
  Mode: open                 # or save, or folder
  Start: "~/Documents"
  Filters {
    Item { Label: "TDL files", Patterns: ["*.tdl"] }
  }
  Value: <| plan |>          # the chosen path, written when OK is pressed
  On_Accept: load_plan
  On_Cancel: stay
}
```

From Python, `tess_ui.file_dialog.FileDialogRequest(self)` in a ViewModel makes the names a `FileDialog` call binds and opens it with `show(mode=..., on_accept=fn)`, which
`fn` gets the chosen paths as a list. [File dialog](../components/file-dialogs.md) has everything it does: the path bar, the types, the hidden names, the root that confines it,
the keyboard, and the file system layer a test swaps.

## Not yet covered

- Dialog and snackbar text is one line. Long supporting text doesn't
  wrap yet.
- Submenus: `menu_item(submenu=True)` draws the chevron, and opening a
  nested menu is up to you.
