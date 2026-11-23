#!/usr/bin/env python3
"""
Pausa / reactivación de los 9 descuentos automáticos de Black Friday 2026 («Black Friday 2026 · 15 % jamones enteros · …»).
Decisión de Jorge (23/11/2026): desactivarlos SIN borrarlos y CON LA MISMA FECHA DE FIN (30/11 23:59 Madrid) hasta justo antes de
fusionar el PR #16; reactivarlos cuando él lo diga y repetir entonces las pruebas 1–5 (probar_black_friday_2026.py --variante B).

POR QUÉ NO SE USA discountAutomaticDeactivate/Activate (comprobado el 23/11/2026 con un descuento real):
  · Deactivate pone endsAt = «ahora» (estado EXPIRED) y Activate deja endsAt = null: al reactivar, el descuento no acabaría nunca.
Lo que hace este script en su lugar (discountAutomaticBasicUpdate): deja endsAt = 2026-11-30T22:59:00Z y mueve startsAt a un minuto
antes del fin (2026-11-30T22:58:00Z). El descuento queda PROGRAMADO (SCHEDULED), sin efecto hoy, con su fecha de fin intacta.
Reactivar = devolver startsAt a su valor original (2026-11-22T23:00:00Z, ya pasado -> ACTIVO al instante).

Uso:  python3 -I tools/shopify_bf_pausa_2026.py estado                     # solo lee
      python3 -I tools/shopify_bf_pausa_2026.py pausar    [--apply]        # copia de seguridad + pausa + verifica (carrito de prueba: 258 €)
      python3 -I tools/shopify_bf_pausa_2026.py reactivar [--apply]        # restaura startsAt/endsAt originales + verifica (carrito: 219,30 €)
Solo toca descuentos cuyo título empieza por «Black Friday 2026 ·». No toca Meta ni ClickUp ni el tema.
"""
import importlib.util, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base
BK = os.path.join(HERE, "..", "_backup")

PREFIJO = "Black Friday 2026 ·"
STARTS, ENDS = "2026-11-22T23:00:00Z", "2026-11-30T22:59:00Z"     # programación original (23/11 00:00 -> 30/11 23:59 Madrid)
PAUSA_STARTS = "2026-11-30T22:58:00Z"                              # 1 minuto antes del fin: el descuento queda SCHEDULED
DOM, UA = "https://casamaravillas.com", {"User-Agent": "casamaravillas-prueba-bf-pausa/1.0"}
JAMON = 53448578466130                                             # cebo de campo 7–8 kg / pieza entera (SKU 450): 258 € sin descuento, 219,30 € con él
Q = """{ automaticDiscountNodes(first:100){ nodes{ id automaticDiscount{ __typename ... on DiscountAutomaticBasic{ title status startsAt endsAt } } } } }"""
M = """mutation($id:ID!,$d:DiscountAutomaticBasicInput!){ discountAutomaticBasicUpdate(id:$id, automaticBasicDiscount:$d){
  automaticDiscountNode{ id } userErrors{ field message code } } }"""
CART = """mutation($i:CartInput!){ cartCreate(input:$i){ cart{ cost{ totalAmount{ amount } } } userErrors{ message } } }"""


def leer(token):
    return [{"id": n["id"], "title": n["automaticDiscount"]["title"], "status": n["automaticDiscount"]["status"],
             "startsAt": n["automaticDiscount"]["startsAt"], "endsAt": n["automaticDiscount"]["endsAt"]}
            for n in base.gql(token, Q)["automaticDiscountNodes"]["nodes"]
            if n["automaticDiscount"]["__typename"] == "DiscountAutomaticBasic" and (n["automaticDiscount"]["title"] or "").startswith(PREFIJO)]


def escribir(token, did, starts, ends):
    e = base.gql(token, M, {"id": did, "d": {"startsAt": starts, "endsAt": ends}})["discountAutomaticBasicUpdate"]["userErrors"]
    if e:
        sys.exit(f"ERROR discountAutomaticBasicUpdate {did}: {e}")


def carrito():
    body = {"query": CART, "variables": {"i": {"lines": [{"merchandiseId": f"gid://shopify/ProductVariant/{JAMON}", "quantity": 1}], "buyerIdentity": {"countryCode": "ES"}}}}
    req = urllib.request.Request(f"{DOM}/api/2025-07/graphql.json", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **UA})
    time.sleep(0.6)
    return float(json.load(urllib.request.urlopen(req, timeout=30))["data"]["cartCreate"]["cart"]["cost"]["totalAmount"]["amount"])


def mostrar(ds):
    for d in ds:
        print(f"  {d['id'].split('/')[-1]}  {d['status']:9} {d['startsAt']} → {d['endsAt']}  {d['title']}")


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("estado", "pausar", "reactivar"):
        sys.exit(__doc__)
    apply = "--apply" in a
    token, _ = base.get_token()
    ds = leer(token)
    print(f"Tienda: {base.SHOP} | {a[0]} | {'APPLY' if apply else 'simulacro'} | descuentos «{PREFIJO}»: {len(ds)}\n")
    mostrar(ds)
    if len(ds) != 9:
        sys.exit(f"ERROR: se esperaban 9 descuentos de Black Friday y hay {len(ds)}. Abortado.")
    if a[0] == "estado":
        print(f"\nCarrito de prueba (jamón cebo 7–8 kg pieza, 258 € de lista): {carrito():.2f} €")
        return

    if a[0] == "pausar":
        nuevos = (PAUSA_STARTS, ENDS)
        esperado_estado, esperado_total = "SCHEDULED", 258.00
    else:
        nuevos = (STARTS, ENDS)
        esperado_estado, esperado_total = "ACTIVE", 219.30
    print(f"\nTras {a[0]}: startsAt {nuevos[0]} · endsAt {nuevos[1]} · estado esperado {esperado_estado} · carrito esperado {esperado_total:.2f} €")
    if not apply:
        print("(simulacro) No se ha escrito nada. Añade --apply.")
        return

    os.makedirs(BK, exist_ok=True)
    path = os.path.abspath(os.path.join(BK, f"bf_{a[0]}_{time.strftime('%Y%m%d-%H%M%S')}.json"))
    json.dump({"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "orden": a[0], "originales_programados": {"startsAt": STARTS, "endsAt": ENDS}, "antes": ds},
              open(path, "w"), ensure_ascii=False, indent=1)
    print("Copia de seguridad:", path)
    for d in ds:
        escribir(token, d["id"], *nuevos)
    despues = leer(token)
    print("\nRelectura:")
    mostrar(despues)
    fallos = [d for d in despues if d["status"] != esperado_estado or d["endsAt"] != ENDS or d["startsAt"] != nuevos[0]]
    total = carrito()
    print(f"\nCarrito de prueba (jamón cebo 7–8 kg pieza): {total:.2f} € (esperado {esperado_total:.2f} €)")
    ok = not fallos and abs(total - esperado_total) < 0.011
    print("Todo OK." if ok else f"REVISAR: {len(fallos)} descuento(s) con estado/fechas inesperados o carrito distinto.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
