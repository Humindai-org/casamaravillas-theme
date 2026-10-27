#!/usr/bin/env python3
"""
Retira los productos de jamón deshuesado (el deshuesado pasa a ser un formato de la pieza entera):
los archiva y les vacía el SKU, para liberar los SKUs 471/473/474 que el escandallo asigna a los embutidos.

Hazlo DESPUÉS de crear la opción Formato en la pieza entera (tools/shopify_formatos_jamon_entero.py).
Luego: python3 tools/shopify_update_embutidos_enteros.py [--apply]

Uso:
  python3 tools/shopify_retirar_deshuesados.py            # dry-run (solo lee)
  python3 tools/shopify_retirar_deshuesados.py --apply    # aplica (guarda backup en _backup/)
  python3 tools/shopify_retirar_deshuesados.py --rollback _backup/deshuesados_XXXX.json --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

Q = """{ products(first:20, query:"tag:deshuesado AND status:active"){ nodes{ id title handle status
  variants(first:5){ nodes{ id sku price } } } } }"""
M_STATUS = """mutation($i:ProductUpdateInput!){ productUpdate(product:$i){ userErrors{ field message } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, _ = base.get_token()

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: reactivar y restaurar SKUs")
        if not apply:
            print("(dry-run) añade --apply")
            return
        for p in bk:
            check(base.gql(token, M_VAR, {"p": p["id"], "v": [
                {"id": v["id"], "inventoryItem": {"sku": v["sku"]}} for v in p["variants"]["nodes"]]}), "productVariantsBulkUpdate")
            check(base.gql(token, M_STATUS, {"i": {"id": p["id"], "status": "ACTIVE"}}), "productUpdate")
        print("Restaurado.")
        return

    products = base.gql(token, Q)["products"]["nodes"]
    if not products:
        sys.exit("No hay productos deshuesados activos.")
    print("== DESHUESADOS A RETIRAR (archivar + vaciar SKU) ==")
    for p in products:
        print(f"  {p['title']}  /products/{p['handle']}  sku {[v['sku'] for v in p['variants']['nodes']]}")
    print("\n  Recuerda crear una redirección /products/<handle> -> la pieza entera correspondiente (Tienda online > Navegación).")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"deshuesados_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump(products, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)
    for p in products:
        check(base.gql(token, M_VAR, {"p": p["id"], "v": [
            {"id": v["id"], "inventoryItem": {"sku": ""}} for v in p["variants"]["nodes"]]}), "productVariantsBulkUpdate")
        check(base.gql(token, M_STATUS, {"i": {"id": p["id"], "status": "ARCHIVED"}}), "productUpdate")
        print("  OK", p["handle"])
    print("Aplicado.")


if __name__ == "__main__":
    main()
