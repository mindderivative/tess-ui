# The Shell Configuration App

`apps/shell_config/` in the Tesserae UI repository is a complete application built with Tesserae UI: the graphical editor for the files of Tesserae Shell. It is a good example of a
real app: a ViewModel over a plain-Python model, one view file, a stylesheet, the toolkit's `Tree` and `TextInput`, keyboard shortcuts and a headless test that drives the window with key events only.

It is its own package (`tesserae-shell-config`, import `tess_shell_config`, command `tesserae-shell-config`) with its own `pyproject.toml`. Its README has the install steps and the keys.

## How it is put together

| Part | Does |
|---|---|
| `schema.py` | Reads the schema the `tesserae-shell` command exports into typed classes; refuses a major version it does not know. No key name is written in the code |
| `shell.py` | Runs `tesserae-shell schema`, `check` and `status` as short-lived subprocesses with a timeout, off the UI thread (`Offload` posts the answer to the loop with `app.thread_handle().call_soon`) |
| `files.py`, `folder.py` | Lossless reading and an atomic write of the `.tdl` files, a backup of the first save, the folder's files by type |
| `model.py` | One open file: its text, its lossless tree, a history of snapshots for undo and redo, and a selection kept by index path |
| `viewmodel.py`, `Views/` | The window: `Signal`s for the three areas and a handler for each action |

## Driving a window from a test

The app's tests build the window with `App(...)` over a copy of a configuration folder in `tmp_path`, advance frames, and press keys with `window.simulate("key_down", key=...)`. A key goes to the
focused node and bubbles to the view's root, where `handlers: {on_key: ...}` hears it; that is how the window's shortcuts work wherever the focus is. A multi-line `TextInput` takes Tab itself, so
the window gives the keyboard a way out (F6 moves between the three areas).

## The form generator (a generated form from data)

The Form area shows the keys of the selected block, one row each, **generated entirely from the schema**: no key name, enum value or default is in the code. It is a good example of data-driven views.

| Part | Does |
|---|---|
| `widgets.py` | A *registry* from a schema kind to a widget (switch, choice, number, length, sides, colour, text, path, and the generic TDL field). A widget reads a value from the file, says what it shows, and turns an edit into TDL text or refuses it with a message. A new widget plugs in with one line: `registry.register("icon", IconPickerWidget)` (and the cell shape it draws, in `Views/Main_View.yaml`) |
| `form.py` | `Form.build(model)` makes the rows by the schema's groups; `commit`, `reset`, `toggle_expression`, `use_token` are one `DocumentModel` edit each; `coverage(schema)` lists the keys that got the generic field, with the reason |
| `formcontrol.py` | Puts the form's `Signal`s and handlers on the window's ViewModel, keeps the focus on the row being edited while it is built again from the file, and drives the picker list and the file dialog |

Things the toolkit made us do, which any big generated view meets: the view language redraws the whole window after a change, so the form builds only the groups that are open (a closed group is one header), the window is updated inside one `batch(...)`, and a commit that arrives while the form is being rebuilt (the old field losing its focus) is ignored.
