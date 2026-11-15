# File dialog

*Containment*

## In Material Design 3

Material Design 3 has no file dialog: a desktop app needs one, and it is built from the parts MD3 does describe, a modal dialog over a scrim, a list, text fields, buttons and a menu.

## In Tesserae

`FileDialog` is a view Tesserae ships (`FileDialog_View.tdl`): a modal [`Overlay`](../guide/view-language.md#overlays) holding a panel (28 pixel corners, 24 of padding, as a
[dialog](dialogs.md) has) for choosing files and folders inside the app, with no window of the operating system. `Mode` is `open` (existing files: one, or several with `multiple`),
`save` (a folder and a name) or `folder` (a folder). `Open` is two-way: Escape and a press on the scrim write `false` back and call `On_Cancel`; so does Cancel. OK is off until
there is something to give. Pressing it writes `Value`, the absolute path as text (a list of paths when `multiple`), closes the dialog and calls `On_Accept`. Nothing is read from the disk until
`Open` goes true, and each opening starts again at `Start` with the folder as it is then.

What it shows. A path bar (a text field: type a path, or `~`, and press Enter; one that is not a folder says so under the list) with Back, Forward, Up, Home and Refresh, and under it the
folders of the path as buttons. A list of the folder with a column of names, one of sizes and one of times: folders first, then files, each sorted without regard to case. A switch for the
names that start with a dot (off unless `Show_Hidden`). `Filters` is the file types, each `{label, patterns: ["*.tdl"]}`; an `All files` choice always follows them, the first is the one in
use (`Filter` says another), and a type hides the files that do not match (case does not count) and never a folder. With only `All files` there is no type button. In a `folder` dialog only folders
are listed. `New folder` is offered when saving and when choosing a folder: it asks for a name and makes the folder, and it is picked.

