# Tesserae Shell Configuration

`tesserae-shell-config` is the graphical editor for the files of [Tesserae Shell](https://github.com/mindderivative): the shell files, modules, styles, stylesheets, themes and `settings.tdl` in the shell's configuration folder. It is built on Tesserae UI and edits the `.tdl` files in place, so comments, blank lines, order and everything you did not touch stay byte for byte as you wrote them.

This is the first part of the application: the window with the Files, Structure and Text areas, and opening and saving. The form for a block's keys, the problems list from `check`, the file watch and the theme, stylesheet and settings pages come later.

## Install and start

The application needs Python 3.14 (the TDL library's floor) and the `tesserae-shell` command on the `PATH`; it bundles no schema of its own and reads the shell's with `tesserae-shell schema --json`.

```bash
pip install -e ../..        # Tesserae UI, from the repository root, for development
pip install -e .
tesserae-shell-config                       # the folder the shell names, else ~/.config/tesserae-shell
tesserae-shell-config --config-dir ~/shell  # a folder of your own
```

Without the `tesserae-shell` command, or with a schema whose major version the application does not know, it says so on standard error and stops (exit status 3).

## The window

| Area | Shows | Does |
|---|---|---|
| Files | The folder's files by type, read from each file's root block: Shells, Modules, Styles, Stylesheets, Themes, Settings | Enter on a file opens it. A file with syntax errors or unsaved changes says so in words |
| Structure | The open file's blocks as a tree, with `If` and `For` as labelled nodes (an `If` with an `Else` shows the else body under an `Else` node) | Choosing a row selects that block |
| Text | The file as TDL | Edit it by hand; the structure follows when the text parses. A file with syntax errors is edited here only, with its errors listed (line, column, what is wrong, what to write) |

The toolbar has Save, Undo, Redo and Format file (formatting is never done unless you press it). Everything works from the keyboard:

| Keys | Does |
|---|---|
| Tab, Shift+Tab | Move through the toolbar, the Files tree, the Structure tree and the text |
| Arrow keys, Enter | Move in a tree, open or select the row |
| F6, Shift+F6 | Move to the next or previous area (the way out of the text editor, which takes Tab itself) |
| Ctrl+S | Save |
| Ctrl+Z, Ctrl+Y (or Ctrl+Shift+Z) | Undo, redo |

## What it keeps and what it never does

- Opening a file and saving it without a change leaves it byte for byte the same (a byte order mark, CRLF or a missing final newline included).
- A save writes a temporary file in the same folder and renames it over the old one, so a refused write or a full disk leaves the old file whole, and the message names the cause.
- Before the first save of a file in a session, its old content is copied to `backups/` in the application's own state folder (`$XDG_STATE_HOME/tesserae-shell-config`).
- It reads and writes only inside the chosen folder and its own state folder.

## Development

The application's tests are in `tests/` here and run in the repository's `pytest` run (they are skipped on a Python without `tess_dl`). They use a recorded schema (`tests/fixtures/schema.json`), the `tess_dl` corpus, the shell's shipped files and a fake `tesserae-shell` script written under `tmp_path`; the real shell and the real configuration folder are never touched, and the real-session guard of the repository's tests applies.
