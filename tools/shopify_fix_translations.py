#!/usr/bin/env python3
"""
Corrige/completa traducciones de Shopify (Translate & Adapt) para en y fr:
opciones de variante, menú, ajustes del tema y metacampos de origen.

Es "por reglas": busca recursos cuyo texto ORIGINAL (es) coincide con RULES y registra
la traducción con el digest actual (lo que además limpia el aviso "outdated").
Reutiliza la auth de shopify_update_ingredients.py (Keychain, nunca se imprime nada).
Scopes: read_locales + write_translations (la app ya los tiene).

Uso:
  python3 tools/shopify_fix_translations.py                    # dry-run (solo lee)
  python3 tools/shopify_fix_translations.py --apply            # escribe (backup en _backup/)
  python3 tools/shopify_fix_translations.py --rollback _backup/translations_XXXX.json --apply
"""
import argparse, json, sys, time
import shopify_update_ingredients as base

NBSP = " "

# (tipo de recurso, key, texto original) -> {locale: traducción}
RULES = [
    ("PRODUCT_OPTION", "name", "Corte", {"en": "Cut", "fr": "Coupe"}),
    ("PRODUCT_OPTION", "name", "Selecciona tu vino", {"en": "Choose your wine", "fr": "Choisissez votre vin"}),
    ("PRODUCT_OPTION_VALUE", "name", "Cortado a Mano · 80 g", {"en": "Hand Cut · 80 g", "fr": "Coupé à la main · 80 g"}),
    ("PRODUCT_OPTION_VALUE", "name", "Cortado a Máquina · 100 g", {"en": "Machine Cut · 100 g", "fr": "Coupé à la machine · 100 g"}),
    ("LINK", "title", "Packs & Regalos", {"en": "Packs & Gifts", "fr": "Coffrets & Cadeaux"}),
    ("METAFIELD", "value", "Salamanca, España", {"en": "Salamanca, Spain", "fr": "Salamanque, Espagne"}),
    ("METAFIELD", "value", "7–8 kg, 8–9 kg o 9–10 kg", {"en": "7–8 kg, 8–9 kg or 9–10 kg", "fr": "7–8 kg, 8–9 kg ou 9–10 kg"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "accordion_dA6gdX.title:", "Cata", {"en": "Tasting", "fr": "Dégustation"}),
    ("ONLINE_STORE_THEME_JSON_TEMPLATE", "product_information_zDBpen.card3_title:", "Alérgenos e Ingredientes",
     {"en": "Allergens & Ingredients", "fr": "Allergènes et ingrédients"}),
    ("ONLINE_STORE_THEME", "section.index.json.newsletter.success_text:",
     "¡Gracias por suscribirte! Te escribiremos pronto.",
     {"en": "Thank you for subscribing! We'll be in touch soon.", "fr": "Merci pour votre inscription ! Nous vous écrirons bientôt."}),
    ("ONLINE_STORE_THEME", "main.pack_options:", "1 ud., 10 ud.",
     {"en": "1 pc., 10 pcs.", "fr": "1 u., 10 u."}),
    ("ONLINE_STORE_THEME", "marquee.text_peninsula:",
     "Jamón Ibérico de Bellota | Embutidos Artesanales | Packs Regalo | Envío en 24–48h | Tres Generaciones | Calidad Garantizada | Dehesa Española",
     {"en": "Acorn-fed Iberian Ham | Artisan Cured Meats | Gift Packs | Delivery in 24–48h | Three Generations | Guaranteed Quality | Spanish Dehesa",
      "fr": "Jambon Ibérique de Bellota | Charcuteries Artisanales | Coffrets Cadeaux | Livraison en 24–48h | Trois Générations | Qualité Garantie | Dehesa Espagnole"}),
    ("ONLINE_STORE_THEME", "announcement_text_peninsula:",
     f"Envío gratis a partir de <em>€80</em> {NBSP}·{NBSP} Entrega en 24–48h {NBSP}·{NBSP} Ibéricos Seleccionados",
     {"en": f"Free shipping from <em>€80</em> {NBSP}·{NBSP} Delivery in 24–48h {NBSP}·{NBSP} Selected Iberian Products",
      "fr": f"Livraison offerte dès <em>€80</em> {NBSP}·{NBSP} Livraison en 24–48h {NBSP}·{NBSP} Ibériques Sélectionnés"}),
]

# Traducciones vigentes pero erróneas que sí hay que sobrescribir: (texto original, locale)
FORCE = {("Corte", "en"), ("Cata", "en"), ("Cata", "fr")}  # "Court" y "Cata" (sin traducir) estaban mal

TYPES = sorted({r[0] for r in RULES})
Q = """query($t:TranslatableResourceType!,$after:String){translatableResources(first:100,resourceType:$t,after:$after){
  pageInfo{hasNextPage endCursor}
  nodes{resourceId translatableContent{key value digest}
    en: translations(locale:"en"){key value outdated}
    fr: translations(locale:"fr"){key value outdated}}}}"""
M_REG = """mutation($id:ID!,$t:[TranslationInput!]!){
  translationsRegister(resourceId:$id,translations:$t){userErrors{field message code}}}"""


def all_nodes(token, rtype):
    after = None
    while True:
        r = base.gql(token, Q, {"t": rtype, "after": after})["translatableResources"]
        yield from r["nodes"]
        if not r["pageInfo"]["hasNextPage"]:
            return
        after = r["pageInfo"]["endCursor"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", metavar="JSON")
    a = ap.parse_args()
    token, scopes = base.get_token()
    print(f"Conectado a {base.SHOP}.")
    if a.apply and "write_translations" not in scopes:
        sys.exit("Falta el scope write_translations en la app.")

    plan = []  # (resourceId, translation-input, antes)
    if a.rollback:
        for p in json.load(open(a.rollback)):
            if p["antes"] is not None:
                plan.append((p["id"], {"key": p["key"], "value": p["antes"], "locale": p["locale"],
                                       "translatableContentDigest": p["digest"]}, p["despues"]))
    else:
        for rtype in TYPES:
            rules = [r for r in RULES if r[0] == rtype]
            for n in all_nodes(token, rtype):
                for c in n["translatableContent"]:
                    for _, kpart, src, tr in rules:
                        if c["value"] != src or kpart not in c["key"]:
                            continue
                        for loc, new in tr.items():
                            cur = next((t for t in n[loc] if t["key"] == c["key"]), None)
                            # Solo rellena huecos y outdated; no pisa traducciones vigentes salvo las erróneas de FORCE.
                            if cur and not cur["outdated"] and (src, loc) not in FORCE:
                                continue
                            if cur and cur["value"] == new and not cur["outdated"]:
                                continue
                            rid = n["resourceId"].split("/")[-1]
                            print(f"~ [{loc}] {rtype} {rid} {c['key'][:60]}\n    antes:   {cur['value'] if cur else None!r}\n    después: {new!r}")
                            plan.append((n["resourceId"], {"key": c["key"], "value": new, "locale": loc,
                                                           "translatableContentDigest": c["digest"]},
                                         cur["value"] if cur else None))

    print(f"\n{len(plan)} traducción(es) a registrar.")
    if not a.apply:
        print("DRY-RUN: no se ha escrito nada. Repite con --apply para aplicar.")
        return
    if not plan:
        return
    base.BACKUP_DIR.mkdir(exist_ok=True)
    bpath = base.BACKUP_DIR / f"translations_{time.strftime('%Y%m%d-%H%M%S')}.json"
    bpath.write_text(json.dumps([
        {"id": rid, "key": t["key"], "locale": t["locale"], "digest": t["translatableContentDigest"],
         "antes": antes, "despues": t["value"]} for rid, t, antes in plan], ensure_ascii=False, indent=2))
    print(f"Backup: {bpath}")
    for rid, t, _ in plan:
        res = base.gql(token, M_REG, {"id": rid, "t": [t]})["translationsRegister"]
        if res["userErrors"]:
            sys.exit("userErrors: " + json.dumps(res["userErrors"], ensure_ascii=False))
    print("OK: aplicado. Rollback: python3 tools/shopify_fix_translations.py --rollback", bpath, "--apply")
    print("Nota: el rollback solo restaura traducciones que existían antes; las nuevas quedan (bórralas desde Translate & Adapt si hace falta).")


if __name__ == "__main__":
    main()
