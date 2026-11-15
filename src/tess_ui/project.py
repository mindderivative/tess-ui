"""A project's files, found by name.

A project is a folder with standard places for each kind of file:

    Views/        Name_View.tdl
    ViewModels/   Name_ViewModel.py
    Themes/       Name_Theme.tdl
    Styles/       Name_Stylesheet.tdl

Views, stylesheets and themes are TDL. A YAML file (`Name_View.yaml`) is no longer read: `yaml_refused` says so, and where to go from there.

`App(root=...)` is the project's root (the folder `app.py` is in, by default). `search=[...]` adds folders to
look in, for every kind; `recursive=True` looks through the whole project instead. A name that is in two places
is an error naming both, not a choice made for you. A path still works wherever a name does.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

__all__ = ["KINDS", "Project", "ProjectError", "is_name", "is_view_file", "kind_of_keys", "kind_of_tdl", "looks_like", "project_of", "sibling_file",
           "view_stem", "yaml_refused"]

#: Each kind of file: the end of its name, and the folders it is kept in.
KINDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "view": ("_View.tdl", ("Views",)),
    "viewmodel": ("_ViewModel.py", ("ViewModels",)),
    "theme": ("_Theme.tdl", ("Themes",)),
    "stylesheet": ("_Stylesheet.tdl", ("Styles",)),
}
#: The word a TDL file's root block has, by the kind it makes the file: a stylesheet is `Styles { }`, a theme `Theme { }`, anything else is a view's widget.
_TDL_ROOTS = {"Styles": "stylesheet", "Theme": "theme"}
_TDL_META = re.compile(r"\A\ufeff?(?:[ \t\r\n]|#[^\n]*(?=\n|\Z))*---[ \t]*\r?\n.*?^---[ \t]*(?:\r?\n|\Z)", re.S | re.M)
_TDL_WORD = re.compile(r"(?:[ \t\r\n]|#[^\n]*(?=\n|\Z))*([A-Za-z_][A-Za-z0-9_]*)")
#: The root keys only a theme has. A theme may hold `styles:` too, so one of these decides before `styles:` does.
_THEME_KEYS = frozenset({"seed", "dark", "colors", "typography", "components"})
#: Folders a whole-project search never goes into.
_SKIPPED = frozenset({"__pycache__", "node_modules", "build", "dist", "site", "site-packages"})


def yaml_refused(file: str | Path) -> Optional[str]:
    """The sentence to raise for a YAML view, stylesheet or theme (a name ending in `.yaml` or `.yml`), which Tesserae no longer reads; `None` for any other
    name. It says what to do: the files are TDL now, and the release that has the converter (`tesserae migrate-tdl`) is `tesserae-ui<0.6.1`."""
    name = Path(file).name
    if not name.endswith((".yaml", ".yml")):
        return None
    return (f"{name}: Tesserae no longer reads YAML files; views, stylesheets and themes are TDL (`*_View.tdl`, `*_Stylesheet.tdl`, `*_Theme.tdl`). "
            "Write the file as TDL: `tesserae migrate-tdl` in an older release does it (`pip install 'tesserae-ui<0.6.1'`), and docs/migration.md "
            "(Migrating from YAML) says how")


def view_stem(path: str | Path) -> str:
    """A view file's name without its `_View.tdl` end (`Main`); a name without it is its file name as it is."""
    name = Path(path).name
    return name.removesuffix(KINDS["view"][0]) if name.endswith(KINDS["view"][0]) else name


def is_view_file(path: str | Path) -> bool:
    """Whether `path` is named like a view file, `*_View.tdl`."""
    return Path(path).name.endswith(KINDS["view"][0])


def sibling_file(beside: Path, kind: str, name: str) -> Optional[Path]:
    """The file of `kind` called `name` in the folder of `beside`, or `None` when there is none."""
    found = beside.with_name(f"{name}{KINDS[kind][0]}")
    return found if found.is_file() else None


def _tdl_root(text: str) -> Optional[tuple[str, int]]:
    """The word that heads the root block of the TDL `text` and where it is (an offset), or `None`. Nothing is parsed."""
    meta = _TDL_META.match(text)
    word = _TDL_WORD.match(text, meta.end() if meta else 0)
    return None if word is None else (word[1], word.start(1))


def kind_of_tdl(text: str) -> Optional[str]:
    """What the root block of the TDL `text` says the file is: `"stylesheet"` for `Styles { }`, `"theme"` for `Theme { }`, `"view"` for any other
    word (a widget); `None` when the text has no root word. Nothing is parsed, so a file that does not read can still be told what it looks like."""
    root = _tdl_root(text)
    return None if root is None else _TDL_ROOTS.get(root[0], "view")


