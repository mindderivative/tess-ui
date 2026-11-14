"""Spike: YAML view -> TDL text -> tess_dl tree -> dict, compared with the original dict. Not product code.

Mapping: node = block headed by the widget (CamelCase); `Name:`; scalar keys as properties; a dict value = a block headed by the key (lower case);
`children` = a block of node blocks; `if:` / `for:` = an `If` / `For` wrapper around the node; `handlers` = blocks of `Set` / `Call` steps."""
import ast
import glob
import json
import re
import sys

import tess_dl
import yaml

NOTES = {"tuple-for": 0, "slot-with-braces": 0, "handler-as-text": 0}


# -- YAML -> TDL ----------------------------------------------------------------------------------------------------------------------
def val(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        return "[" + ", ".join(val(i) for i in v) + "]"
    s = str(v)
    if s == s.strip() and s.startswith("{{") and s.endswith("}}") and s.count("{{") == 1:
        if "}}" in s[2:-2]:
            NOTES["slot-with-braces"] += 1
            return json.dumps(s, ensure_ascii=False)
        return s
    return json.dumps(s, ensure_ascii=False)


def slot(expr):
    e = str(expr).strip()
    if e.startswith("{{") and e.endswith("}}"):
        return e
    return "{{ " + e + " }}"


def step_text(text):
    """A handler text as Set / Call step blocks, or None."""
    out = []
    for s in ast.parse(text.strip()).body:
        if isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name):
            out.append(f"Set {{ Target: {s.targets[0].id}, Value: {slot(ast.unparse(s.value))} }}")
        elif isinstance(s, ast.AugAssign) and isinstance(s.target, ast.Name):
            expr = ast.unparse(ast.BinOp(ast.Name(s.target.id, ast.Load()), s.op, s.value))
            out.append(f"Set {{ Target: {s.target.id}, Value: {slot(expr)} }}")
        elif isinstance(s, ast.Expr) and isinstance(s.value, ast.Call):
            args = [slot(ast.unparse(a)) for a in s.value.args]
            kw = "".join(f", {k.arg}: {slot(ast.unparse(k.value))}" for k in s.value.keywords)
            out.append(f"Call {{ Action: {json.dumps(ast.unparse(s.value.func))}{', Args: [' + ', '.join(args) + ']' if args else ''}{kw} }}")
        elif isinstance(s, ast.Expr) and isinstance(s.value, ast.Name):
            out.append(f"Call {{ Action: {json.dumps(s.value.id)} }}")
        else:
            return None
    return out


def mapping(key, d, ind):
    lines = [f"{ind}{key} {{"]
    for k, v in d.items():
        if k == "handlers":
            lines += handlers(v, ind + "  ")
        elif isinstance(v, dict):
            lines += mapping(k, v, ind + "  ")
        else:
            lines.append(f"{ind}  {k}: {val(v)}")
    lines.append(f"{ind}}}")
    return lines


def handlers(d, ind):
    lines = [f"{ind}handlers {{"]
    for ev, text in d.items():
        steps = step_text(text) if isinstance(text, str) else None
        if steps is None:
            NOTES["handler-as-text"] += 1
            lines.append(f"{ind}  {ev}: {val(text)}")
        else:
            lines += [f"{ind}  {ev} {{"] + [f"{ind}    {s}" for s in steps] + [f"{ind}  }}"]
    lines.append(f"{ind}}}")
    return lines


def node(n, ind):
    lines = [f"{ind}{n['widget']} {{"]
    if "name" in n:
        lines.append(f"{ind}  Name: {n['name']}")
    for k, v in n.items():
        if k in ("widget", "name", "if", "for", "key"):
            continue
        if k == "children":
            lines.append(f"{ind}  children {{")
            for c in v:
                lines += node(c, ind + "    ")
            lines.append(f"{ind}  }}")
        elif k == "handlers":
            lines += handlers(v, ind + "  ")
        elif isinstance(v, dict):
            lines += mapping(k, v, ind + "  ")
        else:
            lines.append(f"{ind}  {k}: {val(v)}")
    lines.append(f"{ind}}}")
    if "if" in n:
        lines = [f"{ind}If {slot(n['if'])} {{"] + ["  " + line for line in lines] + [f"{ind}}}"]
    if "for" in n:
        target, _, it = str(n["for"]).partition(" in ")
        names = [t.strip() for t in target.split(",")]
        if len(names) > 1:
            NOTES["tuple-for"] += 1
        first = names[0]
        extra = f"{ind}  Target: {json.dumps(target.strip())}\n" if len(names) > 1 else ""
        lines = [f"{ind}For {first} In {slot(it)} Key {slot(n.get('key', 'None'))} {{"] + ([extra.rstrip()] if extra else []) + ["  " + line for line in lines] + [f"{ind}}}"]
    return lines


def to_tdl(d):
    d = dict(d)
    marker = d.pop("tesserae", None)
    params = d.pop("params", None)
    lines = node({**d, **({"params": params} if params else {})}, "")
    return f'---\nTDL: 0.1\nName: {d.get("name", "View")}\nTesserae: "{marker}"\n---\n\n' + "\n".join(lines) + "\n"


# -- TDL tree -> dict -------------------------------------------------------------------------------------------------------------------
def back_value(v):
    if isinstance(v, tess_dl.Word):
        return {"true": True, "false": False, "null": None}.get(v.text, v.text)
    if isinstance(v, tess_dl.String):
        return v.value
    if isinstance(v, tess_dl.Number):
        return v.value
    if isinstance(v, tess_dl.List):
        return [back_value(i) for i in v.items]
    if isinstance(v, tess_dl.Slot):
        return "{{" + v.text + "}}"
    raise ValueError(f"unsupported value {v!r}")


