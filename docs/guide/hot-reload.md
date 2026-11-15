# Hot Reload

`App.run(hot_reload=True)` applies an edit to a running app, and keeps its state. What it watches depends on how a file was
opened:

| File | When you save it |
| --- | --- |
| a theme: `App(custom_theme=)`, `App(default_theme=)` | every view is re-themed in place ([below](#theme-and-stylesheet-files)) |
| a view the app opened with `app.open_view` or `app.open_window`, any view it calls, and the pictures it draws | the view is composed again in place: its ViewModel, the nodes that keep their name or position, and their `State` stay ([below](#a-view-written-in-blocks)) |
| the app's stylesheet of rules (`App(stylesheet=)`, `Widget:` rules) | every view opened with `open_view` is composed again under the new rules, its state kept; a sheet with a mistake leaves them as they were |

The log says what is watched when it starts (`hot reload on: watching 2 screen(s) and 2 theme/stylesheet file(s)`), and names a screen it does not watch:
`hot reload: screen 'Tasks' isn't watched -- it was built from a spec, not a file`.

## A view written in blocks

```python
app = App()
app.bind(CounterViewModel)
app.open_view("Counter")
app.show("Counter")
app.run(hot_reload=True)
```

Save `Counter_View.tdl`, a view it calls (and the views those call), or a picture it draws, and the window shows the change at once. The view is
composed again from the new files and drawn over the old: the ViewModel and its Signals are the same ones, so the counter keeps its count; a node
that keeps its place (its `name`, or its position, with the `key` of a row under `For`) keeps its `State`; a handler is wired again. A view
the file starts to call is watched from then on. The views Tesserae ships are not watched. A view opened while the app runs is watched too, and
so is every window `open_window` opens.

A mistake leaves the window as it was and is logged as an `ERROR` naming the file: a syntax error, a call with a wrong parameter, a name that is
not defined, or a widget the engine rejects. Fix the file and save.

Not reloaded: the Python files (a ViewModel's code is not reloaded), and a `Window { }`
view's window options (its size, title and flags are read when it opens).

An edit reaches a window left alone: the watcher runs on its own thread,
and other Python threads run while a window sits idle. See the
[Python API](../api/python.md) for `App.run`.

Behind the scenes each view gets a `ComposedWatcher` on a background
thread. It listens for file-change events (using
[`watchfiles`](https://watchfiles.helpmanual.io/)), reads the files
there -- so file reading never slows the UI --
and hands only the final update to the event loop through
`App.thread_handle()` ([Python API](../api/python.md)).

## When an edit is broken

If a reload fails -- a syntax error, an unknown component, a widget `tess_re`
rejects -- Tesserae logs one `ERROR` line naming the file and the error
(the traceback is at `DEBUG`), and the screen stays as it was. The app
and the watcher keep running: fix the file, save, and it reloads. Each
reload that works is logged at `INFO`. See [Logging](logging.md).

## The window view

A `Window { }` view is recomposed like any view opened with `app.open_view`: [above](#a-view-written-in-blocks). Its window options (title, size, flags) are read when it opens.

## Theme and stylesheet files

`App.run(hot_reload=True)` also watches the theme files given to
`App(default_theme=..., custom_theme=)`. When you save one, Tesserae
re-reads both on the watcher thread, then re-themes every view the app opened
through `app.set_theme_specs(...)`: a different `Seed:`, `Colors` or
`Typography` shows at once, and bound values stay live. A theme given as a
`*_spec=` dict has no file, so it isn't watched. A broken edit is logged
at `ERROR` like a failed view reload, and the app keeps its previous theme.

Stylesheet files are watched:

- **The default stylesheet** from `App(stylesheet=)`: saving it
  re-styles every screen that uses the default, through
  `app.set_stylesheet_spec(...)`.
- **A stylesheet of `Widget:` rules** (`App(stylesheet=)`, used by views opened with `app.open_view`): every such view is composed again under the new
  rules, its state kept. A mistake in the sheet is logged as an `ERROR` naming the file, and the views keep their old rules.
A stylesheet `tess_re` rejects is reported naming the file, and every
screen keeps its old stylesheet.

### Handlers fire when bindings are re-applied

After a theme or stylesheet change, `tess_re` re-applies every binding so
bound nodes keep their live values. It does this by setting each bound
value again, so a declared `on_change` handler on a bound node (a
`Checkbox` with `Checked:` bound, a `TextField` with `Text:` bound)
runs once per reload, even though the value didn't change. The same
thing happens when a view is first attached and on a view-file reload.
Write `on_change` handlers so that running one again with the same value
is harmless: set a `Signal` to the node's current value, don't toggle
it or append to a list. This is a known behaviour of `tess_re`.

## Limits

- **Don't use `tess_re`'s own `View.poll_reload()`.** Tesserae gives `tess_re`
  the finished view as data, never a file, so `tess_re` has nothing to
  watch.
