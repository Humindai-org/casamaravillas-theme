#!/usr/bin/env python3
"""
Comprueba con carritos de PRUEBA (Storefront API sin token, cartCreate: no crea pedidos ni checkouts) si el
envío gratis se concede según el umbral esperado, con y sin BIENVENIDA10. El umbral se mide DESPUÉS de los
descuentos (carrito 99,50 € con -10 % de BIENVENIDA10 = 89,55 €).

Detecta el envío gratis por la asignación de descuento "Envío gratis…" del carrito, que solo aparece si el carrito
lleva una dirección de entrega (aquí, Madrid).
Además, con --ficha, comprueba que la tienda anuncia el umbral esperado (barra de anuncios, cajón y /pages/envios).

Uso:
  python3 -I tools/probar_envio_gratis.py --umbral 80            # estado actual
  python3 -I tools/probar_envio_gratis.py --umbral 99 --ficha    # estado final
"""
import itertools, json, re, sys, time, urllib.request

DOM = "https://casamaravillas.com"
UA = {"User-Agent": "casamaravillas-prueba-envio/1.0"}
WELCOME = "BIENVENIDA10"
# Productos SIN descuento por volumen en estas cantidades (así el total es predecible)
CATALOGO = [("lomo-bellota-iberico", 5), ("lomito-presa-bellota", 5), ("lomo-cebo-campo-50-iberico", 5),
            ("chorizo-bellota-iberico", 5), ("jamon-bellota-100-iberico-loncheado-a-maquina", 9),
            ("jamon-bellota-100-iberico-loncheado-a-mano", 9), ("chorizo-bellota-iberico-loncheado", 4)]
Q = """mutation($i:CartInput!){ cartCreate(input:$i){ cart{ cost{ subtotalAmount{amount} totalAmount{amount} }
  discountCodes{ code applicable }
  discountAllocations{ __typename discountedAmount{ amount } ... on CartAutomaticDiscountAllocation{ title } ... on CartCodeDiscountAllocation{ code } } }
  userErrors{ message } } }"""


def get(url):
    for i in range(4):
        try:
            time.sleep(0.4)
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode()
        except Exception:
            time.sleep(2 * (i + 1))
    raise SystemExit(f"No se pudo leer {url}")


def variantes():
    out = {}
    for h, _ in CATALOGO:
        p = json.loads(get(f"{DOM}/products/{h}.js"))
        out[h] = (p["variants"][0]["id"], round(p["variants"][0]["price"]))
    return out


def combo(objetivo_cents, vs):
    """Combinación sin descuento por volumen cuyo total sea el más cercano posible al objetivo (±5 cts)."""
    mejor = None
    rangos = [range(0, mx + 1) for _, mx in CATALOGO]
    for cants in itertools.product(*rangos):
        total = sum(c * vs[h][1] for c, (h, _) in zip(cants, CATALOGO))
        if sum(cants) and (mejor is None or abs(total - objetivo_cents) < abs(mejor[0] - objetivo_cents)):
            mejor = (total, cants)
            if total == objetivo_cents:
                break
    total, cants = mejor
    return total, [(vs[h][0], c, h) for c, (h, _) in zip(cants, CATALOGO) if c]


def cart(lines, codes=()):
    body = {"query": Q, "variables": {"i": {"lines": [{"merchandiseId": f"gid://shopify/ProductVariant/{i}", "quantity": q} for i, q, _ in lines],
                                            "discountCodes": list(codes), "buyerIdentity": {"countryCode": "ES", "deliveryAddressPreferences": [{"deliveryAddress": {"address1": "Calle Mayor 1", "city": "Madrid", "zip": "28013", "country": "ES", "province": "M"}}]}}}}
    req = urllib.request.Request(f"{DOM}/api/2025-07/graphql.json", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **UA})
    c = json.load(urllib.request.urlopen(req, timeout=30))["data"]["cartCreate"]["cart"]
    envio = [a.get("title") for a in c["discountAllocations"] if a.get("title") and "nvío" in a["title"]]
    # Importe NETO de la compra (lo que mide el umbral): subtotal tras descuentos de producto menos los descuentos
    # de pedido (códigos). totalAmount no sirve: suma el envío cuando no es gratis.
    dto_pedido = sum(float(a["discountedAmount"]["amount"]) for a in c["discountAllocations"] if not (a.get("title") and "nvío" in a["title"]))
    return round(float(c["cost"]["subtotalAmount"]["amount"]) - dto_pedido, 2), bool(envio), envio, c["discountCodes"]


def main():
    args = sys.argv[1:]
    if "--umbral" not in args:
        sys.exit("Falta --umbral 80|99")
    umbral = int(args[args.index("--umbral") + 1])
    vs = variantes()
    fallos = 0
    print(f"Umbral esperado: {umbral} € (medido tras descuentos)")
    for objetivo in (8500, 9950):
        total, lines = combo(objetivo, vs)
        desc = " + ".join(f"{q}×{h}" for _, q, h in lines)
        for codes in ((), (WELCOME,)):
            neto, gratis, titulo, dc = cart(lines, codes)
            esperado = neto >= umbral
            ok = gratis == esperado
            fallos += not ok
            print(f"  {'PASS' if ok else 'FAIL'}  bruto {total/100:6.2f} € | {'con ' + WELCOME if codes else 'sin código  '} | total tras dto. {neto:6.2f} € | "
                  f"envío gratis: {'SÍ' if gratis else 'no':2} (esperado {'SÍ' if esperado else 'no'}){'  ' + str(titulo) if titulo else ''}")
        print(f"        carrito: {desc}")
    if "--ficha" in args:
        html = " ".join(get(DOM + u) for u in ("/", "/pages/envios"))
        txt = re.sub(r"<script.*?</script>|<[^>]+>", " ", html, flags=re.S)
        malos = sorted(set(re.findall(r"[^.]{0,40}(?<![\d.,])80(?:[.,]00)?\s?(?:€|&euro;|euros?)[^.]{0,20}|[^.]{0,30}€\s?80(?![\d])[^.]{0,20}", txt)))
        buenos = re.findall(r"(?:€\s?%d|%d\s?(?:€|&euro;))" % (umbral, umbral), txt)
        ok = bool(buenos) and not malos
        fallos += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  la tienda anuncia {umbral} € ({len(buenos)} menciones en portada y /pages/envios) y ninguna dice 80 € {malos[:2] if malos else ''}")
    print("Todo OK." if not fallos else f"{fallos} comprobación(es) FALLIDA(S).")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
