# Tesserae Shell Configuration

`tesserae-shell-config` is the graphical editor for the files of [Tesserae Shell](https://github.com/mindderivative): the shell files, modules, styles, stylesheets, themes and `settings.tdl` in the shell's configuration folder. It is built on Tesserae UI and edits the `.tdl` files in place, so comments, blank lines, order and everything you did not touch stay byte for byte as you wrote them.

The window has the Files, Structure, Form, Text and Problems areas; it opens and saves files, builds the form of a block's keys from the schema, adds, removes, moves and duplicates blocks with undo and redo, runs `check` and lists its findings, applies as you edit, watches the files, and has pages for themes, stylesheets and settings, module calls (the shipped modules and your own), a Files area that makes, copies, renames and deletes files, and the keyboard map below. The user guide (with pictures) is in the Tesserae UI documentation, `guide/shell-config.md`.

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
| Tab, Shift+Tab | Move through the toolbar, the Files tree, the Structure tree, the form and the text |
| Arrow keys, Enter | Move in a tree, open or select the row |
| Space, Enter | Toggle a switch, press a button, open or close a group of keys |
| Enter, or Tab out of a field | Write the field's value (nothing is written while you type) |
| Up, Down (in a number field) | One step of the key's `step`, inside its range |
| Escape | Close a list, a menu or a dialog |
| Ctrl+S | Save the open file |
| Ctrl+Z | Undo |
| Ctrl+Y, Ctrl+Shift+Z | Redo |
| F6, Shift+F6 | Move the focus to the next, or the previous, of the areas: Files, Structure, Form, Text, and Problems when it lists something |
| F5 | Run `check` on the folder (the Check button) |
| Ctrl+Shift+R | Ask the running shell to reload (Reload shell) |
| Ctrl+Shift+A | Switch "Apply as I edit" on or off |
| Ctrl+Shift+L, Ctrl+Shift+U | The file changed on disk: reload it from disk (L), or use your version, Keep mine (U; Ctrl+K and Ctrl+J are the text editor's own) |
| Ctrl+N | A new file from a type (a list of the types, then a name) |
| F2 | Rename the file chosen in the Files area |
| Ctrl+Alt+D | Duplicate the file chosen in the Files area |
| Delete (in the Files area) | Delete the file: it moves to the trash folder of the state folder |
| Ctrl+Shift+N | Add a child to the selected block (a list of the blocks the schema lets it hold) |
| Delete (in the Structure tree), Ctrl+Shift+Delete | Remove the selected block |
| Alt+Up, Alt+Down | Move the selected block up or down among its siblings |
| Ctrl+Shift+M | Move the selected block into another block, chosen from a list |
| Ctrl+Shift+D | Duplicate the selected block (a `Name:` becomes a name no other block has) |
| Menu key, Shift+F10 | The Structure menu, with every action and its shortcut |

A right click in the Structure area opens the same menu. Every area, button, form row and menu entry has an accessible name, and a description (the key's doc line for a form row).

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
| shadows, block | A button: **Add** writes the block (`Shadows { }`, `Inner_Border { ... }`) with its required keys, **Open** chooses it in the Structure (its own keys and children are edited there), Reset removes it. A token reference the key takes instead (`Shadows: $elevation.max`) is shown as TDL text |
| tooltip, and a kind this version does not know | The value as TDL text: a tooltip is a Popup's name (a bare word), a short quoted text or an inline block, which what is typed does not say (the coverage test lists these with the reason of each) |

A value the widget cannot show (a call, a token reference, a hand-written expression, a list it does not understand) is shown as its TDL text and never rewritten unless you edit it. A style key that is already inside a block's `Style { }` is read and changed there. A property the schema does not name is listed under "Not in the schema". Keys the shell does not build are grouped last; a key TDL reserves (`Key`) cannot be written by `tess_dl`'s edits and says so. In a theme, a token group shows one column for the base and one for each mode the file defines.

## Themes, stylesheets and settings

- **A theme file.** Choose a token group (`Color`, `Type`, `Shape`, `Space`, `Elevation`, `Motion`) in the Structure: the Form lists the group's tokens (from the schema's `tokens` table) with a column for the base and one for each mode the file defines under `Modes`; a colour token has a swatch in each column. **Add child** on the theme offers the token groups the file lacks and `Modes`; on `Modes` it offers the modes (Light, Dark, High_Contrast, Reduced_Motion), and a new mode is a new column; removing the mode's block removes the column.
- **A stylesheet.** The Structure lists the `Rule`s in the order they are written, each with its selector (`Rule  Text:hovered`); order decides ties, so Move up and Move down (Alt+Up, Alt+Down) reorder. The Form of a rule starts with the **selector builder**: Applies to (a block or module name, a class, a name), Target, Part (`Module::part`, modules only) and State (`hovered`, `pressed`, `disabled`, `selected`, `checked`, `focused`); each change writes the whole `Selector:`. The style keys below are those of the selector's block type (a module's root block for a module name), every style key for a class or a name; a key the rule already has stays shown. A selector the builder cannot read (a descendant, a state the shell does not know) is shown as written with the union of style keys.
- **settings.tdl.** Each section (`Logging`, `Validation`, `Appearance`, `Directories`, `Debug`, and `Shortcuts` when the shell exports it) is a page: choose it in the Structure. A section the file lacks is in the **Add child** list of the root block.
- **Popups.** A `Popup` named like a default popup of the schema's `popups` table (`Tray_Menu`...) says which module opens it and that it replaces that popup whole, and shows its values (`Attach`, `Alignment`, `Gap`, `Max_Height`) as placeholders; any other `Popup` is told the names it could take.

## Module calls

The **Add child** list of a block that takes module calls has every module of the schema's `modules` table and then **your own modules**: every module file under the folder's `Modules/` folder, whose `Params` block the application reads with `tess_dl` (`name { Type: string, Default: "world" }` or `Param { Name: ..., Type: ... }`). A user module's params show with their name and `type ...` and no doc line (the file has none); a `Type` that is not a schema kind (`boolean`, `int` and `float` are mapped) gets the generic TDL field. A shipped module is never replaced by a user module of its name. The form of a call is the module's params (type, default, doc), then the keys every module takes.

## The Files area

Above the Files tree: **New** (Ctrl+N: the type, then a name; the file is `Name_Type.tdl` in its type's folder, a module in a folder of its own name, with its metadata block and an empty root block; `settings.tdl` asks for no name and exists once), **Duplicate** (Ctrl+Alt+D; the metadata `Name` follows the new name), **Rename** (F2; the file moves, a module's folder too, and its `Name` follows) and **Delete** (Delete in the Files area). A delete moves the file to `trash/<time>/<path>` in the application's state folder and never removes it; a rename keeps the old file there too. A name is letters, digits and `_`, starting with a letter; a name in use is refused with the reason, in the prompt. A file with unsaved changes is not renamed or deleted (save or undo first); a copy is of the saved file. A folder of more than 12 files starts with only the open file's group open in the Files tree.

## Editing the structure

The row of buttons above the Structure tree, the Structure menu and the shortcuts do the same five things on the selected block (a theme, a mode and a settings root offer their own children: see above). Each is one edit of the file (one undo step), writes only the lines of that entry, and leaves the selection on the block it was on (the block that was moved or copied keeps being the selected one, the copy is not). A button is dimmed when the action cannot be done to the selected block.

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

`tests/test_shell_config_acceptance.py` holds the criteria that need the whole application (the shipped default configuration opens with no finding, byte-for-byte opening of every shipped file, ranges and tokens over the whole schema, one key-only pass), `tests/test_shell_config_a11y.py` the names, descriptions and Tab order. `tools/perf.py` measures the two budgeted actions (selecting a block, one committed edit) on a headless window over a temporary copy of the test configuration: `PYTHONPATH=src:apps/shell_config/src python apps/shell_config/tools/perf.py`. `tests/test_shell_config_perf.py` asserts the counts that make them fast: the window is composed once for each.
