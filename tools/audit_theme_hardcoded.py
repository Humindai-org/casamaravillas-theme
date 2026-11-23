#!/usr/bin/env python3
"""Barrido estático (solo lectura): texto en español fijo en .liquid (fuera de schema/comentarios/style)
y strings en español en assets/*.js que no pasan por cmT. Uso: python3 tools/audit_theme_hardcoded.py [--js]"""
import re, glob, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ES = re.compile(r"[áéíóúñ¿¡Á-Ú]|\b(el|la|los|las|del|con|para|tu|tus|una|y|en|ver|más|envío|jamón|comprar|añadir|carrito|pedido|gratis|desde|todos|sin|por|que|como|nuestr\w+|producto\w*|cantidad|total|continuar|cerrar|buscar|siguiente|anterior)\b", re.I)
def clean(src):
    src = re.sub(r"{%-?\s*schema.*?endschema\s*-?%}", "", src, flags=re.S)
    src = re.sub(r"{%-?\s*comment\s*-?%}.*?{%-?\s*endcomment\s*-?%}", "", src, flags=re.S)
    src = re.sub(r"{%-?\s*(stylesheet|javascript).*?end\1\s*-?%}|<style.*?</style>|<!--.*?-->", "", src, flags=re.S)
    src = re.sub(r"{%-?.*?-?%}|{{-?.*?-?}}", " ", src, flags=re.S)  # tags/outputs fuera
    return src
def hits(path):
    raw = open(path).read(); src = clean(raw)
    if "<script" in src:
        js = re.findall(r"<script[^>]*>(.*?)</script>", src, flags=re.S)
        src = re.sub(r"<script.*?</script>", "", src, flags=re.S)
    out = []
    for m in re.finditer(r">([^<>]{3,})<", src):
        t = " ".join(m.group(1).split())
        if len(t) > 2 and ES.search(t) and re.search(r"[A-Za-zÁ-úñ]{3}", t): out.append(("text", t[:90]))
    for m in re.finditer(r'\b(aria-label|alt|placeholder|title|data-[\w-]*(?:label|text|title|message))="([^"{}]{3,})"', src):
        if ES.search(m.group(2)): out.append((m.group(1), m.group(2)[:90]))
    return out
tot = 0
for f in sorted(glob.glob(f"{ROOT}/sections/*.liquid") + glob.glob(f"{ROOT}/snippets/*.liquid") + glob.glob(f"{ROOT}/layout/*.liquid") + glob.glob(f"{ROOT}/templates/*.liquid")):
    h = hits(f)
    if h:
        print(f"\n{os.path.relpath(f, ROOT)}  ({len(h)})")
        for k, t in h[:12]: print(f"   {k}: {t}")
        tot += len(h)
if "--js" in sys.argv:
    for f in sorted(glob.glob(f"{ROOT}/assets/*.js")):
        for i, l in enumerate(open(f), 1):
            if re.search(r"""(['"`])([^'"`\n]*[áéíóúñ¿¡][^'"`\n]*)\1""", l) and "cmT" not in l and not l.strip().startswith(("//", "*")):
                print(f"{os.path.basename(f)}:{i}: {l.strip()[:130]}")
print(f"\n{tot} coincidencias en liquid.")