def expr(slot_value):
    return slot_value.text.strip()


def back_step(b):
    p = {e.key: e.value for e in b.entries if isinstance(e, tess_dl.Property)}
    if b.type == "Set":
        return f"{p['Target'].text} = {expr(p['Value'])}"
    args = [expr(a) for a in p["Args"].items] if "Args" in p else []
    args += [f"{k}={expr(v)}" for k, v in p.items() if k not in ("Action", "Args")]
    return f"{back_value(p['Action'])}({', '.join(args)})"


def back_handlers(block):
    out = {}
    for e in block.entries:
        if isinstance(e, tess_dl.Property):
            out[e.key] = back_value(e.value)
        else:
            out[e.type] = "; ".join(back_step(s) for s in e.entries)
    return out


def back_map(block):
    out = {}
    for e in block.entries:
        if isinstance(e, tess_dl.Property):
            out[e.key] = back_value(e.value)
        elif e.type == "handlers":
            out[e.type] = back_handlers(e)
        else:
            out[e.type] = back_map(e)
    return out


def back_node(entry):
    if isinstance(entry, tess_dl.If):
        inner = back_node(entry.body[0])
        inner["if"] = expr(entry.condition)
        return inner
    if isinstance(entry, tess_dl.For):
        extra = [e for e in entry.body if isinstance(e, tess_dl.Property)]
        inner = back_node([e for e in entry.body if not isinstance(e, tess_dl.Property)][0])
        inner["for"] = (back_value(extra[0].value) if extra else entry.variable) + " in " + expr(entry.items)
        key = expr(entry.key)
        if key != "None":
            inner["key"] = key
        return inner
    n = {"widget": entry.type}
    for e in entry.entries:
        if isinstance(e, tess_dl.Property):
            n["name" if e.key == "Name" else e.key] = back_value(e.value)
        elif e.type == "children":
            n["children"] = [back_node(c) for c in e.entries]
        elif e.type == "handlers":
            n["handlers"] = back_handlers(e)
        elif e.type[0].islower():
            n[e.type] = back_map(e)
        else:
            raise ValueError("node-like block where a map was expected")
    return n


def from_tdl(text, path):
    doc = tess_dl.loads(text, path=path)
    n = back_node(doc.root)
    n["tesserae"] = doc.metadata["Tesserae"].value
    return n


# -- comparison -----------------------------------------------------------------------------------------------------------------------
def norm_py(text):
    try:
        return "; ".join(ast.unparse(s) for s in ast.parse(text.strip()).body)
    except SyntaxError:
        return text


def norm(x, key=None):
    if isinstance(x, dict):
        return {k: norm(v, k) for k, v in x.items()}
    if isinstance(x, list):
        return [norm(v) for v in x]
    if key in ("if", "key") and isinstance(x, str):
        return norm_py(x.strip().removeprefix("{{").removesuffix("}}"))
    if key == "for" and isinstance(x, str):
        t, _, it = x.partition(" in ")
        return t.strip() + " in " + norm_py(it.strip().removeprefix("{{").removesuffix("}}"))
    if key == "tesserae":
        return str(x)
    return x


def norm_handlers(x):
    if isinstance(x, dict):
        return {k: (norm_py(v) if k not in ("handlers",) and isinstance(v, str) and False else norm_handlers(v)) for k, v in x.items()}
    return x


def handler_fix(x, parent_key=None):
    if isinstance(x, dict):
        return {k: (handler_fix(v, k) if k != "handlers" else {e: (norm_py(t) if isinstance(t, str) else t) for e, t in v.items()}) for k, v in x.items()}
    if isinstance(x, list):
        return [handler_fix(v) for v in x]
    return x


def main():
    files = sorted(glob.glob("src/tess_ui/views/*_View.yaml"))
    same = bad = 0
    shown = 0
    for f in files:
        d = yaml.safe_load(open(f))
        try:
            text = to_tdl(d)
            doc_errors = tess_dl.parse(text, path=f).errors
            if doc_errors:
                raise ValueError(f"TDL error {doc_errors[0].code} line {doc_errors[0].origin.line}: {doc_errors[0].message}")
            got = handler_fix(norm(from_tdl(text, f)))
            want = handler_fix(norm(d))
            if got == want:
                same += 1
            else:
                raise ValueError("different: " + first_diff(want, got))
        except Exception as e:  # noqa: BLE001
            bad += 1
            if shown < 8:
                print(f.split("/")[-1], "-", str(e)[:300])
                shown += 1
    print(f"views {len(files)} round-trip-equal {same} not {bad}; notes {NOTES}")


def first_diff(a, b, path=""):
    if type(a) is not type(b):
        return f"{path}: {a!r:.60} vs {b!r:.60}"
    if isinstance(a, dict):
        for k in a.keys() | b.keys():
            if k not in a or k not in b:
                return f"{path}/{k}: missing in {'original' if k not in a else 'result'}"
            r = first_diff(a[k], b[k], f"{path}/{k}")
            if r:
                return r
        return ""
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: len {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            r = first_diff(x, y, f"{path}[{i}]")
            if r:
                return r
        return ""
    return "" if a == b else f"{path}: {a!r:.60} vs {b!r:.60}"


if __name__ == "__main__":
    main()
