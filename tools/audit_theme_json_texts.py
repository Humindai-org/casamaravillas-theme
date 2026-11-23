#!/usr/bin/env python3
"""Solo lectura. Compara los textos en español de templates/*.json, sections/*.json y config/settings_data.json del repo
con el contenido traducible del tema en Shopify (por valor): detecta textos NUEVOS/CAMBIADOS (aún sin registrar en T&A)
y textos registrados pero sin traducción EN/FR. Uso: python3 tools/audit_theme_json_texts.py [THEME_ID]"""
import sys, re, json, glob, os
import shopify_update_ingredients as base
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME = sys.argv[1] if len(sys.argv) > 1 else "199321256274"
ES = re.compile(r"[áéíóúñ¿¡]|\b(el|la|los|las|del|con|para|tu|tus|una|en|ver|más|envío|jamón|comprar|nuestr\w+|gratis|desde|todos|sin|por|que|como)\b", re.I)
TYPES = ["ONLINE_STORE_THEME_JSON_TEMPLATE", "ONLINE_STORE_THEME_SECTION_GROUP", "ONLINE_STORE_THEME_SETTINGS_DATA_SECTIONS", "ONLINE_STORE_THEME_SETTINGS_CATEGORY", "ONLINE_STORE_THEME"]
Q = """query($t:TranslatableResourceType!,$after:String){translatableResources(first:50,resourceType:$t,after:$after){
 pageInfo{hasNextPage endCursor} nodes{resourceId translatableContent{key value} en: translations(locale:"en"){key value outdated} fr: translations(locale:"fr"){key value outdated}}}}"""
def norm(v): return re.sub(r"\s+", " ", v).strip()
def live_map():
    m = {}
    tok, _ = base.get_token()
    for t in TYPES:
        after = None
        while True:
            r = base.gql(tok, Q, {"t": t, "after": after})["translatableResources"]
            for n in r["nodes"]:
                if THEME not in n["resourceId"] and t != "ONLINE_STORE_THEME_SETTINGS_DATA_SECTIONS" and "theme_id" in n["resourceId"]: continue
                if "theme_id=" in n["resourceId"] and THEME not in n["resourceId"]: continue
                for c in n["translatableContent"]:
                    st = {}
                    for loc in ("en", "fr"):
                        cur = next((x for x in n[loc] if x["key"] == c["key"]), None)
                        st[loc] = "ok" if cur and cur["value"].strip() and not cur["outdated"] else ("outdated" if cur and cur["value"].strip() else "missing")
                    m.setdefault(norm(c["value"]), []).append((n["resourceId"].split("/")[-1][:40], c["key"][:60], st))
            if not r["pageInfo"]["hasNextPage"]: break
            after = r["pageInfo"]["endCursor"]
    return m
def repo_texts():
    out = []
    for f in sorted(glob.glob(f"{ROOT}/templates/*.json") + glob.glob(f"{ROOT}/sections/*.json") + [f"{ROOT}/config/settings_data.json"]):
        try: d = json.loads(re.sub(r"^\s*/\*.*?\*/", "", open(f).read(), flags=re.S))
        except Exception: continue
        def walk(o, path):
            if isinstance(o, dict):
                for k, v in o.items(): walk(v, path + [k])
            elif isinstance(o, list):
                for i, v in enumerate(o): walk(v, path + [str(i)])
            elif isinstance(o, str):
                k = path[-1]
                if re.search(r"(url|link|image|icon|color|handle|tag|class|font|id|type|style|layout|collection|product|menu|video|filter|source|template|metafield)$", k, re.I): return
                t = norm(re.sub(r"<[^>]+>", " ", o))
                if len(t) > 2 and ES.search(t) and not o.startswith(("shopify://", "http", "/", "#")): out.append((os.path.basename(f), ".".join(path)[-50:], o))
        walk(d, [])
    return out
m = live_map(); new, gap = [], []
for f, k, v in repo_texts():
    hit = m.get(norm(v))
    if not hit: new.append((f, k, v))
    elif not any(s["en"] == "ok" and s["fr"] == "ok" for _, _, s in hit): gap.append((f, k, v, hit[0][2]))
print(f"Tema {THEME}: {len(m)} textos traducibles en Shopify.\n")
print(f"== NUEVOS/CAMBIADOS en el repo (no existen en Shopify; tras subir hay que traducirlos): {len(new)}")
for f, k, v in new: print(f"  {f:<34} {k:<42} {norm(v)[:90]!r}")
print(f"\n== Registrados pero sin traducción EN/FR vigente: {len(gap)}")
for f, k, v, st in gap: print(f"  {f:<34} {k:<42} {st} {norm(v)[:70]!r}")