def tdl_wrong_kind(text: str, is_kind: str, file: str = "") -> Optional[tuple[str, int, int]]:
    """`(hint, line, column)` when the root block of the TDL `text`, read as `is_kind`, says it is another kind (`this looks like a theme: name it
    Brand_Theme.tdl`), the line and 0-based column being those of the root word; `None` when it says the same or nothing."""
    root = _tdl_root(text)
    hint = looks_like_kind(None if root is None else _TDL_ROOTS.get(root[0], "view"), is_kind, file)
    if hint is None or root is None:
        return None
    start = root[1]
    return hint, text.count("\n", 0, start) + 1, start - (text.rfind("\n", 0, start) + 1)


class ProjectError(LookupError):
    """A name that is nowhere, or in two places."""


def is_name(ref: Any) -> bool:
    """Whether `ref` is a bare name (`"Main"`), not a path (`"Views/Main_View.tdl"`, a `Path`)."""
    return isinstance(ref, str) and ref != "" and not any(c in ref for c in ("/", "\\")) and "." not in ref


def kind_of_keys(keys: Iterable[Any]) -> Optional[str]:
    """What a file's root keys say it looks like: `"view"` (`widget:`), `"theme"` (`seed`, `dark`, `colors`, `typography` or
    `components`; these win over `styles:`), `"stylesheet"` (`styles:`), or `None` for none of them. Any other key, the first-line
    `tesserae:` marker included, says nothing. The one list every loader's "looks like" hint reads."""
    present = set(keys)
    if "widget" in present:
        return "view"
    if present & _THEME_KEYS:
        return "theme"
    return "stylesheet" if "styles" in present else None


def looks_like(keys: Iterable[Any], is_kind: str, file: str = "") -> Optional[str]:
    """`this looks like a stylesheet: name it Brand_Stylesheet.tdl`, for a file read as `is_kind` whose root `keys` say it is another
    kind; `None` when they say nothing or say the same. `file` is the file's name (its part before `_Kind.tdl` is kept, else `<Name>`)."""
    return looks_like_kind(kind_of_keys(keys), is_kind, file)


def looks_like_kind(kind: Optional[str], is_kind: str, file: str = "") -> Optional[str]:
    """`looks_like` for a kind already found (from root keys, or `kind_of_tdl` for a TDL file)."""
    if kind is None or kind == is_kind:
        return None
    name = Path(file).name if file else ""
    stem = name.removesuffix(KINDS[is_kind][0]) if name.endswith(KINDS[is_kind][0]) else "<Name>"
    return f"this looks like a {kind}: name it {stem}{KINDS[kind][0]}"


