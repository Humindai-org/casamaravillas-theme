#!/usr/bin/env python3
"""
Embutidos enteros (pieza): precios y SKUs vigentes (495-499).
OJO: los precios del escandallo del cliente (20,40/42,80/55,50/46,70 €, SKU 471-475) estaban por debajo de margen y se descartaron (2026-10-22).

Reutiliza la auth (Keychain, client credentials) de shopify_update_ingredients.py.

Uso:
  python3 tools/shopify_update_embutidos_enteros.py            # dry-run (solo lee)
  python3 tools/shopify_update_embutidos_enteros.py --apply    # aplica (guarda backup en _backup/)
  python3 tools/shopify_update_embutidos_enteros.py --rollback _backup/embutidos_enteros_XXXX.json --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

# handle -> (precio, sku). Precios anteriores, vigentes en tienda.
PLAN = {
    "chorizo-bellota-iberico":     ("25.10", "495"),
    "salchichon-bellota-iberico":  ("25.10", "496"),
    "lomo-cebo-campo-50-iberico":  ("57.90", "497"),
    "lomo-bellota-iberico":        ("71.80", "498"),
    "lomito-presa-bellota":        ("71.80", "499"),
}
WARN_PCT = 15  # avisa si el precio cambia más de este %

Q_PRODUCT = """query($h:String!){ productByHandle(handle:$h){ id title
  variants(first:5){ nodes{ id title sku price } } } }"""
Q_SKUS = """query($c:String){ productVariants(first:100, after:$c){ pageInfo{hasNextPage endCursor}
  nodes{ id sku title product{ title status } } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def sku_owners(token):
    out, cur = {}, None
    while True:
        r = base.gql(token, Q_SKUS, {"c": cur})["productVariants"]
        for v in r["nodes"]:
            if v["sku"]:
                out.setdefault(v["sku"], []).append((v["id"], f"{v['product']['title']} ({v['product']['status']})"))
        if not r["pageInfo"]["hasNextPage"]:
            return out
        cur = r["pageInfo"]["endCursor"]


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, _ = base.get_token()

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: restaurar precios y SKUs anteriores")
        for h, p in bk.items():
            print(" ", h, [(v["sku"], v["price"]) for v in p["variants"]["nodes"]])
        if not apply:
            print("(dry-run) añade --apply")
            return
        for h, p in bk.items():
            check(base.gql(token, M_VAR, {"p": p["id"], "v": [
                {"id": v["id"], "price": v["price"], "inventoryItem": {"sku": v["sku"]}} for v in p["variants"]["nodes"]]}),
                "productVariantsBulkUpdate")
        print("Restaurado.")
        return

    owners = sku_owners(token)
    products, ups, conflicts = {}, {}, []
    print("== EMBUTIDOS ENTEROS ==")
    for h, (price, sku) in PLAN.items():
        p = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
        if not p:
            sys.exit(f"No existe {h}")
        if len(p["variants"]["nodes"]) != 1:
            sys.exit(f"{h}: se esperaba 1 variante")
        v = p["variants"]["nodes"][0]
        products[h] = p
        ups[h] = [{"id": v["id"], "price": price, "inventoryItem": {"sku": sku}}]
        for vid, label in owners.get(sku, []):
            if vid != v["id"]:
                conflicts.append((sku, label))
        chg = (float(price) - float(v["price"])) / float(v["price"]) * 100
        flag = "   <-- REVISAR" if abs(chg) > WARN_PCT else ""
        print(f"  {p['title']:38} precio {v['price']:>6} -> {price:>6} ({chg:+.0f}%)   sku {v['sku']} -> {sku}{flag}")
    if conflicts:
        sys.exit(f"Abortado: SKU ya usado por otra variante: {conflicts}")
    print("\n  Sin conflictos de SKU en el resto de la tienda.")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"embutidos_enteros_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump(products, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)
    for h, p in products.items():
        check(base.gql(token, M_VAR, {"p": p["id"], "v": ups[h]}), "productVariantsBulkUpdate")
        print("  OK", h)
    print("Aplicado.")


if __name__ == "__main__":
    main()
