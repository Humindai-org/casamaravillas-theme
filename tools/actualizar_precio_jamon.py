#!/usr/bin/env python3
"""
Cambia el precio de la PIEZA o del SERVICIO de un jamón y recalcula todas las variantes padre afectadas
(invariante: precio del padre = precio de la pieza + precio del servicio). Dry-run por defecto.

NOTA IMPORTANTE: Los precios de los jamones se cambian con tools/actualizar_precio_jamon.py (usa la app
HumindAI Analytics), no desde el editor masivo ni CSV.

  python3 -I tools/actualizar_precio_jamon.py --comprobar                        # solo lee: invariante, componentes, IVA
  python3 -I tools/actualizar_precio_jamon.py --pieza 450 --precio 262           # dry-run
  python3 -I tools/actualizar_precio_jamon.py --servicio maquina --precio 45     # dry-run (afecta a 9 padres)
  python3 -I tools/actualizar_precio_jamon.py --pieza 450 --precio 262 --apply   # aplica (backup en _backup/)
  python3 -I tools/actualizar_precio_jamon.py --rollback _backup/precio_jamon_XXXX.json --apply
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jamon_bundles as jb

base = jb.base
JAMONES = ["jamon-cebo-de-campo-50-iberico-pieza-entera", "jamon-bellota-50-iberico-pieza-entera",
           "jamon-bellota-100-iberico-pieza-entera"]
SERVICIO_TITULO = "Servicio de preparación del jamón"
SERVICIOS = {"deshuesado": "Deshuesado", "maquina": "Corte a máquina y envasado", "mano": "Corte a mano y envasado"}
PIEZA = "Pieza entera"

Q_JAMON = """query($h:String!){ productByHandle(handle:$h){ id handle category{ id }
  variants(first:50){ nodes{ id title sku price selectedOptions{ name value }
    productVariantComponents(first:5){ nodes{ quantity productVariant{ id sku product{ handle } } } } } } } }"""
SERVICIO_HANDLE = "servicio-de-preparacion-del-jamon"  # por handle: la búsqueda por título no indexa borradores
Q_SERVICIO = """query($h:String!){ productByHandle(handle:$h){ id handle title status category{ id }
  variants(first:10){ nodes{ id title sku price } } } }"""
M_UPD = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){
  userErrors{ field message } } }"""


def cargar(tok):
    srv = base.gql(tok, Q_SERVICIO, {"h": SERVICIO_HANDLE})["productByHandle"]
    if not srv:
        sys.exit(f"No existe el producto «{SERVICIO_TITULO}» ({SERVICIO_HANDLE}).")
    jamones = []
    for h in JAMONES:
        p = base.gql(tok, Q_JAMON, {"h": h})["productByHandle"]
        if not p:
            sys.exit(f"No existe {h}")
        vs = []
        for v in p["variants"]["nodes"]:
            o = {x["name"]: x["value"] for x in v["selectedOptions"]}
            vs.append(dict(v, peso=o["Peso"], formato=o["Formato"], precio=round(float(v["price"]) * 100)))
        jamones.append({"handle": h, "id": p["id"], "category": p["category"], "variantes": vs})
    return srv, jamones


def precios_servicio(srv):
    return {v["title"]: round(float(v["price"]) * 100) for v in srv["variants"]["nodes"]}


def esperado(jamon, serv_precios, piezas, formato, peso):
    return piezas[(jamon["handle"], peso)] + serv_precios[SERVICIOS_INV[formato]]


SERVICIOS_INV = {v: v for v in SERVICIOS.values() if v != PIEZA}  # formato -> título de variante del servicio (coinciden)


