#!/usr/bin/env python3
"""Lista (solo lectura) texto en español fijo por archivo y línea: elementos de una línea y atributos aria/alt/placeholder/title.
Uso: python3 tools/i18n_extract.py sections/a.liquid sections/b.liquid"""
import re, sys
ES = re.compile(r"[áéíóúñ¿¡ÁÉÍÓÚÑ]|\b(el|la|los|las|del|con|para|tu|tus|una|en|ver|más|envío|gratis|desde|todos|sin|por|que|como|nuestr\w+|producto\w*|cantidad|elige|selecciona|buscar|zona|teléfono|calidad|jamón|sabor|raza|descripción|fecha|pedido)\b", re.I)
def main(paths):
    for p in paths:
        src = open(p).read().split("\n")
        skip = None
        for i, l in enumerate(src, 1):
            s = l.strip()
            if skip:
                if re.search(skip, s): skip = None
                continue
            m = re.match(r"<(style|script)\b", s) or re.match(r"{%-?\s*(schema|comment|stylesheet|javascript)\b", s)
            if m and not re.search(r"</(style|script)>|end(schema|comment|stylesheet|javascript)", s):
                skip = r"</(style|script)>|end(schema|comment|stylesheet|javascript)"; continue
            t = re.sub(r"{%-?.*?-?%}|{{-?.*?-?}}", "", s)
            for m in re.finditer(r'\b(aria-label|alt|placeholder|title|data-[\w-]*(?:label|text|title))="([^"]*)"', l):
                if ES.search(re.sub(r"{%-?.*?-?%}|{{-?.*?-?}}", "", m.group(2))) and not m.group(2).startswith("{{"):
                    print(f"{p}:{i}: ATTR {m.group(1)}={m.group(2)[:100]}")
            txt = re.sub(r"<[^>]+>", " ", t); txt = " ".join(txt.split())
            if txt and ES.search(txt) and re.search(r"[A-Za-zÁ-úñ]{3}", txt):
                print(f"{p}:{i}: {s[:230]}")
main(sys.argv[1:])
