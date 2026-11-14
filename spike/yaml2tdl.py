"""Spike: shipped YAML view -> TDL text, to see what the language mapping needs. Not product code."""
import json, re, sys, yaml

def scalar(v):
    if v is True: return "true"
    if v is False: return "false"
    if v is None: return "null"
    if isinstance(v, (int, float)): return json.dumps(v)
    s = str(v)
    if s.strip().startswith("{{") and s.strip().endswith("}}") and s.count("{{") == 1 and "\n" not in s: return s.strip()  # one slot
    return json.dumps(s, ensure_ascii=False)  # a quoted string (slots inside quotes are plain text in TDL: mixed ones are listed as a finding)

def value(v, ind):
    if isinstance(v, list) and all(not isinstance(i, (dict, list)) for i in v): return "[" + ", ".join(scalar(i) for i in v) + "]"
    return scalar(v)

def props(d, ind, skip=()):
    out = []
    for k, v in d.items():
        if k in skip: continue
        if isinstance(v, dict): out.append(f"{ind}{head(k)} {{\n" + props(v, ind + '  ') + f"{ind}}}\n")
        elif isinstance(v, list) and any(isinstance(i, dict) for i in v):
            out.append(f"{ind}{head(k)} {{\n" + "".join(node(i, ind + '  ') for i in v) + f"{ind}}}\n")
        else: out.append(f"{ind}{k}: {value(v, ind)}\n")
    return "".join(out)

def head(k): return k[:1].upper() + k[1:] if k in ("style", "handlers", "a11y", "children", "params") else k

def node(n, ind):
    if not isinstance(n, dict) or "widget" not in n: return props({"item": n}, ind) if False else f"{ind}# not a node: {n!r}\n"
    body = f"{ind}{n['widget']} {{\n" + (f"{ind}  Name: {n['name']}\n" if "name" in n else "") + props(n, ind + "  ", skip=("widget", "name", "if", "for", "key")) + f"{ind}}}\n"
    if "if" in n:
        cond = n["if"] if str(n["if"]).strip().startswith("{{") else "{{ " + str(n["if"]) + " }}"
        body = f"{ind}If {cond} {{\n" + body.replace("\n" + ind, "\n" + ind + "  ").replace(ind + n['widget'], ind + "  " + n['widget'], 1) + f"{ind}}}\n"
    return body

def convert(path):
    d = yaml.safe_load(open(path))
    marker = d.pop("tesserae", None)
    root = d.get("widget")
    meta = f"---\nTDL: 0.1\nName: {d.get('name', 'View')}\nTesserae: \"{marker}\"\n---\n\n"
    params = d.pop("params", None)
    text = node({**d, "widget": root or "View"}, "")
    if params: text = text.replace("{\n", "{\n  Params {\n" + props(params, "    ") + "  }\n", 1)
    return meta + text

if __name__ == "__main__":
    sys.stdout.write(convert(sys.argv[1]))
