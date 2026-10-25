#!/usr/bin/env python3
"""
Jamón de bellota 100 %, tramo 9-10 kg (SKU 458): dejar las 4 variantes "Agotado" SIN borrarlas.

Las 4 variantes (Pieza entera, Deshuesado, Corte a máquina, Corte a mano) están hoy con
seguimiento de inventario desactivado (tracked=False), así que figuran siempre disponibles.
Plan: tracked=True + cantidad disponible 0 + política DENY (no vender sin stock).
No toca las otras 8 variantes del producto ni otros productos (cebo de campo, bellota 50 %).

Reutiliza la auth de shopify_update_precios_embutido.py (Keychain, client credentials).

Uso:
  python3 -I tools/shopify_update_agotar_bellota100_9_10kg.py            # dry-run (solo lee)
  python3 -I tools/shopify_update_agotar_bellota100_9_10kg.py --apply    # aplica (backup en _backup/)
  python3 -I tools/shopify_update_agotar_bellota100_9_10kg.py --rollback _backup/agotar_bellota100_XXXX.json --apply

Para volver a vender el tramo cuando Luis Juan confirme existencias: --rollback (vuelve a
tracked=False) o, si hay piezas concretas, poner la cantidad en Shopify (el seguimiento ya estará activo).
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base  # auth y gql ya apuntados a la tienda/credenciales reales

HANDLE = "jamon-bellota-100-iberico-pieza-entera"
OPTION = "Peso"
TARGET_VALUE = "9.0kg - 10.0kg"
TARGET_SKU = "458"
EXPECTED_VARIANTS = 4

Q_PRODUCT = """query($h:String!){ productByHandle(handle:$h){ id title status tracksInventory
  variants(first:100){ nodes{ id title sku price availableForSale inventoryPolicy
    selectedOptions{ name value }
    inventoryItem{ id tracked inventoryLevels(first:10){ nodes{ location{ id name }
      quantities(names:["available"]){ name quantity } } } } } } } }"""
Q_SKU = """query($q:String){ productVariants(first:100, query:$q){ nodes{ id sku } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""
M_QTY = """mutation($i:InventorySetQuantitiesInput!){
  inventorySetQuantities(input:$i){ userErrors{ field message } } }"""


def levels(v):
    """[(locationId, locationName, available)] de una variante."""
    out = []
    for lv in v["inventoryItem"]["inventoryLevels"]["nodes"]:
        q = next((x["quantity"] for x in lv["quantities"] if x["name"] == "available"), None)
        out.append((lv["location"]["id"], lv["location"]["name"], q))
    return out


def fetch(token):
    p = base.gql(token, Q_PRODUCT, {"h": HANDLE})["productByHandle"]
    if not p:
        sys.exit(f"No existe {HANDLE}")
    return p


def opt(v, name):
    return next(o["value"] for o in v["selectedOptions"] if o["name"] == name)


def snapshot(v):
    return {"id": v["id"], "title": v["title"], "sku": v["sku"], "price": v["price"],
            "inventoryItemId": v["inventoryItem"]["id"], "tracked": v["inventoryItem"]["tracked"],
            "policy": v["inventoryPolicy"], "available": v["availableForSale"],
            "levels": [{"locationId": l, "name": n, "available": q} for l, n, q in levels(v)]}


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, scopes = base.get_token()
    sc = scopes.split(",")
    print(f"Tienda: {base.SHOP} | write_products: {'write_products' in sc} | write_inventory: {'write_inventory' in sc}")

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: restaurar seguimiento/política/cantidad de las variantes tocadas")
        for v in bk["changed"]:
            print(f"  {v['title']:34} tracked -> {v['tracked']}  política -> {v['policy']}  "
                  f"cantidad -> {[l['available'] for l in v['levels']]}")
        if not apply:
            print("(dry-run) añade --apply")
            return
        inputs = [{"id": v["id"], "inventoryPolicy": v["policy"], "inventoryItem": {"tracked": v["tracked"]}}
                  for v in bk["changed"]]
        check(base.gql(token, M_VAR, {"p": bk["productId"], "v": inputs}), "productVariantsBulkUpdate")
        quantities = [{"inventoryItemId": v["inventoryItemId"], "locationId": l["locationId"],
                       "quantity": l["available"]} for v in bk["changed"] for l in v["levels"]
                      if l["available"] is not None]
        if quantities and bk["changed"][0]["tracked"]:  # solo se puede fijar cantidad con seguimiento activo
            check(base.gql(token, M_QTY, {"i": {"name": "available", "reason": "correction",
                  "ignoreCompareQuantity": True, "quantities": quantities}}), "inventorySetQuantities")
        print("Restaurado.")
        return

    p = fetch(token)
    all_vars = p["variants"]["nodes"]
    targets = [v for v in all_vars if opt(v, OPTION) == TARGET_VALUE and v["sku"] == TARGET_SKU]
    others = [v for v in all_vars if v not in targets]

    # Comprobaciones de seguridad (abortan si algo no cuadra)
    if len(targets) != EXPECTED_VARIANTS:
        sys.exit(f"Se esperaban {EXPECTED_VARIANTS} variantes {TARGET_VALUE} con SKU {TARGET_SKU}, hay {len(targets)}.")
    in_tramo = [v for v in all_vars if opt(v, OPTION) == TARGET_VALUE]
    if len(in_tramo) != len(targets):
        sys.exit(f"Hay variantes del tramo {TARGET_VALUE} con otro SKU: revisar antes de aplicar.")
    sku_hits = base.gql(token, Q_SKU, {"q": f"sku:{TARGET_SKU}"})["productVariants"]["nodes"]
    if {n["id"] for n in sku_hits} != {v["id"] for v in targets}:
        sys.exit(f"El SKU {TARGET_SKU} existe en variantes fuera de la selección: abortado.")
    if len({v["inventoryItem"]["id"] for v in targets}) != len(targets):
        sys.exit("Dos variantes comparten el mismo inventory item: abortado.")

    print(f"\n== {p['title']} [{HANDLE}] ({p['status']}) ==")
    print(f"  Variantes en total: {len(all_vars)} | a cambiar: {len(targets)} | intactas: {len(others)}")
    print("\n  A CAMBIAR (tramo", TARGET_VALUE + ", SKU", TARGET_SKU + "):")
    plan = []
    for v in targets:
        lvls = levels(v)
        need_qty = [(l, n) for l, n, q in lvls if q != 0]
        need_track = not v["inventoryItem"]["tracked"]
        need_policy = v["inventoryPolicy"] != "DENY"
        plan.append((v, need_track, need_policy, need_qty))
        print(f"    {opt(v, 'Formato'):28} {v['price']:>7} €  tracked {v['inventoryItem']['tracked']!s:5} -> True | "
              f"política {v['inventoryPolicy']} -> DENY | cantidad {[q for _, _, q in lvls]} -> 0 | "
              f"disponible {v['availableForSale']} -> False")
    print("\n  INTACTAS (se verifican igual antes/después):")
    for v in others:
        print(f"    {opt(v, OPTION):15} {opt(v, 'Formato'):28} sku {v['sku']}  tracked {v['inventoryItem']['tracked']!s:5} "
              f"política {v['inventoryPolicy']}  disponible {v['availableForSale']}")
    print("\n  Comprobado: el SKU 458 solo está en estas 4 variantes de toda la tienda; cada una tiene su propio"
          "\n  inventory item (el seguimiento se activa por variante, no afecta a las demás).")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"agotar_bellota100_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"productId": p["id"], "handle": HANDLE, "changed": [snapshot(v) for v in targets],
               "untouched": [snapshot(v) for v in others]}, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)

    inputs = [{"id": v["id"], "inventoryPolicy": "DENY", "inventoryItem": {"tracked": True}} for v, *_ in plan]
    check(base.gql(token, M_VAR, {"p": p["id"], "v": inputs}), "productVariantsBulkUpdate")
    print("  OK seguimiento activado y política DENY")
    quantities = [{"inventoryItemId": v["inventoryItem"]["id"], "locationId": loc, "quantity": 0}
                  for v, _, _, need in plan for loc, _ in need]
    if quantities:
        check(base.gql(token, M_QTY, {"i": {"name": "available", "reason": "correction",
              "ignoreCompareQuantity": True, "quantities": quantities}}), "inventorySetQuantities")
        print("  OK cantidad fijada a 0")

    print("\nRelectura:")
    after = fetch(token)["variants"]["nodes"]
    by_id = {v["id"]: v for v in after}
    bad = False
    for v in targets:
        a = by_id[v["id"]]
        ok = (a["inventoryItem"]["tracked"] and a["inventoryPolicy"] == "DENY" and not a["availableForSale"]
              and all(q == 0 for _, _, q in levels(a)) and a["price"] == v["price"] and a["sku"] == v["sku"])
        bad = bad or not ok
        print(f"  {opt(a, 'Formato'):28} tracked={a['inventoryItem']['tracked']} política={a['inventoryPolicy']} "
              f"cantidad={[q for _, _, q in levels(a)]} disponible={a['availableForSale']}  {'OK' if ok else '¡REVISAR!'}")
    for v in others:
        a = by_id[v["id"]]
        same = snapshot(a) == snapshot(v)
        bad = bad or not same
        if not same:
            print(f"  ¡CAMBIÓ una variante que no debía!: {a['title']}")
    print(f"  Variantes intactas sin cambios: {all(snapshot(by_id[v['id']]) == snapshot(v) for v in others)}")
    print("Aplicado." if not bad else "Aplicado, pero hay diferencias: revisar.")


if __name__ == "__main__":
    main()
