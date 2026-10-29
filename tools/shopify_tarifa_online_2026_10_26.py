#!/usr/bin/env python3
"""
Tarifa ONLINE de Casa Maravillas del 26/10/2026 (la que envió Luis Juan, tal cual): precios de 14 SKU.

Busca cada variante por SKU en TODA la tienda (debe haber exactamente una) y cambia solo `price`.
Antes de escribir comprueba que el precio actual coincide con la columna «antes» de la tarifa; si algo
no coincide (o el SKU no es único), aborta sin escribir nada. No toca pesos, compareAt, inventario, SKU,
ni el recargo de formato (corte/deshuesado) del jamón entero (SKU 450-458), ni el lomo de pieza (497, 498).

Equivalencias: embutido de pieza = IDs 471-475 de la tarifa = SKU web 495-499 (aquí solo 495, 496, 499).

Reutiliza la auth de shopify_update_precios_embutido.py (Keychain, client credentials).

Uso:
  python3 -I tools/shopify_tarifa_online_2026_10_26.py            # dry-run (solo lee)
  python3 -I tools/shopify_tarifa_online_2026_10_26.py --apply    # aplica (backup en _backup/)
  python3 -I tools/shopify_tarifa_online_2026_10_26.py --rollback _backup/tarifa_online_XXXX.json --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base

# SKU web -> (descripción, precio antes, precio después)
TARIFA = {
    "495": ("Chorizo de pieza", "25.10", "19.90"),
    "496": ("Salchichón de pieza", "25.10", "19.90"),
    "499": ("Lomito de presa de pieza", "43.90", "44.90"),
    "476": ("Chorizo loncheado 100 g", "4.90", "3.99"),
    "478": ("Salchichón loncheado 100 g", "4.90", "3.99"),
    "480": ("Lomo de cebo loncheado", "8.70", "6.99"),
    "482": ("Lomo de bellota loncheado", "10.20", "8.99"),
    "484": ("Lomito loncheado", "10.20", "9.99"),
    "465": ("Jamón a máquina 100 g · cebo", "11.20", "9.99"),
    "467": ("Jamón a máquina 100 g · bellota 50 %", "15.60", "14.99"),
    "469": ("Jamón a máquina 100 g · bellota 100 %", "17.70", "18.99"),
    "459": ("Jamón a mano 80 g · cebo", "12.60", "10.99"),
    "461": ("Jamón a mano 80 g · bellota 50 %", "16.00", "13.99"),
    "463": ("Jamón a mano 80 g · bellota 100 %", "18.00", "16.99"),
}

Q_SKU = """query($q:String){ productVariants(first:10, query:$q){ nodes{ id sku title price compareAtPrice
  product{ id handle title status } } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def same(a, b):
    return abs(float(a) - float(b)) < 1e-9


def lookup(token):
    found, problems = {}, []
    for sku in TARIFA:
        nodes = [n for n in base.gql(token, Q_SKU, {"q": f"sku:{sku}"})["productVariants"]["nodes"] if n["sku"] == sku]
        if len(nodes) != 1:
            problems.append(f"SKU {sku}: {len(nodes)} variantes en la tienda (se esperaba 1)")
            continue
        found[sku] = nodes[0]
    return found, problems


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, scopes = base.get_token()
    print(f"Tienda: {base.SHOP} | write_products: {'write_products' in scopes.split(',')}")

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: restaurar el precio anterior de estas variantes")
        for v in bk["changed"]:
            print(f"  SKU {v['sku']:>4} {v['handle']:52} -> {v['price']}")
        if not apply:
            print("(dry-run) añade --apply")
            return
        by_prod = {}
        for v in bk["changed"]:
            by_prod.setdefault(v["productId"], []).append({"id": v["id"], "price": v["price"]})
        for pid, vs in by_prod.items():
            check(base.gql(token, M_VAR, {"p": pid, "v": vs}), "productVariantsBulkUpdate")
        print("Restaurado.")
        return

    found, problems = lookup(token)
    print("\n== TARIFA ONLINE 26/10/2026\n")
    print(f"  {'SKU':>4}  {'producto (handle)':52} {'tarifa':36} {'antes (web)':>11} {'tarifa antes':>12} {'después':>8}  estado")
    todo, bad = [], list(problems)
    for sku, (desc, antes, despues) in TARIFA.items():
        n = found.get(sku)
        if not n:
            continue
        cur = n["price"]
        if same(cur, despues):
            estado = "ya aplicado"
        elif same(cur, antes):
            estado = "CAMBIA"
            todo.append(n)
        else:
            estado = f"¡NO COINCIDE con el «antes» ({antes})!"
            bad.append(f"SKU {sku} ({desc}): la web tiene {cur} y la tarifa esperaba {antes}")
        cmp_ = f" compareAt={n['compareAtPrice']}" if n["compareAtPrice"] else ""
        print(f"  {sku:>4}  {n['product']['handle']:52} {desc:36} {cur:>11} {antes:>12} {despues:>8}  {estado}{cmp_}"
              f"  [{n['product']['status']}]")
    print(f"\n  Cambian {len(todo)} de {len(TARIFA)}. Solo `price`; pesos, compareAt, inventario, SKU y recargos de formato no se tocan.")
    if bad:
        print("\n¡PROBLEMAS! No se aplicará nada hasta resolverlos:")
        for b in bad:
            print("  -", b)
        sys.exit(1)

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return
    if not todo:
        print("\nNada que aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"tarifa_online_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"tarifa": "2026-10-26", "changed": [{"id": n["id"], "sku": n["sku"], "price": n["price"], "productId": n["product"]["id"],
                                                    "handle": n["product"]["handle"]} for n in todo]},
              open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", os.path.abspath(bpath))
    by_prod = {}
    for n in todo:
        by_prod.setdefault(n["product"]["id"], []).append({"id": n["id"], "price": TARIFA[n["sku"]][2]})
    for pid, vs in by_prod.items():
        check(base.gql(token, M_VAR, {"p": pid, "v": vs}), "productVariantsBulkUpdate")
    print(f"  OK {len(todo)} variantes en {len(by_prod)} productos")

    print("\nRelectura:")
    after, probs = lookup(token)
    ok_all = not probs
    for sku, (desc, antes, despues) in TARIFA.items():
        n = after.get(sku)
        ok = bool(n) and same(n["price"], despues)
        ok_all = ok_all and ok
        print(f"  SKU {sku:>4} {desc:38} {n['price'] if n else '?':>7} (esperado {despues})  {'OK' if ok else '¡NO COINCIDE!'}")
    print("Aplicado." if ok_all else "Aplicado, pero hay diferencias: revisar.")


if __name__ == "__main__":
    main()
