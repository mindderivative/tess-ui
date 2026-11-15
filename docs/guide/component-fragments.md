# Component Views

A **component** is a view with `Params`. Another view calls it by name, gives it values as plain keys, and may hand it children. There
is no separate kind of file for it: a component is `<Name>_View.tdl`, like any view. A component has no ViewModel of its own and no
state of its own beyond what it declares: it is part of the view that calls it, built where it is written. This is a different thing
from opening a whole view against a ViewModel, which [Components & Embedding](components.md) covers.

Tesserae's own [Material 3 components](../components/index.md) (`Button`, `Card`, `Tabs`, `Dialog`, ...) are views of exactly this kind,
and you can write your own the same way. The whole language is in [The View Language](view-language.md); this page is about writing
and calling components.

## Using one

```tdl
Container {
  Name: actions
  Style { Flex_Direction: horizontal, Gap: 8, Padding: 16, Align_Content: center }
  Children {
    Button {
      Name: save
      Label: Save
      Icon: check
      Handlers {
        On_Click: save
      }
    }
    Button {
      Name: cancel
      Label: Cancel
      Variant: outlined
    }
  }
}
```

- `Button { }` is the call. It finds `Button_View.tdl`, first in your project and then among the views Tesserae ships.
- `label`, `icon` and `variant` are the component's params, written as plain keys. A param you leave out takes its default; one the
  component marks `required` must be there; a key the component does not declare is an error that names it.
- `Name:` is optional. It is how a ViewModel, a stylesheet rule or a test finds this call again.
- Each widget's page under [Components](../components/index.md) lists its params.

The values are checked when the view loads, against what the component declares, and the error names the file, line and column:

```
Main_View.tdl:5:5: error: Stat: 'label' is required
Main_View.tdl:5:40: error: Stat: no property 'colour' (properties: label, value, unit, size)
Main_View.tdl:5:46: error: Stat: 'size' is 'xl', which is not one of: s, m
Main_View.tdl:5:43: error: Stat: 'n' takes a number from 0 to 10, got 11   # for a param declared {type: int, min: 0, max: 10}
```

### Handlers, bindings and names on a call

A call takes the keys every node takes. They go on the component's root, over what the root has:

```text
Button {
  Name: save
  Label: Save
  Handlers {
    On_Click: save
  }
  A11y { Label: "Save the note" }
  Classes: [primary_action]
  Style { Width: 160 }
}
```

- `Handlers` run in the caller's names: `On_Click: save` is the caller's ViewModel method, and `On_Click { Set { Target: saved, Value: <| True |> } }` writes the
  caller's state. If the component's root has a handler for the same event, the component's runs first and the call's after it.
- `Style`, `Classes:`, `A11y`, `Interaction:` and `Tooltip` lie over the root's own. `Style` wins for the fields it sets and no
  others. `Visible: false` hides the whole component.
- A value written as an expression (`Label: <| 'Save changes' if dirty else 'Save' |>`) is read where it is written, in the caller's
  names, and stays reactive inside the component. That is all a "binding" is now: there is no `Bindings:` key.
- The component cannot see the caller's names, only its params. To let it change something of the caller's, pass a model param or a
  handler param (see below).
- With `For`, every item gets the call's keys.
- A clickable root is a button for the keyboard and assistive technology too, with the state layer and ripple
  (see [Interaction](interaction.md)).

The call's `Name:` is the prefix of everything inside it. The component's nodes that have a name are its **parts**, and the call
`save` above has `save.label` and `save.icon`. A stylesheet rule reaches a part with `Part:`, and a test with the full id
(`root.save.label`).

## Writing your own

Put a `<Name>_View.tdl` in `Views/` and call it as `Name { }`; it is found by name. To keep views in other folders, give the app
`search=[...]`, or `recursive=True` to look through the whole project ([Projects](projects.md)).

```tdl
# Stat_View.tdl
Container {
  Params {
    Label { Type: str, Required: true, Doc: "What the number is" }
    Value { Type: float, Default: 0 }
    Unit { Type: str, Default: "" }
    Size { Type: enum, Choices: [s, m], Default: s }
  }
  Style { Flex_Direction: vertical, Gap: 2 }
  Children {
    Text {
      Name: value
      Text: <| format_number(value) |><| unit |>
      Typography_Role: <| 'title_large' if size == 'm' else 'title_medium' |>
      Style { Foreground: on_surface }
    }
    Text {
      Name: label
      Text: <| label |>
      Typography_Role: label_medium
      Style { Foreground: on_surface_variant }
    }
  }
}
```

