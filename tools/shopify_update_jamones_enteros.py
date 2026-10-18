#!/usr/bin/env python3
"""
Jamón entero (pieza entera): precios/SKUs del escandallo (450-458) y nuevo rango 9-10 kg.

Reutiliza la auth (Keychain, client credentials) de shopify_update_ingredients.py.

Uso:
  python3 tools/shopify_update_jamones_enteros.py            # dry-run (solo lee)
  python3 tools/shopify_update_jamones_enteros.py --apply    # aplica (guarda backup en _backup/)
  python3 tools/shopify_update_jamones_enteros.py --rollback _backup/jamones_enteros_XXXX.json --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

OPTION = "Peso"
NEW_VALUE = "9.0kg - 10.0kg"
NEW_WEIGHT_KG = 10.0
WEIGHT_INFO = "7–8 kg, 8–9 kg o 9–10 kg"

# handle -> { valor de la opción Peso: (precio, sku) }. Fuente: ESCANDALLO WEB (columna REDOND., IVA incl.)
PLAN = {
    "jamon-cebo-de-campo-50-iberico-pieza-entera": {  # Selección Bronce
        "7.0kg - 8.0kg": ("258.00", "450"), "8.0kg - 9.0kg": ("290.00", "451"), NEW_VALUE: ("322.00", "452")},
    "jamon-bellota-50-iberico-pieza-entera": {        # Selección Plata
        "7.0kg - 8.0kg": ("382.00", "453"), "8.0kg - 9.0kg": ("430.00", "454"), NEW_VALUE: ("477.00", "455")},
    "jamon-bellota-100-iberico-pieza-entera": {       # Selección Oro
        "7.0kg - 8.0kg": ("498.00", "456"), "8.0kg - 9.0kg": ("561.00", "457"), NEW_VALUE: ("623.00", "458")},
}

Q_PRODUCT = """query($h:String!){ productByHandle(handle:$h){ id title
  options{ id name optionValues{ name } }
  metafield(namespace:"custom", key:"weight_info"){ value }
  variants(first:20){ nodes{ id title sku price selectedOptions{ name value } } } } }"""
Q_SKUS = """query($c:String){ productVariants(first:100, after:$c){ pageInfo{hasNextPage endCursor}
  nodes{ id sku title product{ title status } } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""
M_CREATE = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkCreate(productId:$p, variants:$v){ productVariants{ id title sku } userErrors{ field message } } }"""
M_DELETE = """mutation($p:ID!,$v:[ID!]!){
  productVariantsBulkDelete(productId:$p, variantsIds:$v){ userErrors{ field message } } }"""
M_MF = """mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }"""


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def all_skus(token):
    out, cur = {}, None
    while True:
        r = base.gql(token, Q_SKUS, {"c": cur})["productVariants"]
        for v in r["nodes"]:
            if v["sku"]:
                out.setdefault(v["sku"], []).append(f"{v['product']['title']} / {v['title']} ({v['product']['status']})")
        if not r["pageInfo"]["hasNextPage"]:
            return out
        cur = r["pageInfo"]["endCursor"]


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, _ = base.get_token()

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: restaurar precios/SKUs y borrar la variante", NEW_VALUE)
        if not apply:
            print("(dry-run) añade --apply")
            return
        for h, p in bk["products"].items():
            cur = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
            new_ids = [v["id"] for v in cur["variants"]["nodes"] if v["selectedOptions"][0]["value"] == NEW_VALUE]
            old = [{"id": v["id"], "price": v["price"], "inventoryItem": {"sku": v["sku"]}} for v in p["variants"]["nodes"]]
            check(base.gql(token, M_VAR, {"p": p["id"], "v": old}), "productVariantsBulkUpdate")
            if new_ids:
                check(base.gql(token, M_DELETE, {"p": p["id"], "v": new_ids}), "productVariantsBulkDelete")
            if p.get("weight_info"):
                check(base.gql(token, M_MF, {"m": [{"ownerId": p["id"], "namespace": "custom", "key": "weight_info",
                      "type": "single_line_text_field", "value": p["weight_info"]}]}), "metafieldsSet")
        print("Restaurado.")
        return

    products = {}
    for h in PLAN:
        p = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
        if not p:
            sys.exit(f"No existe {h}")
        if p["options"][0]["name"] != OPTION:
            sys.exit(f"{h}: la primera opción no es '{OPTION}'")
        products[h] = p

    skus = all_skus(token)
    print("== JAMONES ENTEROS ==")
    updates, creates, conflicts = {}, {}, []
    for h, p in products.items():
        print(f"  {p['title']}")
        ups = []
        existing = {v["selectedOptions"][0]["value"]: v for v in p["variants"]["nodes"]}
        for val, (price, sku) in PLAN[h].items():
            v = existing.get(val)
            for other in skus.get(sku, []):
                if not v or v["id"] not in other:  # SKU ya usado por otra variante
                    if not (v and other.startswith(p["title"]) and other.split(" / ")[1].startswith(v["title"])):
                        conflicts.append((sku, other))
            if v:
                print(f"    {val:16} precio {v['price']:>7} -> {price:>7}   sku {v['sku']} -> {sku}")
                ups.append({"id": v["id"], "price": price, "inventoryItem": {"sku": sku}})
            else:
                print(f"    {val:16} NUEVA variante: precio {price:>7}   sku {sku}   peso de envío {NEW_WEIGHT_KG:g} kg")
                creates[h] = {"optionValues": [{"optionName": OPTION, "name": val}], "price": price,
                              "inventoryPolicy": "DENY", "taxable": True,
                              "inventoryItem": {"sku": sku, "tracked": False,
                                                "measurement": {"weight": {"value": NEW_WEIGHT_KG, "unit": "KILOGRAMS"}}}}
        updates[h] = ups
        print(f"    metacampo custom.weight_info: {p['metafield']['value'] if p['metafield'] else None!r} -> {WEIGHT_INFO!r}")
    if conflicts:
        print("\n¡SKU ya usado por otra variante!", conflicts)
        sys.exit("Abortado: resuelve los SKUs duplicados antes de aplicar.")
    print("\n  Sin conflictos de SKU en el resto de la tienda.")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"jamones_enteros_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"products": {h: {"id": p["id"], "variants": p["variants"],
                               "weight_info": p["metafield"]["value"] if p["metafield"] else None}
                            for h, p in products.items()}}, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)
    for h, p in products.items():
        if updates[h]:
            check(base.gql(token, M_VAR, {"p": p["id"], "v": updates[h]}), "productVariantsBulkUpdate")
        if h in creates:
            check(base.gql(token, M_CREATE, {"p": p["id"], "v": [creates[h]]}), "productVariantsBulkCreate")
        check(base.gql(token, M_MF, {"m": [{"ownerId": p["id"], "namespace": "custom", "key": "weight_info",
              "type": "single_line_text_field", "value": WEIGHT_INFO}]}), "metafieldsSet")
        print("  OK", h)
    print("Aplicado.")


if __name__ == "__main__":
    main()
