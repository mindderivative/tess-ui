# Trees

*Containment*

## In Material Design 3

Material Design 3 has no tree view; this is MD3's list row, indented by depth, with a chevron on the rows
that open.

## In Tesserae

Views Tesserae ships: `Tree` (the whole tree from data), and `TreeNode` (one row, a branch with a chevron or a leaf). The rows are one flat list (`tree_rows(nodes, expanded)`):
the children of an open branch follow it.

The `Nodes` are rows, `{Value, Label}` and optionally `{Icon, children, Disabled}`, where `children` is a list of the same shape. `Expanded` (the values of the open branches)
and `Selected` (the value of the chosen row) are two-way. Rows are 56 pixels tall, or 40 with `Compact`.

A row is indented 16 pixels plus 24 for each level, has a 24 pixel chevron that turns a quarter when its branch opens (a leaf keeps the room), an optional icon and a `body_large`
label; the chosen row is `secondary_container`. A press chooses a row and opens or closes a branch. One Tab stop; the up and down arrows move through the rows that show, Right
opens a branch and Left closes it, and typing the start of a label jumps to a row. A screen reader hears a tree whose items are flat rows with their level, their place among their siblings (`pos_in_set` of `set_size`)
and, for a branch, whether it is expanded: there is no group around the children of an open branch. `TreeNode` can be used alone for a custom tree. `Multiple: true` chooses several rows (the engine's rules: click chooses one, Ctrl+click toggles, Shift+click and Shift+Arrow choose a range, Space toggles, Ctrl+A chooses the rows that show); `Selection` holds the chosen values, two-way, and a chosen row inside a closed branch stays chosen; `On_Change` is called after each change to them, with `event.reason` (`pointer`, `keyboard`, `api`), `event.detail` (`select`, `toggle`, `range`, `all`, `clear`), `event.count`, `event.selection` and `event.anchor`. Not built: loading children when a branch first opens, dragging to reorder, a context menu, and
building only the rows in view for a very large tree.

## How it is built

A view Tesserae ships is a `<Name>_View.tdl` (what it takes and what it is made of) with a `<Name>_Stylesheet.tdl` (how it looks). Use it by name: `Tree { ... }`. A file of the same name in your project replaces it.

### `Tree`

A tree (the WAI-ARIA tree pattern in Material 3's list terms): rows that open to show their children, one level inside the next (the rows are one flat list: each open branch's children follow it, so a screen reader hears each row's level, `Pos_In_Set` and `Set_Size`, not nested groups). `Nodes` is a list of {value, label} and optionally {icon, children, disabled}, the children being the same shape. `Expanded` is the list of values of the open branches and `Selected` the value of the chosen row; both are two-way. A press on a row chooses it, and on a branch opens or closes it too. One Tab stop; the up and down arrows move through the rows that show, Right opens a branch and Left closes one, and typing the start of a label jumps to a row.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Nodes` | `list` | `[]` | The rows: {value, label} and optionally {icon, children, disabled}; children are the same shape. |
| `Expanded` | `list` | `[]` | The values of the branches that are open. Two-way: give it a bare reference and the view writes it back. |
| `Selected` | `any` |  | The value of the chosen row. Two-way: give it a bare reference and the view writes it back. |
| `Selection` | `list` | `[]` | With `Multiple`: the values of the chosen rows. Two-way. A chosen row inside a closed branch stays in it. Two-way: give it a bare reference and the view writes it back. |
| `Multiple` | `bool` | `false` | Choose several rows: click chooses one, Ctrl+click toggles, Shift+click and Shift+Arrow choose a range, Space toggles, Ctrl+A chooses every row that shows (AC-SLT-7). `Selected` then follows the last row pressed. |
| `Select_All_Key` | `bool` | `true` | With `Multiple`: whether Ctrl+A chooses every row that shows. |
| `On_Change` | `handler` |  | With `Multiple`: called after the chosen rows change, with `event.reason` (`pointer`, `keyboard` or `api`), `event.detail` (`select`, `Toggle`, `range`, `all` or `clear`), `event.count`, `event.selection` (the chosen values) and `event.anchor`. |
| `Compact` | `bool` | `false` | 40 pixel rows instead of 56. |
| `Label` | `str` | `Tree` | The tree's accessible name: what the pane is (Files, Structure), not the word Tree (AC-TRE-01). |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `row` (TreeNode).

### `TreeNode`

One row of a tree: a leaf or a branch with a chevron that turns a quarter when it opens. 56 pixels tall (40 when `Compact`), indented 16 pixels plus 24 for each `Level`, with an optional 24 pixel icon and a `body_large` label; a selected row is `secondary_container`. A screen reader hears a tree item at level `level + 1`, "`Pos_In_Set` of `Set_Size`" among its siblings, a branch saying whether it is expanded. It is pressable; `Handlers: {On_Click: ...}` on the call is what a press does. `Tree` puts the rows together.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Label` | `str` |  | The row's text. |
| `Icon` | `str` |  | A leading icon. |
| `Level` | `int` | `0` | How deep it is: 0 for the top. |
| `Set_Size` | `int` | `0` | How many siblings the row has (itself included): a screen reader says "3 of 7". 0 leaves it unsaid. |
| `Pos_In_Set` | `int` | `0` | Which of its siblings the row is, from 1. 0 leaves it unsaid. |
| `Branch` | `bool` | `false` | It has children: a chevron shows. |
| `Expanded` | `bool` | `false` | For a branch: whether its children show. |
| `Selected` | `bool` | `false` | Whether this is the chosen row. |
| `Compact` | `bool` | `false` | A 40 pixel row instead of 56 at density `default`. |
| `Selection_Key` | `any` |  | What names the row in a `Tree`'s `Selection`; the tree sets it. |
| `Disabled` | `bool` | `false` | Dimmed and not pressable. |

Its parts, by name (a stylesheet rule's `Part` or `Name` addresses one): `chevron` (Icon), `chevron_space` (Container), `icon` (Icon), `label` (Text).

Its look is in [`TreeNode_Stylesheet.tdl`](../stylesheets/trees/tree-node.md).

## Using it

```tdl
Container {
  Name: files
  Style { Width: 360, Height: 420 }
  Children {
    Tree {
      Expanded: <| open |>
      Selected: <| current |>
      Nodes {
        Item {
          Value: docs
          Label: Documents
          Icon: folder
          Children {
            Item { Value: a, Label: Letter }
            Item { Value: b, Label: Reports, Children { Item { Value: q, Label: Q1 } } }
          }
        }
        Item { Value: readme, Label: Readme, Icon: file }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import tree_node

folder = tree_node(app.window, "src", depth=0, expanded=True)
file = tree_node(app.window, "app.py", depth=1, leaf=True)
```

## Changing its look

To restyle it in your whole app, write rules for it in your app's stylesheet, or put `<Name>_Stylesheet.tdl` next to your views (or in `Styles/`); it is read only while the app uses the view. A rule names the widget and may narrow it by the properties it declares, a part and a state; the most specific rule wins, and a node's own `Style` beats every rule:

```tdl
# TreeNode_Stylesheet.tdl, or any stylesheet your app loads
Styles {
  Rule {
    Widget: TreeNode
    Part: chevron
    Style { Foreground: tertiary }
  }
}
```

See [Component stylesheets](../stylesheets/index.md).

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
