"""Real, repeatable coverage for `tess_ui.instantiate`'s naming check -- the real,
enforced-naming counterpart to `tess_re.View.instantiate`/`Component
.instantiate` (TRE M43), used by `examples/todo_list/` for a real
dynamic list of independently-`ViewModel`'d components.

`instantiate()` reads only a component file in the older `id:`/`kind:` YAML syntax (`component:`, `include:`), which is
not written any more; its embedding tests went with that syntax. The naming check runs before the file is read.
"""

import importlib.util
import sys

import pytest

from tess_ui import View, instantiate

PARENT_SPEC = {
    "id": "root", "kind": "Container", "style": {"flex_direction": "vertical", "width": 300, "height": 200, "gap": 8, "padding": 8},
    "children": [{"id": "item_list", "kind": "Container", "style": {"flex_direction": "vertical", "gap": 4, "width": 280, "height": 180}}],
}

ITEM_VIEW = """---
TDL: 0.2
Name: item
---
Rect { Style { Width: 260, Height: 32, Background: "#112233" } }
"""


def write(tmp_path, text, name):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def load_viewmodel_class(tmp_path, filename, class_name):
    path = tmp_path / filename
    path.write_text(
        f"from tess_ui import Signal, ViewModel\n\n\n"
        f"class {class_name}(ViewModel):\n"
        f"    def __init__(self, view):\n"
        f"        self.value = Signal(0)\n"
        f"        super().__init__(view)\n"
    )
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return getattr(module, class_name)


def test_instantiate_rejects_a_mismatched_naming_pair(tmp_path):
    item_path = write(tmp_path, ITEM_VIEW, "item.tdl")  # missing _View suffix
    vm_cls = load_viewmodel_class(tmp_path, "Item_ViewModel.py", "ItemViewModel")

    view = View(PARENT_SPEC)
    container = view.node("item_list")

    with pytest.raises(ValueError, match=r"_View\.\w+ naming convention"):
        instantiate(view, item_path, vm_cls, container)