Picking. A press picks a row; Ctrl and Shift (with `multiple`) flip and extend the picks. A folder is entered by pressing it twice (or Enter on it), a file chosen the same way. In an open dialog a
folder is never an answer; in a folder dialog nothing picked means the folder shown. When saving, the file name field starts with `Filename`, picking a file puts its name there, and a name with no
extension gets the one of the file type in use (`*.tdl` gives `.tdl`; `All files` adds none). A name with a `/` or `\`, or the name of a folder, is a problem the dialog says; a name that is a file already asks
"Replace file?" before it answers. The dialog never writes the file: it only says which.

`Root` keeps it inside a folder: the path bar, Up, Back, Home and the trail cannot leave it, nor can a link inside it that leads out. `Start` is the folder it opens in (`Root`, then the working folder, when left
out); a start that cannot be read opens the nearest folder above it and says why. A folder that cannot be read (permission denied), has gone, or is a file is a message in red under the list, and the dialog
stays where it was, usable; it never raises.

The keyboard. The list has the focus when the dialog opens. Up, Down, Page Up, Page Down, Home and End move the cursor row and pick it (Shift extends, with `multiple`); Enter opens the row; Backspace goes up;
Alt+Left and Alt+Right are Back and Forward; Ctrl+A picks every file (with `multiple`); letters jump to the next name that starts with them. The list scrolls to keep the cursor in view. A screen reader
hears a `dialog` named by `Headline` (`Open file`, `Save file` or `Choose folder` when left out), a `list` of `listitem`s each named by its file and `Selected` when picked, labelled buttons, and an `alert` for a message.

The list is a `VirtualList`: it builds only the rows in view (`Rows` of them, 8 by default, and three past each edge), and a folder is read once, when entered, with one listing and one `stat` for each entry,
so a folder of ten thousand files opens at once. The disk is reached only through `tess_ui.filesystem` (`FileSystem`: `list_dir`, `is_dir`, `exists`, `make_dir`, `real_path`, `home`, `cwd`), which `filesystem.use()`
swaps for a test or for something that is not a disk. What the dialog keeps (the folder, the history, the picks, the rules above) is `tess_ui.file_browser.FileBrowser`, which has no window and can be used
alone; the view reaches it through `FileBrowser`, a control that draws nothing (`tess_ui.file_controls`).

The look is in `FileDialog_Stylesheet.tdl`: write one in your project to change the panel, the rows and the message. Not built: bookmarks and a places sidebar, a preview, drag and drop, renaming and deleting,
sorting by a column, a column for the file type, hidden attributes other than a leading dot (Windows' hidden flag), a folder tree, drives on their own (a Windows drive letter is the first step of the trail).

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `FileDialog { ... }`. A file of the same name in your project replaces it.

### `FileDialog`

The file dialog: a modal panel over a scrim for choosing a file to open (`Mode: open`, one or, with `Multiple`, several), a folder and a name to save under (`Mode: save`, which asks before it writes over a file that is there), or a folder (`Mode: folder`). A path bar (type a path and press Enter) and the folders of the path as buttons; Back, Forward, Up and Home; a list of the folder's entries, folders first and then files, each sorted without regard to case, with their sizes and times; a switch for the names that start with a dot; the file types (`Filters`, each {label, patterns}; an `All files` choice follows them) that hide the files that do not match and never a folder; and, when saving or choosing a folder, a button that makes a new folder. `Root` is a folder it never leaves. `Value` is two-way and gets the answer when OK is pressed: the path as text, or a list of paths when `Multiple`; `On_Accept` is called after it is written and `On_Cancel` when Escape, Cancel or a press outside closes it instead. Nothing is read from the disk until `Open` goes true, and only the folder shown is read. The keyboard in the list: Up, Down, Page Up, Page Down, Home and End move; Enter opens the folder or chooses the file; Backspace goes Up; Alt+Left and Alt+Right are Back and Forward; typing jumps to the next name that starts with it; Ctrl+A picks all when `Multiple`; Shift and Ctrl with a press or an arrow extend or flip the picks. The list shows `Rows` rows at a time and builds only those (a folder of ten thousand entries opens at once). The disk is read through `tess_ui.filesystem`. What the parts do is in the FileBrowser control (`tess_ui.file_controls`), which this view drives by writing a numbered command to `cmd` and reading what comes back.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Open` | `bool` | `false` | Whether it is showing; Escape and a press outside write false. Two-way: give it a bare reference and the view writes it back. |
| `Mode` | `open` or `save` or `folder` | `open` | open picks existing files; save picks a folder and a name; folder picks a folder. |
| `Headline` | `str` |  | The title; `Open file`, `Save file` or `Choose folder` when left out. |
| `Accept_Label` | `str` |  | The label of the OK button; `Open`, `Save` or `Choose` when left out. |
| `Multiple` | `bool` | `false` | More than one file (or folder) may be picked; `Value` is then a list. |
| `Start` | `str` |  | The folder it opens in; the root, else the working folder, when left out. |
| `Root` | `str` |  | A folder it never leaves: nothing above it can be entered. |
| `Filters` | `list` | `[]` | The file types, each {label, patterns: [glob, ...]}, such as {label: TDL files, patterns: ['*.tdl']}; `All files` is added after them. |
| `Filter` | `int` | `0` | The number of the file type it opens with. |
| `Show_Hidden` | `bool` | `false` | Whether names that start with a dot are listed when it opens; the person can switch them. |
| `Filename` | `str` |  | A save dialog's starting file name. A name typed with no extension gets the one the file type gives (`*.tdl` gives `.tdl`). |
| `Rows` | `int`, 3 to 20 | `8` | How many rows of the list show at once. |
| `Width` | `float`, 480 to 1080 | `720` | How wide the panel is. |
| `Value` | `any` |  | The answer, written when OK is pressed: the absolute path as text, or a list of paths when `Multiple`. Two-way: give it a bare reference and the view writes it back. |
| `On_Accept` | `handler` |  | Called after `Value` has been written and the dialog has closed. |
| `On_Cancel` | `handler` |  | Called when the dialog is closed without an answer. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `panel` (Container), `browser` (FileBrowser), `headline` (Text), `toolbar` (Container), `back` (IconButton), `forward` (IconButton), `up` (IconButton), `home` (IconButton), `refresh` (IconButton), `path_field` (TextField), `crumbs` (Container), `crumb` (Container), `crumb_gap` (Icon), `crumb_button` (Button), `columns` (Container), `column_icon` (Container), `column_name_cell` (Container), `column_name` (Text), `column_size` (Text), `column_modified` (Text), `list_group` (Container), `list_box` (Container), `list` (VirtualList), `row` (Container), `row_icon` (Icon), `row_name_cell` (Container), `row_name` (Text), `row_size` (Text), `row_modified` (Text), `empty` (Text), `message_text` (Text), `new_folder_row` (Container), `new_folder_field` (TextField), `new_folder_make` (Button), `new_folder_cancel` (Button), `filename_field` (TextField), `options` (Container), `show_hidden_box` (Checkbox), `new_folder_button` (Button), `spacer` (Container), `filter_button` (Button), `filter_menu` (Menu), `actions` (Container), `cancel` (Button), `accept` (Button), `replace` (Overlay), `replace_panel` (Container), `replace_headline` (Text), `replace_body` (Text), `replace_actions` (Container), `replace_cancel` (Button), `replace_yes` (Button).

Its look is in [`FileDialog_Stylesheet.tdl`](../stylesheets/file-dialogs/file-dialog.md).

