#!/usr/bin/env python3
"""
Jamón loncheado: precios/SKUs del escandallo, gramos en el nombre de la variante
y descuentos por cantidad (solo 10 uds, -10%).

Reutiliza la auth (Keychain, client credentials) de shopify_update_ingredients.py.

Uso:
  python3 tools/shopify_update_loncheados.py            # dry-run (solo lee)
  python3 tools/shopify_update_loncheados.py --apply    # aplica (guarda backup en _backup/)
  python3 tools/shopify_update_loncheados.py --apply --solo-nombres   # solo renombra el corte (80 g / 100 g); no toca precios, SKUs ni descuentos
  python3 tools/shopify_update_loncheados.py --rollback _backup/loncheados_XXXX.json --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

MANO, MAQ = "Cortado a Mano", "Cortado a Máquina"
MANO_NEW, MAQ_NEW = "Cortado a Mano · 80 g", "Cortado a Máquina · 100 g"

# handle -> (precio, sku) por corte. Fuente: ESCANDALLO WEB (columna REDOND.), SKU de la referencia de 1 ud.
PLAN = {
    "jamon-cebo-de-campo-50-iberico-cortado-a-mano": {MANO: ("12.60", "459"), MAQ: ("11.20", "465")},
    "jamon-bellota-50-iberico-cortado-a-mano":       {MANO: ("16.00", "461"), MAQ: ("15.60", "467")},
    "jamon-bellota-100-iberico-cortado-a-mano":      {MANO: ("18.00", "463"), MAQ: ("17.70", "469")},
}
# Embutidos loncheados: handle -> (nombre, precio 1 ud, sku 1 ud). Pack de 5 uds con -10%.
EMB_PLAN = {
    "chorizo-bellota-iberico-loncheado":        ("Chorizo de Bellota Ibérico",        "4.90", "476"),
    "salchichon-bellota-iberico-loncheado":     ("Salchichón de Bellota Ibérico",     "4.90", "478"),
    "lomo-cebo-campo-50-iberico-loncheado":     ("Lomo de Cebo de Campo Ibérico 50%", "8.70", "480"),
    "lomo-bellota-iberico-loncheado-2":         ("Lomo de Bellota Ibérico",           "10.20", "482"),
    "lomo-bellota-iberico-loncheado-1":         ("Lomito de Presa Ibérico",          "10.20", "484"),
}
EMB_QTY = "5"
DISCOUNT_PCT = 0.10
KEEP_QTY = "10"

Q_PRODUCT = """query($h:String!){ productByHandle(handle:$h){ id title options{ id name optionValues{ id name } }
  variants(first:20){ nodes{ id title sku price selectedOptions{ name value } } } } }"""
Q_DISC = """{ discountNodes(first:100){ nodes{ id discount{ __typename
  ... on DiscountAutomaticBasic{ title status minimumRequirement{ ... on DiscountMinimumQuantity{ greaterThanOrEqualToQuantity } }
     customerGets{ value{ ... on DiscountPercentage{ percentage } }
       items{ ... on DiscountProducts{ products(first:3){ nodes{ handle title status } } } } } } } } } }"""
M_OPT = """mutation($p:ID!,$o:OptionUpdateInput!,$v:[OptionValueUpdateInput!]){
  productOptionUpdate(productId:$p, option:$o, optionValuesToUpdate:$v){ userErrors{ field message } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""
M_DISC_UPD = """mutation($id:ID!,$d:DiscountAutomaticBasicInput!){
  discountAutomaticBasicUpdate(id:$id, automaticBasicDiscount:$d){ userErrors{ field message } } }"""
M_DISC_NEW = """mutation($d:DiscountAutomaticBasicInput!){
  discountAutomaticBasicCreate(automaticBasicDiscount:$d){ userErrors{ field message } } }"""
M_DISC_DEL = """mutation($id:ID!){ discountAutomaticDelete(id:$id){ userErrors{ field message } } }"""


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def read_state(token):
    products = {}
    for h in PLAN:
        p = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
        if not p:
            sys.exit(f"No existe el producto {h}")
        products[h] = p
    discounts = []
    for n in base.gql(token, Q_DISC)["discountNodes"]["nodes"]:
        d = n["discount"]
        if d["__typename"] != "DiscountAutomaticBasic":
            continue
        prods = [x["handle"] for x in (d["customerGets"]["items"].get("products") or {}).get("nodes", [])]
        title = d["title"]
        if not any(k in title for k in ("Jamón Cebo", "Jamón Bellota")) or "uds" not in title:
            continue
        discounts.append({"id": n["id"], "title": title, "status": d["status"], "handles": prods,
                          "qty": d["minimumRequirement"]["greaterThanOrEqualToQuantity"],
                          "pct": d["customerGets"]["value"]["percentage"]})
    return products, discounts


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    names_only = "--solo-nombres" in args
    token, _ = base.get_token()

    if "--rollback" in args:
        path = args[args.index("--rollback") + 1]
        bk = json.load(open(path))
        print("Rollback desde", path)
        for h, p in bk["products"].items():
            print(" ", h, [(v["title"], v["sku"], v["price"]) for v in p["variants"]["nodes"]])
        if not apply:
            print("(dry-run) añade --apply para restaurar productos. Los descuentos borrados hay que recrearlos a mano (datos en el backup).")
            return
        for h, p in bk["products"].items():
            opt = p["options"][0]
            old_names = {v["id"]: v["name"] for v in opt["optionValues"]}
            cur = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]["options"][0]["optionValues"]
            check(base.gql(token, M_OPT, {"p": p["id"], "o": {"id": opt["id"]},
                  "v": [{"id": v["id"], "name": old_names[v["id"]]} for v in cur if v["id"] in old_names]}), "productOptionUpdate")
            check(base.gql(token, M_VAR, {"p": p["id"], "v": [
                {"id": v["id"], "price": v["price"], "inventoryItem": {"sku": v["sku"]}} for v in p["variants"]["nodes"]]}),
                "productVariantsBulkUpdate")
        print("Productos restaurados.")
        return

    products, discounts = read_state(token)

    print("== PRODUCTOS ==")
    var_updates, opt_updates = {}, {}
    for h, p in products.items():
        opt = p["options"][0]
        if opt["name"] != "Corte":
            sys.exit(f"{h}: la primera opción no es 'Corte'")
        vals = {v["name"]: v["id"] for v in opt["optionValues"]}
        ren = []
        for old, new in ((MANO, MANO_NEW), (MAQ, MAQ_NEW)):
            if old in vals:
                ren.append({"id": vals[old], "name": new})
        opt_updates[h] = ren
        vu = []
        for v in p["variants"]["nodes"]:
            corte = v["selectedOptions"][0]["value"]
            base_name = MANO if corte.startswith(MANO) else MAQ
            price, sku = PLAN[h][base_name]
            new_name = MANO_NEW if base_name == MANO else MAQ_NEW
            print(f"  {p['title']}\n    {corte:24} -> {new_name:28} precio {v['price']:>6} -> {price:>6}   sku {v['sku']} -> {sku}")
            vu.append({"id": v["id"], "price": price, "inventoryItem": {"sku": sku}})
        var_updates[h] = vu

    print("\n== DESCUENTOS AUTOMÁTICOS ==")
    keep, delete = [], []
    for d in discounts:
        live = any(h in PLAN for h in d["handles"])
        if live and d["qty"] == KEEP_QTY:
            keep.append(d)
            print(f"  MODIFICAR  {d['title']}  {d['pct']*100:.0f}% -> {DISCOUNT_PCT*100:.0f}%")
        else:
            delete.append(d)
            why = "tramo eliminado" if live else "producto archivado/no usado"
            print(f"  BORRAR     {d['title']}  ({d['pct']*100:.0f}%, min {d['qty']}; {why})")

    print("\n== EMBUTIDOS LONCHEADOS (1 ud. / 5 uds., -10% desde 5) ==")
    emb = {}
    for h, (name, price, sku) in EMB_PLAN.items():
        p = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
        if not p:
            sys.exit(f"No existe el producto {h}")
        v = p["variants"]["nodes"]
        if len(v) != 1:
            sys.exit(f"{h}: se esperaba 1 variante, hay {len(v)}")
        emb[h] = p
        print(f"  {p['title']:46} precio {v[0]['price']:>6} -> {price:>6}   sku {v[0]['sku']} -> {sku}")
        print(f"      + descuento automático: {name} — 5 uds (-10%)")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"loncheados_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"products": {**products, **emb}, "discounts": discounts}, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)

    for h, p in products.items():
        if opt_updates[h]:
            check(base.gql(token, M_OPT, {"p": p["id"], "o": {"id": p["options"][0]["id"]}, "v": opt_updates[h]}), "productOptionUpdate")
        if not names_only:
            check(base.gql(token, M_VAR, {"p": p["id"], "v": var_updates[h]}), "productVariantsBulkUpdate")
        print("  OK producto", h)
    if names_only:
        print("Aplicado (solo nombres de variante).")
        return
    for d in keep:
        new_title = d["title"].replace("(-5%)", "(-10%)")
        check(base.gql(token, M_DISC_UPD, {"id": d["id"], "d": {"title": new_title,
              "customerGets": {"value": {"percentage": DISCOUNT_PCT}}}}), "discountAutomaticBasicUpdate")
        print("  OK descuento", new_title)
    for h, (name, price, sku) in EMB_PLAN.items():
        p = emb[h]
        check(base.gql(token, M_VAR, {"p": p["id"], "v": [
            {"id": p["variants"]["nodes"][0]["id"], "price": price, "inventoryItem": {"sku": sku}}]}), "productVariantsBulkUpdate")
        check(base.gql(token, M_DISC_NEW, {"d": {
            "title": f"{name} — 5 uds (-10%)", "startsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "combinesWith": {"productDiscounts": True, "orderDiscounts": False, "shippingDiscounts": True},
            "minimumRequirement": {"quantity": {"greaterThanOrEqualToQuantity": EMB_QTY}},
            "customerGets": {"value": {"percentage": DISCOUNT_PCT}, "items": {"products": {"productsToAdd": [p["id"]]}}}}}),
            "discountAutomaticBasicCreate")
        print("  OK embutido + descuento", name)
    for d in delete:
        check(base.gql(token, M_DISC_DEL, {"id": d["id"]}), "discountAutomaticDelete")
        print("  OK borrado", d["title"])
    print("Aplicado.")


if __name__ == "__main__":
    main()
