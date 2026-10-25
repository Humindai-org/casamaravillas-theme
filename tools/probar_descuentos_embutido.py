#!/usr/bin/env python3
"""
Comprueba con carritos de PRUEBA (Storefront API sin token, cartCreate: no crea pedidos ni checkouts)
que el carrito cobra el descuento esperado del embutido loncheado, y, con --ficha, que la ficha
publicada promete lo mismo (lee el JS publicado de main-product.js).

Uso:
  python3 -I tools/probar_descuentos_embutido.py --esperado 10   # estado actual (antes del Paso 5)
  python3 -I tools/probar_descuentos_embutido.py --esperado 5 --ficha   # estado final (después del Paso 5)

--ficha solo tiene sentido con --esperado 5: antes del Paso 5 el JS publicado es el antiguo y falla (es lo esperado).
"""
import json, re, sys, time, urllib.error, urllib.request

DOM = "https://casamaravillas.com"
UA = {"User-Agent": "casamaravillas-prueba-descuentos/1.0"}
JAMON, EMBUTIDO_A, EMBUTIDO_B = ("jamon-bellota-100-iberico-loncheado-a-maquina",
                                  "chorizo-bellota-iberico-loncheado", "salchichon-bellota-iberico-loncheado")
WELCOME = "BIENVENIDA10"

Q = """mutation($i:CartInput!){ cartCreate(input:$i){ cart{ cost{ subtotalAmount{amount} totalAmount{amount} }
  discountCodes{ code applicable } } userErrors{ message } } }"""


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode()


def variant_id(handle):
    p = json.loads(get(f"{DOM}/products/{handle}.js"))
    return p["variants"][0]["id"], p["variants"][0]["price"] / 100


def cart_total(lines, codes=()):
    body = {"query": Q, "variables": {"i": {"lines": [{"merchandiseId": f"gid://shopify/ProductVariant/{i}", "quantity": q}
                                                      for i, q in lines], "discountCodes": list(codes),
                                           "buyerIdentity": {"countryCode": "ES"}}}}
    req = urllib.request.Request(f"{DOM}/api/2025-07/graphql.json", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **UA})
    c = json.load(urllib.request.urlopen(req, timeout=30))["data"]["cartCreate"]["cart"]
    return float(c["cost"]["totalAmount"]["amount"]), c["discountCodes"]


def main():
    args = sys.argv[1:]
    if "--esperado" not in args:
        sys.exit("Falta --esperado 5|10 (descuento actual esperado del embutido, en %)")
    pct = int(args[args.index("--esperado") + 1])
    jamon, pj = variant_id(JAMON)
    ea, pa = variant_id(EMBUTIDO_A)
    eb, pb = variant_id(EMBUTIDO_B)
    r = lambda x: round(x + 1e-9, 2)
    cases = [
        ("4 chorizo loncheado (bajo el umbral)", [(ea, 4)], (), r(4 * pa)),
        (f"5 chorizo loncheado (-{pct} %)", [(ea, 5)], (), r(5 * pa * (100 - pct) / 100)),
        (f"5 chorizo + 5 salchichón (-{pct} % cada línea)", [(ea, 5), (eb, 5)], (), r(5 * pa * (100 - pct) / 100 + 5 * pb * (100 - pct) / 100)),
        ("10 jamón a máquina (-10 %, no cambia)", [(jamon, 10)], (), r(10 * pj * 0.9)),
        (f"5 chorizo + {WELCOME} (gana el 10 % sobre todo el carrito)", [(ea, 5)], (WELCOME,), r(5 * pa * 0.9)),
    ]
    fails = 0
    for label, lines, codes, expected in cases:
        total, dc = cart_total(lines, codes)
        ok = abs(total - expected) < 0.011
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {label:62} total {total:7.2f} € (esperado {expected:7.2f})"
              + (f"  códigos {[(d['code'], d['applicable']) for d in dc]}" if codes else ""))

    if "--ficha" in args:
        html = get(f"{DOM}/products/{EMBUTIDO_A}?cb={int(time.time())}")
        m = re.search(r'https://[^"\']*main-product\.js[^"\']*', html)
        js = get(m.group(0)) if m else ""
        want = re.search(r"embutido:\s*\{\s*minQty:\s*5,\s*pct:\s*%d\s*\}" % pct, js)
        jam = re.search(r"jamon:\s*\{\s*minQty:\s*10,\s*pct:\s*10\s*\}", js)
        ok = bool(want and jam)
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  ficha publicada: JS con embutido -{pct} % desde 5 uds y jamón -10 % desde 10 uds")
    print("Todo OK." if not fails else f"{fails} comprobación(es) FALLIDA(S).")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
