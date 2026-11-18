#!/usr/bin/env python3
"""
Crea el metacampo de producto custom.gramaje (texto de una línea) y le pone valor a los productos
que tienen un gramaje único conocido. Tarea ClickUp 123m57f5hyx.

Valores:
  loncheado de jamón a máquina  «100 g»      loncheado de jamón a mano  «80 g»
  loncheado de embutido         «100 g»      embutido de pieza          «600–800 g»
  lomito de presa (pieza)       «450–550 g»
  jamón pieza entera, deshuesado, packs y servicios: SIN valor (la variante ya trae el rango o no hay dato único).

Es idempotente: solo escribe donde el valor actual difiere, y deja un backup JSON con los valores previos.
Nada del tema lee este metacampo hasta que se publique la rama del tema, así que escribirlo no cambia la tienda.

Auth: cliente de analytics (clients/casamaravillas/analytics/shopify_admin.py, Keychain; el secreto no se lee aquí).
Scopes: read_products (dry-run) y write_products (--apply).

Uso (Python ≥ 3.10 con -I):
  python3 -I tools/shopify_gramaje_metacampo.py            # dry-run: muestra qué haría
  python3 -I tools/shopify_gramaje_metacampo.py --apply    # crea la definición y escribe los valores
  python3 -I tools/shopify_gramaje_metacampo.py --rollback _backup/gramaje_XXXX.json --apply
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADMIN = HERE.parent.parent.parent / "clients" / "casamaravillas" / "analytics" / "shopify_admin.py"
BACKUP_DIR = HERE.parent / "_backup"
NAMESPACE, KEY = "custom", "gramaje"

LONCHEADO_JAMON_MAQUINA = "100 g"
LONCHEADO_JAMON_MANO = "80 g"
LONCHEADO_EMBUTIDO = "100 g"
EMBUTIDO_PIEZA = "600–800 g"
LOMITO_PRESA_PIEZA = "450–550 g"

# handle -> valor. Lo que no esté aquí queda sin valor (se borra si lo tuviera).
VALORES = {
    "jamon-bellota-100-iberico-loncheado-a-maquina": LONCHEADO_JAMON_MAQUINA,
    "jamon-bellota-50-iberico-loncheado-a-maquina": LONCHEADO_JAMON_MAQUINA,
    "jamon-cebo-de-campo-50-iberico-loncheado-a-maquina": LONCHEADO_JAMON_MAQUINA,
    "jamon-bellota-100-iberico-loncheado-a-mano": LONCHEADO_JAMON_MANO,
    "jamon-bellota-50-iberico-loncheado-a-mano": LONCHEADO_JAMON_MANO,
    "jamon-cebo-de-campo-50-iberico-loncheado-a-mano": LONCHEADO_JAMON_MANO,
    "chorizo-bellota-iberico-loncheado": LONCHEADO_EMBUTIDO,
    "salchichon-bellota-iberico-loncheado": LONCHEADO_EMBUTIDO,
    "lomo-cebo-campo-50-iberico-loncheado": LONCHEADO_EMBUTIDO,
    "lomo-bellota-iberico-loncheado-1": LONCHEADO_EMBUTIDO,  # «Lomito de Presa de Bellota - Loncheado»
    "lomo-bellota-iberico-loncheado-2": LONCHEADO_EMBUTIDO,
    "chorizo-bellota-iberico": EMBUTIDO_PIEZA,
    "salchichon-bellota-iberico": EMBUTIDO_PIEZA,
    "lomo-cebo-campo-50-iberico": EMBUTIDO_PIEZA,
    "lomo-bellota-iberico": EMBUTIDO_PIEZA,
    "lomito-presa-bellota": LOMITO_PRESA_PIEZA,
}

Q_PRODUCTS = """query($a:String){products(first:100,after:$a){pageInfo{hasNextPage endCursor}
  nodes{id handle title status g: metafield(namespace:"custom",key:"gramaje"){value}}}}"""
Q_DEF = """{metafieldDefinitions(ownerType:PRODUCT,first:1,namespace:"custom",key:"gramaje"){nodes{id name type{name}}}}"""
M_DEF = """mutation($d:MetafieldDefinitionInput!){metafieldDefinitionCreate(definition:$d){
  createdDefinition{id} userErrors{field message code}}}"""
M_SET = """mutation($m:[MetafieldsSetInput!]!){metafieldsSet(metafields:$m){userErrors{field message code}}}"""
M_DEL = """mutation($m:[MetafieldIdentifierInput!]!){metafieldsDelete(metafields:$m){userErrors{field message}}}"""


def load_admin():
    spec = importlib.util.spec_from_file_location("shopify_admin", ADMIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def all_products(sa, tok):
    out, after = [], None
    while True:
        p = sa.graphql(Q_PRODUCTS, {"a": after}, token=tok)["data"]["products"]
        out += p["nodes"]
        if not p["pageInfo"]["hasNextPage"]:
            return out
        after = p["pageInfo"]["endCursor"]


def user_errors(res, root):
    errs = res["data"][root]["userErrors"]
    if errs:
        sys.exit(f"{root}: {json.dumps(errs, ensure_ascii=False)}")


def chunks(seq, n=25):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def aplicar(sa, tok, cambios, borrados):
    for lote in chunks(cambios):
        user_errors(sa.graphql(M_SET, {"m": lote}, token=tok), "metafieldsSet")
    for lote in chunks(borrados):
        user_errors(sa.graphql(M_DEL, {"m": lote}, token=tok), "metafieldsDelete")


def rollback(sa, tok, path, apply):
    prev = json.loads(Path(path).read_text())
    por_handle = {p["handle"]: p["id"] for p in all_products(sa, tok)}
    sets, dels = [], []
    for handle, valor in prev.items():
        pid = por_handle.get(handle)
        if not pid:
            continue
        if valor is None:
            dels.append({"ownerId": pid, "namespace": NAMESPACE, "key": KEY})
        else:
            sets.append({"ownerId": pid, "namespace": NAMESPACE, "key": KEY, "type": "single_line_text_field", "value": valor})
    print(f"Rollback: {len(sets)} valores a restaurar, {len(dels)} a borrar ({'APLICADO' if apply else 'dry-run'})")
    if apply:
        aplicar(sa, tok, sets, dels)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--rollback", metavar="BACKUP_JSON")
    args = ap.parse_args()

    sa = load_admin()
    tok = sa.get_access_token()
    if args.rollback:
        return rollback(sa, tok, args.rollback, args.apply)

    existe = sa.graphql(Q_DEF, token=tok)["data"]["metafieldDefinitions"]["nodes"]
    print("Definición custom.gramaje:", "ya existe" if existe else "NO existe → se creará")
    if existe and existe[0]["type"]["name"] != "single_line_text_field":
        sys.exit(f"La definición existente es de tipo {existe[0]['type']['name']}, no single_line_text_field.")

    productos = all_products(sa, tok)
    handles = {p["handle"] for p in productos}
    faltan = sorted(set(VALORES) - handles)
    if faltan:
        sys.exit(f"Handles esperados que no existen en la tienda: {faltan}")

    cambios, borrados, backup = [], [], {}
    for p in productos:
        actual = (p["g"] or {}).get("value")
        deseado = VALORES.get(p["handle"])
        if actual == deseado:
            continue
        backup[p["handle"]] = actual
        ident = {"ownerId": p["id"], "namespace": NAMESPACE, "key": KEY}
        if deseado is None:
            borrados.append(ident)
        else:
            cambios.append({**ident, "type": "single_line_text_field", "value": deseado})
        print(f"  {p['handle']:55} {actual!r} → {deseado!r}")
    print(f"{len(cambios)} por escribir, {len(borrados)} por borrar, {len(productos) - len(backup)} sin cambios.")

    if not args.apply:
        print("Dry-run: no se ha escrito nada. Añade --apply.")
        return
    if not existe:
        d = {"name": "Gramaje", "namespace": NAMESPACE, "key": KEY, "type": "single_line_text_field", "ownerType": "PRODUCT",
             "description": "Contenido real del producto (p. ej. «100 g»). Se muestra en las tarjetas y en el cajón del carrito. Vacío si el peso varía por variante."}
        user_errors(sa.graphql(M_DEF, {"d": d}, token=tok), "metafieldDefinitionCreate")
        print("Definición creada.")
    BACKUP_DIR.mkdir(exist_ok=True)
    ruta = BACKUP_DIR / f"gramaje_{time.strftime('%Y%m%d-%H%M%S')}.json"
    ruta.write_text(json.dumps(backup, ensure_ascii=False, indent=1))
    aplicar(sa, tok, cambios, borrados)
    print(f"Hecho. Backup en {ruta}")


if __name__ == "__main__":
    main()
