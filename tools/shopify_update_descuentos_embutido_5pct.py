#!/usr/bin/env python3
"""
Descuentos automáticos del embutido loncheado: de -10 % a -5 % (desde 5 uds) y título "(-5%)".

Afecta SOLO a los 5 descuentos automáticos de los productos de embutido loncheado
(chorizo, salchichón, lomo de cebo de campo, lomo de bellota, lomito de presa).
Cambia título y porcentaje; NO toca combinesWith, mínimo de unidades, productos, fechas ni estado.
Los 12 descuentos de jamón, BIENVENIDA10, CESTA5-K7Q2 y el envío gratis no se tocan.

Aplicación segura: actualiza primero UN descuento (canario), relee y comprueba que solo han
cambiado título y porcentaje; si algo más cambió, lo restaura y aborta sin tocar los otros 4.

Reutiliza la auth de shopify_update_precios_embutido.py (Keychain, client credentials).

Uso:
  python3 -I tools/shopify_update_descuentos_embutido_5pct.py            # dry-run (solo lee)
  python3 -I tools/shopify_update_descuentos_embutido_5pct.py --apply    # aplica (backup en _backup/)
  python3 -I tools/shopify_update_descuentos_embutido_5pct.py --rollback _backup/descuentos_embutido_XXXX.json --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base

HANDLES = {
    "chorizo-bellota-iberico-loncheado",
    "salchichon-bellota-iberico-loncheado",
    "lomo-bellota-iberico-loncheado-2",
    "lomo-bellota-iberico-loncheado-1",
    "lomo-cebo-campo-50-iberico-loncheado",
}
EXPECTED_COUNT = 5
OLD_PCT, NEW_PCT = 0.10, 0.05
OLD_TAG, NEW_TAG = "(-10%)", "(-5%)"

Q = """{ automaticDiscountNodes(first:100){ nodes{ id automaticDiscount{ __typename
  ... on DiscountAutomaticBasic{ title status startsAt endsAt
    combinesWith{ orderDiscounts productDiscounts shippingDiscounts }
    minimumRequirement{ __typename ... on DiscountMinimumQuantity{ greaterThanOrEqualToQuantity } }
    customerGets{ value{ __typename ... on DiscountPercentage{ percentage } }
      items{ __typename ... on DiscountProducts{ products(first:20){ nodes{ id handle } } } } } } } } } }"""
M_UPD = """mutation($id:ID!,$d:DiscountAutomaticBasicInput!){
  discountAutomaticBasicUpdate(id:$id, automaticBasicDiscount:$d){ userErrors{ field message } } }"""


def state(node):
    d = node["automaticDiscount"]
    items = (d["customerGets"].get("items") or {})
    prods = items.get("products", {}).get("nodes", []) if items.get("__typename") == "DiscountProducts" else []
    return {"id": node["id"], "title": d["title"], "status": d["status"], "startsAt": d["startsAt"], "endsAt": d["endsAt"],
            "combinesWith": d["combinesWith"], "minimumRequirement": d["minimumRequirement"],
            "pct": d["customerGets"]["value"].get("percentage"),
            "productIds": sorted(p["id"] for p in prods), "handles": sorted(p["handle"] for p in prods)}


def fetch(token):
    nodes = base.gql(token, Q)["automaticDiscountNodes"]["nodes"]
    return {n["id"]: state(n) for n in nodes if n["automaticDiscount"]["__typename"] == "DiscountAutomaticBasic"}


def targets(all_states):
    """Descuentos del embutido loncheado: todos sus productos están en HANDLES."""
    return [s for s in all_states.values() if s["handles"] and set(s["handles"]) <= HANDLES]


def same_except(a, b, ignore=("title", "pct")):
    return {k: v for k, v in a.items() if k not in ignore} == {k: v for k, v in b.items() if k not in ignore}


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def update(token, s, title, pct):
    check(base.gql(token, M_UPD, {"id": s["id"], "d": {"title": title, "customerGets": {"value": {"percentage": pct}}}}),
          "discountAutomaticBasicUpdate")


def restore_items_if_needed(token, current, original):
    """Por si una actualización alterase los productos: los vuelve a añadir (idempotente)."""
    missing = sorted(set(original["productIds"]) - set(current["productIds"]))
    if missing:
        check(base.gql(token, M_UPD, {"id": original["id"], "d": {"customerGets": {"items":
              {"products": {"productsToAdd": missing}}}}}), "discountAutomaticBasicUpdate")


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, scopes = base.get_token()
    print(f"Tienda: {base.SHOP} | write_discounts: {'write_discounts' in scopes.split(',')}")

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: restaurar título y porcentaje originales")
        for s in bk["discounts"]:
            print(f"  {s['title']!r}  ({float(s['pct']) * 100:g}%)")
        if not apply:
            print("(dry-run) añade --apply")
            return
        for orig in bk["discounts"]:
            update(token, orig, orig["title"], float(orig["pct"]))
            cur = fetch(token)[orig["id"]]
            restore_items_if_needed(token, cur, orig)
            print("  restaurado", orig["title"])
        print("Restaurado.")
        return

    found = targets(fetch(token))
    print("\n== DESCUENTOS DEL EMBUTIDO LONCHEADO: -10 % -> -5 % ==\n")
    if len(found) != EXPECTED_COUNT:
        sys.exit(f"Se esperaban {EXPECTED_COUNT} descuentos del embutido y hay {len(found)}. Abortado.")
    plan = []
    for s in sorted(found, key=lambda x: x["title"]):
        pct = float(s["pct"])
        if s["status"] != "ACTIVE":
            sys.exit(f"{s['title']!r} no está ACTIVE ({s['status']}). Abortado.")
        done = abs(pct - NEW_PCT) < 1e-9 and NEW_TAG in s["title"]
        if not done and (abs(pct - OLD_PCT) > 1e-9 or OLD_TAG not in s["title"]):
            sys.exit(f"{s['title']!r}: estado inesperado ({pct * 100:g}%). Abortado.")
        new_title = s["title"].replace(OLD_TAG, NEW_TAG)
        minq = (s["minimumRequirement"] or {}).get("greaterThanOrEqualToQuantity")
        cw = ",".join(k.replace("Discounts", "") for k, v in s["combinesWith"].items() if v)
        print(f"  {s['title']}\n     → {new_title}" + ("   (ya aplicado)" if done else ""))
        print(f"     porcentaje {pct * 100:g}% → {NEW_PCT * 100:g}% | mínimo {minq} uds (sin cambio) | "
              f"combina con: {cw} (sin cambio) | {', '.join(s['handles'])}")
        if not done:
            plan.append((s, new_title))
    print(f"\n  A cambiar: {len(plan)} de {EXPECTED_COUNT}. Solo título y porcentaje; combinesWith, mínimo, productos y fechas no se tocan.")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return
    if not plan:
        print("\nNada que aplicar.")
        return

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"descuentos_embutido_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"discounts": [s for s, _ in plan]}, open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)

    canary, canary_title = plan[0]
    update(token, canary, canary_title, NEW_PCT)
    after = fetch(token)[canary["id"]]
    if not (same_except(after, canary) and abs(float(after["pct"]) - NEW_PCT) < 1e-9 and after["title"] == canary_title):
        print("¡El canario no quedó como se esperaba! Restaurando y abortando sin tocar el resto.")
        update(token, canary, canary["title"], float(canary["pct"]))
        restore_items_if_needed(token, fetch(token)[canary["id"]], canary)
        sys.exit("Abortado: revisar el descuento canario.")
    print("  OK canario:", canary_title)
    for s, new_title in plan[1:]:
        update(token, s, new_title, NEW_PCT)
        print("  OK", new_title)

    print("\nRelectura:")
    now = fetch(token)
    bad = False
    for s, new_title in plan:
        a = now[s["id"]]
        ok = same_except(a, s) and abs(float(a["pct"]) - NEW_PCT) < 1e-9 and a["title"] == new_title
        bad = bad or not ok
        print(f"  {a['title']:56} {float(a['pct']) * 100:g}% {a['status']}  {'OK' if ok else '¡REVISAR!'}")
    print("Aplicado." if not bad else "Aplicado, pero hay diferencias: revisar.")


if __name__ == "__main__":
    main()
