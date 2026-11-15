# Title bar

*Windows and docking*

## In Material Design 3

Material Design 3's top app bar sits inside the window; a title bar is the window's own strip. A desktop app that
draws its own keeps the OS's behaviour: drag to move, double-click to maximize.

## In Tesserae

`TitleBar` in a view, or `Title_Bar:` on a `Window`. It has a `Title`, an `Icon` and `Buttons` (any of `minimize`, `maximize` and `close`, all three by default). It
is 40 pixels high unless its `Style` gives another height, and each button is 46 pixels wide. A press on the bar (or its title or icon) moves the window and a double click
maximizes it. Its buttons are the handlers `window.minimize`, `window.toggle_maximized`, `window.close` and the like, which need no ViewModel; in a dialog or a sheet
`Buttons: [dismiss]` closes it. The maximize button shows the restore glyph while the window is maximized, and each button says what it does when the pointer rests on it
(Minimize, Maximize, Close). While the window is not the focused one, the title, icon and buttons fade. The bar's children sit between the title and the buttons, so tabs, a
search field or icon buttons can live there; the window's `Flex_Direction: vertical` puts the bar above the content. On macOS the bar leaves room at its start for the
traffic lights and hides its own buttons. A right click on the bar opens the OS's window menu only if the app was made with `system_menu=True`. Not built: the Windows 11 snap
layouts on the maximize button, and a different glyph set for the buttons.

## How it is built

### `TitleBar`

A custom title bar.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Title` | `str` |  |  |
| `Icon` | `icon` |  |  |
| `Buttons` | `list` |  |  |

## Using it

```tdl
Container {
  Name: notes_bar
  Style { Flex_Direction: vertical, Width: 640, Height: 200 }
  Children {
    TitleBar {
      Name: bar
      Title: Notes
      Icon: home
      Buttons: [minimize, maximize, close]
      Children {
        IconButton {
          Name: find
          Icon: search
          Label: Find
          Handlers {
            On_Click: find
          }
        }
      }
    }
  }
}
```

## See also

- [Custom Title Bars](../guide/custom-title-bars.md)
- [Windows And Docks](../guide/windows-and-docks.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
