#!/usr/bin/env python3
"""
Registra la traducción al inglés (locale "en") del metacampo custom.ingredients
de los productos de shopify_update_ingredients.HANDLES.

Reutiliza la autenticación de shopify_update_ingredients.py (Keychain, nunca se imprime nada).
Scopes: read_products + write_translations (la app ya lo tiene).

Uso:
  python3 tools/shopify_update_ingredients_en.py            # dry-run (solo lee)
  python3 tools/shopify_update_ingredients_en.py --apply    # escribe
  python3 tools/shopify_update_ingredients_en.py --rollback _backup/ingredients_en_XXXX.json --apply
"""
import argparse, json, sys, time
import shopify_update_ingredients as base

LOCALE = "en"

EN = {
    "jamon-bellota-50-iberico-pieza-entera":
        "Iberian pork ham, salt, dextrose, sugar, preservative (E-252) and antioxidant (E-316).",
    "lomo-bellota-iberico":
        "Iberian Bellota Loin (100% Iberian pork), salt, natural spices, garlic, preservatives (E-250, E-252), antioxidant (E-301).",
    "lomo-bellota-iberico-loncheado-2":
        "Bellota Ibérico Loin (100% Iberian pork), salt, natural spices, garlic, preservatives (E-250, E-252), antioxidant (E-301).",
    "lomo-cebo-campo-50-iberico":
        "Iberian Cebo de Campo Loin 50% (50% Iberian pork + 50% white pork), salt, natural spices, garlic, preservatives (E-250, E-252), antioxidant (E-301).",
    "lomo-cebo-campo-50-iberico-loncheado":
        "Loin of Iberian Acorn-fed Pig 50% (50% Iberian pork + 50% white pork), salt, natural spices, garlic, preservatives (E-250, E-252), antioxidant (E-301).",
    "salchichon-bellota-iberico":
        "Iberian Acorn-fed Cured Sausage (100% Iberian pork), salt, spices (black pepper), garlic, preservatives (E-250, E-252), antioxidant (E-301).",
    "salchichon-bellota-iberico-loncheado":
        "Ibérico acorn-fed salchichón (100% Iberian pork), salt, spices (black pepper), garlic, preservatives (E-250, E-252), antioxidant (E-301).",
    "chorizo-bellota-iberico":
        "Iberian Acorn-fed Chorizo (100% Iberian pork), salt, spices (sweet and hot paprika), garlic, preservatives (E-250, E-252).",
    "chorizo-bellota-iberico-loncheado":
        "Iberian Acorn-fed Chorizo (100% Iberian pork), salt, spices (sweet and hot paprika), garlic, preservatives (E-250, E-252).",
    "lomito-presa-bellota":
        "Acorn-fed Iberian Pork Loin (100% Iberian pig), salt, natural spices (black pepper), preservatives (E-250, E-252).",
    "lomo-bellota-iberico-loncheado-1":
        "Acorn-fed Iberian Pork Presa Loin (100% Iberian pig), salt, natural spices (black pepper), preservatives (E-250, E-252).",
}

Q_MF = 'query($h:String!){productByHandle(handle:$h){metafield(namespace:"custom",key:"ingredients"){id value}}}'
Q_TR = """query($id:ID!){translatableResource(resourceId:$id){
  translatableContent{key digest}
  translations(locale:"%s"){key value outdated}}}""" % LOCALE
M_REG = """mutation($id:ID!,$t:[TranslationInput!]!){
  translationsRegister(resourceId:$id,translations:$t){
    translations{key value} userErrors{field message code}}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", metavar="JSON")
    a = ap.parse_args()

    token, scopes = base.get_token()
    print(f"Conectado a {base.SHOP}.")
    if a.apply and "write_translations" not in scopes:
        sys.exit("Falta el scope write_translations en la app.")

    desired = EN
    if a.rollback:
        desired = {h: d["antes"] for h, d in json.load(open(a.rollback)).items() if d["antes"]}

    plan, backup = [], {}
    for h, new in desired.items():
        mf = base.gql(token, Q_MF, {"h": h})["productByHandle"]
        if not mf or not mf["metafield"]:
            print(f"AVISO: {h} sin producto o sin metacampo"); continue
        mid = mf["metafield"]["id"]
        r = base.gql(token, Q_TR, {"id": mid})["translatableResource"]
        digest = next((c["digest"] for c in r["translatableContent"] if c["key"] == "value"), None)
        cur = next((t for t in r["translations"] if t["key"] == "value"), None)
        if cur and cur["value"] == new and not cur["outdated"]:
            print(f"= {h}: sin cambios"); continue
        print(f"\n~ {h}\n    antes:   {cur['value'] if cur else None}\n    después: {new}")
        plan.append((mid, {"key": "value", "value": new, "locale": LOCALE, "translatableContentDigest": digest}))
        backup[h] = {"id": mid, "antes": cur["value"] if cur else None, "despues": new}

    print(f"\n{len(plan)} traducción(es) a registrar.")
    if not a.apply:
        print("DRY-RUN: no se ha escrito nada. Repite con --apply para aplicar.")
        return
    if not plan:
        return

    base.BACKUP_DIR.mkdir(exist_ok=True)
    bpath = base.BACKUP_DIR / f"ingredients_en_{time.strftime('%Y%m%d-%H%M%S')}.json"
    bpath.write_text(json.dumps(backup, ensure_ascii=False, indent=2))
    print(f"Backup: {bpath}")
    for mid, t in plan:
        res = base.gql(token, M_REG, {"id": mid, "t": [t]})["translationsRegister"]
        if res["userErrors"]:
            sys.exit("userErrors: " + json.dumps(res["userErrors"], ensure_ascii=False))
    print("OK: aplicado. Rollback: python3 tools/shopify_update_ingredients_en.py --rollback", bpath, "--apply")


if __name__ == "__main__":
    main()