### `FileBrowser`

The file dialog's mind: it draws nothing. It reads folders through `tess_ui.filesystem`, keeps the history, the selection and the rules, and tells the view through the names it is bound to.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Mode` | `open` or `save` or `folder` | `open` | `Open` picks existing files, `save` a folder and a name, `Folder` a folder. |
| `Multiple` | `bool` |  | More than one file (or folder) may be picked. |
| `Start` | `str` |  | The folder it opens in; the root, else the working folder, when left out. |
| `Root` | `str` |  | A folder it never leaves: nothing above it can be entered. |
| `Filters` | `list` | `[]` | The file types: each {label, patterns: [glob, ...]}; an `All files` choice is added. |
| `Open` | `bool` |  | Whether the dialog is showing: going true makes a new browser at `Start`; nothing is read from the disk before. |
| `Initial` | `str` |  | The file name a save starts with. |
| `Rows` | `int` | `8` | How many rows the list shows at once (for Page Up and Page Down and for scrolling the cursor into view). |
| `Row_Height` | `float` | `40.0` | How tall a row is, in pixels. |
| `Command` | `str` |  | What to do, written as text that starts with a number that is new each time: `7 click 3 ctrl`, `8 key arrow_down`, `9 up`, `10 back`, `11 forward`, `12 home`, `13 refresh`, `14 goto` (the text in `Path`), `15 open 3`, `16 accept`, `17 new_folder Name`, `18 confirmed`. |
| `Path` | `str` |  | The text of the path bar: it follows the folder, and `goto` goes to what was typed. Two-way. |
| `Filename` | `str` |  | The name typed in a save dialog; picking a file there puts its name here. Two-way. |
| `Hidden` | `bool` |  | Whether names that start with a dot are listed. Two-way. |
| `Filter` | `int` |  | The number of the file type in use. Two-way. |
| `Scroll` | `float` |  | The list's scroll offset: bind the list's `Scroll_Offset` to the same name; moving the cursor writes the offset that shows it. Two-way. |
| `Confirm` | `bool` |  | A save of a file that is there is waiting for a yes; the view writes false to cancel it. Two-way. |
| `Entries` | `list` |  | Output: written to the name it is bound to. The rows shown: {name, path, dir, icon, size, modified, hidden}, folders first. Two-way. |
| `Selection` | `list` |  | Output: written to the name it is bound to. The paths picked. Two-way. |
| `Cursor` | `int` |  | Output: written to the name it is bound to. The row the keyboard is on, or -1. Two-way. |
| `Folder` | `str` |  | Output: written to the name it is bound to. The folder being shown. Two-way. |
| `Crumbs` | `list` |  | Output: written to the name it is bound to. The folder as a trail: each {name, path}. Two-way. |
| `Message` | `str` |  | Output: written to the name it is bound to. What last went wrong, such as a folder that cannot be read; empty when nothing has. Two-way. |
| `Valid` | `bool` |  | Output: written to the name it is bound to. Whether OK may be pressed. Two-way. |
| `Target` | `list` |  | Output: written to the name it is bound to. The paths OK would give. Two-way. |
| `Chosen` | `str` |  | Output: written to the name it is bound to. The name (the last part) of the first of `Target`. Two-way. |
| `Exists` | `bool` |  | Output: written to the name it is bound to. A save whose file is there already. Two-way. |
| `Problem` | `str` |  | Output: written to the name it is bound to. Why the save name will not do. Two-way. |
| `Can_Back` | `bool` |  | Output: written to the name it is bound to. Two-way. |
| `Can_Forward` | `bool` |  | Output: written to the name it is bound to. Two-way. |
| `Can_Up` | `bool` |  | Output: written to the name it is bound to. Two-way. |
| `Filter_Items` | `list` |  | Output: written to the name it is bound to. The file types as menu items: {value, label}. Two-way. |

## Using it

```tdl
Container {
  Name: documents
  Style { Flex_Direction: vertical, Width: 900, Height: 700 }
  Children {
    Button {
      Name: choose
      Label: "Open a plan"
      Handlers {
        On_Click { Set { Target: choosing, Value: <| True |> } }
      }
    }
    FileDialog {
      Open: <| choosing |>
      Mode: open
      Start: "~/Documents"
      Filters {
        Item { Label: "TDL files", Patterns: ["*.tdl"] }
        Item { Label: Text, Patterns: ["*.txt", "*.md"] }
      }
      Value: <| plan |>
      On_Accept: load_plan
    }
  }
}
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

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# FileDialog_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: FileDialog
    Part: panel
    Style { Background: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Overlays](../guide/overlays.md)
- [Dialogs](../components/dialogs.md)
- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
