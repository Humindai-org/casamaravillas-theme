#!/usr/bin/env python3
"""
Comprueba el montaje del 23/11/2026 (Black Friday 15 % en jamones enteros + envío a 4,99 €) con carritos de PRUEBA:
Storefront API sin token, cartCreate. No crea pedidos ni checkouts, no se paga nada, no pasa por el navegador
(así no contamina Clarity; si se repite en navegador, entrar con ?utm_source=interno).

Casos (el 15 % solo existe desde el 23/11 00:00 Madrid; antes de eso FALLAN los casos 3 y 4, es lo esperado):
  1. Un sobre (chorizo loncheado 100 g, <99 €)            -> envío 8,94 € (decisión 22/11: el 4,99 € NO se aplica; ajustar TARIFA_SOBRE si cambia)
  2. Cesta de más de 99 € (5 chorizos de pieza)           -> envío gratis (descuento «Envío gratis desde 99 €»)
  3. Jamón cebo de campo 7–8 kg, pieza entera (258 €)     -> 219,30 €
  4. Lo mismo + BIENVENIDA10                              -> sigue en 219,30 € (el 10 % no se suma al 15 %)
  5. Cesta: jamón entero + chorizo de pieza + BIENVENIDA10 -> el jamón sigue en 219,30 € y envío gratis (cesta > 99 €)
  Extra informativo: bundles de corte del mismo jamón (máquina / mano / deshuesado) y jamón + sobre + BIENVENIDA10.

Uso:  python3 -I tools/probar_black_friday_2026.py --variante A|B
      A: el 15 % cae sobre el bundle entero (298 € máquina -> 253,30 €)   B: solo sobre la pieza (298 € -> 259,30 €)
"""
import json, sys, time, urllib.error, urllib.request

DOM = "https://casamaravillas.com"
UA = {"User-Agent": "casamaravillas-prueba-black-friday/1.0"}
WELCOME = "BIENVENIDA10"
TARIFA_SOBRE = 8.94      # tarifa Península «hasta 5 kg» vigente; 4,99 € solo si Jorge decide aplicarlo
ALICANTE = {"address1": "Calle Mayor 1", "city": "Alicante", "zip": "03001", "country": "ES", "province": "A"}
SOBRE, CESTA = "chorizo-bellota-iberico-loncheado", "chorizo-bellota-iberico"
JAMON = 53448578466130                                   # cebo de campo 7–8 kg / Pieza entera (SKU 450)
BUNDLES = {"deshuesado": (55164185968978, 268.00), "máquina": (55164186001746, 298.00), "mano": (55164186034514, 328.00)}
Q = """mutation($i:CartInput!){ cartCreate(input:$i){ cart{ cost{ subtotalAmount{amount} totalAmount{amount} }
  discountCodes{ code applicable }
  discountAllocations{ __typename discountedAmount{ amount } ... on CartAutomaticDiscountAllocation{ title } ... on CartCodeDiscountAllocation{ code } }
  lines(first:10){ nodes{ cost{ totalAmount{ amount } } discountAllocations{ discountedAmount{ amount } ... on CartAutomaticDiscountAllocation{ title } } } }
  deliveryGroups(first:3){ nodes{ deliveryOptions{ title estimatedCost{ amount } } } } }
  userErrors{ message } } }"""


def http(req, intentos=5):
    for i in range(intentos):
        try:
            time.sleep(0.6)
            return urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == intentos - 1:
                raise
            time.sleep(int(e.headers.get("Retry-After", 30)) + 2)


def variante_de(handle):
    p = json.load(http(urllib.request.Request(f"{DOM}/products/{handle}.js", headers=UA)))
    return p["variants"][0]["id"], p["variants"][0]["price"] / 100


