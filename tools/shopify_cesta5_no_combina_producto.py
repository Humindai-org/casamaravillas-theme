#!/usr/bin/env python3
"""
Código de descuento CESTA5-K7Q2 («Crea tu cesta — 5% desde 3 productos»): «Combina con descuentos de producto» a NO.

Solo cambia `combinesWith.productDiscounts` (true -> false). Se mantienen tal cual orderDiscounts (false) y
shippingDiscounts (true), y no se toca porcentaje, mínimo de 3 artículos, productos, clientes, fechas, usos ni estado.
Motivo: regla de negocio «el cliente recibe siempre el mayor descuento, sin acumular los de porcentaje»
(el descuento por volumen por línea es de producto y no debe sumarse al 5 % de la cesta).

Antes de escribir guarda el estado completo en _backup/ y, tras escribir, relee y comprueba que SOLO cambió
combinesWith.productDiscounts; si cambió algo más, restaura el estado original y aborta.

Reutiliza la auth de shopify_update_precios_embutido.py (Keychain, client credentials). Requiere write_discounts.

Uso:
  python3 -I tools/shopify_cesta5_no_combina_producto.py            # dry-run (solo lee)
  python3 -I tools/shopify_cesta5_no_combina_producto.py --apply    # aplica (backup en _backup/)
  python3 -I tools/shopify_cesta5_no_combina_producto.py --rollback _backup/cesta5_combina_XXXX.json --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base

CODE = "CESTA5-K7Q2"

Q = """query($c:String!){ codeDiscountNodeByCode(code:$c){ id codeDiscount{ __typename
  ... on DiscountCodeBasic{ title status startsAt endsAt usageLimit appliesOncePerCustomer asyncUsageCount
    recurringCycleLimit
    codes(first:5){ nodes{ code } }
    combinesWith{ orderDiscounts productDiscounts shippingDiscounts }
    minimumRequirement{ __typename ... on DiscountMinimumQuantity{ greaterThanOrEqualToQuantity }
      ... on DiscountMinimumSubtotal{ greaterThanOrEqualToSubtotal{ amount } } }
    customerSelection{ __typename }
    customerGets{ value{ __typename ... on DiscountPercentage{ percentage } }
      items{ __typename ... on AllDiscountItems{ allItems } } } } } } }"""
M_UPD = """mutation($id:ID!,$d:DiscountCodeBasicInput!){
  discountCodeBasicUpdate(id:$id, basicCodeDiscount:$d){ userErrors{ field message } } }"""


def fetch(token):
    node = base.gql(token, Q, {"c": CODE})["codeDiscountNodeByCode"]
    if not node or node["codeDiscount"]["__typename"] != "DiscountCodeBasic":
        sys.exit(f"No se encuentra el código {CODE} (DiscountCodeBasic). Abortado.")
    d = node["codeDiscount"]
    s = {k: v for k, v in d.items() if k != "__typename"}
    s["codes"] = [c["code"] for c in d["codes"]["nodes"]]
    s["id"] = node["id"]
    return s


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def set_combines(token, s, combines):
    check(base.gql(token, M_UPD, {"id": s["id"], "d": {"combinesWith": combines}}), "discountCodeBasicUpdate")


def strip(s):
    """Estado sin lo que debe cambiar ni el contador de usos (puede subir solo)."""
    return {k: v for k, v in s.items() if k not in ("combinesWith", "asyncUsageCount")}


def show(s):
    cw = ",".join(k.replace("Discounts", "") for k, v in s["combinesWith"].items() if v) or "nada"
    minq = (s["minimumRequirement"] or {}).get("greaterThanOrEqualToQuantity")
    print(f"  {s['title']!r}  [{', '.join(s['codes'])}]  {s['status']}  {float(s['customerGets']['value']['percentage']) * 100:g}% "
          f"| mínimo {minq} uds | usos {s['asyncUsageCount']}")
    print(f"  combinesWith: {s['combinesWith']}   (combina con: {cw})")


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, scopes = base.get_token()
    print(f"Tienda: {base.SHOP} | write_discounts: {'write_discounts' in scopes.split(',')}")
    if "write_discounts" not in scopes.split(","):
        sys.exit("Falta el permiso write_discounts. No se intenta nada.")

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        orig = bk["discount"]
        print("Rollback: restaurar combinesWith original ->", orig["combinesWith"])
        if not apply:
            print("(dry-run) añade --apply")
            return
        set_combines(token, orig, orig["combinesWith"])
        print("Restaurado:", fetch(token)["combinesWith"])
        return

    s = fetch(token)
    print("\n== CESTA5-K7Q2: «Combina con descuentos de producto» -> NO ==\n")
    show(s)
    new = {"orderDiscounts": s["combinesWith"]["orderDiscounts"], "productDiscounts": False,
           "shippingDiscounts": s["combinesWith"]["shippingDiscounts"]}
    print(f"  antes  : {s['combinesWith']}\n  después: {new}")
    if s["combinesWith"] == new:
        print("\nYa está así. Nada que aplicar.")
        return
    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.abspath(os.path.join(HERE, "..", "_backup", f"cesta5_combina_{time.strftime('%Y%m%d-%H%M%S')}.json"))
    json.dump({"discount": s}, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)
    print("Rollback: python3 -I tools/shopify_cesta5_no_combina_producto.py --rollback", os.path.relpath(bpath, os.path.join(HERE, "..")), "--apply")

    set_combines(token, s, new)
    after = fetch(token)
    print("\nRelectura:")
    show(after)
    if after["combinesWith"] != new or strip(after) != strip(s):
        print("¡Algo más cambió o combinesWith no quedó como se esperaba! Restaurando.")
        set_combines(token, s, s["combinesWith"])
        sys.exit("Abortado: revisar el descuento.")
    print("Aplicado: solo cambió combinesWith.productDiscounts (true -> false).")


if __name__ == "__main__":
    main()