def comprobar(tok, srv, jamones, piezas, serv):
    fallos = []
    if srv.get("category"):
        fallos.append("El servicio TIENE categoría: perdería el 21 % (debe quedar sin categoría).")
    for j in jamones:
        for v in j["variantes"]:
            if v["formato"] == PIEZA:
                continue
            exp = esperado(j, serv, piezas, v["formato"], v["peso"])
            if v["precio"] != exp:
                fallos.append(f"{j['handle']} {v['title']}: precio {v['precio']/100:.2f} ≠ pieza+servicio {exp/100:.2f}")
            comp = {(c["productVariant"]["product"]["handle"], c["productVariant"]["sku"]): c["quantity"]
                    for c in v["productVariantComponents"]["nodes"]}
            if len(comp) != 2 or j["handle"] not in {k[0] for k in comp}:
                fallos.append(f"{j['handle']} {v['title']}: componentes inesperados {sorted(comp)}")
    # IVA real: pieza al 10 %, servicio al 21 % (draftOrderCalculate, no crea pedidos)
    muestras = [("pieza", next(v for v in jamones[0]["variantes"] if v["formato"] == PIEZA)["id"], 10.0)]
    muestras += [(n, next(x for x in srv["variants"]["nodes"] if x["title"] == n)["id"], 21.0) for n in SERVICIOS.values()]
    for nombre, vid, tasa in muestras:
        tl = jb.calcular_impuestos(tok, [(vid, 1)])["taxLines"]
        got = sorted({t["ratePercentage"] for t in tl})
        print(f"  IVA {nombre:30} {got}")
        if got != [tasa]:
            fallos.append(f"IVA de {nombre}: {got}, se esperaba {tasa}")
    return fallos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comprobar", action="store_true")
    ap.add_argument("--pieza", help="SKU de la pieza entera (450-458)")
    ap.add_argument("--servicio", choices=SERVICIOS)
    ap.add_argument("--precio", help="precio nuevo en euros, IVA incluido")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback")
    a = ap.parse_args()
    tok, _ = base.get_token()

    if a.rollback:
        bk = json.load(open(a.rollback))
        print("Rollback de precios:")
        for pid, vs in bk["por_producto"].items():
            for v in vs:
                print(f"  {v['id'].split('/')[-1]} -> {v['price']}")
        if not a.apply:
            print("(dry-run) añade --apply"); return
        for pid, vs in bk["por_producto"].items():
            jb.ok(base.gql(tok, M_UPD, {"p": pid, "v": vs}), "productVariantsBulkUpdate")
        print("Restaurado. Ejecuta --comprobar."); return

    srv, jamones = cargar(tok)
    serv = precios_servicio(srv)
    piezas = {(j["handle"], v["peso"]): v["precio"] for j in jamones for v in j["variantes"] if v["formato"] == PIEZA}

    if a.comprobar:
        fallos = comprobar(tok, srv, jamones, piezas, serv)
        print("\nCOMPROBACIÓN:", "OK" if not fallos else "FALLOS")
        for f in fallos:
            print("  -", f)
        sys.exit(1 if fallos else 0)

    if a.precio is None or not (a.pieza or a.servicio) or (a.pieza and a.servicio):
        sys.exit("Indica --pieza SKU o --servicio X, con --precio.")
    nuevo = round(float(a.precio.replace(",", ".")) * 100)
    cambios = {}  # product_id -> [{id, price, antes}]
    if a.pieza:
        objetivo = [(j, v) for j in jamones for v in j["variantes"] if v["formato"] == PIEZA and v["sku"] == a.pieza]
        if len(objetivo) != 1:
            sys.exit(f"SKU {a.pieza}: {len(objetivo)} piezas (se esperaba 1).")
        j0, v0 = objetivo[0]
        piezas[(j0["handle"], v0["peso"])] = nuevo
        cambios.setdefault(j0["id"], []).append({"id": v0["id"], "price": nuevo, "antes": v0["precio"]})
        padres = [(j0, v) for v in j0["variantes"] if v["peso"] == v0["peso"] and v["formato"] != PIEZA]
    else:
        titulo = SERVICIOS[a.servicio]
        sv = next(x for x in srv["variants"]["nodes"] if x["title"] == titulo)
        serv[titulo] = nuevo
        cambios.setdefault(srv["id"], []).append({"id": sv["id"], "price": nuevo, "antes": round(float(sv["price"]) * 100)})
        padres = [(j, v) for j in jamones for v in j["variantes"] if v["formato"] == titulo]
    for j, v in padres:
        exp = esperado(j, serv, piezas, v["formato"], v["peso"])
        if exp != v["precio"]:
            cambios.setdefault(j["id"], []).append({"id": v["id"], "price": exp, "antes": v["precio"]})

    print(f"{'DRY-RUN' if not a.apply else 'APLICAR'}: {sum(len(x) for x in cambios.values())} variantes cambian")
    for pid, vs in cambios.items():
        for v in vs:
            print(f"  {v['id'].split('/')[-1]}: {v['antes']/100:.2f} -> {v['price']/100:.2f}")
    if not a.apply:
        print("(dry-run) añade --apply"); return
    os.makedirs("_backup", exist_ok=True)
    bpath = f"_backup/precio_jamon_{time.strftime('%Y%m%d-%H%M%S')}.json"
    json.dump({"por_producto": {pid: [{"id": v["id"], "price": f"{v['antes']/100:.2f}"} for v in vs]
                                for pid, vs in cambios.items()}}, open(bpath, "w"), indent=1)
    for pid, vs in cambios.items():
        jb.ok(base.gql(tok, M_UPD, {"p": pid, "v": [{"id": v["id"], "price": f"{v['price']/100:.2f}"} for v in vs]}),
              "productVariantsBulkUpdate")
    print(f"Aplicado. Backup: {bpath}. Ejecuta --comprobar.")


if __name__ == "__main__":
    main()
