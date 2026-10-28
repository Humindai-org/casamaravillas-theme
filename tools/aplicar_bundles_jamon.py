#!/usr/bin/env python3
"""
Convierte las 9 variantes de corte/deshuesado de UN jamón de pieza entera en variantes padre (bundles de variante):
componentes = la «Pieza entera» del mismo peso (IVA 10 %) + la variante del producto «Servicio de preparación del
jamón» (IVA 21 %). El precio del padre no cambia (debe ser ya pieza + servicio: si no, aborta). Dry-run por defecto.

NOTA IMPORTANTE: Los precios de los jamones se cambian con tools/actualizar_precio_jamon.py (usa la app
HumindAI Analytics), no desde el editor masivo ni CSV.

  python3 -I tools/aplicar_bundles_jamon.py --producto cebo                      # dry-run
  python3 -I tools/aplicar_bundles_jamon.py --producto cebo --apply              # convierte (backup en _backup/)
  python3 -I tools/aplicar_bundles_jamon.py --rollback _backup/bundles_jamon_XXXX.json --apply
Productos: cebo | bellota50 | bellota100. Si tras convertir algo no cuadra (precio, disponibilidad, componentes),
revierte solo ese producto y sale con error.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jamon_bundles as jb

base = jb.base
HANDLES = {"cebo": "jamon-cebo-de-campo-50-iberico-pieza-entera", "bellota50": "jamon-bellota-50-iberico-pieza-entera",
           "bellota100": "jamon-bellota-100-iberico-pieza-entera"}
SERVICIO_HANDLE = "servicio-de-preparacion-del-jamon"  # por handle: la búsqueda por título no indexa borradores
PIEZA = "Pieza entera"

Q_PRODUCTO = """query($h:String!){ productByHandle(handle:$h){ id title category{ id }
  variants(first:50){ nodes{ id title sku price availableForSale requiresComponents
    inventoryItem{ tracked measurement{ weight{ value } } }
    selectedOptions{ name value }
    productVariantComponents(first:5){ nodes{ quantity productVariant{ id } } } } } } }"""
Q_VARIANTE = """query($id:ID!){ productVariant(id:$id){ id title price availableForSale requiresComponents
  inventoryItem{ measurement{ weight{ value } } }
  productVariantComponents(first:5){ nodes{ quantity productVariant{ id } } } } }"""


def estado(tok, vid):
    v = base.gql(tok, Q_VARIANTE, {"id": vid})["productVariant"]
    return {"id": vid, "title": v["title"], "price": v["price"], "available": v["availableForSale"],
            "requiresComponents": v["requiresComponents"], "weight": v["inventoryItem"]["measurement"]["weight"]["value"],
            "components": sorted(c["productVariant"]["id"] for c in v["productVariantComponents"]["nodes"])}


def plan(tok, clave):
    srv = base.gql(tok, Q_PRODUCTO, {"h": SERVICIO_HANDLE})["productByHandle"]
    jam = base.gql(tok, Q_PRODUCTO, {"h": HANDLES[clave]})["productByHandle"]
    if not srv or not jam:
        sys.exit("No existe el producto del jamón o el del servicio.")
    if srv["category"]:
        sys.exit("El servicio TIENE categoría: perdería el 21 %. Aborto.")
    servicio = {v["title"]: v for v in srv["variants"]["nodes"]}
    piezas, padres = {}, []
    for v in jam["variants"]["nodes"]:
        o = {x["name"]: x["value"] for x in v["selectedOptions"]}
        (piezas.__setitem__(o["Peso"], v) if o["Formato"] == PIEZA else padres.append((o["Peso"], o["Formato"], v)))
    filas, errores = [], []
    for peso, formato, v in padres:
        pz, sv = piezas.get(peso), servicio.get(formato)
        if not pz or not sv:
            errores.append(f"{v['title']}: sin pieza o servicio correspondiente"); continue
        esperado = round(float(pz["price"]) * 100) + round(float(sv["price"]) * 100)
        if round(float(v["price"]) * 100) != esperado:
            errores.append(f"{v['title']}: precio {v['price']} ≠ pieza+servicio {esperado/100:.2f}")
        ya = sorted(c["productVariant"]["id"] for c in v["productVariantComponents"]["nodes"])
        comp = sorted([pz["id"], sv["id"]])
        if ya and ya != comp:
            errores.append(f"{v['title']}: ya tiene componentes distintos de los previstos")
        filas.append({"padre": v, "pieza": pz, "servicio": sv, "ya": bool(ya)})
    if len(filas) != 9:
        errores.append(f"se esperaban 9 padres y hay {len(filas)}")
    return jam, filas, errores


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--producto", choices=HANDLES)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback")
    a = ap.parse_args()
    tok, _ = base.get_token()

    if a.rollback:
        bk = json.load(open(a.rollback))
        print(f"Rollback de {bk['producto']}: {len(bk['padres'])} padres")
        if not a.apply:
            print("(dry-run) añade --apply"); return
        for p in bk["padres"]:
            jb.desenlazar(tok, p["id"])
            ahora = estado(tok, p["id"])
            malo = ahora["price"] != p["price"] or ahora["available"] != p["available"] or ahora["requiresComponents"]
            print(f"  {p['title']}: {ahora['price']} avail={ahora['available']} comps={len(ahora['components'])}"
                  + ("  <-- NO COINCIDE" if malo else ""))
        print("Restaurado. Ejecuta --comprobar de actualizar_precio_jamon.py o verifica la ficha."); return

    if not a.producto:
        sys.exit("Indica --producto cebo|bellota50|bellota100 (o --rollback).")
    jam, filas, errores = plan(tok, a.producto)
    print(f"{jam['title']}: {len(filas)} padres")
    for f in filas:
        v = f["padre"]
        print(f"  {v['sku']:>4} {v['title'][:44]:44} {v['price']:>7} = pieza {f['pieza']['price']:>7} + servicio {f['servicio']['price']:>5}"
              f"  avail={v['availableForSale']}{'  (ya es bundle)' if f['ya'] else ''}")
    if errores:
        print("\nABORTO, no cuadra:"); [print("  -", e) for e in errores]; sys.exit(1)
    if not a.apply:
        print("\n(dry-run) añade --apply"); return

    os.makedirs("_backup", exist_ok=True)
    bpath = f"_backup/bundles_jamon_{a.producto}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    antes = {f["padre"]["id"]: estado(tok, f["padre"]["id"]) for f in filas}
    json.dump({"producto": a.producto, "padres": list(antes.values())}, open(bpath, "w"), indent=1)
    print(f"\nBackup: {bpath}")
    hechos = []
    for f in filas:
        pid = f["padre"]["id"]
        if f["ya"]:
            continue
        jb.enlazar(tok, pid, [(f["pieza"]["id"], 1), (f["servicio"]["id"], 1)])
        hechos.append(pid)
        d = estado(tok, pid)
        disp_esperada = f["pieza"]["availableForSale"]
        malo = []
        if d["price"] != antes[pid]["price"]: malo.append(f"precio {antes[pid]['price']} -> {d['price']}")
        if not d["requiresComponents"] or d["components"] != sorted([f["pieza"]["id"], f["servicio"]["id"]]):
            malo.append("componentes")
        if d["available"] != disp_esperada: malo.append(f"disponibilidad {d['available']} (pieza {disp_esperada})")
        if d["weight"] != antes[pid]["weight"]: malo.append(f"peso {antes[pid]['weight']} -> {d['weight']}")
        print(f"  {d['title'][:44]:44} {d['price']:>7} avail={d['available']} peso={d['weight']}" + (f"  <-- {malo}" if malo else ""))
        if malo:
            print("\nALGO NO CUADRA: revierto este producto.")
            for p in hechos:
                jb.desenlazar(tok, p)
            sys.exit(2)
    print("Convertido. Verifica ficha, carrito, checkout y --comprobar.")


if __name__ == "__main__":
    main()
