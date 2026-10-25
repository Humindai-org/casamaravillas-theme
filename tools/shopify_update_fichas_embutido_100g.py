#!/usr/bin/env python3
"""
Embutido loncheado: el formato pasa de 80 g a 100 g en las 5 fichas (chorizo, salchichón,
lomo de bellota, lomito de presa y lomo de cebo de campo).

Cambia, solo en esos 5 productos:
  - descripción (descriptionHtml): "Formato de 80g", "Peso: 80 g"
  - SEO (título y descripción, = metacampos global.title_tag / global.description_tag)
  - traducciones (en/fr/...) de body_html, meta_title y meta_description que digan "80 g"
  - peso de envío de la variante: 0,08 -> 0,10 kg
NO toca el jamón loncheado ("estuche"), ni ningún otro producto.

Reutiliza la auth de shopify_update_precios_embutido.py (Keychain, client credentials).

Uso:
  python3 -I tools/shopify_update_fichas_embutido_100g.py              # dry-run (solo lee)
  python3 -I tools/shopify_update_fichas_embutido_100g.py --solo-es    # dry-run sin traducciones
  python3 -I tools/shopify_update_fichas_embutido_100g.py --apply      # aplica (backup en _backup/)
  python3 -I tools/shopify_update_fichas_embutido_100g.py --rollback _backup/fichas_embutido_XXXX.json --apply
"""
import importlib.util, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base

HANDLES = [
    "chorizo-bellota-iberico-loncheado",
    "salchichon-bellota-iberico-loncheado",
    "lomo-bellota-iberico-loncheado-2",
    "lomo-bellota-iberico-loncheado-1",   # Lomito de presa
    "lomo-cebo-campo-50-iberico-loncheado",
]
WEIGHT_OLD, WEIGHT_NEW = 0.08, 0.10
TRANSLATION_KEYS = ("body_html", "meta_title", "meta_description")
# 80g / 80 g / 80&nbsp;g / 80 gramos -> 100... (respeta el espaciado original; \b evita 180 g, 0,80 g...)
GRAMS = re.compile(r"(?<![\d.,])80((?:\s|&nbsp;| )?)(g|gr|grs|gramos)\b", re.I)

Q_PRODUCT = """query($h:String!){ productByHandle(handle:$h){ id handle title descriptionHtml seo{ title description }
  variants(first:5){ nodes{ id sku inventoryItem{ measurement{ weight{ value unit } } } } } } }"""
Q_LOCALES = "{ shopLocales{ locale primary published } }"
Q_TRANS = """query($id:ID!,$l:String!){ translatableResource(resourceId:$id){
  translatableContent{ key digest } translations(locale:$l){ key value outdated } } }"""
