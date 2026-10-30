#!/usr/bin/env python3
"""
⛔ NO EJECUTAR (aviso del 28/10/2026, regla de descuentos de Casa Maravillas):
   el cliente recibe SIEMPRE el mayor descuento (tope 10 %), los de porcentaje no se acumulan y solo se combina el
   envío gratis desde 99 € (medido tras descuentos). Este script la rompería:
   - El paso 2 pone BIENVENIDA10 en «combina con descuentos de producto» = true: BIENVENIDA10 se acumularía con el
     descuento por volumen (hoy está en false a propósito).
   - El paso 1 crea CESTA5-K7Q2 con «combina con descuentos de producto» = true. El código YA existe y el 27/10 se puso
     a false por API (tools/shopify_cesta5_no_combina_producto.py; rollback en _backup/cesta5_combina_*.json).
     Volver a ejecutar esto lo deshacería. Ya está creado: no hay nada que ejecutar.

Crea tu cesta: descuento del 5% a partir de 3 productos (toda la cesta), aplicado por el propio constructor
mediante un código.

  1. Crea el código CESTA5-K7Q2: 5% sobre todos los productos, mínimo 3 unidades en el carrito.
     Combina con el envío gratis automático y con otros descuentos de producto que lo permitan (BIENVENIDA10).
     No se suma al descuento por cantidad de los loncheados: Shopify aplica el mayor en cada línea.
  2. Permite que BIENVENIDA10 se combine con otros descuentos de producto (necesario para que un cliente nuevo
     pueda usar BIENVENIDA10 además del 5% de la cesta). Es el único cambio sobre un descuento existente.

La caja de regalo NO es un producto: es el propio embalaje del envío, así que el constructor no añade ninguna línea.

Reutiliza la auth (Keychain, client credentials) de shopify_update_ingredients.py.

Uso:
  python3 tools/shopify_crear_cesta.py            # dry-run (solo lee)
  python3 tools/shopify_crear_cesta.py --apply
  python3 tools/shopify_crear_cesta.py --rollback _backup/cesta_XXXX.json --apply   # borra el código y restaura BIENVENIDA10
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

CODE = "CESTA5-K7Q2"
PCT = 0.05
MIN_QTY = "3"
WELCOME = "BIENVENIDA10"

Q = """query($c:String!,$w:String!){
  cesta: codeDiscountNodeByCode(code:$c){ id }
  welcome: codeDiscountNodeByCode(code:$w){ id codeDiscount{ ... on DiscountCodeBasic{ combinesWith{ productDiscounts orderDiscounts shippingDiscounts } } } } }"""
M_CODE = """mutation($d:DiscountCodeBasicInput!){ discountCodeBasicCreate(basicCodeDiscount:$d){
  codeDiscountNode{ id } userErrors{ field message } } }"""
M_UPD = """mutation($id:ID!,$d:DiscountCodeBasicInput!){ discountCodeBasicUpdate(id:$id, basicCodeDiscount:$d){ userErrors{ field message } } }"""
M_DEL = """mutation($id:ID!){ discountCodeDelete(id:$id){ userErrors{ field message } } }"""


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
        print("Rollback:", bk)
        if not apply:
            print("(dry-run) añade --apply")
            return
        if bk.get("code_id"):
            check(base.gql(token, M_DEL, {"id": bk["code_id"]}), "discountCodeDelete")
        if bk.get("welcome_id") and bk.get("welcome_combines"):
            check(base.gql(token, M_UPD, {"id": bk["welcome_id"], "d": {"combinesWith": bk["welcome_combines"]}}), "discountCodeBasicUpdate")
        print("Restaurado.")
        return

    ex = base.gql(token, Q, {"c": CODE, "w": WELCOME})
    wel = ex["welcome"]
    if not wel:
        sys.exit(f"No existe el código {WELCOME}")
    wc = wel["codeDiscount"]["combinesWith"]
    print("== CREA TU CESTA ==")
    print(f"  Código {CODE}: {PCT * 100:.0f}% sobre todos los productos, mínimo {MIN_QTY} uds; combina con envío gratis y con "
          f"{WELCOME}" + ("   [YA EXISTE]" if ex["cesta"] else ""))
    print(f"  {WELCOME}: combinesWith productDiscounts {wc['productDiscounts']} -> True "
          f"(orderDiscounts {wc['orderDiscounts']}, shippingDiscounts {wc['shippingDiscounts']} sin cambios)")
    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    created = {"welcome_id": wel["id"], "welcome_combines": wc}
    if not ex["cesta"]:
        r = base.gql(token, M_CODE, {"d": {
            "title": "Crea tu cesta — 5% desde 3 productos", "code": CODE,
            "startsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "customerSelection": {"all": True}, "appliesOncePerCustomer": False,
            "combinesWith": {"shippingDiscounts": True, "productDiscounts": True, "orderDiscounts": False},
            "minimumRequirement": {"quantity": {"greaterThanOrEqualToQuantity": MIN_QTY}},
            "customerGets": {"value": {"percentage": PCT}, "items": {"all": True}}}})
        check(r, "discountCodeBasicCreate")
        created["code_id"] = r["discountCodeBasicCreate"]["codeDiscountNode"]["id"]
        print("  OK código", CODE)
    check(base.gql(token, M_UPD, {"id": wel["id"], "d": {"combinesWith": {
        "productDiscounts": True, "orderDiscounts": wc["orderDiscounts"], "shippingDiscounts": wc["shippingDiscounts"]}}}),
        "discountCodeBasicUpdate")
    print(f"  OK {WELCOME} ahora combina con otros descuentos de producto")

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"cesta_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump(created, open(bpath, "w"), indent=1)
    print("\nBackup (para rollback):", bpath)
    print("Aplicado.")


if __name__ == "__main__":
    main()
