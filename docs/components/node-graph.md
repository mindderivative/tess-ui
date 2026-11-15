# Node graph

*Beyond MD3*

## In Material Design 3

Material Design 3 has no node graph. This is a pannable canvas of titled boxes joined by edges, for tools.

## In Tesserae

The `NodeGraph` kind (`NodeGraph` in a view), with `GraphNode` children at an `X` and a `Y`. Drag the background to pan, the wheel zooms about the pointer, drag a node (or
press the arrow keys on a focused one) to move it, and its edges follow.

`Edges` are the links, each `{from: id, to: id}`, the ids of the `GraphNode`s: their path from the view's root, as `root.graph.load` for the node `load` in the graph `graph`; an edge runs from the right side of one node to the left of the other, as a curve. `Snap`
makes a node the user moves land on a multiple of that many pixels (an arrow key steps one square, or 8 pixels with no grid; `0` is no grid), `Arrows` ends each edge in an arrowhead, and `Fit`
pans and zooms when it opens so every node shows (never past actual size). A `GraphNode` has a `Label` (its title), an `X` and a `Y` in the graph's own coordinates, and its
size from `Style`; what it holds goes in its body.

Pressing a node chooses it (a `primary` border, and it is selected to a screen reader); pressing the background chooses none. From Python the widget has `fit_to_view(padding)`,
`zoom`, `Offset`, `Snap`, `Arrows` and `Selected` (a `Signal` of the node chosen). Not built: ports and dragging to connect, labels on edges, selecting several, a minimap, undo, and
building only the nodes in view.

## How it is built

### `NodeGraph`

A canvas of linked nodes you can pan, zoom and move.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Edges` | `list` |  | The links: each {from: id, to: id}, the ids of the GraphNodes. |
| `Snap` | `float` |  | A node the user moves lands on a multiple of this many pixels; 0 is no grid. |
| `Arrows` | `bool` |  | Each edge ends in an arrowhead. |
| `Fit` | `bool` |  | Pan and zoom, when it opens, so every node shows (never beyond actual size). |

### `GraphNode`

A node of a NodeGraph.

| Property | Type | Default | Meaning |
| --- | --- | --- | --- |
| `Label` | `str` |  |  |
| `X` | `float` |  |  |
| `Y` | `float` |  |  |

## Using it

```tdl
Container {
  Name: pipeline
  Style { Width: 640, Height: 360 }
  Children {
    NodeGraph {
      Name: graph
      Arrows: true
      Fit: true
      Snap: 20
      Edges {
        Item { From: root.graph.load, To: root.graph.clean }
        Item { From: root.graph.clean, To: root.graph.save }
      }
      Style { Width: 640, Height: 360 }
      Children {
        GraphNode {
          Name: load
          Label: Load
          X: 20
          Y: 40
          Style { Width: 140, Height: 80 }
        }
        GraphNode {
          Name: clean
          Label: Clean
          X: 240
          Y: 100
          Style { Width: 140, Height: 80 }
        }
        GraphNode {
          Name: save
          Label: Save
          X: 460
          Y: 40
          Style { Width: 140, Height: 80 }
        }
      }
    }
  }
}
```

## Using it in Python

```python
from tess_ui.widgets import graph_node, node_graph

graph = node_graph(app.window, 480, 320)
source = graph_node(app.window, graph, "Source", 40, 40, 120, 60)
```

## See also

- [Python API reference](../api/python.md)
- [TDL reference](../api/tdl.md)
