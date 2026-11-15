# Projects

A project is a folder with a place for each kind of file. Tesserae finds a file by its name, so
`app.open_view("Main")` is enough and a view calls `Stat { }` without a path. `tesserae new` makes one:

```bash
tesserae new notes
cd notes
source .venv/bin/activate     # Windows: .venv\Scripts\activate
python app.py
```

```text
notes/
  .venv/              a virtual environment with Tesserae in it
  app.py
  Views/              Main_View.tdl, Window_View.tdl (the window), Name_View.tdl: every screen and every view you call
  ViewModels/         Main_ViewModel.py
  Themes/             Name_Theme.tdl
  Styles/             Name_Stylesheet.tdl
```

The files `tesserae new` writes are TDL, the current view language; a project written in YAML is moved as [Migrating from YAML](../migration.md#migrating-from-yaml) says, and the
[project tutorial](../tutorial-project.md) shows the app written in TDL.

The [project tutorial](../tutorial-project.md) builds an app in one, step by step, beside the
[flat-folder tutorial](../tutorial.md).

`--no-venv` makes the folders and files without the virtual environment (the environment needs the network to
install Tesserae). [The `tesserae` command](cli.md) has the rest.

## Finding files by name

| You write | Tesserae opens |
| --- | --- |
| `app.open_view("Main")` | `Views/Main_View.tdl` |
| `app.bind(app.project.viewmodel("Main"))` | `ViewModels/Main_ViewModel.py`, the class `MainViewModel`, imported for you |
| `app.open_view("Window")` | `Views/Window_View.tdl`, the window (a `Window` view) |
| `Side { }` in a view | the view `Side`: `Views/Side_View.tdl`, or one of the views Tesserae ships; a name of yours wins |
| `App(custom_theme="Brand")` | `Themes/Brand_Theme.tdl` |
| `App(stylesheet="Page")` | `Styles/Page_Stylesheet.tdl` |
| a view `Stat` that a view calls | `Stat_Stylesheet.tdl` beside `Stat_View.tdl`, or in `Styles/`: its look, read only while the app uses `Stat` |

A **path** works wherever a name does: `app.open_view(HERE / "Views" / "Main_View.tdl")`. A string with a `/` or a `.` is a
path too, read from the folder you run in, so build it from `HERE` (the script's folder) and it works from anywhere. A name has
no `/` and no `.`.

The project's root is `App(root=...)`, which defaults to the folder of the script that runs (`app.py`).
`tesserae new` passes `root=HERE` so it doesn't depend on where you start it from.

A ViewModel is imported from its file, and its folder goes on Python's path, so a ViewModel can import another
by its file name (`from Helper_ViewModel import HelperViewModel`).

## More places to look

```python
app = App(root=HERE, search=["shared", "../common/ui"])
```

`search=` adds folders, relative to the root or absolute, to look in for every kind of file, after the
standard ones. `search=["."]` makes the root itself one of them, which is how an app whose files all sit side by side
(a flat folder, as in the [tutorial](../tutorial.md)) finds its views by name. To look through the whole project instead, give the app `recursive=True`: every folder under
the root is searched for every kind, except hidden folders, virtual environments, `__pycache__`,
`node_modules`, `site-packages`, `build`, `dist` and `site`. It is slower in a big tree, and it finds files you didn't
mean to use, which is why it is opt-in.

```python
app = App(root=HERE, recursive=True)
```

## A name in two places

If two folders have a file with the same name, Tesserae stops and says so, rather than choose:

```text
ProjectError: Main_View.tdl is in two places, Views/Main_View.tdl and shared/Main_View.tdl: keep one, or name them differently
```

A name that is nowhere says where it looked:

```text
ProjectError: no view called 'Nope' (Nope_View.tdl) in Views under /home/you/notes: add the folder to App(search=[...]) or pass the file's path
```

## A name in the wrong place

A file that exists, but where Tesserae does not look, is named in the same error:

```text
ProjectError: no view called 'Extra' (Extra_View.tdl) in Views under /home/you/notes: add the folder to App(search=[...]) or pass the file's path; found Themes/Extra_View.tdl: views are read from Views/ (or add Themes to App(search=[...]))
```

A file of another kind with the same name is named for what it is: `found Views/Brand_View.tdl, a view, not a theme`.

## Adding to a project

`tesserae add screen Settings` writes `Views/Settings_View.tdl` and `ViewModels/Settings_ViewModel.py` and adds
its `bind`, `open_view` and route to `app.py` ([the command](cli.md#add-a-screen)). In a project written in TDL a
screen is a view in `Views/` whose root has a `Name`, a ViewModel in `ViewModels/` that serves it, and a `bind` and an
`open_view` in `app.py`; a view you call is a file in `Views/`; a theme or a stylesheet is a file in `Themes/` or `Styles/`.
Nothing else needs registering.

The API is [`tess_ui.project`](../api/python.md#projects); an app's is `app.project`.
