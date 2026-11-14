# The `tesserae` Command

Installing Tesserae installs a `tesserae` command (`python -m tess_ui` is the same).
It starts apps and screens from templates, moves a project to the current view syntax, writes views as TDL, builds an app into one executable, and
finds the editor schemas. `tesserae --version` prints the version, and `tesserae <command> --help` lists a command's options.

## Start an app

```bash
tesserae new notes
cd notes
source .venv/bin/activate     # Windows: .venv\Scripts\activate
python app.py
```

`notes/` is a [project](projects.md): a virtual environment with Tesserae installed in it, the folders `Views/`,
`ViewModels/`, `Components/`, `Themes/` and `Styles/`, `app.py`, and a `Main` screen, `Views/Main_View.yaml` and
`ViewModels/Main_ViewModel.py`, that follow the [naming convention](naming-convention.md): a greeting from the app's
[shared state](apps-and-screens.md#shared-state) and a button that counts its clicks.
`app.py` gives Main the route `""`, so `python app.py <route>` opens on a screen by its
route (a [deep link](apps-and-screens.md#routes-and-deep-links)).

The files are written in the current [view language](view-language.md): `Main_View.yaml` is a tree of `widget:` nodes, `Main_ViewModel.py` says which
view it serves with `views = "Main"`, and `app.py` binds it (`app.bind(app.project.viewmodel("Main"))`) and opens the view
(`app.open_view("Main")`). The [project tutorial](../tutorial-project.md) grows the same project into the Tasks app.

| Option | What it does |
| --- | --- |
| `--no-venv` | Makes the folders and files without the virtual environment, which needs the network to install Tesserae. |
| `--window` | Makes the app one [`Window_View.yaml`](windows-and-docks.md): a title bar, a navigation rail and two routed screens, Main and Settings. One ViewModel, `Window_ViewModel.py`, serves the window and so the screens in it, which have none of their own. |
| `--custom-title-bar` | With `--window`: no OS title bar (`borderless: true`). The window's own [title bar](custom-title-bars.md): it moves the window and has the minimize, maximize and close buttons. The window is at least 480 by 320 (`min_width` and `min_height` in `Window_View.yaml`). |
| `--dir PARENT` | Makes the app in `PARENT` instead of here. |

`NAME` starts with a letter and then has letters, digits, `-` or `_`. Nothing is overwritten: a folder that isn't empty is refused with a one-line message (exit code 2).

## Add a screen

```bash
tesserae add screen Settings
```

This writes `Views/Settings_View.yaml` and `ViewModels/Settings_ViewModel.py` (a title and a Back button that
calls `self.app.back()`) and adds `app.bind(...)`, `app.open_view("Settings")` and its route (`settings`) to
`app.py`, above the marker comment `tesserae new` left there. Without the marker it
prints the lines to add. A CamelCase name gets a kebab-case route: `UserProfile` is
`user-profile`. A screen's name is CamelCase (`Settings`, `UserProfile`; a lower-case `settings` is refused). `--dir` names the app's folder; a screen whose files exist is refused. In an app with its files
in one folder (no `Views/` and `ViewModels/`), it writes them beside `app.py` and adds the import and path too.

In a `--window` project a screen has no ViewModel of its own, so only `Views/Name_View.yaml` is written, and the command prints the two things to add
by hand: the screen's node under `screens` in `Views/Window_View.yaml` (`{widget: Name, name: ..., route: "..."}`) and its item under the rail's `items:`.
Names the screen reads (and a Back handler, `go_back`, which the template has) go in `ViewModels/Window_ViewModel.py`.

## Move a project to the current syntax

```bash
tesserae migrate-yaml            # reports what would change; writes nothing
tesserae migrate-yaml --write    # writes it, if every file checked out
```

`tesserae migrate-yaml [PATH]` (the project's folder, here by default) reads every `*_View.yaml`, `*_Component.yaml` and
`*_Stylesheet.yaml`, translates each, checks the result with the loader an app uses, and writes only if all of them load. `--force`
with `--write` writes the ones that did. Keep the project in version control: the old files are rewritten and a fragment is
renamed (a `*_Style.yaml` file is read in and left in place). The report lists what each ViewModel needs, including the `app.bind` and `app.open_view`
lines for `app.py`, because Python is not rewritten. A call of a shipped fragment that became one view with a property (`ButtonFilled` is `widget: Button` with
`variant: filled`) fails the check with `no widget named 'ButtonFilled'`, and is written by hand from the table in Migrating. The exit code is 1 if any file failed,
A view, stylesheet or theme whose `tesserae:` first line names an older series is also moved to the current one: that line only, nothing else in the file changes, and a file already current, newer or without the line is left alone. and 2 for a wrong argument (`--force` without `--write` is one). [Migrating](../migration.md#to-050) has the table of every change and of the shipped names.

## Write views and stylesheets as TDL

```bash
tesserae migrate-tdl                      # lists what it would convert; writes nothing
tesserae migrate-tdl --write              # writes Views/Name_View.tdl beside each Name_View.yaml
tesserae migrate-tdl Views/Main_View.yaml --write --remove-source   # one file, and deletes its YAML afterwards
```

`tesserae migrate-tdl [PATH]` writes each `*_View.yaml` under `PATH` (a file or the project's folder, here by default) as a `*_View.tdl` file beside it, and each `*_Stylesheet.yaml` as a `*_Stylesheet.tdl` (a root `Styles { }` of `Rule { Widget: Button, Variant: filled, Style { Height: 40 } }` blocks, in order; a style field that holds a map is a block of its own: `Padding { Left: 12 }`; themes are skipped for now). A view:
keys in `Title_Case` (`typography_role` is `Typography_Role`), a node a block headed by its widget (`Button { ... }`), `if:` and `for:` as `If` and `For`
blocks around the node, a handler as `Set` and `Call` steps (`open = not open; on_toggle()` is a `Set { Target: open, Value: <| not open |> }` and a
`Call { Action: "on_toggle" }`), `{{ expression }}` as `<| expression |>`, and a metadata block with the view's `Name` and the `Tesserae` series.
Comments are kept (the ones at the top, the ones above an entry and the ones at the end of a line), and so are blank lines between entries and the order of
the keys. Each entry is on a line of its own; a YAML `{...}` or `[...]` that sits on one line stays on one line when it fits in 150 columns, a list that
does not is wrapped there, and a mapping that does not is opened one entry to a line. The report lists the files, the number of steps written, and
what needs a look.

Every result is read back through the TDL loader and compared with the YAML view before it is written, so a view the command cannot write exactly is
reported with its file, line and what to write instead, and left alone; the other files are still written. It refuses a key that is not lower
`snake_case`, a handler that is not assignments to a name and calls (`if`, `for`, `a[0] = 1`, `go(*args)`), a value of another type than text, number,
yes/no or nothing (a YAML date: quote it), an anchor or alias, and text that holds a `{{ }}` and a `,`, a brace or ` #` (write the whole value as one slot).
An augmented assignment (`x += 1`) is written as `Set { Target: x, Value: <| x + 1 |> }`: the name gets a new value, it is not changed in place.

A `for:` with a pair target (`for: i, item in enumerate(items)`) has no TDL form yet, because a TDL `For` has one variable. It is written with one variable that
joins the names (`For i_item In <| enumerate(items) |> ...`), with a `# TODO tuple for-target: i, item in enumerate(items)` line above it, and listed in the
report with its file and line. The loop's body still uses `i` and `item`: change it by hand to `i_item[0]` and `i_item[1]`.

Running it again changes nothing. It never replaces a file that differs without `--write`; the YAML is kept unless `--remove-source` is given with `--write`, and
then it is deleted only for the files that were written (or already current). Themes (`*_Theme.yaml`) and components are skipped with a note. The
exit code is 1 if any file failed and 2 for a wrong argument. The command needs the `tess_dl` package, which needs Python 3.14.

## Build an executable

```bash
pip install "tesserae-ui[build]"
tesserae build --check
```

Makes one file in `dist/` with every file under the app's folder inside it, and `--check` runs it
briefly to see it start. Options: `--name`, `--icon`, `--console`, `--include GLOB`,
`--exclude GLOB`, and for an installer `--installer` with `--app-version`, `--identifier`,
`--publisher` and `--description`. See [Releasing Your App](releasing.md).

## Find the editor schemas

```bash
tesserae schema            # where the YAML schemas are
tesserae schema --settings # the `yaml.schemas` setting for Red Hat's YAML language server
tesserae schema --settings --project   # the same, with the schema of this project's own views (see Editor Support)
```

See [Editor Support](editor-support.md).
