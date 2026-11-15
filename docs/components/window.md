# Window

*Windows and docking*

## In Material Design 3

Material Design 3 describes how an app's content adapts to a window, not the window itself. `widget: Window` is the OS
window as a view: the root of `Window_View.tdl`, with its title, size and title bar.

## In Tesserae

Before the view is built, the `Window` becomes a vertical container holding the `TitleBar` and a content container;
`App` reads its title, size, `Borderless` and minimum size when it loads the view. A `Window` is the root of its view: it can't be nested or embedded. There is
one `Window` per window view. The app's own window is the window view it opens with `app.open_view("Window")` (an app has one), and a second OS window is another view whose
root is a `Window`, opened with `app.open_window`.

| Property | Meaning |
| --- | --- |
| `Title`, `Borderless`, `Min_Width`, `Min_Height` | the OS window's title, whether it has no OS title bar or borders, and the least the user can resize it to |
| `Title_Bar` | a `{Title, Icon, Buttons}` mapping for the window's title bar; in a window that is not `Borderless` it is a plain header, with no buttons of its own (the OS draws them) |
| `Style` | `Width` and `Height` are the window's size (a second window whose view has no `Window` root is 480 by 320), and `Background` its fill; the rest lays out the content |
| `Remember` | true, or a name: the size, the place (where the platform lets an app say: not Wayland) and the maximized state are kept in a small file in the user's config directory (named for the title, or the name) and put back next run; a maximized window keeps the size it had before. The app's own window only |
| `Fullscreen`, `Maximized` | set when the view loads, only when written (in a second window too) |
| `Transparent`, `Blur_Behind`, `Click_Through` | set before the window opens, only when written; the platform may refuse one, and says so |

A view branches on the window's size with `app.width_class` and `app.height_class` (Material 3's size classes).

**Several windows.** `app.open_window("Prefs")` builds `Prefs_View.tdl` in a new OS window and returns its `AppWindow`; `app.windows` holds the others by name,
`app.window_of("prefs")` finds one and `app.close_window("prefs")` closes it. The view's `Window` root gives that window its title, size, minimum size, `Borderless` and flags.
`modal=True` puts a dimming layer over the parent (the app's window, or `parent=` another `AppWindow`) that takes its input until the child closes. From a view,
the handler `open_window('Prefs')` does the same, and `open_window('Prefs', True)` opens a modal one. A second window has no screens or routes, and closing it leaves the
app running; closing the app's own window closes them all. Not built: a native menu bar.

```tdl
Window {
  Name: window
  Title: Notes
  Borderless: true
  Style { Width: 960, Height: 600, Flex_Direction: vertical }
  Title_Bar { Title: Notes, Buttons: [minimize, maximize, close] }
  Children {
    Main {
      Name: main
      Route: ""
      Style { Flex: fill }
    }
  }
}
```

```python
app = App(title="Notes", root=HERE)
app.open_view("Window")     # Views/Window_View.tdl: the app's window
```

```python
prefs = app.open_window("Prefs", modal=True)   # Prefs_View.tdl, in a window of its own
prefs.on_close(save)
prefs.center()                                 # where the system lets an app place a window
```

## How it is built

### `Window`

The root of an app window.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Title` | `str` | required | The OS window's title. |
| `Borderless` | `bool` |  |  |
| `Remember` | `any` |  | true, or a name: the window's size, place (where the platform lets an app say) and maximized state are kept between runs. |
| `Fullscreen` | `bool` |  | The window fills its monitor, borderless (set when the view loads). |
| `Maximized` | `bool` |  | The window opens maximized. |
| `Transparent` | `bool` |  | A see-through window that draws only what the view paints; the OS fixes it before the window opens. |
| `Blur_Behind` | `bool` |  | The desktop behind a transparent window is blurred (where the compositor does it). |
| `Click_Through` | `bool` |  | Clicks go to the window beneath; the window takes none. |
| `Min_Width` | `float` |  |  |
| `Min_Height` | `float` |  |  |
| `Title_Bar` | `dict` |  | Title, icon and buttons of a custom title bar. |

## See also

- [Windows And Docks](../guide/windows-and-docks.md)
- [Custom Title Bars](../guide/custom-title-bars.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
