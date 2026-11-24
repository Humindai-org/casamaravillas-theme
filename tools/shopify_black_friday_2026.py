#!/usr/bin/env python3
"""
Montaje del lunes 23/11/2026 (ClickUp 123m57f4gzx y 123m57f7r86): Black Friday 15 % en los tres jamones enteros
y envío de la zona «Peninsula» del «General profile» a 4,99 €.

DRY-RUN POR DEFECTO: sin --apply solo lee. Nada se escribe sin el OK de Jorge. No toca Meta ni ClickUp.

Subcomandos:
  backup                         foto de lo que se va a tocar -> _backup/black_friday_2026_pre_<fecha>.json (solo lee la tienda)
  envio  [--apply]               las dos tarifas de la zona Peninsula pasan a 4,99 € (zonas 1-5 no se tocan)
  bf --variante A|B [--apply]    descuento(s) automático(s) del 15 %
        A = UN descuento al 15 % sobre los 3 productos: cae sobre el bundle ENTERO (pieza + servicio de corte/deshuesado)
        B = 9 descuentos de importe fijo (1 por producto y peso): 15 % del precio de la PIEZA, aplicado a la pieza y a sus
            3 bundles; el servicio no se rebaja. Importe fijo = 15 % del precio actual (se recalcula en cada ejecución)
  rollback --backup <json> [--apply]
        borra los descuentos creados (los ids van en el JSON de la ejecución) y restaura las tarifas del backup

Fechas: 23/11/2026 00:00 -> 30/11/2026 23:59 hora de Madrid (CET, UTC+1) = 2026-11-22T23:00:00Z -> 2026-11-30T22:59:00Z.
Combinación: con envío y con otros descuentos de PRODUCTO (productDiscounts = true; orderDiscounts = false). Es necesario: con false,
Shopify aplica solo UNO de los 9 descuentos por carrito y las demás líneas pierden el 15 %. No se suma a BIENVENIDA10 ni a
CESTA5-K7Q2 porque esos códigos tienen productDiscounts = false (Shopify exige que ambos lados lo permitan).
Auth: la de shopify_update_precios_embutido.py (Keychain, client credentials). Scopes: write_shipping, write_discounts.
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base
BK = os.path.join(HERE, "..", "_backup")

PROFILE_NAME, ZONE_NAME = "General profile", "Peninsula"
RATE_BEFORE, RATE_AFTER = ("8.94", "11.2"), "4.99"
STARTS, ENDS = "2026-11-22T23:00:00Z", "2026-11-30T22:59:00Z"
PCT = 0.15
HAMS = {"cebo": "jamon-cebo-de-campo-50-iberico-pieza-entera", "bellota50": "jamon-bellota-50-iberico-pieza-entera",
        "bellota100": "jamon-bellota-100-iberico-pieza-entera"}
LABEL = {"cebo": "cebo de campo 50 %", "bellota50": "bellota 50 %", "bellota100": "bellota 100 %"}
TITLE_A = "Black Friday 2026 · 15 % jamones enteros"
MAX_AUTOMATIC = 25  # límite de Shopify de descuentos automáticos activos

Q_PROFILE = """{ deliveryProfiles(first:10){ nodes{ id name default profileLocationGroups{ locationGroup{ id }
  locationGroupZones(first:20){ nodes{ zone{ id name } methodDefinitions(first:20){ nodes{ id name active
    rateProvider{ __typename ... on DeliveryRateDefinition{ id price{ amount currencyCode } } } } } } } } } } }"""
M_PROFILE = """mutation($id:ID!,$p:DeliveryProfileInput!){ deliveryProfileUpdate(id:$id, profile:$p){
  profile{ id } userErrors{ field message } } }"""
Q_HAM = """query($h:String!){ productByHandle(handle:$h){ id title status variants(first:50){ nodes{ id title sku price
  requiresComponents availableForSale } } } }"""
Q_AUTO = "{ automaticDiscountNodes(first:100){ nodes{ id automaticDiscount{ __typename ... on DiscountAutomaticBasic{ title status } "\
         "... on DiscountAutomaticFreeShipping{ title status } ... on DiscountAutomaticApp{ title status } } } } }"
M_CREATE = """mutation($d:DiscountAutomaticBasicInput!){ discountAutomaticBasicCreate(automaticBasicDiscount:$d){
  automaticDiscountNode{ id } userErrors{ field message code } } }"""
M_DELETE = "mutation($id:ID!){ discountAutomaticDelete(id:$id){ deletedAutomaticDiscountId userErrors{ field message } } }"


def fail(msg):
    sys.exit(f"ERROR: {msg}")


def errs(res, key, sub=None):
    node = res[key]
    e = node.get("userErrors") or []
    if e:
        fail(f"{key}: {e}")
    return node


# ───────────────────────── lectura ─────────────────────────
def read_peninsula(token):
    prof = next((p for p in base.gql(token, Q_PROFILE)["deliveryProfiles"]["nodes"] if p["name"] == PROFILE_NAME), None)
    if not prof:
        fail(f"No existe el perfil {PROFILE_NAME!r}")
    zones = [(g["locationGroup"]["id"], z) for g in prof["profileLocationGroups"] for z in g["locationGroupZones"]["nodes"]
             if z["zone"]["name"].strip() == ZONE_NAME]
    if len(zones) != 1:
        fail(f"Se esperaba 1 zona {ZONE_NAME!r} y hay {len(zones)}")
    group_id, z = zones[0]
    methods = [{"id": m["id"], "rateId": m["rateProvider"]["id"], "price": m["rateProvider"]["price"]["amount"],
                "currency": m["rateProvider"]["price"]["currencyCode"], "name": m["name"], "active": m["active"]}
               for m in z["methodDefinitions"]["nodes"] if m["rateProvider"]["__typename"] == "DeliveryRateDefinition"]
    return prof["id"], group_id, z["zone"]["id"], methods


def read_hams(token):
    out = {}
    for k, h in HAMS.items():
        p = base.gql(token, Q_HAM, {"h": h})["productByHandle"]
        if not p:
            fail(f"No existe el producto {h}")
        out[k] = p
    return out


def automatic_titles(token):
    return {n["id"]: n["automaticDiscount"].get("title") for n in base.gql(token, Q_AUTO)["automaticDiscountNodes"]["nodes"]
            if n["automaticDiscount"].get("status") != "EXPIRED"}


def piece_groups(prod):
    """variantes de un jamón agrupadas por SKU de pieza -> {sku: {'pieza': v, 'bundles': [v...]}}.
    La pieza entera y sus 3 bundles (deshuesado, máquina, mano) comparten SKU (es el de la pieza)."""
    g = {}
    for v in prod["variants"]["nodes"]:
        d = g.setdefault(v["sku"], {"pieza": None, "bundles": []})
        if v["requiresComponents"]:
            d["bundles"].append(v)
        else:
            d["pieza"] = v
    return g


# ───────────────────────── backup ─────────────────────────
def cmd_backup(token):
    pid, gid, zid, methods = read_peninsula(token)
    hams = read_hams(token)
    snap = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "perfil": pid, "locationGroup": gid, "zona": zid, "metodos_peninsula": methods,
            "jamones": {k: {"id": p["id"], "variantes": p["variants"]["nodes"]} for k, p in hams.items()},
            "descuentos_automaticos": automatic_titles(token)}
    os.makedirs(BK, exist_ok=True)
    path = os.path.abspath(os.path.join(BK, f"black_friday_2026_pre_{time.strftime('%Y%m%d-%H%M%S')}.json"))
    json.dump(snap, open(path, "w"), ensure_ascii=False, indent=1)
    print("Backup:", path)
    return path


# ───────────────────────── envío ─────────────────────────
def cmd_envio(token, apply):
    pid, gid, zid, methods = read_peninsula(token)
    print(f"== ENVÍO · perfil {PROFILE_NAME!r} · zona {ZONE_NAME!r} (las zonas 1-5 no se tocan)")
    bad = []
    for m in methods:
        estado = "ya aplicado" if float(m["price"]) == float(RATE_AFTER) else ("CAMBIA" if m["price"] in RATE_BEFORE else "¡PRECIO INESPERADO!")
        if estado.startswith("¡"):
            bad.append(m)
        print(f"  {m['id'].split('/')[-1]}  {m['name']!r:18} activo={m['active']}  {m['price']:>6} → {RATE_AFTER}  {estado}")
    if len(methods) != 2 or bad:
        fail(f"Se esperaban 2 tarifas con {RATE_BEFORE} y hay {len(methods)} / inesperadas: {bad}. Abortado.")
    todo = [m for m in methods if float(m["price"]) != float(RATE_AFTER)]
    payload = {"locationGroupsToUpdate": [{"id": gid, "zonesToUpdate": [{"id": zid, "methodDefinitionsToUpdate": [
        {"id": m["id"], "rateDefinition": {"id": m["rateId"], "price": {"amount": RATE_AFTER, "currencyCode": m["currency"]}}} for m in todo]}]}]}
    print("  payload:", json.dumps(payload))
    print("  Las condiciones de peso (hasta 5 kg / desde 5 kg) no se envían: no cambian.")
    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply (solo con el OK de Jorge).")
        return None
    if not todo:
        print("Nada que aplicar.")
        return None
    errs(base.gql(token, M_PROFILE, {"id": pid, "p": payload}), "deliveryProfileUpdate")
    _, _, _, after = read_peninsula(token)
    ok = all(float(m["price"]) == float(RATE_AFTER) for m in after) and len(after) == 2
    print("Relectura:", [(m["id"].split("/")[-1], m["price"]) for m in after], "→", "OK" if ok else "¡REVISAR!")
    return {"tarifas": {m["id"]: m["price"] for m in methods}}


# ───────────────────────── Black Friday ─────────────────────────
def plan_bf(hams, variante):
    """Lista de descuentos a crear: [(título, input GraphQL)]."""
    comb = {"productDiscounts": True, "orderDiscounts": False, "shippingDiscounts": True}
    if variante == "A":
        ids = [p["id"] for p in hams.values()]
        return [(TITLE_A, {"title": TITLE_A, "startsAt": STARTS, "endsAt": ENDS, "combinesWith": comb,
                           "customerGets": {"value": {"percentage": PCT}, "items": {"products": {"productsToAdd": ids}}}})]
    out = []
    for k, prod in hams.items():
        for sku, g in sorted(piece_groups(prod).items()):
            if not g["pieza"] or len(g["bundles"]) != 3:
                fail(f"{k} SKU {sku}: se esperaba 1 pieza + 3 bundles y hay {bool(g['pieza'])} + {len(g['bundles'])}")
            cents = round(float(g["pieza"]["price"]) * 100)
            off = cents * 15
            if off % 100:
                fail(f"{k} SKU {sku}: el 15 % de {g['pieza']['price']} no es un nº exacto de céntimos")
            amount = f"{off // 100 / 100:.2f}"
            title = f"{TITLE_A} · {LABEL[k]} · {g['pieza']['title'].split(' / ')[0].replace('.0kg', ' kg').replace(' - ', '–')}"
            ids = [g["pieza"]["id"]] + [b["id"] for b in g["bundles"]]
            out.append((title, {"title": title, "startsAt": STARTS, "endsAt": ENDS, "combinesWith": comb,
                                "customerGets": {"value": {"discountAmount": {"amount": amount, "appliesOnEachItem": True}},
                                                 "items": {"products": {"productVariantsToAdd": ids}}}}))
    return out


def cmd_bf(token, variante, apply):
    hams = read_hams(token)
    existing = automatic_titles(token)
    plan = plan_bf(hams, variante)
    print(f"== BLACK FRIDAY · variante {variante} · {STARTS} → {ENDS}  (23/11 00:00 → 30/11 23:59 Madrid)")
    print(f"  descuentos automáticos hoy: {len(existing)}; tras crear: {len(existing) + len(plan)} (máx. {MAX_AUTOMATIC})")
    if len(existing) + len(plan) > MAX_AUTOMATIC:
        fail("Se superaría el límite de descuentos automáticos.")
    dup = [t for t, _ in plan if t in existing.values()]
    if dup:
        fail(f"Ya existen descuentos con estos títulos: {dup}")
    for t, d in plan:
        v = d["customerGets"]["value"]
        val = f"{v['percentage'] * 100:g} %" if "percentage" in v else f"-{v['discountAmount']['amount']} € por unidad"
        n = d["customerGets"]["items"]["products"]
        alc = f"{len(n['productsToAdd'])} productos (todas sus variantes, bundles incluidos)" if "productsToAdd" in n else f"{len(n['productVariantsToAdd'])} variantes"
        print(f"  · {t}\n      {val} · {alc} · combina solo con envío")
    if not apply:
        print("\n(dry-run) No se ha creado nada. Añade --apply (solo con el OK de Jorge).")
        return None
    created = []
    for t, d in plan:
        r = errs(base.gql(token, M_CREATE, {"d": d}), "discountAutomaticBasicCreate")
        created.append(r["automaticDiscountNode"]["id"])
        print("  creado", created[-1].split("/")[-1], t)
    return {"descuentos_creados": created}


# ───────────────────────── rollback ─────────────────────────
def cmd_rollback(token, path, apply):
    bk = json.load(open(path))
    print("Rollback desde", path)
    ledger = bk.get("aplicado", {})
    for i in ledger.get("descuentos_creados", []):
        print("  borrar descuento", i)
    for mid, price in (bk.get("metodos_peninsula") and {m["id"]: m["price"] for m in bk["metodos_peninsula"]} or {}).items():
        print(f"  restaurar tarifa {mid.split('/')[-1]} → {price}")
    if not apply:
        print("(dry-run) añade --apply")
        return
    for i in ledger.get("descuentos_creados", []):
        errs(base.gql(token, M_DELETE, {"id": i}), "discountAutomaticDelete")
    if ledger.get("tarifas"):
        _, gid, zid, methods = read_peninsula(token)
        payload = {"locationGroupsToUpdate": [{"id": gid, "zonesToUpdate": [{"id": zid, "methodDefinitionsToUpdate": [
            {"id": m["id"], "rateDefinition": {"id": m["rateId"], "price": {"amount": ledger["tarifas"][m["id"]], "currencyCode": m["currency"]}}}
            for m in methods]}]}]}
        errs(base.gql(token, M_PROFILE, {"id": read_peninsula(token)[0], "p": payload}), "deliveryProfileUpdate")
    print("Restaurado.")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    apply = "--apply" in a
    token, scopes = base.get_token()
    sc = scopes.split(",")
    print(f"Tienda: {base.SHOP} | write_shipping: {'write_shipping' in sc} | write_discounts: {'write_discounts' in sc}"
          f" | {'APPLY' if apply else 'dry-run'}\n")
    cmd = a[0]
    if cmd == "backup":
        cmd_backup(token)
    elif cmd == "envio" or cmd == "bf":
        if apply:                      # la copia de seguridad va SIEMPRE antes de escribir
            path = cmd_backup(token)
        res = cmd_envio(token, apply) if cmd == "envio" else cmd_bf(token, a[a.index("--variante") + 1].upper(), apply)
        if apply and res:
            bk = json.load(open(path)); bk["aplicado"] = {**bk.get("aplicado", {}), **res}
            json.dump(bk, open(path, "w"), ensure_ascii=False, indent=1)
            print("Rollback:", f"python3 -I tools/shopify_black_friday_2026.py rollback --backup {os.path.relpath(path, os.path.join(HERE, '..'))} --apply")
    elif cmd == "rollback":
        cmd_rollback(token, a[a.index("--backup") + 1], apply)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
