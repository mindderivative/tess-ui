# Naming Convention

A screen is a `<Name>_View.tdl` and a `<Name>_ViewModel.py`. The names are how Tesserae joins them, and how it
finds them in a [project](projects.md):

|File|What it is|Its name is|
|---|---|---|
|`Counter_View.tdl`|a view|`Counter`: what `app.open_view("Counter")` and a `Counter { }` call say|
|`Counter_ViewModel.py`|its ViewModel, the class `CounterViewModel`|`Counter`: what `app.project.viewmodel("Counter")` finds|
|`Brand_Theme.tdl`|a theme|`Brand`: `App(custom_theme="Brand")`|
|`Tasks_Stylesheet.tdl`|a stylesheet of rules|`Tasks`: `App(stylesheet="Tasks")`|

The part before the suffix is the **name**, and it is CamelCase. A view, a theme and a stylesheet are TDL files (`.tdl`), read by the TDL language 0.2: slots are written
`<| |>`, and a file in an older TDL language, or one that writes a slot as `{{ }}`, is refused with the line. A YAML file is not read: [Migrating from YAML](../migration.md#migrating-from-yaml) says how to move a project.
Which ViewModel serves which view is not decided by the file
names but by a second name, the view's **bind key**, the `Name` of its root node:

```text title="Counter_View.tdl"
---
TDL: 0.2
Name: Counter
Tesserae: "0.6"
---
Container {
  Name: Counter          # the bind key
}
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
(`app.show("Counter")`, `app.navigate("Counter")`). A view whose root has no `Name` is not bound to any ViewModel, and is
registered under its file's name.

## What is checked

- **A ViewModel that is not found.** `app.project.viewmodel("Counter")` imports `Counter_ViewModel.py` and takes the class
  `CounterViewModel`. A file with no such class is an error that lists the classes it does have.
- **A name no ViewModel has.** Every name a view reads and every action a handler calls is looked up when the view
  opens, and a miss is an error that names the file, line and column and the nearest name:
  `Counter_View.tdl:5:43: 'cont' is not defined (did you mean 'count')`.
- **A mismatched pair.** A ViewModel whose `views` names a view that does not exist, because the keys differ in case or
  spelling, is reported by `app.check()`:
  `CounterViewModel serves the view 'counter', but no view has that name`. The view itself then has no ViewModel, and
  fails on the first name it needs. `assert app.check() == []` in a test is the cheap way to keep the two in step.
- **Two ViewModels for one view.** `app.bind` refuses the second.
- **A file that is not where its name is looked for.** `app.open_view("Extra")` with the file in `Themes/` is an error that says where it is and what to do:
  `found Themes/Extra_View.tdl: views are read from Views/ (or add Themes to App(search=[...]))`. The same name under another kind's suffix is named as what it is
  (`found Views/Brand_View.tdl, a view, not a theme`). See [Projects](projects.md#a-name-in-the-wrong-place).
- **A file whose content is another kind.** The kind of a TDL file is the word its root block starts with: `Styles` is a stylesheet, `Theme` a theme, any other word a view.
  A `*_View.tdl` that starts with `Styles` or `Theme`, or a `*_Stylesheet.tdl` or `*_Theme.tdl` that starts with a widget, is an error that says what the file looks like and what to name it
  (`this looks like a stylesheet: name it Brand_Stylesheet.tdl`), pointing at the root word. It is a hint from the root word, not a ruling.

## Stylesheet and theme files

More names say what a TDL file is:

|Suffix|What it holds|Used by|
|---|---|---|
|`*_Stylesheet.tdl`|a stylesheet: a `Styles` block of `Rule` blocks that name a `Widget`|`App(stylesheet=)`, `load_stylesheet`|
|`*_Theme.tdl`|a theme: `Seed`, `Colors`, `Typography`, `Components`|`App(default_theme=, custom_theme=)`, `load_theme`|

A file named for one kind and loaded as another is refused, naming what its name says it is: `load_theme("card_Stylesheet.tdl")`,
say (`load_theme` and `load_stylesheet` are in `tess_ui.spec.themes`). A theme or stylesheet file with neither suffix (`themes/Brand.tdl`) still loads; the suffixes are recommended, not required.

## The metadata block

Every view, stylesheet and theme starts with a metadata block between two `---` lines, and comments and the root block come after it:

```text
---
TDL: 0.2
Name: Card
Tesserae: "0.6"
---
# A card for one subject.
Container {
  Name: Card
}
```

- `TDL` is the language the file is written in. Tesserae reads `0.2`; a file that says `TDL: 0.1` (whose slots are `{{ }}`) is refused at that line.
- `Name` is the file's own name (a view's, a stylesheet's, a theme's): `Card` for `Card_View.tdl`. It is not the root node's `Name`, which is the bind key.
- `Tesserae` is the release series of Tesserae: the first two numbers of its version, written as a quoted string. It is read before anything else in the file, so Tesserae knows a file is one of its own, and a person reading
  it knows too. Nothing in the file treats it as a property or a rule.

|What the file has|What happens|
|---|---|
|`Tesserae: "0.6"`|it loads|
|a value that is not a release series (a whole version with three numbers, `yes`, nothing)|an error: write `Tesserae: "0.6"`|
|a newer series|an error: the file was written for a newer Tesserae, so upgrade|
|an older series|an error that says which series it was written for|
|no `Tesserae` entry|it loads, and the log says once, at the info level, that the file has none. The entry is optional for now, and a later series will ask for it|

`tesserae new` and `tesserae add screen` write it, and so does every file Tesserae ships. A mapping you read from a file yourself and give to
`App(stylesheet_spec=...)` or `custom_theme_spec=` may keep a `tesserae` key: the checks ignore it.

## The views Tesserae ships

Tesserae's own components are views of the same kind: `Button_View.tdl` with its rules in `Button_Stylesheet.tdl`, in the
package. A view of yours named `Button` (a file `Views/Button_View.tdl`) is found first and replaces it, and the shipped rules
for `Button` are not used for it: its look is then your own `Style` and the rules in your app's stylesheet. See
[Stylesheets](../stylesheets/index.md).

## Why a convention at all?

A name that is the same everywhere is a name nobody has to look up: the view, its ViewModel, its route and its tests all say
`Counter`. A project that follows it can open and join screens with the names alone, and a mismatch is caught when the view
opens, not later when a handler does nothing.
