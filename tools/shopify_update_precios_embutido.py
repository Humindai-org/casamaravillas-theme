#!/usr/bin/env python3
"""
Embutido de pieza (SKU 495-499): precios de la tarifa de Luis Juan (23/10/2026) y pesos
(punto medio de los rangos del escandallo).

  - Precio: solo lomo de cebo de campo (497), lomo de bellota (498) y lomito de presa (499).
    Chorizo (495) y salchichón (496): precio FUERA, pendiente de Luis Juan.
  - Peso (peso de envío de la variante): 495-498 a 0,70 kg (600-800 g), 499 a 0,50 kg (450-550 g, rango confirmado por Jorge el 26/10/2026).

Solo envía los campos que difieren de lo que hay en Shopify (idempotente). No toca SKU,
precio de comparación ni inventario.

Reutiliza la auth (Keychain, client credentials) de shopify_update_ingredients.py,
apuntándola a la cuenta/servicios reales de Casa Maravillas.

Uso:
  python3 tools/shopify_update_precios_embutido.py            # dry-run (solo lee)
  python3 tools/shopify_update_precios_embutido.py --apply    # aplica (guarda backup en _backup/)
  python3 tools/shopify_update_precios_embutido.py --rollback _backup/precios_embutido_XXXX.json --apply
"""
import getpass, importlib.util, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

# Credenciales reales (memoria del proyecto): cuenta shopify-casamaravillas, servicios shopify-admin-*.
KC_ACCOUNT = os.environ.get("SHOPIFY_KC_ACCOUNT", "shopify-casamaravillas")
base.SHOP = os.environ.get("SHOPIFY_SHOP", "jbtugu-s0.myshopify.com")
base.KC_ID = os.environ.get("SHOPIFY_KC_CLIENT_ID", "shopify-admin-client-id")
base.KC_SECRET = os.environ.get("SHOPIFY_KC_CLIENT_SECRET", "shopify-admin-client-secret")


