"""A project's files, found by name.

A project is a folder with standard places for each kind of file:

    Views/        Name_View.tdl (or Name_View.yaml)
    ViewModels/   Name_ViewModel.py
    Components/   Name_Component.yaml (and Name_Stylesheet.yaml, its look)
    Themes/       Name_Theme.tdl (or Name_Theme.yaml)
    Styles/       Name_Stylesheet.tdl (or Name_Stylesheet.yaml), Name_Style.yaml

A view, a stylesheet and a theme may be written in TDL (`.tdl`) or in YAML (`.yaml`); a name finds either. When one folder holds both
`Name_View.tdl` and `Name_View.yaml`, the `.tdl` is the file and a note says once that the YAML twin is ignored.

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

from loguru import logger

__all__ = ["KINDS", "Project", "ProjectError", "TDL_SUFFIXES", "is_name", "is_view_file", "kind_of_keys", "kind_of_tdl", "looks_like", "project_of",
           "resolve_view", "sibling_file", "suffixes", "view_stem"]

#: Each kind of file: the end of its name, and the folders it is kept in.
KINDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "view": ("_View.yaml", ("Views",)),
    "viewmodel": ("_ViewModel.py", ("ViewModels",)),
    "component": ("_Component.yaml", ("Components",)),
    "theme": ("_Theme.yaml", ("Themes",)),
    "stylesheet": ("_Stylesheet.yaml", ("Styles",)),
    "style": ("_Style.yaml", ("Styles",)),
}
#: The kinds that may be written in TDL, and the end of their TDL file names (the `KINDS` suffix is the YAML one).
TDL_SUFFIXES: dict[str, str] = {"view": "_View.tdl", "theme": "_Theme.tdl", "stylesheet": "_Stylesheet.tdl"}
#: The word a TDL file's root block has, by the kind it makes the file: a stylesheet is `Styles { }`, a theme `Theme { }`, anything else is a view's widget.
_TDL_ROOTS = {"Styles": "stylesheet", "Theme": "theme"}
_TDL_META = re.compile(r"\A\ufeff?(?:[ \t\r\n]|#[^\n]*)*---[ \t]*\r?\n.*?^---[ \t]*(?:\r?\n|\Z)", re.S | re.M)
_TDL_WORD = re.compile(r"(?:[ \t\r\n]|#[^\n]*)*([A-Za-z_][A-Za-z0-9_]*)")
_NOTED_TWINS: set[Path] = set()
#: The root keys only a theme has. A theme may hold `styles:` too, so one of these decides before `styles:` does.
_THEME_KEYS = frozenset({"seed", "dark", "colors", "typography", "components"})
#: Folders a whole-project search never goes into.
_SKIPPED = frozenset({"__pycache__", "node_modules", "build", "dist", "site", "site-packages"})


def suffixes(kind: str) -> tuple[str, ...]:
    """The ends a file name of `kind` may have, the one that wins first: `("_View.tdl", "_View.yaml")`; one suffix for a kind that has no TDL form."""
    tdl = TDL_SUFFIXES.get(kind)
    return (tdl, KINDS[kind][0]) if tdl else (KINDS[kind][0],)


def view_stem(path: str | Path) -> str:
    """A view file's name without its `_View.tdl` or `_View.yaml` end (`Main`); a name with neither end is its file name as it is."""
    name = Path(path).name
    for suffix in suffixes("view"):
        if name.endswith(suffix):
            return name.removesuffix(suffix)
    return name


def is_view_file(path: str | Path) -> bool:
    """Whether `path` is named like a view file, `*_View.tdl` or `*_View.yaml`."""
    return Path(path).name.endswith(suffixes("view"))


def sibling_file(beside: Path, kind: str, name: str) -> Optional[Path]:
    """The file of `kind` called `name` in the folder of `beside` (the `.tdl` before the `.yaml`), or `None` when there is none."""
    return next((found for found in (beside.with_name(f"{name}{suffix}") for suffix in suffixes(kind)) if found.is_file()), None)


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
    """Whether `ref` is a bare name (`"Main"`), not a path (`"Views/Main_View.yaml"`, a `Path`)."""
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
    """`this looks like a stylesheet: name it Brand_Stylesheet.yaml`, for a file read as `is_kind` whose root `keys` say it is another
    kind; `None` when they say nothing or say the same. `file` is the file's name (its part before `_Kind.yaml` is kept, else `<Name>`)."""
    return looks_like_kind(kind_of_keys(keys), is_kind, file)


