# File dialog

*Containment*

## In Material Design 3

Material Design 3 has no file dialog: a desktop app needs one, and it is built from the parts MD3 does describe, a modal dialog over a scrim, a list, text fields, buttons and a menu.

## In Tesserae

`widget: FileDialog` is a view Tesserae ships (`FileDialog_View.yaml`): a modal [`Overlay`](../guide/view-language.md#overlays) holding a panel (28 pixel corners, 24 of padding, as a
[dialog](dialogs.md) has) for choosing files and folders inside the app, with no window of the operating system. `mode` is `open` (existing files: one, or several with `multiple`),
`save` (a folder and a name) or `folder` (a folder). `open` is two-way: Escape and a press on the scrim write `false` back and call `on_cancel`; so does Cancel. OK is off until
there is something to give. Pressing it writes `value`, the absolute path as text (a list of paths when `multiple`), closes the dialog and calls `on_accept`. Nothing is read from the disk until
`open` goes true, and each opening starts again at `start` with the folder as it is then.

What it shows. A path bar (a text field: type a path, or `~`, and press Enter; one that is not a folder says so under the list) with Back, Forward, Up, Home and Refresh, and under it the
folders of the path as buttons. A list of the folder with a column of names, one of sizes and one of times: folders first, then files, each sorted without regard to case. A switch for the
names that start with a dot (off unless `show_hidden`). `filters` is the file types, each `{label, patterns: ["*.tdl"]}`; an `All files` choice always follows them, the first is the one in
use (`filter` says another), and a type hides the files that do not match (case does not count) and never a folder. With only `All files` there is no type button. In a `folder` dialog only folders
are listed. `New folder` is offered when saving and when choosing a folder: it asks for a name and makes the folder, and it is picked.

