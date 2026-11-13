"""Opening the file dialog from Python and getting the answer back: `FileDialogRequest`.

A `FileDialog` in a view is told what to do by names the view's ViewModel owns (`open`, `mode`, `start`, ...). `FileDialogRequest(viewmodel)` makes those names, as `Signal`s,
on the ViewModel (`file_open`, `file_mode`, ..., or another prefix), with the two handlers the dialog calls (`file_accepted`, `file_cancelled`), so the view only has to say so:

```yaml
- widget: FileDialog
  open: "{{ file_open }}"
  mode: "{{ file_mode }}"
  start: "{{ file_start }}"
  root: "{{ file_root }}"
  filters: "{{ file_filters }}"
  filename: "{{ file_filename }}"
  multiple: "{{ file_multiple }}"
  headline: "{{ file_headline }}"
  accept_label: "{{ file_accept_label }}"
  show_hidden: "{{ file_show_hidden }}"
  value: "{{ file_value }}"
  on_accept: file_accepted
  on_cancel: file_cancelled
```

and the ViewModel opens it and hears the answer:

```python
class MainViewModel(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.files = FileDialogRequest(self)

    def open_plan(self):
        self.files.show(mode="open", filters=[{"label": "TDL files", "patterns": ["*.tdl"]}], on_accept=self.load)

    def load(self, paths):          # always a list, one path unless `multiple`
        ...
```

`show` can be called again while a dialog is showing: it replaces the old request, and the old one's `on_cancel` is not called.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tess_ui.reactive import Signal

__all__ = ["FileDialogRequest"]

#: The properties of the dialog a request holds, with what each is when none is asked for.
_DEFAULTS: dict[str, Any] = {"mode": "open", "headline": "", "accept_label": "", "multiple": False, "start": "", "root": "", "filter": 0, "show_hidden": False, "filename": ""}


class FileDialogRequest:
    """The names a `FileDialog` call binds, and the callbacks for what the person chose. See the module's note."""

    def __init__(self, viewmodel: Any, prefix: str = "file_") -> None:
        self.prefix = prefix
        self.open = Signal(False)
        self.value = Signal("")
        self.filters = Signal([])
        self._signals: dict[str, Signal] = {name: Signal(default) for name, default in _DEFAULTS.items()}
        self._on_accept: Callable[[list[str]], Any] | None = None
        self._on_cancel: Callable[[], Any] | None = None
        for name, signal in {"open": self.open, "value": self.value, "filters": self.filters, **self._signals}.items():
            setattr(viewmodel, prefix + name, signal)
        setattr(viewmodel, prefix + "accepted", self._accepted)
        setattr(viewmodel, prefix + "cancelled", self._cancelled)

    @property
    def is_open(self) -> bool:
        """Whether the dialog is showing."""
        return bool(self.open.get())

    def show(self, *, mode: str = "open", multiple: bool = False, start: str = "", root: str = "", filters: list[Any] | None = None, filter: int = 0,
             show_hidden: bool = False, filename: str = "", headline: str = "", accept_label: str = "",
             on_accept: Callable[[list[str]], Any] | None = None, on_cancel: Callable[[], Any] | None = None) -> None:
        """Opens the dialog. `on_accept(paths)` is called with the chosen paths as a list (one path unless `multiple`), `on_cancel()` when it was closed without one.
        The other arguments are the `FileDialog` properties of the same names."""
        if mode not in ("open", "save", "folder"):
            raise ValueError(f"mode is open, save or folder, not {mode!r}")
        self._on_accept, self._on_cancel = on_accept, on_cancel
        wanted = {"mode": mode, "headline": headline, "accept_label": accept_label, "multiple": multiple, "start": str(start), "root": str(root), "filter": filter,
                  "show_hidden": show_hidden, "filename": filename}
        for name, value in wanted.items():
            self._signals[name].set(value)
        self.filters.set(list(filters or []))
        self.value.set("")
        if self.open.get():  # one already showing is closed first, so the new request opens afresh
            self.open.set(False)
        self.open.set(True)

    def close(self) -> None:
        """Closes the dialog with no answer and without calling `on_cancel`."""
        self._on_accept = self._on_cancel = None
        self.open.set(False)

    def _accepted(self) -> None:
        value = self.value.get()
        paths = [value] if isinstance(value, str) else [str(p) for p in value]
        callback, self._on_accept, self._on_cancel = self._on_accept, None, None
        if callback is not None:
            callback(paths)

    def _cancelled(self) -> None:
        callback, self._on_accept, self._on_cancel = self._on_cancel, None, None
        if callback is not None:
            callback()
