# Side sheets

*Containment*

## In Material Design 3

A side sheet holds secondary content beside the main content. A **standard** one shares the window with it;
a **modal** one covers it over a scrim and must be dismissed.

## In Tesserae

Three views Tesserae ships: `SideSheet` (standard, inline), `SideSheetModal` (over a scrim) and `SideSheetPanel` (the inside they share).

`Open` is two-way: the close button writes `false`, and so do Escape and a press on the scrim of a modal sheet. The header has a `title_large` `Title`, a back button (`Back: true`)
that runs `On_Back`, and a close button (`Closable`, on by default). The sheet is `Width` wide, held between 256 and 400 pixels (360 by default). A modal sheet also takes `Side`
(`end`, the default, or `start`: the edge it comes from) and `Dismissible` (off, Escape and the scrim do not close it).

Children are the content, which scrolls (a line shows over the actions once it has); children with `Slot: actions` are the buttons, in a row at the bottom right.
A standard sheet is inline: it takes room from the content while `Open` and its width eases open and shut; put it first in its row for the start side and last for
the end. A modal sheet is `surface_container_low` at level 1 with 16 pixel corners on the open side, over the content. Not built: the detached sheet, and the modal
sheet sliding in from the edge.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `SideSheet { ... }`. A file of the same name in your project replaces it.

### `SideSheet`

The Material 3 standard side sheet: supplementary content beside the main content, inline, so it pushes the content and takes room only while it is `Open` (the width eases open and shut). Put it first in its row for the start side, last for the end. A header with a title, `Back` and a close button, content that scrolls (children), and actions at the bottom (children with `Slot: actions`). A standard sheet is a landmark, not a dialog: it takes no focus and traps none.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Open` | `bool` | `false` | Whether the sheet is open; the close button writes false. Two-way: give it a bare reference and the view writes it back. |
| `Title` | `str` |  | The sheet's title. |
| `Back` | `bool` | `false` | A back button before the title. |
| `On_Back` | `handler` |  | What the back button does. |
| `Closable` | `bool` | `true` | A close button. |
| `Width` | `float` | `360` | From 256 to 400 pixels. |

Children go in the default slot, the `actions` slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `panel` (SideSheetPanel).

Its look is in [`SideSheet_Stylesheet.tdl`](../stylesheets/side-sheets/side-sheet.md).

### `SideSheetModal`

The Material 3 modal side sheet: the same header, scrolling content and actions as the standard one, over a scrim and on top of the content. `Side` is the end (the default) or the start. Escape and a press on the scrim close it (they write false to `Open`) unless `Dismissible` is off; Tab stays inside it, and focus goes back to where it was. Children are the content; children with `Slot: actions` are the buttons.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Open` | `bool` | `false` | Whether the sheet is showing. Two-way: give it a bare reference and the view writes it back. |
| `Title` | `str` |  | The sheet's title. |
| `Back` | `bool` | `false` | A back button before the title. |
| `On_Back` | `handler` |  | What the back button does. |
| `Closable` | `bool` | `true` | A close button. |
| `Side` | `start` or `end` | `end` | Which edge of the window it comes from. |
| `Dismissible` | `bool` | `true` | Escape and a press on the scrim close it. |
| `Width` | `float` | `360` | From 256 to 400 pixels. |

Children go in the default slot, the `actions` slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `sheet` (Container), `panel` (SideSheetPanel).

Its look is in [`SideSheetModal_Stylesheet.tdl`](../stylesheets/side-sheets/side-sheet-modal.md).

### `SideSheetPanel`

The inside of a side sheet (Material 3): a header with an optional back button, the title and a close button, a content area that scrolls, and a row of actions at the bottom. `SideSheet` (standard, inline) and `SideSheetModal` (over a scrim) both put it in a sheet; use it on its own for a custom one. Children are the content; children with `Slot: actions` are the action buttons (a row, right-aligned).

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Title` | `str` |  | The sheet's title. |
| `Back` | `bool` | `false` | A back button before the title; it runs `On_Back`. |
| `On_Back` | `handler` |  | What the back button does. |
| `Closable` | `bool` | `true` | A close button after the title; it sets `Open` to false. |
| `Open` | `bool` | `true` | Whether the sheet is open; the close button writes false. Two-way: give it a bare reference and the view writes it back. |
| `Width` | `float` | `360` | From 256 to 400 pixels. |

Children go in the default slot, the `actions` slot.

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `header` (Container), `back` (IconButton), `title` (Text), `spacer` (Container), `close` (IconButton), `content` (ScrollView), `line` (Divider), `actions` (Container).

Its look is in [`SideSheetPanel_Stylesheet.tdl`](../stylesheets/side-sheets/side-sheet-panel.md).

## Using it

```tdl
Container {
  Name: editor
  Style { Flex_Direction: horizontal, Width: 720, Height: 420 }
  Children {
    Container {
      Name: page
      Style { Flex: fill, Height: 100% }
    }
    SideSheet {
      Open: <| filtering |>
      Title: Filters
      Children {
        Switch {
          Label: "Only mine"
        }
        Button {
          Slot: actions
          Label: Apply
          Handlers {
            On_Click: apply
          }
        }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import side_sheet

sheet = side_sheet(app.window, 280, modal=True)
sheet.open()
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# SideSheet_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: SideSheet
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