```text
# anywhere else
Stat {
  Name: users
  Label: "Active users"
  Value: <| active |>
  Size: m
}
```

`Params` is a list of names (`[title, icon]`: each is required unless written `{ Icon: null }`) or a mapping of names to a type or to
`{type, default, choices, required, model, doc, min, max}`:

| Key | Meaning |
| --- | --- |
| `type` | one of `str int float bool color length icon enum list dict node nodes handler mask any` |
| `default` | the value when the call leaves it out (a param with a default is optional) |
| `choices` | the values an `enum` allows |
| `required` | the call must give it |
| `model` | the component changes it (see below) |
| `doc` | one line, shown by the editor and in the schema |
| `min`, `max` | the range a number may take |


### Children and slots

A call's `Children` are the component's content. The component says where they go with `Slot { }`:

```tdl
# Panel_View.tdl
Container {
  Params {
    Title { Type: str, Required: true }
  }
  Style { Flex_Direction: vertical, Gap: 8, Padding: 16 }
  Children {
    Text {
      Name: heading
      Text: <| title |>
      Typography_Role: title_medium
      Style { Foreground: on_surface }
    }
    Slot { }  # the default slot
    Slot {
      Name: actions  # a named slot
    }
  }
}
```

```text
Panel {
  Name: profile
  Title: Profile
  Children {
    Text {
      Name: bio
      Text: <| bio |>
      Typography_Role: body_medium
      Style { Foreground: on_surface }
    }
    Button {  # goes into the `actions` slot
      Slot: actions
      Name: edit
      Label: Edit
    }
  }
}
```

- A child without `Slot:` goes into the default slot.
- Slot content is written in the caller's names and keeps them. Its ids are the caller's, under the call: `profile.bio`.
- A component with no `Slot` takes no children: giving it some is an error (`Plain takes no children (its view has no Slot)`).
- A `Card` has a default slot for its content and an `actions` slot for its buttons, a `Dialog` takes its content as children.

### Letting the component change something of the caller's

A param with `Model: true` that is given **one bare reference** to a Signal or to local state passes the thing itself, so the component's own
control edits the caller's value. The `Switch` below writes `dark` in the caller:

```tdl
# Setting_View.tdl
Container {
  Params {
    Label { Type: str, Required: true }
    Checked { Type: bool, Model: true, Default: false }
  }
  Style { Flex_Direction: horizontal, Align_Content: center, Gap: 12 }
  Children {
    Text {
      Name: label
      Text: <| label |>
      Typography_Role: body_large
      Style { Foreground: on_surface }
    }
    Switch {
      Name: toggle
      Selected: <| checked |>
    }
  }
}
```

```text
Setting {
  Name: dark_mode
  Label: "Dark mode"
  Checked: <| dark |>
}
```