class Project:
    """The files under `root`, found by name. See the module docstring."""

    def __init__(self, root: str | Path, search: Iterable[str | Path] = (), recursive: bool = False) -> None:
        self.root = Path(root).resolve()
        self.search = [Path(folder) for folder in search]
        self.recursive = recursive
        self._indexes: dict[str, dict[str, list[Path]]] = {}

    # -- where to look --------------------------------------------------------------------

    def folders(self, kind: str) -> list[Path]:
        """The folders that exist where `kind` is looked for, in order; with `recursive`, every folder under the root."""
        standard = KINDS[kind][1]
        found = [self.root / name for name in standard] + [folder if folder.is_absolute() else self.root / folder
                                                            for folder in self.search]
        folders = [folder for folder in found if folder.is_dir()]
        if self.recursive:
            folders = [self.root, *self._subfolders()]
        return folders

    def _walk(self) -> Iterator[tuple[Path, list[str], list[str]]]:
        """Each folder under the root a whole-project search goes into, with its subfolders (the kept ones, sorted) and its files."""
        for current, names, files in os.walk(self.root):
            names[:] = sorted(n for n in names if not n.startswith(".") and n not in _SKIPPED
                              and not (Path(current, n) / "pyvenv.cfg").exists())
            yield Path(current), names, files

    def _subfolders(self) -> list[Path]:
        return [Path(current, n) for current, names, _ in self._walk() for n in names]

    # -- finding --------------------------------------------------------------------------

    def _scan(self, kind: str) -> dict[str, list[Path]]:
        index: dict[str, list[Path]] = {}
        suffix = KINDS[kind][0]
        for folder in self.folders(kind):
            for path in sorted(folder.glob(f"*{suffix}")):
                if path.is_file():
                    index.setdefault(path.name.removesuffix(suffix), []).append(path)
        return index

    def index(self, kind: str) -> dict[str, Path]:
        """Every name of `kind` and its file. Raises `ProjectError` for a name in two places."""
        found = self._scan(kind)
        for name, paths in found.items():
            if len(paths) > 1:
                where = " and ".join(str(p.relative_to(self.root)) if p.is_relative_to(self.root) else str(p) for p in paths)
                raise ProjectError(f"{name}{KINDS[kind][0]} is in two places, {where}: keep one, or name them differently")
        return {name: paths[0] for name, paths in found.items()}

    def find(self, kind: str, name: str) -> Path:
        """The file of `kind` called `name`; `ProjectError` if there is none, or two."""
        index = self.index(kind)
        if name not in index:
            looked = ", ".join(str(f.relative_to(self.root)) if f.is_relative_to(self.root) else str(f)
                               for f in self.folders(kind)) or "no folder yet"
            raise ProjectError(f"no {kind} called {name!r} ({name}{KINDS[kind][0]}) in {looked}"
                               f" under {self.root}: add the folder to App(search=[...]) or pass the file's path"
                               + self._elsewhere(kind, name))
        return index[name]

    def _elsewhere(self, kind: str, name: str) -> str:
        """What to add to a not-found message when the file is somewhere the project does not look: one walk of the project,
        for the exact file name and for the same stem under another kind's suffix. Empty when there is no such file."""
        exact: list[Path] = []
        other: list[tuple[Path, str]] = []
        yaml: list[Path] = []
        for folder, _, files in self._walk():
            for file in sorted(files):
                if file == f"{name}{KINDS[kind][0]}":
                    exact.append(folder / file)
                elif file in {f"{name}{KINDS[k][0]}" for k in KINDS if k != kind}:
                    other += [(folder / file, k) for k in KINDS if k != kind and file == f"{name}{KINDS[k][0]}"]
                elif file in {f"{name}{KINDS[k][0].removesuffix('.tdl')}.yaml" for k in ("view", "stylesheet", "theme")}:
                    yaml.append(folder / file)

        def rel(path: Path) -> str:
            return path.relative_to(self.root).as_posix()

        parts: list[str] = []
        if exact:
            kept = ", ".join(f"{folder}/" for folder in KINDS[kind][1])
            where = (f"add {rel(exact[0].parent)} to" if len(exact) == 1 else "add their folders to")
            parts.append(f"found {' and '.join(rel(p) for p in exact)}: {kind}s are read from {kept} (or {where} App(search=[...]))")
        parts += [f"found {rel(path)}, a {k}, not a {kind}" for path, k in other]
        parts += [f"found {rel(path)}: {yaml_refused(path)}" for path in yaml]
        return "".join(f"; {part}" for part in parts)

    def resolve(self, kind: str, ref: str | Path) -> Path:
        """`ref` as a file: a path is used as it is, a bare name is found."""
        return self.find(kind, ref) if is_name(ref) else Path(ref)

    # -- ViewModels -----------------------------------------------------------------------

    def viewmodel(self, name: str) -> type:
        """The class `NameViewModel` in `Name_ViewModel.py`, imported. Its folder goes on `sys.path`, so the
        ViewModels can import each other by their file names."""
        path = self.find("viewmodel", name)
        return load_viewmodel(path, name)


def project_of(parent: Any) -> Optional[Project]:
    """The project of the app that `parent` (a view, a component, a window) is in, or `None`."""
    from tess_ui.follow import app_of

    app = app_of(getattr(parent, "window", parent))
    return app.project if app is not None else None


def load_viewmodel(path: Path, name: str) -> type:
    """The class `<name>ViewModel` from the file `path`."""
    folder = str(path.parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    module_name = path.stem
    existing = sys.modules.get(module_name)
    if existing is not None and Path(getattr(existing, "__file__", "") or "").resolve() != path.resolve():
        raise ProjectError(f"{module_name} is already imported from {existing.__file__}, not {path}")
    module = importlib.import_module(module_name)
    wanted = f"{name}ViewModel"
    cls: Optional[type] = getattr(module, wanted, None)
    if not isinstance(cls, type):
        classes = ", ".join(sorted(n for n, v in vars(module).items() if isinstance(v, type) and n.endswith("ViewModel")))
        raise ProjectError(f"{path.name} has no class {wanted}" + (f" (it has {classes})" if classes else ""))
    return cls
