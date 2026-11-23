#!/usr/bin/env python3
"""Auditoría estática del tema (solo lectura): defaults de schema en español que ninguna plantilla
sobrescribe (Translate & Adapt no los ve) y que se imprimen vía section/block.settings.*"""
import json, re, glob, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ES = re.compile(r"[áéíóúñ¿¡]|\b(el|la|los|las|de|del|con|para|tu|tus|una|un|y|en|ver|más|envío|jamón|comprar|añadir|nuestr\w+)\b", re.I)
TEXT = {"text", "textarea", "richtext", "inline_richtext", "html"}

def instances():
    """(archivo, tipo, {ids con valor}) por cada instancia real de sección/bloque en plantillas y section groups."""
    res = []
    for f in sorted(glob.glob(f"{ROOT}/templates/*.json") + glob.glob(f"{ROOT}/sections/*.json")):
        try: d = json.loads(re.sub(r"^\s*/\*.*?\*/", "", open(f).read(), flags=re.S))
        except Exception as e:
            print("! no parsea", f, e); continue
        fn = os.path.basename(f)
        for s in d.get("sections", {}).values():
            t = s.get("type")
            res.append((fn, t, {k for k, v in s.get("settings", {}).items() if v not in ("", None)}))
            for b in s.get("blocks", {}).values():
                res.append((fn, f"{t}::{b.get('type')}", {k for k, v in b.get("settings", {}).items() if v not in ("", None)}))
    return res

INST = instances()
out = []
for f in sorted(glob.glob(f"{ROOT}/sections/*.liquid")):
    src = open(f).read()
    m = re.search(r"{%-?\s*schema\s*-?%}(.*?){%-?\s*endschema", src, re.S)
    if not m: continue
    try: sch = json.loads(m.group(1))
    except Exception: continue
    name = os.path.basename(f)[:-7]
    body = src[:m.start()]
    def check(settings, key, label):
        for s in settings or []:
            if s.get("type") in TEXT and isinstance(s.get("default"), str) and ES.search(s["default"]):
                sid = s["id"]
                if not re.search(r"settings\.%s\b" % re.escape(sid), body): continue
                bad = sorted({fn for fn, t, ids in INST if t == key and sid not in ids})
                if bad: out.append((name, label, sid, ",".join(x[:-5] for x in bad), s["default"][:50]))
    check(sch.get("settings"), name, "section")
    for b in sch.get("blocks", []):
        check(b.get("settings"), f"{name}::{b['type']}", f"block:{b['type']}")
for r in out: print(" | ".join(r))
print(f"\n{len(out)} ajustes con default en español usados en plantillas sin valor propio (no traducibles).")
