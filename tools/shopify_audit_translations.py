#!/usr/bin/env python3
"""
Auditoría de huecos de traducción en Shopify (solo lectura): recorre TODOS los recursos
traducibles y lista, por idioma (en/fr), los textos sin traducir o desactualizados.

Uso:
  python3 tools/shopify_audit_translations.py                 # resumen + detalle en consola
  python3 tools/shopify_audit_translations.py --json out.json # además guarda el informe completo
  python3 tools/shopify_audit_translations.py --types PRODUCT,COLLECTION

Reutiliza la auth de shopify_update_ingredients.py (Keychain). Scopes: read_locales.
"""
import argparse, json, re, sys, time
import shopify_update_ingredients as base

TYPES = ["PRODUCT", "PRODUCT_OPTION", "PRODUCT_OPTION_VALUE", "COLLECTION", "PAGE", "ARTICLE", "BLOG",
         "MENU", "LINK", "METAFIELD", "METAOBJECT", "SHOP", "SHOP_POLICY", "ONLINE_STORE_THEME",
         "ONLINE_STORE_THEME_JSON_TEMPLATE", "ONLINE_STORE_THEME_SECTION_GROUP",
         "ONLINE_STORE_THEME_SETTINGS_CATEGORY", "ONLINE_STORE_THEME_SETTINGS_DATA_SECTIONS",
         "ONLINE_STORE_THEME_LOCALE_CONTENT", "PACKING_SLIP_TEMPLATE", "EMAIL_TEMPLATE",
         "PAYMENT_GATEWAY", "SELLING_PLAN", "SELLING_PLAN_GROUP", "DELIVERY_METHOD_DEFINITION", "FILTER"]

Q_LOCALES = "{ shopLocales { locale name primary published } }"
Q = """query($t:TranslatableResourceType!,$after:String){translatableResources(first:50,resourceType:$t,after:$after){
  pageInfo{hasNextPage endCursor}
  nodes{resourceId translatableContent{key value digest type}
    en: translations(locale:"en"){key value outdated}
    fr: translations(locale:"fr"){key value outdated}}}}"""

# Valores que no se traducen (URLs, números, handles, colores, JSON, ids, una sola palabra de marca...)
SKIP = re.compile(r"^(https?://|/|shopify://|gid://|#[0-9a-fA-F]{3,8}$|[\d\s.,:%€$+\-–/x×]+$|\{|\[|<\s*(svg|iframe))")


def translatable(c):
    v = (c["value"] or "").strip()
    if not v or SKIP.match(v):
        return False
    if c["type"] in ("URL", "FILE_REFERENCE", "JSON", "LINK", "LIST_URL", "HANDLE"):
        return False
    if re.search(r"(handle|url|link|image|icon|color|id|class|font|width|height|size|type|style|layout)$", c["key"].split(":")[-1].split(".")[-1], re.I):
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--types")
    ap.add_argument("--limit", type=int, default=25, help="máx. ejemplos por tipo en consola")
    a = ap.parse_args()
    token, scopes = base.get_token()
    print(f"Conectado a {base.SHOP}.")
    locs = base.gql(token, Q_LOCALES)["shopLocales"]
    for l in locs:
        print(f"  idioma {l['locale']:<6} {l['name']:<12} primario={l['primary']} publicado={l['published']}")
    targets = [l["locale"] for l in locs if not l["primary"] and l["locale"] in ("en", "fr")]
    types = a.types.split(",") if a.types else TYPES
    report = {}
    for rtype in types:
        after, rows, total = None, [], 0
        while True:
            try:
                r = base.gql(token, Q, {"t": rtype, "after": after})["translatableResources"]
            except SystemExit as e:
                print(f"  ! {rtype}: {e}")
                break
            for n in r["nodes"]:
                for c in n["translatableContent"]:
                    if not translatable(c):
                        continue
                    total += 1
                    for loc in targets:
                        cur = next((t for t in n[loc] if t["key"] == c["key"]), None)
                        state = "missing" if not cur or not (cur["value"] or "").strip() else ("outdated" if cur["outdated"] else None)
                        if state:
                            rows.append({"locale": loc, "state": state, "resource": n["resourceId"], "key": c["key"],
                                         "value": c["value"][:160]})
            if not r["pageInfo"]["hasNextPage"]:
                break
            after = r["pageInfo"]["endCursor"]
            time.sleep(0.3)
        report[rtype] = {"total": total, "gaps": rows}
        if total:
            print(f"\n== {rtype}: {len(rows)} hueco(s) de {total} textos x {len(targets)} idiomas")
            for row in rows[: a.limit]:
                print(f"  [{row['locale']}/{row['state']}] {row['resource'].split('/')[-2]}/{row['resource'].split('/')[-1]} {row['key'][:70]}\n      {row['value']!r}")
            if len(rows) > a.limit:
                print(f"  … y {len(rows) - a.limit} más (usa --json)")
    if a.json:
        open(a.json, "w").write(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\nInforme completo: {a.json}")
    print("\nRESUMEN:", {k: len(v["gaps"]) for k, v in report.items() if v["total"]})


if __name__ == "__main__":
    main()