Given an expression (`Checked: <| not light |>`) the component gets a copy that follows it, and a write by the component stays in the copy until the
expression next changes; given a literal or nothing it keeps its own value. A param without `Model: true` follows what it is given and cannot be written.
[Two-way properties](view-language.md#two-way-properties) has the table.

A param of type `handler` takes an action of the caller's, to run when something happens in the component. The component calls it
like an action, and a param the caller left out does nothing when called:

```tdl
# Removable_View.tdl
Container {
  Params {
    Label { Type: str, Required: true }
    On_Remove { Type: handler }
  }
  Style { Flex_Direction: horizontal, Align_Content: center, Gap: 8 }
  Children {
    Text {
      Name: label
      Text: <| label |>
      Typography_Role: body_large
      Style { Foreground: on_surface }
    }
    IconButton {
      Name: remove
      Icon: close
      Label: Remove
      Handlers {
        On_Click: on_remove
      }
    }
  }
}
```

```text
For tag In <| tags |> Key <| tag |> {
  Removable {
    Name: tag
    Label: <| tag |>
    On_Remove: "tags = [t for t in tags if t != tag]"  # read in the caller's names
  }
}
```

## Where the look is

A component holds structure and behaviour. Its look is **rules** that name it: a stylesheet lists them, and the shipped components
come with theirs.

```tdl
Styles {
  Rule {
    Widget: Stat
    Style { Padding: 12, Background: surface_container, Corner_Radius: 12 }
  }
  Rule {
    Widget: Stat
    Size: m
    Style { Padding: 20 }
  }
  Rule {
    Widget: Stat
    Part: label
    Style { Foreground: primary }
  }
}
```

- A rule names a `widget` and may add the params `variant`, `size` and `shape` (when the component declares them), `classes`, `name`,
  a `part` (a named node inside the component) and a `state` (`hovered`, `focused`, `pressed`, `disabled`, `selected`, ...). The most
  specific rule wins.
- A node's inline `Style` beats every rule, for the fields it sets. A shipped component leaves its looks to rules for that reason, and
  a call's `Style` always has the last word.
- Rule values may be expressions over the component's params (`Corner_Radius: <| 12 if size == 'm' else 8 |>`).
- Rules go in the app's stylesheet: `App(stylesheet="App")` finds `Styles/App_Stylesheet.tdl`. Every shipped component's rules are the
  lowest layer under it, so yours override them, field by field.
- Every shipped [stylesheet](../stylesheets/index.md) has a page, and the [Style](view-language.md#style) section of the language page is
  the whole rule format.

### Replacing a shipped component

A `Button_View.tdl` in your project is used instead of the one Tesserae ships, for every `Button { }` in the app, and **its shipped
rules go with it**: the replacement starts with no look until your own stylesheet gives it one. To change only how a shipped component
looks, leave the view alone and write rules.

## Repeating a view: `For`

`For` on a call builds it once for each element of a list. If the list can change while the app runs, the loop is reactive and needs a
`Key`: the identity of an element, so a node whose key stays is kept.

```text
For tag In <| tags |> Key <| tag |> {
  Chip {
    Name: tag
    Label: <| tag |>
    Handlers {
      On_Click { Set { Target: picked, Value: <| tag |> } }
    }
  }
}
```

- The loop variable is in scope for the call's params, its handlers and the children written inside it.
- A list that is replaced updates the screen; one changed in place is not noticed. Write `tags = tags + ['new']`, not `tags.append(...)`.
- A component can take a whole list as one param (`items`, `tabs`) and repeat inside itself. That is how `Tabs`, `NavigationRail`,
  `Menu` and `ButtonGroup` take their items:

```text
Tabs {
  Name: tabs
  Selected: <| section |>
  Tabs {
    Item { Value: inbox, Label: Inbox }
    Item { Value: sent, Label: Sent }
  }
}
```

For rows that are thousands long use a `VirtualList` ([The View Language](view-language.md#long-lists)).

## Optional parts

`If` on a node builds it only while its expression is true, and it can read the component's params. This is how a component has an
icon only when it was given one:

```tdl
Container {
  Params {
    Label { Type: str, Required: true }
    Icon { Type: icon, Default: "" }
  }
  Style { Flex_Direction: horizontal, Align_Content: center, Gap: 8 }
  Children {
    If <| icon != '' |> {
      Icon {
        Name: icon
        Icon: <| icon |>
        Style { Foreground: on_surface }
      }
    }
    Text {
      Name: label
      Text: <| label |>
      Typography_Role: label_large
      Style { Foreground: on_surface }
    }
  }
}
```

For a value that changes with a param, write the expression: `Padding: <| {'left': 16, 'right': 20 } if icon != '' else 20 |>`.
`Visible:` keeps a node built and takes it out of the layout; `If` does not build it at all
(see [The View Language](view-language.md#repeating-choosing-and-remembering)).

## Nesting

A component can call other components, and its parts are named under the outer call's name too (`panel.heading.label`, for a `heading` the `panel` component calls). A component may
call itself, which is how a tree is written, to a depth of 64.

## Looking at the shipped ones

The views Tesserae ships are in the `tess_ui/views` folder of the package: `Button_View.tdl` with `Button_Stylesheet.tdl` beside it.
They are written in exactly this language and are the best examples of it: `Card` (slots), `ButtonGroup` (a list param and a
`For`), `Tabs` (a model param), `Dialog` (an `Overlay`).
