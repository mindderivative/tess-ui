# Tesserae Shell Configuration

`tesserae-shell-config` is the graphical editor for the files of [Tesserae Shell](https://github.com/mindderivative): the shell files, modules, styles, stylesheets, themes and `settings.tdl` in the shell's configuration folder. It is built on Tesserae UI and edits the `.tdl` files in place, so comments, blank lines, order and everything you did not touch stay byte for byte as you wrote them.

This is the fourth part of the application: the window with the Files, Structure, Form, Text and Problems areas, opening and saving, the form for a block's keys, adding, removing, moving and duplicating blocks with undo and redo, `check` and its problems list, "Apply as I edit", the file watch and the shell's status. The stylesheet pages come later.

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
| Structure | The open file's blocks as a tree, with `If` and `For` as labelled nodes (an `If` with an `Else` shows the else body under an `Else` node) | Choosing a row selects that block. Add a child, remove, move up or down, move into another block, duplicate (buttons above the tree, a menu, shortcuts; see below) |
| Problems | The findings of the last `check` (below the three areas): an icon and a word (Error, Warning, Note), `file:line:column`, the message and what to write instead. A message row says when `check` did not run | Click a finding, or Tab to it and press Enter: its file opens, the block it points at is selected and the key's widget in the Form has the focus |
| Text | The file as TDL | Edit it by hand; the structure follows when the text parses. A file with syntax errors is edited here only, with its errors listed (line, column, what is wrong, what to write) |

The toolbar has Save, Undo, Redo, Format file (formatting is never done unless you press it), Check, Reload shell and the switch Apply as I edit. Everything works from the keyboard:

| Keys | Does |
|---|---|
| Tab, Shift+Tab | Move through the toolbar, the Files tree, the Structure tree and the text |
| Arrow keys, Enter | Move in a tree, open or select the row |
| F6, Shift+F6 | Move to the next or previous area (the way out of the text editor, which takes Tab itself); Problems is one of them while it lists something |
| F5 | Run `check` on the folder |
| Ctrl+Shift+R | Ask the running shell to reload (the Reload shell button) |
| Ctrl+Shift+A | Switch Apply as I edit on or off |
| Ctrl+Shift+L, Ctrl+Shift+U | A file changed on disk: reload it from disk, or keep your version (use it) |
| Ctrl+S | Save |
| Ctrl+Z, Ctrl+Y (or Ctrl+Shift+Z) | Undo, redo |
| Ctrl+Shift+N | Add a child to the selected block |
| Delete (in the Structure tree), Ctrl+Shift+Delete | Remove the selected block |
| Alt+Up, Alt+Down | Move the selected block up or down among its siblings |
| Ctrl+Shift+M | Move the selected block into another block |
| Ctrl+Shift+D | Duplicate the selected block |
| Menu key, Shift+F10, a right click in the Structure area | The Structure menu: every action with its shortcut, the ones that cannot be done now dimmed |
| Space or Enter on a switch, button or group header | Toggle it, press it, open or close the group |
| Enter, or Tab out of a field | Write the field's value (nothing is written while you type) |
| Up, Down in a number field | One step of the key's `step`, inside its range |

## The form

Choosing a block (or a setting section, a module call, a theme token group) fills the Form area with its keys, in the schema's groups. Each group is a header; the first group is open, and Enter on a header opens or closes it (the choice is remembered by group name from block to block). One key is one row: its name, the widget of its kind, then the shipped `TokenButton` (it shows the token the key holds with a swatch for a colour, and opens a searchable list of the theme tokens of the groups the key accepts, the schema's `preferred_tokens` first, each with its value; choosing one writes `$group.name`), a `{ }` button for a key that takes an expression (the widget is swapped for a field holding `{{ ... }}`, written as it is) and a reset button (removes the property, so the shell's default applies; disabled while the key is absent). The schema's default is the placeholder; the doc is the row's tooltip and shows under the row that has the focus; a required key that is absent is marked.

| Kind | Widget |
|---|---|
| boolean, enabled | Switch |
| enum | A button that opens a list of the choices (each with its doc where the schema has one) |
| number, whole, percent, duration | A field with the unit as a suffix; a value outside the minimum and maximum is refused with the range, nothing is written and the typed text stays |
| length | A field and a unit button (`px`, `%`, `AUTO`, `EXPAND` from the key's units) |
| sides, radius | One field, or four in the schema's order (Linked/Separate); a blank side is 0 |
| color | The shipped `ColourPicker` (alpha only where the key allows it); written as `"#RRGGBB"` |
| string, name, path | A text field; the schema's `pattern` is checked; a path has a Browse button that opens the shipped `FileDialog` in the key's mode and filters |
| icon | The shipped `IconPicker`: a button with the icon that opens a searchable grid of the built-in icons and the `.svg` and `.png` files of the configuration folder's `Icons/` folder (when it has one); written as the icon's name or the file's name, `"home"`, `"logo.svg"` |
| font | The shipped `FontList`: the installed families (`fc-list : family`), each in its own face; written as one family, `"Roboto"`. A list of families is shown as TDL text and kept |
| key_chord | The shipped `KeyChordField`: press Record and then the keys, or type the chord in any case; written `"Ctrl+Alt+Shift+Meta+Key"` in that order. Text that is not a chord is refused |
| list | The shipped `ListEditor`: a row for each item in the schema's item kind (text, name, number or whole with the key's range, bool, enum with its choices, colour), move and remove buttons and Add; the schema's `length`, `unique` and `one_or_list` apply, and a lone item reads as a list of one. A list the editor cannot show (an item that is a token, say) or an item kind it has no row for is shown as TDL text |
| shadows, block, tooltip, and a kind this version does not know | The value as TDL text (a list of these is in the coverage test) |

A value the widget cannot show (a call, a token reference, a hand-written expression, a list it does not understand) is shown as its TDL text and never rewritten unless you edit it. A style key that is already inside a block's `Style { }` is read and changed there. A property the schema does not name is listed under "Not in the schema". Keys the shell does not build are grouped last; a key TDL reserves (`Key`) cannot be written by `tess_dl`'s edits and says so. In a theme, a token group shows one column for the base and one for each mode the file defines.

## Editing the structure

The row of buttons above the Structure tree, the Structure menu and the shortcuts do the same five things on the selected block. Each is one edit of the file (one undo step), writes only the lines of that entry, and leaves the selection on the block it was on (the block that was moved or copied keeps being the selected one, the copy is not). A button is dimmed when the action cannot be done to the selected block.

| Action | What it does |
|---|---|
| Add child | Opens a list of what the block may hold: the `allowed_children` of its schema entry and, where the block takes module calls, every shipped module. The new block is written with its required keys only, laid out by `tess_dl.format_block` (`Bar` gets `Name: Bar_1`, `Edge`, `Width` and `Height`; a `Box` is `Box { }`); a `Name` is the type and a number no other block of the file has. It goes last. A block the schema does not know has nothing to add |
| Remove | Takes the block with its lines and the comment at the end of its closing line; comment lines above it stay. The selection moves to its parent |
| Move up, Move down | Moves it past the next block, `If` or `For` of its parent (properties and comments between them are not places). A comment line above a block stays where it is, so moving a block and moving it back is not always the same bytes: undo is |
| Move to | Opens a list of the blocks the schema lets hold this one (not the one it is in, not itself or anything below it), each with its place (`Shell › Monitor  Primary › Bar  Top_Bar`); it goes last in the one you pick. This is the keyboard's way to another parent |
| Duplicate | Copies the block's text after it. A `Name:` becomes `Name_Copy`, then `Name_Copy_2`..., so no two blocks of a file share a name. An `If` or `For` cannot be copied here |

A block inside an `If` or `For` can have blocks added to it (and keys changed in the form), but `tess_dl` has no edit that removes, moves or copies the entries of an `If` or `For`: those say so in the status line and change nothing; do them in the text view. An `If` or `For` itself can be removed or moved among its siblings when it is in a block. Undo and redo step through the file's states: a form edit, a structure edit and a run of typing in the text view are one step each, the selection comes back to what it was, and the toolbar's Undo and Redo are dimmed when there is nothing to undo or redo.

## Check, saving and the shell

- **Check.** `tesserae-shell check --json --config-dir <folder>` runs on a worker thread (10 s timeout) after each save, on F5 or the Check button, and the window never waits for it. A check that cannot run or does not answer in time is one message in the list and editing goes on. The check reads the files on disk, so findings are for what is saved; clicking one in a file with unsaved changes says the place may have moved. A file with syntax errors opens in the text view with its errors (there is no structure to select in).
- **Save.** Save writes the open file (atomic, with the first-save backup), then runs `check`. A failed save (a read-only folder, a full disk) leaves the old file whole, keeps your changes in the window and names the cause.
- **Apply as I edit.** A switch in the toolbar, kept in the application's state folder (`settings.json`), off at first. On, each commit (a form value, a structure edit, undo, redo, format) is written at once, typing in the text view once it rests for 200 ms and only when it parses; each write runs `check`. Off, nothing is written until you save.
- **The shell.** The status line says `Shell: running (Top_Bar shown)`, `not running` or `unknown`, from `tesserae-shell status --json`, asked at the start and after each save. After a save the application asks the shell to `reload` only when it is running and Apply as I edit is on; the Reload shell button (enabled while it is running) asks it at any time, for saved files. With no shell running everything else still works.
- **A file changed by another program.** The folder is watched (`watchfiles`, on a worker thread). When the open file's content on disk is not what this application last read or wrote, a banner asks **Reload** (take the disk's version, your unsaved changes for that file are dropped and its undo history starts over) or **Keep mine** (the next save replaces the disk's). The application's own saves never ask. A save over a file that changed is refused until you choose, even when the watch was late, so nothing is overwritten silently.

## What it keeps and what it never does

- Opening a file and saving it without a change leaves it byte for byte the same (a byte order mark, CRLF or a missing final newline included).
- A save writes a temporary file in the same folder and renames it over the old one, so a refused write or a full disk leaves the old file whole, and the message names the cause. It never writes over a file another program changed since it was read or written here.
- Before the first save of a file in a session, its old content is copied to `backups/` in the application's own state folder (`$XDG_STATE_HOME/tesserae-shell-config`).
- It reads and writes only inside the chosen folder and its own state folder.

## Development

The application's tests are in `tests/` here and run in the repository's `pytest` run (they are skipped on a Python without `tess_dl`). They use a recorded schema (`tests/fixtures/schema.json`, schema 1.2) and the recorded `check`, `status` and `version` answers (`tests/fixtures/recorded/`), the `tess_dl` corpus, the shell's shipped files and a fake `tesserae-shell` script written under `tmp_path` that prints those answers; the real shell and the real configuration folder are never touched, and the real-session guard of the repository's tests applies.

`tools/perf.py` measures the two budgeted actions (selecting a block, one committed edit) on a headless window over a temporary copy of the test configuration: `PYTHONPATH=src:apps/shell_config/src python apps/shell_config/tools/perf.py`. `tests/test_shell_config_perf.py` asserts the counts that make them fast: the window is composed once for each.
