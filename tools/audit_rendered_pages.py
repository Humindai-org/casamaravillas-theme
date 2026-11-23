#!/usr/bin/env python3
"""Rastrea páginas renderizadas en es/en/fr y marca texto en EN/FR idéntico al español (no traducido).
Uso: python3 tools/audit_rendered_pages.py [BASE=http://127.0.0.1:9292] [--json out.json]
Solo lectura. Contra el sitio en vivo espaciar peticiones (429); contra `shopify theme dev` no hace falta."""
import sys, re, json, html, time, urllib.request, urllib.error, collections
BASE = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:9292").rstrip("/")
DELAY = 0.0 if "127.0.0.1" in BASE else 2.5
ES = re.compile(r"[áéíóúñ¿¡]|\b(el|la|los|las|del|con|para|tu|tus|una|en|ver|más|envío|jamón|comprar|añadir|carrito|pedido|gratis|desde|todos|sin|por|que|como|nuestr\w+|producto\w*|cantidad|continuar|cerrar|buscar|siguiente|anterior|cesta|regalo|pack|elige|selecciona)\b", re.I)
# Marcas/nombres propios que se quedan igual en todos los idiomas
OK = re.compile(r"^(casa maravillas|bellota|cebo de campo|cebo|ibérico|pata negra|salamanca|guijuelo|jabugo|dehesa.*|.*©.*|[\d\s.,%€x/–—·:+-]+)$", re.I)
def get(path):
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, headers={"User-Agent": "cm-audit"}), timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, ""
def texts(h):
    h = re.sub(r"(?is)<(script|style|svg|noscript|template)\b.*?</\1>|<!--.*?-->", " ", h)
    out = set()
    for m in re.finditer(r'\b(?:aria-label|alt|placeholder|title|data-[\w-]*(?:label|text|title|message|tooltip))="([^"]{3,200})"', h):
        out.add(" ".join(html.unescape(m.group(1)).split()))
    body = re.sub(r"(?is)<head.*?</head>", " ", h)
    for t in re.split(r"<[^>]+>", body):
        t = " ".join(html.unescape(t).split())
        if len(t) > 2: out.add(t)
    return out
def paths():
    P = ["/", "/cart", "/search?q=jamon", "/blogs/news", "/pages/nosotros", "/pages/contact", "/pages/informacion-de-envios", "/pages/devoluciones",
         "/pages/guia-del-iberico", "/pages/aviso-legal", "/pages/privacidad", "/pages/politica-de-cookies", "/pages/terminos-y-condiciones",
         "/pages/no-existe-xyz",
         "/policies/shipping-policy", "/policies/refund-policy", "/policies/terms-of-service", "/policies/legal-notice"]
    s, j = get("/collections.json")
    cols = [c["handle"] for c in json.loads(j).get("collections", [])] if s == 200 else []
    P += [f"/collections/{h}" for h in cols]
    s, j = get("/products.json?limit=250")
    prods = json.loads(j).get("products", []) if s == 200 else []
    seen, pick = set(), []
    for p in prods:  # una muestra por tipo de producto + variantes de plantilla
        k = (p.get("product_type"), len(p["variants"]) > 1, "pack" in p["handle"] or "cesta" in p["handle"] or "pack" in " ".join(p.get("tags", [])))
        if k not in seen: seen.add(k); pick.append(p["handle"])
    P += [f"/products/{h}" for h in pick]
    return P, len(prods)
def links(loc):
    s, h = get(f"/{loc}")
    hs = set(re.findall(r'href="(/%s/(?:pages|collections|blogs|policies|products|cart|search|account)[^"#?]*)"' % loc, h))
    return sorted(hs)
def main():
    P, n = paths(); print(f"{BASE}: {len(P)} URLs ({n} productos en catálogo, muestra por tipo)")
    agg = collections.defaultdict(set); report = {}
    for p in P:
        res = {}
        for loc, pre in (("es", ""), ("en", "/en"), ("fr", "/fr")):
            q = (pre + p) if p != "/" else (pre or "/")
            s, h = get(q); res[loc] = (s, texts(h) if s == 200 else set()); time.sleep(DELAY)
        es = res["es"][1]
        row = {"status": {l: res[l][0] for l in res}, "untranslated": {}}
        for loc in ("en", "fr"):
            bad = sorted(t for t in res[loc][1] if t in es and (ES.search(t) or len(t.split()) >= 2) and re.search(r"[A-Za-zÁ-úñ]{3}", t) and not OK.match(t))
            row["untranslated"][loc] = bad
            for t in bad: agg[t].add(p)
        report[p] = row
        print(f"{p:<52} {row['status']}  EN:{len(row['untranslated']['en']):>3}  FR:{len(row['untranslated']['fr']):>3}")
    # páginas con slug traducido: sin comparar con ES, se marcan los textos con aspecto español
    known = {("/" + l + p) for p in P for l in ("en", "fr")}
    for loc in ("en", "fr"):
        for q in links(loc):
            if q in known or "/products/" in q: continue
            st, h = get(q); time.sleep(DELAY)
            if st != 200: print(f"{q:<52} {st}"); continue
            bad = sorted(t for t in texts(h) if ES.search(t) and len(t.split()) >= 2 and not OK.match(t))
            for t in bad: agg[t].add(q)
            print(f"{q:<52} {st}  ES-like:{len(bad):>3}")
    print("\n=== Textos sin traducir (en EN o FR), agrupados ===")
    for t, ps in sorted(agg.items(), key=lambda x: (-len(x[1]), x[0])):
        print(f"[{len(ps):>2} pág.] {t[:110]!r}  ← {sorted(ps)[0]}")
    if "--json" in sys.argv:
        open(sys.argv[sys.argv.index("--json") + 1], "w").write(json.dumps(report, ensure_ascii=False, indent=1))
main()
