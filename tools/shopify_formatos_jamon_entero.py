#!/usr/bin/env python3
"""
Jamón entero: añade la opción "Formato" (Pieza entera / Deshuesado / Corte a máquina y envasado /
Corte a mano y envasado) con suplemento fijo sobre el precio de la pieza (IVA incl.), igual para los 3 pesos.

3 productos x 3 pesos x 4 formatos = 36 variantes. El SKU es el de la pieza (450-458) en los 4 formatos.

Reutiliza la auth (Keychain, client credentials) de shopify_update_ingredients.py.

Uso:
  python3 tools/shopify_formatos_jamon_entero.py            # dry-run (solo lee)
  python3 tools/shopify_formatos_jamon_entero.py --apply    # aplica (guarda backup en _backup/)
  python3 tools/shopify_formatos_jamon_entero.py --rollback _backup/formatos_jamon_entero_XXXX.json --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

OPT_PESO, OPT_FORMATO = "Peso", "Formato"
BASE_FORMAT = "Pieza entera"
# formato -> suplemento en € (IVA incl.). Fuente: respuesta del cliente.
FORMATS = {BASE_FORMAT: 0, "Deshuesado": 10, "Corte a máquina y envasado": 40, "Corte a mano y envasado": 70}
SHIP_KG = {"7.0kg - 8.0kg": 8.0, "8.0kg - 9.0kg": 9.0, "9.0kg - 10.0kg": 10.0}  # peso de envío = tope del rango

# handle -> { peso: (precio de la pieza, sku) }  (escandallo, ya cargado)
PLAN = {
    "jamon-cebo-de-campo-50-iberico-pieza-entera": {
        "7.0kg - 8.0kg": (258, "450"), "8.0kg - 9.0kg": (290, "451"), "9.0kg - 10.0kg": (322, "452")},
    "jamon-bellota-50-iberico-pieza-entera": {
        "7.0kg - 8.0kg": (382, "453"), "8.0kg - 9.0kg": (430, "454"), "9.0kg - 10.0kg": (477, "455")},
    "jamon-bellota-100-iberico-pieza-entera": {
        "7.0kg - 8.0kg": (498, "456"), "8.0kg - 9.0kg": (561, "457"), "9.0kg - 10.0kg": (623, "458")},
}

Q_PRODUCT = """query($h:String!){ productByHandle(handle:$h){ id title
  options{ id name optionValues{ name } }
  variants(first:50){ nodes{ id title sku price selectedOptions{ name value } } } } }"""
M_OPT_CREATE = """mutation($p:ID!,$o:[OptionCreateInput!]!){
  productOptionsCreate(productId:$p, options:$o, variantStrategy:LEAVE_AS_IS){ userErrors{ field message } } }"""
M_OPT_DELETE = """mutation($p:ID!,$o:[ID!]!){ productOptionsDelete(productId:$p, options:$o){ userErrors{ field message } } }"""
M_CREATE = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkCreate(productId:$p, variants:$v){ userErrors{ field message } } }"""
M_DELETE = """mutation($p:ID!,$v:[ID!]!){ productVariantsBulkDelete(productId:$p, variantsIds:$v){ userErrors{ field message } } }"""


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def money(n):
    return f"{n:.2f}"


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, _ = base.get_token()

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: borrar las variantes con Formato distinto de 'Pieza entera' y la opción Formato")
        if not apply:
            print("(dry-run) añade --apply")
            return
        for h in bk["handles"]:
            p = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
            extra = [v["id"] for v in p["variants"]["nodes"]
                     if any(o["name"] == OPT_FORMATO and o["value"] != BASE_FORMAT for o in v["selectedOptions"])]
            if extra:
                check(base.gql(token, M_DELETE, {"p": p["id"], "v": extra}), "productVariantsBulkDelete")
            opt = [o["id"] for o in p["options"] if o["name"] == OPT_FORMATO]
            if opt:
                check(base.gql(token, M_OPT_DELETE, {"p": p["id"], "o": opt}), "productOptionsDelete")
            print("  OK", h)
        return

    products = {}
    print("== FORMATOS DE JAMÓN ENTERO ==")
    for h, pesos in PLAN.items():
        p = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
        if not p:
            sys.exit(f"No existe {h}")
        names = [o["name"] for o in p["options"]]
        if names != [OPT_PESO]:
            sys.exit(f"{h}: se esperaba una única opción '{OPT_PESO}', hay {names}")
        existing = {v["selectedOptions"][0]["value"]: v for v in p["variants"]["nodes"]}
        for peso, (price, sku) in pesos.items():
            v = existing.get(peso)
            if not v:
                sys.exit(f"{h}: falta la variante {peso}")
            if float(v["price"]) != float(price) or v["sku"] != sku:
                sys.exit(f"{h} / {peso}: precio/SKU actuales ({v['price']}, {v['sku']}) no son los del escandallo ({price}, {sku})")
        products[h] = p
        print(f"\n  {p['title']}   (SKU de la pieza en los 4 formatos)")
        print(f"    {'':16}" + "".join(f"{f:>30}" for f in FORMATS))
        for peso, (price, sku) in pesos.items():
            print(f"    {peso:16}" + "".join(f"{money(price + s) + ' €':>30}" for s in FORMATS.values()) + f"   sku {sku}")
    n_new = len(PLAN) * len(SHIP_KG) * (len(FORMATS) - 1)
    print(f"\n  Variantes: {len(PLAN) * len(SHIP_KG)} existentes (pasan a '{BASE_FORMAT}') + {n_new} nuevas = "
          f"{len(PLAN) * len(SHIP_KG) * len(FORMATS)} en total.")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"formatos_jamon_entero_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"handles": list(PLAN), "products": products}, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)

    for h, pesos in PLAN.items():
        p = products[h]
        check(base.gql(token, M_OPT_CREATE, {"p": p["id"], "o": [
            {"name": OPT_FORMATO, "values": [{"name": BASE_FORMAT}]}]}), "productOptionsCreate")
        new = []
        for peso, (price, sku) in pesos.items():
            for fmt, extra in FORMATS.items():
                if fmt == BASE_FORMAT:
                    continue
                new.append({
                    "optionValues": [{"optionName": OPT_PESO, "name": peso}, {"optionName": OPT_FORMATO, "name": fmt}],
                    "price": money(price + extra), "inventoryPolicy": "DENY", "taxable": True,
                    "inventoryItem": {"sku": sku, "tracked": False,
                                      "measurement": {"weight": {"value": SHIP_KG[peso], "unit": "KILOGRAMS"}}}})
        check(base.gql(token, M_CREATE, {"p": p["id"], "v": new}), "productVariantsBulkCreate")
        print("  OK", h)
    print("Aplicado.")


if __name__ == "__main__":
    main()
