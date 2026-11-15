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
`ViewModels/`, `Components/`, `Themes/` and `Styles/`, `app.py`, and a `Main` screen, `Views/Main_View.tdl` and
`ViewModels/Main_ViewModel.py`, that follow the [naming convention](naming-convention.md): a greeting from the app's
[shared state](apps-and-screens.md#shared-state) and a button that counts its clicks.
`app.py` gives Main the route `""`, so `python app.py <route>` opens on a screen by its
route (a [deep link](apps-and-screens.md#routes-and-deep-links)).

The files are written in the current [view language](view-language.md): `Main_View.tdl` is a tree of widget blocks written in TDL (the metadata block, then the root `Container { }`), `Main_ViewModel.py` says which
view it serves with `views = "Main"`, and `app.py` binds it (`app.bind(app.project.viewmodel("Main"))`) and opens the view
(`app.open_view("Main")`). The [project tutorial](../tutorial-project.md) grows the same project into the Tasks app.

| Option | What it does |
| --- | --- |
| `--no-venv` | Makes the folders and files without the virtual environment, which needs the network to install Tesserae. |
| `--window` | Makes the app one [`Window_View.tdl`](windows-and-docks.md): a title bar, a navigation rail and two routed screens, Main and Settings. One ViewModel, `Window_ViewModel.py`, serves the window and so the screens in it, which have none of their own. |
| `--custom-title-bar` | With `--window`: no OS title bar (`Borderless: true`). The window's own [title bar](custom-title-bars.md): it moves the window and has the minimize, maximize and close buttons. The window is at least 480 by 320 (`Min_Width` and `Min_Height` in `Window_View.tdl`). |
| `--dir PARENT` | Makes the app in `PARENT` instead of here. |

`NAME` starts with a letter and then has letters, digits, `-` or `_`. Nothing is overwritten: a folder that isn't empty is refused with a one-line message (exit code 2).

## Add a screen

```bash
tesserae add screen Settings
```

This writes `Views/Settings_View.tdl` and `ViewModels/Settings_ViewModel.py` (a title and a Back button that
calls `self.app.back()`) and adds `app.bind(...)`, `app.open_view("Settings")` and its route (`settings`) to
`app.py`, above the marker comment `tesserae new` left there. Without the marker it
prints the lines to add. A CamelCase name gets a kebab-case route: `UserProfile` is
`user-profile`. A screen's name is CamelCase (`Settings`, `UserProfile`; a lower-case `settings` is refused). `--dir` names the app's folder; a screen whose files exist is refused. In an app with its files
in one folder (no `Views/` and `ViewModels/`), it writes them beside `app.py` and adds the import and path too.

In a `--window` project a screen has no ViewModel of its own, so only `Views/Name_View.tdl` is written, and the command prints the two things to add
by hand: the screen's block under `screens`' `Children` in `Views/Window_View.tdl` (`Name { Name: ..., Route: "..." ... }`) and its `Item` under the rail's `Items`.
Names the screen reads (and a Back handler, `go_back`, which the template has) go in `ViewModels/Window_ViewModel.py`.

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
tesserae schema            # where the JSON schemas are: a view, a stylesheet and a theme
tesserae schema --project  # also writes a schema that knows this project's own views (see Editor Support)
```

See [Editor Support](editor-support.md).