M_PRODUCT = """mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ id } userErrors{ field message } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""
M_TRANS = """mutation($id:ID!,$t:[TranslationInput!]!){
  translationsRegister(resourceId:$id, translations:$t){ userErrors{ field message } } }"""


def to_100(text):
    return GRAMS.sub(lambda m: f"100{m.group(1)}{m.group(2)}", text or "")


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def snippet(old, new):
    """Fragmento antes -> después alrededor de la primera diferencia."""
    m = GRAMS.search(old)
    a, b = max(0, m.start() - 28), m.end() + 14
    return f"…{old[a:b]!r}…  →  …{to_100(old[a:b])!r}…".replace("\\n", " ")


def weight_of(v):
    w = (v["inventoryItem"].get("measurement") or {}).get("weight")
    return float(w["value"]) if w else None


def fetch_product(token, handle, locales):
    p = base.gql(token, Q_PRODUCT, {"h": handle})["productByHandle"]
    if not p:
        sys.exit(f"No existe {handle}")
    p["translations"] = {}
    for loc in locales:
        r = base.gql(token, Q_TRANS, {"id": p["id"], "l": loc})["translatableResource"]
        p["translations"][loc] = {t["key"]: t for t in r["translations"]}
    return p


def plan_for(p):
    """Cambios previstos de un producto: [(campo, antes, después)] + peso."""
    changes = []
    for label, old in (("descripción [es]", p["descriptionHtml"]), ("SEO título [es]", p["seo"]["title"]),
                       ("SEO descripción [es]", p["seo"]["description"])):
        if GRAMS.search(old or ""):
            changes.append((label, old, to_100(old)))
    for loc, tr in p["translations"].items():
        for key in TRANSLATION_KEYS:
            if key in tr and GRAMS.search(tr[key]["value"] or ""):
                changes.append((f"{key} [{loc}]", tr[key]["value"], to_100(tr[key]["value"])))
    return changes


def register_translations(token, p, wanted):
    """wanted: {locale: {key: value}}; usa los digest ACTUALES del texto en español."""
    digests = {c["key"]: c["digest"] for c in base.gql(token, Q_TRANS, {"id": p["id"], "l": "es"})
               ["translatableResource"]["translatableContent"]}
    for loc, kv in wanted.items():
        items = [{"locale": loc, "key": k, "value": v, "translatableContentDigest": digests[k]} for k, v in kv.items()]
        if items:
            check(base.gql(token, M_TRANS, {"id": p["id"], "t": items}), "translationsRegister")


def main():
    args = sys.argv[1:]
    apply, only_es = "--apply" in args, "--solo-es" in args
    token, scopes = base.get_token()
    sc = scopes.split(",")
    print(f"Tienda: {base.SHOP} | write_products: {'write_products' in sc} | write_translations: "
          f"{'write_translations' in sc}")
    locales = [] if only_es else [l["locale"] for l in base.gql(token, Q_LOCALES)["shopLocales"] if not l["primary"]]

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: restaurar descripción, SEO, peso y traducciones originales de", len(bk["products"]), "productos")
        if not apply:
            print("(dry-run) añade --apply")
            return
        for h, b in bk["products"].items():
            check(base.gql(token, M_PRODUCT, {"p": {"id": b["id"], "descriptionHtml": b["descriptionHtml"],
                  "seo": {"title": b["seoTitle"], "description": b["seoDescription"]}}}), "productUpdate")
            check(base.gql(token, M_VAR, {"p": b["id"], "v": [{"id": v["id"], "inventoryItem": {"measurement":
                  {"weight": {"value": v["weight"], "unit": "KILOGRAMS"}}}} for v in b["variants"]]}),
                  "productVariantsBulkUpdate")
            register_translations(token, {"id": b["id"]}, b["translations"])
            print("  restaurado", h)
        print("Restaurado.")
        return

    products = {h: fetch_product(token, h, locales) for h in HANDLES}
    print(f"\n== FICHAS DEL EMBUTIDO LONCHEADO: 80 g -> 100 g ({'solo español' if only_es else 'es + traducciones'}) ==")
    total = 0
    for h, p in products.items():
        print(f"\n  {p['title']}  [{h}]")
        for label, old, new in plan_for(p):
            total += 1
            n = len(GRAMS.findall(old))
            print(f"    {label:26} {snippet(old, new)}" + (f"  (+{n - 1} más en el mismo campo)" if n > 1 else ""))
        for v in p["variants"]["nodes"]:
            w = weight_of(v)
            if w not in (WEIGHT_OLD, WEIGHT_NEW):
                sys.exit(f"{h}: peso inesperado {w} kg en SKU {v['sku']} (se esperaba {WEIGHT_OLD} o {WEIGHT_NEW}). Abortado.")
            print(f"    {'peso envío SKU ' + str(v['sku']):26} {w:.2f} kg -> {WEIGHT_NEW:.2f} kg" + ("  (ya está)" if w == WEIGHT_NEW else ""))
    print(f"\n  Campos de texto a cambiar: {total} | Variantes: {len(HANDLES)}. No se toca ningún otro producto.")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"fichas_embutido_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"products": {h: {
        "id": p["id"], "descriptionHtml": p["descriptionHtml"], "seoTitle": p["seo"]["title"],
        "seoDescription": p["seo"]["description"],
        "variants": [{"id": v["id"], "sku": v["sku"], "weight": weight_of(v)} for v in p["variants"]["nodes"]],
        "translations": {loc: {k: t["value"] for k, t in tr.items() if k in TRANSLATION_KEYS and GRAMS.search(t["value"] or "")}
                         for loc, tr in p["translations"].items()}}
        for h, p in products.items()}}, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)

    for h, p in products.items():
        check(base.gql(token, M_PRODUCT, {"p": {"id": p["id"], "descriptionHtml": to_100(p["descriptionHtml"]),
              "seo": {"title": to_100(p["seo"]["title"]), "description": to_100(p["seo"]["description"])}}}), "productUpdate")
        check(base.gql(token, M_VAR, {"p": p["id"], "v": [{"id": v["id"], "inventoryItem": {"measurement":
              {"weight": {"value": WEIGHT_NEW, "unit": "KILOGRAMS"}}}} for v in p["variants"]["nodes"]]}),
              "productVariantsBulkUpdate")
        wanted = {loc: {k: to_100(t["value"]) for k, t in tr.items() if k in TRANSLATION_KEYS and GRAMS.search(t["value"] or "")}
                  for loc, tr in p["translations"].items()}
        register_translations(token, p, wanted)
        print("  OK", h)

    print("\nRelectura:")
    bad = False
    for h in HANDLES:
        p = fetch_product(token, h, locales)
        left = plan_for(p)
        stale = [(loc, k) for loc, tr in p["translations"].items() for k, t in tr.items()
                 if k in TRANSLATION_KEYS and t["outdated"]]
        ok_w = all(weight_of(v) == WEIGHT_NEW for v in p["variants"]["nodes"])
        bad = bad or bool(left) or not ok_w
        print(f"  {h:40} '80 g' que quedan: {len(left)} | peso 0,10 kg: {ok_w} | traducciones desactualizadas: {stale or 'ninguna'}")
    print("Aplicado." if not bad else "Aplicado, pero hay diferencias: revisar.")


if __name__ == "__main__":
    main()