def _keychain(service):
    r = subprocess.run(["security", "find-generic-password", "-a", KC_ACCOUNT, "-s", service, "-w"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"No encuentro '{service}' (cuenta '{KC_ACCOUNT}') en el Keychain.")
    return r.stdout.strip()


base.keychain = _keychain

# handle -> { SKU: (precio nuevo IVA incl. o None si queda fuera, peso nuevo en kg) }.
# Precios: tarifa de Luis Juan 23/10/2026. Pesos: punto medio de los rangos del escandallo.
PLAN = {
    "chorizo-bellota-iberico": {"495": (None, 0.70)},        # precio pendiente de Luis Juan
    "salchichon-bellota-iberico": {"496": (None, 0.70)},     # precio pendiente de Luis Juan
    "lomo-cebo-campo-50-iberico": {"497": ("44.90", 0.70)},
    "lomo-bellota-iberico": {"498": ("54.90", 0.70)},
    "lomito-presa-bellota": {"499": ("43.90", 0.50)},   # punto medio de 450-550 g (antes 350-550 g -> 0,45 kg)
}

Q_PRODUCT = """query($h:String!){ productByHandle(handle:$h){ id title status
  variants(first:50){ nodes{ id title sku price compareAtPrice inventoryPolicy
    inventoryItem{ tracked measurement{ weight{ value unit } } } } } } }"""
Q_SKUS = """query($c:String){ productVariants(first:100, after:$c){ pageInfo{hasNextPage endCursor}
  nodes{ id sku title product{ title status } } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""


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
                out.setdefault(v["sku"], []).append(v["id"])
        if not r["pageInfo"]["hasNextPage"]:
            return out
        cur = r["pageInfo"]["endCursor"]


def weight_of(v):
    w = (v["inventoryItem"].get("measurement") or {}).get("weight")
    return float(w["value"]) if w else None


def fmt_kg(x):
    return "-" if x is None else f"{x:.2f} kg"


def diff_fields(v, price, weight):
    """Campos de la variante que difieren del plan (None = no tocar ese campo)."""
    new_price = price if price is not None and float(v["price"]) != float(price) else None
    cur_w = weight_of(v)
    new_weight = weight if cur_w is None or abs(cur_w - weight) > 1e-9 else None
    return new_price, new_weight


def build_input(v, new_price, new_weight):
    inp = {"id": v["id"]}
    if new_price is not None:
        inp["price"] = new_price
    if new_weight is not None:
        inp["inventoryItem"] = {"measurement": {"weight": {"value": new_weight, "unit": "KILOGRAMS"}}}
    return inp


def rollback_input(v):
    inp = {"id": v["id"], "price": v["price"]}
    if v.get("weight") is not None:  # los backups antiguos (solo precios) no traen peso
        inp["inventoryItem"] = {"measurement": {"weight": {"value": v["weight"], "unit": "KILOGRAMS"}}}
    return inp


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, scopes = base.get_token()
    print(f"Tienda: {base.SHOP} | scopes de escritura de productos: "
          f"{'write_products' in scopes.split(',')} | inventario: {'write_inventory' in scopes.split(',')}")

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: restaurar precio (y peso, si el backup lo trae) de estas variantes")
        for h, p in bk["products"].items():
            for v in p["changed"]:
                print(f"  {h:32} SKU {v['sku']}: precio -> {v['price']}  peso -> {fmt_kg(v.get('weight'))}")
        if not apply:
            print("(dry-run) añade --apply")
            return
        for h, p in bk["products"].items():
            old = [rollback_input(v) for v in p["changed"]]
            check(base.gql(token, M_VAR, {"p": p["id"], "v": old}), "productVariantsBulkUpdate")
        print("Restaurado.")
        return

    skus = all_skus(token)
    print("\n== EMBUTIDO DE PIEZA: PRECIOS Y PESOS ==")
    products, updates = {}, {}
    for h, plan in PLAN.items():
        p = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
        if not p:
            sys.exit(f"No existe {h}")
        products[h] = p
        print(f"\n  {p['title']}  [{h}]  ({p['status']})")
        ups, changed = [], []
        for v in p["variants"]["nodes"]:
            if v["sku"] not in plan:
                print(f"    variante {v['title']:22} sku {str(v['sku']):>5}  (fuera del plan, no se toca)")
                continue
            price, weight = plan[v["sku"]]
            new_price, new_weight = diff_fields(v, price, weight)
            price_txt = (f"{v['price']:>6} -> {new_price:>6}" if new_price
                         else f"{v['price']:>6}" + (" (ya aplicado)" if price else " (PENDIENTE Luis Juan)"))
            weight_txt = (f"{fmt_kg(weight_of(v))} -> {fmt_kg(new_weight)}" if new_weight is not None
                          else f"{fmt_kg(weight_of(v))} (sin cambio)")
            extra = f"  compareAt={v['compareAtPrice']}" if v["compareAtPrice"] else ""
            print(f"    sku {v['sku']}  precio {price_txt:<34} peso {weight_txt}{extra}")
            if new_price is not None or new_weight is not None:
                ups.append(build_input(v, new_price, new_weight))
                changed.append({"id": v["id"], "sku": v["sku"], "title": v["title"],
                                "price": v["price"], "weight": weight_of(v)})
        missing = set(plan) - {v["sku"] for v in p["variants"]["nodes"]}
        if missing:
            sys.exit(f"{h}: no hay variante con SKU {sorted(missing)}. Abortado.")
        for sku in plan:
            n = len(skus.get(sku, []))
            if n != 1:
                sys.exit(f"SKU {sku} aparece en {n} variantes de la tienda (se esperaba 1). Abortado.")
        updates[h] = (ups, changed)
    n_changes = sum(len(u[0]) for u in updates.values())
    print("\n  SKU únicos en toda la tienda: OK. Solo se envían los campos que difieren; "
          "SKU, compareAt e inventario no se tocan.")

    if not apply:
        print(f"\n(dry-run) No se ha cambiado nada ({n_changes} variante(s) con cambios). Añade --apply para aplicar.")
        return
    if not n_changes:
        print("\nNada que aplicar: Shopify ya coincide con el plan.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"precios_embutido_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"products": {h: {"id": products[h]["id"], "changed": updates[h][1]}
                            for h in PLAN if updates[h][1]}},
              open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)
    for h, p in products.items():
        if updates[h][0]:
            check(base.gql(token, M_VAR, {"p": p["id"], "v": updates[h][0]}), "productVariantsBulkUpdate")
            print("  OK", h)

    print("\nRelectura:")
    bad = False
    for h, plan in PLAN.items():
        cur = base.gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
        for v in cur["variants"]["nodes"]:
            if v["sku"] in plan:
                price, weight = plan[v["sku"]]
                ok_p = price is None or float(v["price"]) == float(price)
                ok_w = weight_of(v) is not None and abs(weight_of(v) - weight) < 1e-9
                bad = bad or not (ok_p and ok_w)
                estado = "OK" if ok_p and ok_w else "¡NO COINCIDE!"
                print(f"  SKU {v['sku']}: precio {v['price']} peso {fmt_kg(weight_of(v))}  {estado}")
    print("Aplicado." if not bad else "Aplicado, pero hay diferencias: revisar.")


if __name__ == "__main__":
    main()