def looks_like_kind(kind: Optional[str], is_kind: str, file: str = "") -> Optional[str]:
    """`looks_like` for a kind already found (from root keys, or `kind_of_tdl` for a TDL file). The name it suggests ends as the file does: `.tdl` for a TDL
    file (`Brand_Stylesheet.tdl`), else `.yaml`."""
    if kind is None or kind == is_kind:
        return None
    name = Path(file).name if file else ""
    as_tdl = name.endswith(".tdl") and kind in TDL_SUFFIXES
    stem = next((name.removesuffix(s) for s in suffixes(is_kind) if name.endswith(s)), "<Name>")
    return f"this looks like a {kind}: name it {stem}{TDL_SUFFIXES[kind] if as_tdl else KINDS[kind][0]}"


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
        for folder in self.folders(kind):
            kept: dict[str, Path] = {}
            for suffix in suffixes(kind):  # the `.tdl` first: in one folder it wins over its YAML twin
                for path in sorted(folder.glob(f"*{suffix}")):
                    name = path.name.removesuffix(suffix)
                    if not path.is_file():
                        continue
                    if name in kept:
                        self._note_twin(kept[name], path)
                    else:
                        kept[name] = path
            for name, path in kept.items():
                index.setdefault(name, []).append(path)
        return index

    @staticmethod
    def _note_twin(kept: Path, ignored: Path) -> None:
        """Says once that `ignored`, the YAML twin of the TDL file `kept` in the same folder, is not read."""
        if ignored not in _NOTED_TWINS:
            _NOTED_TWINS.add(ignored)
            logger.info("{} and {} are both here: the .tdl is read, the YAML twin is ignored (remove it, or `tesserae migrate-tdl --remove-source`)",
                        kept.name, ignored.name)

    def index(self, kind: str) -> dict[str, Path]:
        """Every name of `kind` and its file. Raises `ProjectError` for a name in two places."""
        found = self._scan(kind)
        for name, paths in found.items():
            if len(paths) > 1:
                where = " and ".join(str(p.relative_to(self.root)) if p.is_relative_to(self.root) else str(p) for p in paths)
                end = next(s for s in suffixes(kind) if paths[0].name.endswith(s))
                raise ProjectError(f"{name}{end} is in two places, {where}: keep one, or name them differently")
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
        for folder, _, files in self._walk():
            for file in sorted(files):
                if file in {f"{name}{s}" for s in suffixes(kind)}:
                    exact.append(folder / file)
                else:
                    other += [(folder / file, k) for k in KINDS if k != kind and file in {f"{name}{s}" for s in suffixes(k)}]

        def rel(path: Path) -> str:
            return path.relative_to(self.root).as_posix()

        parts: list[str] = []
        if exact:
            kept = ", ".join(f"{folder}/" for folder in KINDS[kind][1])
            where = (f"add {rel(exact[0].parent)} to" if len(exact) == 1 else "add their folders to")
            parts.append(f"found {' and '.join(rel(p) for p in exact)}: {kind}s are read from {kept} (or {where} App(search=[...]))")
        parts += [f"found {rel(path)}, a {k}, not a {kind}" for path, k in other]
        return "".join(f"; {part}" for part in parts)

    def resolve(self, kind: str, ref: str | Path) -> Path:
        """`ref` as a file: a path is used as it is, a bare name is found."""
        return self.find(kind, ref) if is_name(ref) else Path(ref)

    def component_dirs(self) -> list[Path]:
        """The folders the components are in (each once), for `component:` to look in. A name in two is an error."""
        self.index("component")
        out: list[Path] = []
        for folder in self.folders("component"):
            if any(folder.glob(f"*{KINDS['component'][0]}")) or any(folder.glob(f"*{KINDS['stylesheet'][0]}")):
                out.append(folder)
        return out

    def style_dirs(self) -> list[Path]:
        """The folders that have `*_Style.yaml` files, for a node's `style:` that names one."""
        return [folder for folder in self.folders("style") if any(folder.glob(f"*{KINDS['style'][0]}"))]

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


def resolve_view(project: Optional[Project], ref: str | Path, viewmodel_cls: Optional[type] = None) -> tuple[Path, type]:
    """The view file and the ViewModel class for `ref`: a path, or a name found in `project`. A class left out is
    found by the view's name, beside the view (`Name_ViewModel.py`) or in the project. One rule for `app.load`,
    `instantiate` and `Repeater`."""
    if is_name(ref):
        if project is None:
            raise ProjectError(f"{ref!r} is a name, but there is no project to look in: it needs an App "
                               "(its root and folders), or pass the file's path")
        path = project.find("view", ref)
    else:
        path = Path(ref)
    if viewmodel_cls is None:
        prefix = view_stem(path)
        beside = path.with_name(f"{prefix}{KINDS['viewmodel'][0]}")
        if is_view_file(path) and beside.is_file():
            viewmodel_cls = load_viewmodel(beside, prefix)
        elif project is not None:
            viewmodel_cls = project.viewmodel(prefix)
        else:
            raise ProjectError(f"no ViewModel class given, and {beside.name} isn't beside {path.name} "
                               "(and there is no project to look in)")
    return path, viewmodel_cls


def resolve_embedded(project: Optional[Project], ref: str | Path, base: Optional[Path] = None) -> tuple[Path, Optional[type]]:
    """The view file for a `view:` node, and its ViewModel class, or `None` for a view that has none: a path, or a name
    found in `project` (a relative path is the folder `base`'s, the file that names it); the class is
    `Name_ViewModel.py` beside the view or in the project, and no such file is fine."""
    if is_name(ref):
        if project is None:
            raise ProjectError(f"{ref!r} is a name, but there is no project to look in: it needs an App "
                               "(its root and folders), or give the file's path")
        path = project.find("view", ref)
    else:
        path = Path(ref)
        if base is not None and not path.is_absolute():
            path = base / path
    if not is_view_file(path):
        return path, None
    prefix = view_stem(path)
    beside = path.with_name(f"{prefix}{KINDS['viewmodel'][0]}")
    if beside.is_file():
        return path, load_viewmodel(beside, prefix)
    if project is not None and prefix in project.index("viewmodel"):
        return path, project.viewmodel(prefix)
    return path, None


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