def cart(lines, codes=()):
    body = {"query": Q, "variables": {"i": {"lines": [{"merchandiseId": f"gid://shopify/ProductVariant/{i}", "quantity": q} for i, q in lines],
            "discountCodes": list(codes), "buyerIdentity": {"countryCode": "ES", "deliveryAddressPreferences": [{"deliveryAddress": ALICANTE}]}}}}
    req = urllib.request.Request(f"{DOM}/api/2025-07/graphql.json", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **UA})
    r = json.load(http(req))["data"]["cartCreate"]
    if r["userErrors"]:
        sys.exit(f"cartCreate: {r['userErrors']}")
    c = r["cart"]
    envio_gratis = any("nvío" in (a.get("title") or "") for a in c["discountAllocations"])
    lineas = [a.get("title") for n in c["lines"]["nodes"] for a in n["discountAllocations"] if a.get("title")]
    tarifa = [float(o["estimatedCost"]["amount"]) for g in c["deliveryGroups"]["nodes"] for o in g["deliveryOptions"]]
    return {"total": float(c["cost"]["totalAmount"]["amount"]), "tarifa": tarifa[0] if tarifa else None, "gratis": envio_gratis,
            "dtos": lineas, "codigos": [(d["code"], d["applicable"]) for d in c["discountCodes"]],
            "lineas": [float(n["cost"]["totalAmount"]["amount"]) for n in c["lines"]["nodes"]]}


def main():
    a = sys.argv[1:]
    if "--variante" not in a:
        sys.exit("Falta --variante A|B")
    var = a[a.index("--variante") + 1].upper()
    sobre, _ = variante_de(SOBRE)
    cesta, _ = variante_de(CESTA)
    fallos = 0

    def check(label, ok, detalle):
        nonlocal fallos
        fallos += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {label:62} {detalle}")

    r = cart([(sobre, 1)])
    check(f"1. un sobre: envío {str(TARIFA_SOBRE).replace('.', ',')} €", r["tarifa"] == TARIFA_SOBRE and not r["gratis"],
          f"tarifa {r['tarifa']} € (esperado {TARIFA_SOBRE}) · gratis={r['gratis']}")
    r = cart([(cesta, 5)])
    check("2. cesta > 99 €: envío gratis", r["gratis"], f"total {r['total']:.2f} € · gratis={r['gratis']} · tarifa base {r['tarifa']} €")
    r = cart([(JAMON, 1)])
    check("3. jamón cebo 7–8 kg pieza: 258 € -> 219,30 €", abs(r["total"] - 219.30) < 0.011, f"total {r['total']:.2f} € · {r['dtos']}")
    r = cart([(JAMON, 1)], (WELCOME,))
    check(f"4. con {WELCOME}: no se suma al 15 % (sigue en 219,30 €)", abs(r["total"] - 219.30) < 0.011,
          f"total {r['total']:.2f} € · códigos {r['codigos']} · {r['dtos']}")

    # 5. Cesta con jamón entero + otro producto + BIENVENIDA10: el jamón se queda en 219,30 € (el 10 % no se suma al 15 %)
    #    y la cesta (> 99 €) lleva envío gratis. La línea del chorizo y el total se imprimen, sin exigir un valor.
    r = cart([(JAMON, 1), (cesta, 1)], (WELCOME,))
    # Shopify devuelve las líneas en otro orden que el de entrada (00:02 del 23/11: [19.9, 219.3]): se busca el jamón por importe.
    jamon_ok = any(abs(x - 219.30) < 0.011 for x in r["lineas"])
    check(f"5. cesta jamón + chorizo + {WELCOME}: jamón en 219,30 € y envío gratis", jamon_ok and r["gratis"],
          f"líneas {r['lineas']} · total {r['total']:.2f} € · gratis={r['gratis']} · códigos {r['codigos']} · {r['dtos']}")

    print(f"\n  Informativo (variante {var}): bundles de corte del jamón cebo 7–8 kg")
    for nombre, (vid, precio) in BUNDLES.items():
        r = cart([(vid, 1)])
        a_ = round(precio * 0.85, 2)
        b_ = round(precio - 38.70, 2)
        print(f"    {nombre:10} lista {precio:6.2f} € -> carrito {r['total']:7.2f} €   (A, 15 % del bundle entero: {a_:.2f} · B, 15 % de la pieza: {b_:.2f})")
    r = cart([(JAMON, 1), (sobre, 1)], (WELCOME,))
    print(f"    jamón + sobre + {WELCOME}: total {r['total']:.2f} € · códigos {r['codigos']} · {r['dtos']}")
    print("\nTodo OK." if not fallos else f"\n{fallos} comprobación(es) FALLIDA(S).")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
