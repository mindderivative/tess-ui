# Tesserae

**Write desktop apps in Python and TDL.** A Tesserae app is **TDL views** (what the screen looks
like), each paired with a Python **ViewModel** (what it does), drawn by the
[Tesserae Render Engine](https://github.com/mindderivative/tess-re) (`tess_re`): rendering, layout, animation
and accessibility in Rust underneath, which you never have to touch.

```tdl
---
TDL: 0.2
Name: Counter
Tesserae: "0.6"
---
# Counter_View.tdl
Container {
  Name: Counter
  Style { Flex_Direction: vertical, Gap: 12, Padding: 24, Background: surface }
  Children {
    Text {
      Name: label
      Text: Count: <| count |>
      Typography_Role: headline_medium
      Style { Foreground: on_surface }
    }
    Button {
      Name: button
      Label: Count
      Style { Width: 120 }
      Handlers { On_Click: increment }
    }
  }
}
```

```python
# Counter_ViewModel.py
from tess_ui import Signal, ViewModel

class CounterViewModel(ViewModel):
    views = "Counter"             # the view it serves

    def __init__(self):
        super().__init__()
        self.count = Signal(0)

    def increment(self):
        self.count.update(lambda n: n + 1)
```

```python
# app.py
from tess_ui import App
from Counter_ViewModel import CounterViewModel

app = App(width=240, height=160, title="Counter", search=["."])
app.bind(CounterViewModel)
app.open_view("Counter")      # Counter_View.tdl
app.show("Counter")
app.run()
```

Tesserae is on PyPI as [`tesserae-ui`](https://pypi.org/project/tesserae-ui/), pre-alpha, and runs on
Linux, macOS and Windows.

## What you get

- **Views and ViewModels.** A view is TDL: a tree of nodes, each a block headed by its widget. A ViewModel is Python, and serves the
  views that name it. A view with `Params` is a component, called by its name; `For` and `If` build lists and choices
  from data. See [The View Language](guide/view-language.md), [Apps & Screens](guide/apps-and-screens.md) and
  [Components & Embedding](guide/components.md).
- **Reactive state.** `Signal`, `Computed`, `Effect` and `ViewModel`: [bindings](guide/bindings.md) keep
  the screen in step with them. See [Reactivity](guide/reactivity.md).
- **Material Design 3.** Every MD3 [component](components/index.md) with its TDL, a
  [stylesheet](stylesheets/index.md) for each, and [themes](themes/index.md): a seed colour makes the
  palette, and light and dark follow the OS. High contrast and reduced motion follow it too.
- **Real desktop behaviour.** [Keyboard, state layers and screen-reader support](guide/interaction.md),
  [overlays](guide/overlays.md), [a window, docks, routed screens and several windows](guide/windows-and-docks.md),
  and [custom title bars](guide/custom-title-bars.md). A layout can follow the window's size class.
- **Fast iteration.** [Hot reload](guide/hot-reload.md) shows an edited view, or a theme, in a running app with its state kept,
  and [editor support](guide/editor-support.md) completes and checks your TDL.
- **Shipping.** `tesserae build` makes one executable, or an installer: [Releasing](guide/releasing.md).

## Where to go

| | |
| --- | --- |
| [Installation](installation.md) | `pip install tesserae-ui` |
| [Getting Started](getting-started.md) | Your first window and node, declaratively and from Python |
| [Tutorial](tutorial.md) and [the same as a project](tutorial-project.md) | A Tasks app in six steps: components, styling, screens, a custom window; in one flat folder, then as a `tesserae new` project |
| [Guide](guide/apps-and-screens.md) | How each part works |
| [Components](components/index.md) and [Stylesheets](stylesheets/index.md) | Every MD3 component, its TDL and its look |
| [Themes](themes/index.md) | Colour, shape, type, light and dark |
| [Python API](api/python.md) and [TDL reference](api/tdl.md) | Every class, function and key |
| [Architecture](architecture.md) | How it fits together |
| [Changelog](changelog.md) and [Migrating](migration.md) | What changed, release by release |

## Files: Tesserae reads them, `tess_re` gets data

You always give Tesserae file paths or names: views, images, themes, stylesheets and fonts. Tesserae reads, parses and
decodes them itself and hands `tess_re` only data. Every error names the file, line and column you wrote, and the nearest
name when you misspelt one.
