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
