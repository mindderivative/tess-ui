# Naming Convention

A screen is a `<Name>_View.yaml` and a `<Name>_ViewModel.py`. The names are how Tesserae joins them, and how it
finds them in a [project](projects.md):

| File | What it is | Its name is |
|---|---|---|
| `Counter_View.yaml` | a view | `Counter`: what `app.open_view("Counter")` and `widget: Counter` say |
| `Counter_ViewModel.py` | its ViewModel, the class `CounterViewModel` | `Counter`: what `app.project.viewmodel("Counter")` finds |
| `Brand_Theme.yaml` | a theme | `Brand`: `App(custom_theme="Brand")` |
| `Tasks_Stylesheet.yaml` | a stylesheet of rules | `Tasks`: `App(stylesheet="Tasks")` |

The part before the suffix is the **name**, and it is CamelCase. Which ViewModel serves which view is not decided by the file
names but by a second name, the view's **bind key**:

```yaml
tesserae: 0.5
# Counter_View.yaml
name: Counter            # the bind key
widget: Container
```

```python
# Counter_ViewModel.py
class CounterViewModel(ViewModel):
    views = "Counter"    # the bind keys it serves: a string, or a list for several
```

```python
app.bind(CounterViewModel)
app.open_view("Counter")
```

Keep the bind key equal to the file's name, so one name finds the view, the ViewModel and the screen
(`app.show("Counter")`, `app.navigate("Counter")`). A view with no `name:` is not bound to any ViewModel, and is
registered under its file's name.

## What is checked

- **A ViewModel that is not found.** `app.project.viewmodel("Counter")` imports `Counter_ViewModel.py` and takes the class
  `CounterViewModel`. A file with no such class is an error that lists the classes it does have.
- **A name no ViewModel has.** Every name a view reads and every action a handler calls is looked up when the view
  opens, and a miss is an error that names the file, line and column and the nearest name:
  `Counter_View.yaml:5:43: 'cont' is not defined (did you mean 'count')`.
- **A mismatched pair.** A ViewModel whose `views` names a view that does not exist, because the keys differ in case or
  spelling, is reported by `app.check()`:
  `CounterViewModel serves the view 'counter', but no view has that name`. The view itself then has no ViewModel, and
  fails on the first name it needs. `assert app.check() == []` in a test is the cheap way to keep the two in step.
- **Two ViewModels for one view.** `app.bind` refuses the second.
- **A file that is not where its name is looked for.** `app.open_view("Extra")` with the file in `Themes/` is an error that says where it is and what to do:
  `found Themes/Extra_View.yaml: views are read from Views/ (or add Themes to App(search=[...]))`. The same name under another kind's suffix is named as what it is
  (`found Views/Brand_View.yaml, a view, not a theme`). See [Projects](projects.md#a-name-in-the-wrong-place).

## Stylesheet and theme files

More names say what a YAML file is:

| Suffix | What it holds | Used by |
|---|---|---|
| `*_Stylesheet.yaml` | a stylesheet: a `styles:` list of rules that name a `widget` | `App(stylesheet=)`, `load_stylesheet` |
| `*_Theme.yaml` | a theme: `seed:`, `colors:`, `typography:`, `components:` | `App(default_theme=, custom_theme=)`, `load_theme` |
| `*_Style.yaml` | one node's style, kept in `Styles/` | the older syntax; the current language refuses it |
| `*_Component.yaml` | a fragment of the older syntax, kept in `Components/` | `app.load` |

A file named for one kind and loaded as another is refused, naming what its name says it is: `load_theme("card_Stylesheet.yaml")`,
say (`load_theme` and `load_stylesheet` are in `tesserae.spec.themes`). A theme or stylesheet file with neither suffix (`themes/Brand.yaml`) still loads; the suffixes are recommended, not required.

## The first line

Every view, stylesheet and theme starts with the line it was written for, and comments come after it:

```yaml
tesserae: 0.5
# A card for one subject.
name: Card
widget: Container
```

`tesserae: 0.5` is the release series of Tesserae: the first two numbers of its version. It is read before anything else in the file, so Tesserae knows a file is one of its own and
which language it is in, and a person reading it knows too. It has to be the **first line** (a byte order mark and Windows line endings are fine), and nothing in the file
treats it as a property or a rule.

| What the file has | What happens |
| --- | --- |
| `tesserae: 0.5` on line 1 | it loads |
| `tesserae:` anywhere else, under a comment, a blank line or `---` | an error that names the line it is on: move it to line 1 |
| a value that is not a release series (a whole version with three numbers, `yes`, nothing) | an error: write `tesserae: 0.5` |
| a newer series | an error: the file was written for a newer Tesserae, so upgrade |
| an older series | an error: run `tesserae migrate-yaml` |
| no `tesserae:` line | it loads, and the log says once, at the info level, that the file has none. The line is optional for now, and a later series will ask for it |

`tesserae new`, `tesserae add screen` and `tesserae migrate-yaml` write it, and so does every file Tesserae ships. A mapping you read from such a file yourself
(`yaml.safe_load`) and give to `App(stylesheet_spec=...)` or `custom_theme_spec=` may keep the key: the checks ignore it. The files of the older syntax have none, which is how they
are told apart. An editor's schema modeline cannot sit under the line: see [Editor Support](editor-support.md#or-one-file-at-a-time).

## The views Tesserae ships

Tesserae's own components are views of the same kind: `Button_View.yaml` with its rules in `Button_Stylesheet.yaml`, in the
package. A view of yours named `Button` (a file `Views/Button_View.yaml`) is found first and replaces it, and the shipped rules
for `Button` are not used for it: its look is then your own `style:` and the rules in your app's stylesheet. See
[Stylesheets](../stylesheets/index.md).

## Why a convention at all?

A name that is the same everywhere is a name nobody has to look up: the view, its ViewModel, its route and its tests all say
`Counter`. A project that follows it can open and join screens with the names alone, and a mismatch is caught when the view
opens, not later when a handler does nothing.

## Views in the older syntax

A view written with `kind:` and `id:` is paired by file name alone: `app.load("Counter")` checks that `Counter_View.yaml` and the
`Counter_ViewModel.py` that defines the ViewModel class (found with `inspect.getfile`, not a string you pass) have the same
prefix, and raises `ValueError` immediately if the view does not end in `_View.yaml`, the ViewModel's file does not end in
`_ViewModel.py`, or the prefixes differ. `instantiate` does the same check for an embedded component
(`tesserae.naming.check_naming_convention` is the shared code); `App.register` and a `Component` built by hand take what you
give them. `tesserae migrate-yaml` moves such a project to the names above ([Migrating](../migration.md)).