Picking. A press picks a row; Ctrl and Shift (with `multiple`) flip and extend the picks. A folder is entered by pressing it twice (or Enter on it), a file chosen the same way. In an open dialog a
folder is never an answer; in a folder dialog nothing picked means the folder shown. When saving, the file name field starts with `filename`, picking a file puts its name there, and a name with no
extension gets the one of the file type in use (`*.tdl` gives `.tdl`; `All files` adds none). A name with a `/` or `\`, or the name of a folder, is a problem the dialog says; a name that is a file already asks
"Replace file?" before it answers. The dialog never writes the file: it only says which.

`root` keeps it inside a folder: the path bar, Up, Back, Home and the trail cannot leave it, nor can a link inside it that leads out. `start` is the folder it opens in (`root`, then the working folder, when left
out); a start that cannot be read opens the nearest folder above it and says why. A folder that cannot be read (permission denied), has gone, or is a file is a message in red under the list, and the dialog
stays where it was, usable; it never raises.

The keyboard. The list has the focus when the dialog opens. Up, Down, Page Up, Page Down, Home and End move the cursor row and pick it (Shift extends, with `multiple`); Enter opens the row; Backspace goes up;
Alt+Left and Alt+Right are Back and Forward; Ctrl+A picks every file (with `multiple`); letters jump to the next name that starts with them. The list scrolls to keep the cursor in view. A screen reader
hears a `dialog` named by `headline` (`Open file`, `Save file` or `Choose folder` when left out), a `list` of `listitem`s each named by its file and `selected` when picked, labelled buttons, and an `alert` for a message.

The list is a `VirtualList`: it builds only the rows in view (`rows` of them, 8 by default, and three past each edge), and a folder is read once, when entered, with one listing and one `stat` for each entry,
so a folder of ten thousand files opens at once. The disk is reached only through `tess_ui.filesystem` (`FileSystem`: `list_dir`, `is_dir`, `exists`, `make_dir`, `real_path`, `home`, `cwd`), which `filesystem.use()`
swaps for a test or for something that is not a disk. What the dialog keeps (the folder, the history, the picks, the rules above) is `tess_ui.file_browser.FileBrowser`, which has no window and can be used
alone; the view reaches it through `widget: FileBrowser`, a control that draws nothing (`tess_ui.file_controls`).

The look is in `FileDialog_Stylesheet.yaml`: write one in your project to change the panel, the rows and the message. Not built: bookmarks and a places sidebar, a preview, drag and drop, renaming and deleting,
sorting by a column, a column for the file type, hidden attributes other than a leading dot (Windows' hidden flag), a folder tree, drives on their own (a Windows drive letter is the first step of the trail).

## How it is built

A view Tesserae ships is a `<Name>_View.yaml` (what it takes and what it is made of) with a `<Name>_Stylesheet.yaml` (how it looks). Use it by name: `widget: FileDialog`. A file of the same name in your project replaces it.

### `FileDialog`

The file dialog: a modal panel over a scrim for choosing a file to open (`mode: open`, one or, with `multiple`, several), a folder and a name to save under (`mode: save`, which asks before it writes over a file that is there), or a folder (`mode: folder`). A path bar (type a path and press Enter) and the folders of the path as buttons; Back, Forward, Up and Home; a list of the folder's entries, folders first and then files, each sorted without regard to case, with their sizes and times; a switch for the names that start with a dot; the file types (`filters`, each {label, patterns}; an `All files` choice follows them) that hide the files that do not match and never a folder; and, when saving or choosing a folder, a button that makes a new folder. `root` is a folder it never leaves. `value` is two-way and gets the answer when OK is pressed: the path as text, or a list of paths when `multiple`; `on_accept` is called after it is written and `on_cancel` when Escape, Cancel or a press outside closes it instead. Nothing is read from the disk until `open` goes true, and only the folder shown is read. The keyboard in the list: Up, Down, Page Up, Page Down, Home and End move; Enter opens the folder or chooses the file; Backspace goes Up; Alt+Left and Alt+Right are Back and Forward; typing jumps to the next name that starts with it; Ctrl+A picks all when `multiple`; Shift and Ctrl with a press or an arrow extend or flip the picks. The list shows `rows` rows at a time and builds only those (a folder of ten thousand entries opens at once). The disk is read through `tess_ui.filesystem`. What the parts do is in the FileBrowser control (`tess_ui.file_controls`), which this view drives by writing a numbered command to `cmd` and reading what comes back.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `open` | `bool` | `false` | Whether it is showing; Escape and a press outside write false. Two-way: give it a bare reference and the view writes it back. |
| `mode` | `open` or `save` or `folder` | `open` | open picks existing files; save picks a folder and a name; folder picks a folder. |
| `headline` | `str` |  | The title; `Open file`, `Save file` or `Choose folder` when left out. |
| `accept_label` | `str` |  | The label of the OK button; `Open`, `Save` or `Choose` when left out. |
| `multiple` | `bool` | `false` | More than one file (or folder) may be picked; `value` is then a list. |
| `start` | `str` |  | The folder it opens in; the root, else the working folder, when left out. |
| `root` | `str` |  | A folder it never leaves: nothing above it can be entered. |
| `filters` | `list` | `[]` | The file types, each {label, patterns: [glob, ...]}, such as {label: TDL files, patterns: ['*.tdl']}; `All files` is added after them. |
| `filter` | `int` | `0` | The number of the file type it opens with. |
| `show_hidden` | `bool` | `false` | Whether names that start with a dot are listed when it opens; the person can switch them. |
| `filename` | `str` |  | A save dialog's starting file name. A name typed with no extension gets the one the file type gives (`*.tdl` gives `.tdl`). |
| `rows` | `int`, 3 to 20 | `8` | How many rows of the list show at once. |
| `width` | `float`, 480 to 1080 | `720` | How wide the panel is. |
| `value` | `any` |  | The answer, written when OK is pressed: the absolute path as text, or a list of paths when `multiple`. Two-way: give it a bare reference and the view writes it back. |
| `on_accept` | `handler` |  | Called after `value` has been written and the dialog has closed. |
| `on_cancel` | `handler` |  | Called when the dialog is closed without an answer. |

Its parts, by name (a stylesheet rule's `part:` or `name:` addresses one): `panel` (Container), `browser` (FileBrowser), `headline` (Text), `toolbar` (Container), `back` (IconButton), `forward` (IconButton), `up` (IconButton), `home` (IconButton), `refresh` (IconButton), `path_field` (TextField), `crumbs` (Container), `crumb` (Container), `crumb_gap` (Icon), `crumb_button` (Button), `columns` (Container), `column_icon` (Container), `column_name_cell` (Container), `column_name` (Text), `column_size` (Text), `column_modified` (Text), `list_group` (Container), `list_box` (Container), `list` (VirtualList), `row` (Container), `row_icon` (Icon), `row_name_cell` (Container), `row_name` (Text), `row_size` (Text), `row_modified` (Text), `empty` (Text), `message_text` (Text), `new_folder_row` (Container), `new_folder_field` (TextField), `new_folder_make` (Button), `new_folder_cancel` (Button), `filename_field` (TextField), `options` (Container), `show_hidden_box` (Checkbox), `new_folder_button` (Button), `spacer` (Container), `filter_button` (Button), `filter_menu` (Menu), `actions` (Container), `cancel` (Button), `accept` (Button), `replace` (Overlay), `replace_panel` (Container), `replace_headline` (Text), `replace_body` (Text), `replace_actions` (Container), `replace_cancel` (Button), `replace_yes` (Button).

Its look is in [`FileDialog_Stylesheet.yaml`](../stylesheets/file-dialogs/file-dialog.md).

### `FileBrowser`

The file dialog's mind: it draws nothing. It reads folders through `tess_ui.filesystem`, keeps the history, the selection and the rules, and tells the view through the names it is bound to.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `mode` | `open` or `save` or `folder` | `open` | `open` picks existing files, `save` a folder and a name, `folder` a folder. |
| `multiple` | `bool` |  | More than one file (or folder) may be picked. |
| `start` | `str` |  | The folder it opens in; the root, else the working folder, when left out. |
| `root` | `str` |  | A folder it never leaves: nothing above it can be entered. |
| `filters` | `list` | `[]` | The file types: each {label, patterns: [glob, ...]}; an `All files` choice is added. |
| `open` | `bool` |  | Whether the dialog is showing: going true makes a new browser at `start`; nothing is read from the disk before. |
| `initial` | `str` |  | The file name a save starts with. |
| `rows` | `int` | `8` | How many rows the list shows at once (for Page Up and Page Down and for scrolling the cursor into view). |
| `row_height` | `float` | `40.0` | How tall a row is, in pixels. |
| `command` | `str` |  | What to do, written as text that starts with a number that is new each time: `7 click 3 ctrl`, `8 key arrow_down`, `9 up`, `10 back`, `11 forward`, `12 home`, `13 refresh`, `14 goto` (the text in `path`), `15 open 3`, `16 accept`, `17 new_folder Name`, `18 confirmed`. |
| `path` | `str` |  | The text of the path bar: it follows the folder, and `goto` goes to what was typed. Two-way. |
| `filename` | `str` |  | The name typed in a save dialog; picking a file there puts its name here. Two-way. |
| `hidden` | `bool` |  | Whether names that start with a dot are listed. Two-way. |
| `filter` | `int` |  | The number of the file type in use. Two-way. |
| `scroll` | `float` |  | The list's scroll offset: bind the list's `scroll_offset` to the same name; moving the cursor writes the offset that shows it. Two-way. |
| `confirm` | `bool` |  | A save of a file that is there is waiting for a yes; the view writes false to cancel it. Two-way. |
| `entries` | `list` |  | Output: written to the name it is bound to. The rows shown: {name, path, dir, icon, size, modified, hidden}, folders first. Two-way. |
| `selection` | `list` |  | Output: written to the name it is bound to. The paths picked. Two-way. |
| `cursor` | `int` |  | Output: written to the name it is bound to. The row the keyboard is on, or -1. Two-way. |
| `folder` | `str` |  | Output: written to the name it is bound to. The folder being shown. Two-way. |
| `crumbs` | `list` |  | Output: written to the name it is bound to. The folder as a trail: each {name, path}. Two-way. |
| `message` | `str` |  | Output: written to the name it is bound to. What last went wrong, such as a folder that cannot be read; empty when nothing has. Two-way. |
| `valid` | `bool` |  | Output: written to the name it is bound to. Whether OK may be pressed. Two-way. |
| `target` | `list` |  | Output: written to the name it is bound to. The paths OK would give. Two-way. |
| `chosen` | `str` |  | Output: written to the name it is bound to. The name (the last part) of the first of `target`. Two-way. |
| `exists` | `bool` |  | Output: written to the name it is bound to. A save whose file is there already. Two-way. |
| `problem` | `str` |  | Output: written to the name it is bound to. Why the save name will not do. Two-way. |
| `can_back` | `bool` |  | Output: written to the name it is bound to. Two-way. |
| `can_forward` | `bool` |  | Output: written to the name it is bound to. Two-way. |
| `can_up` | `bool` |  | Output: written to the name it is bound to. Two-way. |
| `filter_items` | `list` |  | Output: written to the name it is bound to. The file types as menu items: {value, label}. Two-way. |

## Using it

```yaml
name: documents
widget: Container
style: {flex_direction: vertical, width: 900, height: 700}
children:
  - widget: Button
    name: choose
    label: Open a plan
    handlers: {on_click: "choosing = True"}
  - widget: FileDialog
    open: "{{ choosing }}"
    mode: open
    start: ~/Documents
    filters:
      - {label: TDL files, patterns: ["*.tdl"]}
      - {label: Text, patterns: ["*.txt", "*.md"]}
    value: "{{ plan }}"
    on_accept: load_plan
```

## Using it in Python

```python
from tess_ui import Signal, ViewModel
from tess_ui.file_dialog import FileDialogRequest


class DocumentsViewModel(ViewModel):
    views = "documents"

    def __init__(self):
        super().__init__()
        self.files = FileDialogRequest(self)      # file_open, file_mode, file_start, ... and file_accepted, file_cancelled

    def save_as(self):
        self.files.show(mode="save", filters=[{"label": "TDL files", "patterns": ["*.tdl"]}], filename="plan",
                        on_accept=lambda paths: print("save to", paths[0]))
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.yaml` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `style:` beats every rule:

```yaml
# FileDialog_Stylesheet.yaml, or any stylesheet your app loads
styles:
  - widget: FileDialog
    part: panel
    style: {background: tertiary}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Dialogs](../components/dialogs.md)
- [Python API reference](../api/python.md)
- [YAML reference](../api/yaml.md)
