#!/usr/bin/env python3
"""
Prueba AISLADA del IVA con bundles de variante (jamón con corte). No toca los 3 jamones ni el tema.

  setup    crea «Servicio de preparación del jamón» (BORRADOR, sin categoría) y «ZZ Prueba IVA (no comprar)»
           (activo SOLO en Tienda online) con 2 padres bundle: uno disponible y otro con la pieza agotada.
  calc     draftOrderCalculate (no crea pedidos) para pieza, corte y descuentos; imprime el IVA por línea.
  cleanup  borra el producto de prueba (el servicio se conserva salvo --con-servicio).

Estado (ids) en _backup/prueba_iva_bundle.json (ignorado por git).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jamon_bundles as jb

ESTADO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_backup", "prueba_iva_bundle.json")
base = jb.base


def guardar(d):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    json.dump(d, open(ESTADO, "w"), indent=1, ensure_ascii=False)


def cargar():
    return json.load(open(ESTADO))


def setup(tok):
    cat = base.gql(tok, """{ productByHandle(handle:"jamon-cebo-de-campo-50-iberico-pieza-entera"){ category{ id } } }""")
    cat_id = cat["productByHandle"]["category"]["id"]
    srv_vars = [
        {"valor": "Deshuesado", "precio": "10.00", "sku": "SRV-DESH", "envio": False},
        {"valor": "Corte a máquina y envasado", "precio": "40.00", "sku": "SRV-MAQ", "envio": False},
        {"valor": "Corte a mano y envasado", "precio": "70.00", "sku": "SRV-MANO", "envio": False},
    ]
    srv, sv = jb.crear_producto(tok, "Servicio de preparación del jamón", "DRAFT", None, "Servicio", srv_vars,
                                descripcion="<p>Servicio de preparación (IVA 21 %). No asignar categoría: sin categoría Shopify aplica la tasa general. Componente de las variantes de corte del jamón; no vender suelto.</p>")
    print("servicio:", srv["id"], {k: v["id"].split("/")[-1] for k, v in sv.items()})
    test_vars = [
        {"valor": "Pieza entera", "precio": "258.00", "sku": "ZZ-1", "peso_kg": 8.0},
        {"valor": "Corte a máquina", "precio": "298.00", "sku": "ZZ-1", "peso_kg": 8.0},
        {"valor": "Pieza agotada", "precio": "623.00", "sku": "ZZ-2", "peso_kg": 10.0, "rastrear": True},
        {"valor": "Corte agotado", "precio": "663.00", "sku": "ZZ-2", "peso_kg": 10.0, "rastrear": True},
    ]
    test, tv = jb.crear_producto(tok, "ZZ Prueba IVA (no comprar)", "ACTIVE", cat_id, "Formato", test_vars, tags=["prueba-iva"])
    guardar({"servicio": srv["id"], "servicio_vars": {k: v["id"] for k, v in sv.items()},
             "test": test["id"], "test_vars": {k: v["id"] for k, v in tv.items()}})
    print("test:", test["id"], {k: v["id"].split("/")[-1] for k, v in tv.items()})
    maq = sv["Corte a máquina y envasado"]["id"]
    for padre, pieza in (("Corte a máquina", "Pieza entera"), ("Corte agotado", "Pieza agotada")):
        r = jb.enlazar(tok, tv[padre]["id"], [(tv[pieza]["id"], 1), (maq, 1)])
        print("bundle", padre, "->", json.dumps(r, ensure_ascii=False))


def calc(tok):
    st = cargar()
    tv, sv = st["test_vars"], st["servicio_vars"]
    casos = [
        ("pieza 258", [(tv["Pieza entera"], 1)], None),
        ("corte 298", [(tv["Corte a máquina"], 1)], None),
        ("servicio suelto 40", [(sv["Corte a máquina y envasado"], 1)], None),
        ("corte 298 con -10 % (BIENVENIDA10)", [(tv["Corte a máquina"], 1)], {"valueType": "PERCENTAGE", "value": 10.0, "title": "B10"}),
        ("3 cortes con -5 % (CESTA5)", [(tv["Corte a máquina"], 3)], {"valueType": "PERCENTAGE", "value": 5.0, "title": "C5"}),
    ]
    for nombre, lineas, desc in casos:
        try:
            c = jb.calcular_impuestos(tok, lineas, desc)
            print(f"{nombre:38} total={c['totalPriceSet']['shopMoney']['amount']:>8} IVA={c['totalTaxSet']['shopMoney']['amount']:>6}",
                  [(t['ratePercentage'], t['priceSet']['shopMoney']['amount']) for t in c["taxLines"]])
        except SystemExit as e:
            print(nombre, "->", e)


def cleanup(tok, con_servicio):
    st = cargar()
    jb.borrar_producto(tok, st["test"]); print("borrado test")
    if con_servicio:
        jb.borrar_producto(tok, st["servicio"]); print("borrado servicio")


if __name__ == "__main__":
    tok, _ = base.get_token()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"setup": lambda: setup(tok), "calc": lambda: calc(tok),
     "cleanup": lambda: cleanup(tok, "--con-servicio" in sys.argv)}.get(cmd, lambda: sys.exit(__doc__))()
