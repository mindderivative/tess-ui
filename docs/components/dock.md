# Dock

*Windows and docking*

## In Material Design 3

Material Design 3 has no dock. A desktop tool often wants panels around its content that the user can move and
resize: files on the left, output below.

## In Tesserae

`Dock` holds `DockPanel`s; each says its zone with the style field `Zone`: `left`, `right`, `top`, `bottom` or `center`. A left or right zone's size is its panel's
`Width`, and a top or bottom one's its `Height` (240 and 180 pixels when the panel gives none). Each zone is a column: a strip of tabs, one for each panel, over the panel
that is showing. The tab is the panel's `Title` (else its name). A click or Enter on a tab shows its panel, and the left and right arrow keys move along the strip. The user
drags a tab to another zone, or to a half of a split (see the dock panel), and drags the handles between zones to resize them. Dragging is pointer only, so a tab's context menu
(a right click, the Menu key or Shift+F10) offers "Move to ..." for each zone and each half. A window has one `Dock`, and `Zone:` is an error on anything but a `DockPanel` in a `Dock`.

`view.dock_host(id)` reads and sets the layout from Python. A node's id is its path from the view's root, so the dock named `dock` is `view.dock_host("root.dock")`, and
its panel `files` is `"root.dock.files"`:

| Call | What it does |
| --- | --- |
| `set_size(zone, px)`, `size(zone)` | a zone's size, kept between 120 pixels and 70% of the room |
| `layout()` | where every panel is, which tab shows in each zone, the zone sizes, the sizes of the splits, and the halves (see the dock panel), as plain data |
| `restore(saved)` | puts a `layout()` back; titles, zones and halves the dock does not have are skipped |
| `move(panel, where)` | a panel (its id) to the tabs of a zone (`"left"`) or a half (its id), from code |
| `closed()`, `close(panel)`, `reopen(panel)`, `on_closed(fn)` | the closable panels that are shut |

Editing the view while the app runs keeps the layout the user made: which zone each panel is in, which tab shows, and the sizes.

A panel with `Closable: true` has a close button on its tab. A Dock's `Closed` (a list, two-way) holds the names of the closable panels that are shut: a close
button adds its panel's name, and taking a name out opens the panel again, as the last tab of its zone. Putting names in shuts them without the button. Not built: floating
panels, tearing a panel off into a window, maximising a panel, reordering tabs, and layouts saved by name.

## How it is built

### `Dock`

Panels docked around a centre.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Closed` | `list` |  | The names of the closable panels that are shut; a close button adds its panel, and taking a name out opens the panel again. Two-way. |

## Using it

```tdl
Window {
  Name: studio
  Title: Studio
  Style { Width: 900, Height: 600, Flex_Direction: vertical }
  Children {
    Dock {
      Closed: <| shut |>
      Children {
        DockPanel {
          Name: files
          Title: Files
          Closable: true
          Style { Zone: left, Width: 220 }
        }
        DockPanel {
          Name: editor
          Title: Editor
          Style { Zone: center }
        }
      }
    }
  }
}
```

## See also

- [Windows And Docks](../guide/windows-and-docks.md)
- [Docking](../guide/docking.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
