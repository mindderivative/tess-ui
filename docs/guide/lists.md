# Lists

A list on screen is a `For` in a view. For a list that changes, the node repeats for each element and a `Key` says which
element each built node belongs to:

```tdl
Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 300, Gap: 4 }
  Children {
    Rect {
      Name: add
      Style { Width: 80, Height: 30, Background: primary }
      Handlers { On_Click: add }
    }
    For item In <| items |> Key <| item.id |> {
      Container {
        Name: row
        State { Done: false }
        Style { Height: 30, Gap: 8 }
        Children {
          Checkbox { Name: box, Checked: <| done |> }
          Text { Name: title, Text: <| item.title |>, Typography_Role: body_large, Style { Foreground: on_surface } }
          Rect {
            Name: remove
            Style { Width: 24, Height: 24, Background: error }
            Handlers { On_Click { Call { Action: remove, Args: [<| item.id |>] } } }
          }
        }
      }
    }
  }
}
```

```python
class MainViewModel(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.items = Signal([{"id": 1, "title": "Milk"}, {"id": 2, "title": "Eggs"}])   # the single source of truth

    def add(self):
        self.items.update(lambda items: [*items, {"id": len(items) + 11, "title": "New"}])

    def remove(self, id):
        self.items.update(lambda items: [i for i in items if i["id"] != id])
```

When the list is replaced, nodes whose key stays are kept (with their `State`), new keys are built, removed keys are gone, and the order
follows the list. A list changed in place is not noticed: replace it, as `update` does. Each row has its own
`State` and its own handlers, in which the loop variable (`item`) is in scope. Every row is built; for thousands of equal rows use a
`VirtualList` instead ([Long lists](view-language.md#long-lists)). The rest of `For` is in
[Repeating, choosing and remembering](view-language.md#repeating-choosing-and-remembering).

`examples/todo_list/` in the repository is the same list written in TDL: the view builds one row for each item by `For` and `Key`, and the ViewModel changes the one
`items` list.

## In a scrolling list

Put a node with a `For` inside a `ScrollView`: see [Layout](layout.md#scrolling).
