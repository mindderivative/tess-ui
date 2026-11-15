# Dock panel

*Windows and docking*

## In Material Design 3

Material Design 3 has no dock panel. It is one panel of a dock: a titled tab in a zone.

## In Tesserae

`DockPanel`, with `Zone` in its `Style` and a `Title` for its tab (else its name). `Closable: true` puts a close button on its tab (see the Dock's `Closed`).

A `DockPanel` inside another is a split of it, side by side (`Flex_Direction: horizontal`, the default) or top and bottom (`vertical`), with a handle between the halves
to resize them. A half with a `Width` (or `Height`) of its own keeps it, and the others share what is left. A panel has either splits or content, not both, and a half has no
`Zone`. Each half is a small zone of its own: a tab strip over it, with a tab for the half's own content (titled by its `Title:`, else its name) and one for each panel dropped
on it.

Drag a tab over a half and the highlight shows what a drop will do. The outer quarter of each side of a half is an **edge**: dropping there splits the half, the panel
taking a new half on that side with a handle between the two. The rest, the tab strip included, is the **middle**: dropping there adds the panel to the half as another tab,
and the half shows it. A tab in a half is dragged like any other, to a zone, to another half or to the edge of one. A half that a drop made collapses when its last panel
leaves, and its neighbour takes the room back. You cannot drop a panel on the halves inside it. In the tab menu (right click, the Menu key or Shift+F10) "Move to ..."
lists the halves too.

From Python, with `dock = view.dock_host("root.dock")`. The half and the panel are named by their ids, their paths from the view's root (`root.dock.editor.source`):

| Call | What it does |
| --- | --- |
| `dock.halves()` | each half's panels (their ids) and the one it shows (`None`: the half's own content) |
| `dock.show_in_half(half, panel)` | shows a panel in a half; `panel` of `None` shows the half's own content |
| `dock.half_of(panel)` | the id of the half a panel is in, or `None` if it is in a zone |
| `dock.move(panel, where)` | a panel into a half or a zone (`"left"`) |

`dock.layout()` records the halves, so the arrangement the user made survives a restart: `halves` has, for each half, the titles of the panels in it and the tab it shows,
and `made` has, for each half of the view that the user split, the tree of the splits (an `axis` of `x` or `y`, the first part's `size` in pixels, and its `first` and
`second` parts), as plain data you can write to a file. `dock.restore(saved)` takes the user's splits apart, makes the ones in the layout and puts the panels in their
halves; halves and titles the dock does not have are skipped, and a split none of whose panels come back is not made. A half is found by its id, so renaming one in the
file means a saved layout no longer finds it. Editing the view while the app runs keeps the strips, the panels dropped on a half and the splits the user made; a half the
file removes sends the panels dropped in it back to their zones. Not built: dragging or closing a half's own content (what the view put in it), and reordering tabs.

## How it is built

### `DockPanel`

One panel of a Dock.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Title` | `str` |  | The panel's tab, when its zone has several. |
| `Closable` | `bool` |  | Its tab has a close button. |

## Using it

```tdl
Window {
  Name: studio
  Title: Studio
  Style { Width: 900, Height: 600, Flex_Direction: vertical }
  Children {
    Dock {
      Children {
        DockPanel {
          Name: outline
          Title: Outline
          Style { Zone: left, Width: 220 }
        }
        DockPanel {
          Name: editor
          Title: Editor
          Style { Zone: center }
          Children {
            DockPanel {
              Name: source
              Title: Source
              Style { Width: 400 }
            }
            DockPanel {
              Name: preview
              Title: Preview
            }
          }
        }
      }
    }
  }
}
```

## See also

- [Windows And Docks](../guide/windows-and-docks.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
