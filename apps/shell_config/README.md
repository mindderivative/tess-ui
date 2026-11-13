# Tesserae Shell Configuration

`tesserae-shell-config` is the graphical editor for the files of [Tesserae Shell](https://github.com/mindderivative): the shell files, modules, styles, stylesheets, themes and `settings.tdl` in the shell's configuration folder. It is built on Tesserae UI and edits the `.tdl` files in place, so comments, blank lines, order and everything you did not touch stay byte for byte as you wrote them.

This is the second part of the application: the window with the Files, Structure, Form and Text areas, opening and saving, and the form for a block's keys. The problems list from `check`, the file watch, add and remove, and the stylesheet pages come later.

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
| Space or Enter on a switch, button or group header | Toggle it, press it, open or close the group |
| Enter, or Tab out of a field | Write the field's value (nothing is written while you type) |
| Up, Down in a number field | One step of the key's `step`, inside its range |

## The form

Choosing a block (or a setting section, a module call, a theme token group) fills the Form area with its keys, in the schema's groups. Each group is a header; the first group is open, and Enter on a header opens or closes it (the choice is remembered by group name from block to block). One key is one row: its name, the widget of its kind, then a `$` button (a list of the theme tokens the key accepts, the schema's preferred ones first, a colour with its swatch), a `{ }` button for a key that takes an expression (the widget is swapped for a field holding `{{ ... }}`, written as it is) and a reset button (removes the property, so the shell's default applies; disabled while the key is absent). The schema's default is the placeholder; the doc is the row's tooltip and shows under the row that has the focus; a required key that is absent is marked.

| Kind | Widget |
|---|---|
| boolean, enabled | Switch |
| enum | A button that opens a list of the choices (each with its doc where the schema has one) |
| number, whole, percent, duration | A field with the unit as a suffix; a value outside the minimum and maximum is refused with the range, nothing is written and the typed text stays |
| length | A field and a unit button (`px`, `%`, `AUTO`, `EXPAND` from the key's units) |
| sides, radius | One field, or four in the schema's order (Linked/Separate); a blank side is 0 |
| color | The shipped `ColourPicker` (alpha only where the key allows it); written as `"#RRGGBB"` |
| string, name, path | A text field; the schema's `pattern` is checked; a path has a Browse button that opens the shipped `FileDialog` in the key's mode and filters |
| shadows, block, tooltip, list, icon, font, and a kind this version does not know | The value as TDL text (a list of these is in the coverage test); the icon picker, font list and list editor of other branches plug in with one line in `widgets.default_registry` |

A value the widget cannot show (a call, a token reference, a hand-written expression, a list it does not understand) is shown as its TDL text and never rewritten unless you edit it. A style key that is already inside a block's `Style { }` is read and changed there. A property the schema does not name is listed under "Not in the schema". Keys the shell does not build are grouped last; a key TDL reserves (`Key`) cannot be written by `tess_dl`'s edits and says so. In a theme, a token group shows one column for the base and one for each mode the file defines.

## What it keeps and what it never does

- Opening a file and saving it without a change leaves it byte for byte the same (a byte order mark, CRLF or a missing final newline included).
- A save writes a temporary file in the same folder and renames it over the old one, so a refused write or a full disk leaves the old file whole, and the message names the cause.
- Before the first save of a file in a session, its old content is copied to `backups/` in the application's own state folder (`$XDG_STATE_HOME/tesserae-shell-config`).
- It reads and writes only inside the chosen folder and its own state folder.

## Development

The application's tests are in `tests/` here and run in the repository's `pytest` run (they are skipped on a Python without `tess_dl`). They use a recorded schema (`tests/fixtures/schema.json`), the `tess_dl` corpus, the shell's shipped files and a fake `tesserae-shell` script written under `tmp_path`; the real shell and the real configuration folder are never touched, and the real-session guard of the repository's tests applies.
