#!/usr/bin/env python3
"""
⛔ NO EJECUTAR (aviso del 28/10/2026, regla de descuentos de Casa Maravillas):
   el cliente recibe SIEMPRE el mayor descuento (tope 10 %), los de porcentaje no se acumulan y solo se combina el
   envío gratis desde 99 € (medido tras descuentos). Este script la rompería:
   - `crear` / `activar` publican un descuento de app con loncheados al 10 % contando TODA la cesta: choca con el
     -5 % por línea del embutido y con la ficha, y conviviría con los 11 descuentos automáticos antiguos de loncheados
     (el script no los desactiva). El código de la Function `cesta-descuentos` no está en este repo: no se puede auditar.
   - Hoy NO existe ningún descuento de app en la tienda. Antes de activar nada, hablarlo con Jorge y con Luis Juan.

Descuento automático de la app "Casa Maravillas Cesta" (Shopify Function `cesta-descuentos`):
cesta 5% desde 3 productos (solo líneas de la cesta) + loncheados por cantidad (10%, cuenta toda la cesta y
lo de fuera). En cada línea se aplica el mayor; no se combina con otros descuentos (salvo el envío gratis).

Usa las credenciales de ESA app (no las de HumindIA Analytics), guardadas en el Keychain de macOS:
  security add-generic-password -a "$USER" -s casamaravillas-cesta-client-id -w
  security add-generic-password -a "$USER" -s casamaravillas-cesta-client-secret -w
(Client ID y secreto: Dev Dashboard > Casa Maravillas Cesta > Ajustes.)

Uso:
  python3 tools/shopify_descuento_app.py estado             # lee: función, descuento y descuentos antiguos
  python3 tools/shopify_descuento_app.py crear              # crea el descuento con inicio en +2 días (inactivo)
  python3 tools/shopify_descuento_app.py activar            # el descuento empieza ya
  python3 tools/shopify_descuento_app.py desactivar         # lo pone en el futuro (deja de aplicarse)
"""
import datetime, importlib.util, os, sys

os.environ.setdefault("SHOPIFY_KC_CLIENT_ID", "casamaravillas-cesta-client-id")
os.environ.setdefault("SHOPIFY_KC_CLIENT_SECRET", "casamaravillas-cesta-client-secret")
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

TITLE = "Casa Maravillas: cesta 5% y loncheados por cantidad"
HANDLE = "cesta-descuentos"

Q_STATE = """{ shopifyFunctions(first:10){ nodes{ id title handle apiType } }
  discountNodes(first:100){ nodes{ id discount{ __typename
    ... on DiscountAutomaticApp{ title status startsAt combinesWith{productDiscounts orderDiscounts shippingDiscounts} }
    ... on DiscountAutomaticBasic{ title status }
    ... on DiscountCodeBasic{ title status } } } } }"""
M_CREATE = """mutation($d:DiscountAutomaticAppInput!){ discountAutomaticAppCreate(automaticAppDiscount:$d){
  automaticAppDiscount{ discountId title status startsAt } userErrors{ field message code } } }"""
M_UPDATE = """mutation($id:ID!,$d:DiscountAutomaticAppInput!){ discountAutomaticAppUpdate(id:$id, automaticAppDiscount:$d){
  automaticAppDiscount{ discountId status startsAt } userErrors{ field message code } } }"""


def iso(days=0):
    return (datetime.datetime.utcnow() + datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def find(token):
    for n in base.gql(token, Q_STATE)["discountNodes"]["nodes"]:
        d = n["discount"]
        if d.get("title") == TITLE:
            return n["id"], d
    return None, None


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "estado"
    token, scopes = base.get_token()
    print("Scopes de la app:", scopes)
    st = base.gql(token, Q_STATE)
    print("Funciones:", [(f["handle"], f["apiType"]) for f in st["shopifyFunctions"]["nodes"]])
    did, d = find(token)
    print("Descuento:", (did, d["status"], d["startsAt"]) if did else "no existe")

    if cmd == "estado":
        print("\nDescuentos antiguos de loncheados (los sustituye la función):")
        for n in st["discountNodes"]["nodes"]:
            x = n["discount"]
            if x.get("__typename") == "DiscountAutomaticBasic" and "uds" in (x.get("title") or ""):
                print("  ", x["status"], x["title"])
        return
    if cmd == "crear":
        if did:
            sys.exit("Ya existe.")
        r = base.gql(token, M_CREATE, {"d": {"title": TITLE, "functionHandle": HANDLE, "discountClasses": ["PRODUCT"],
              "startsAt": iso(2), "combinesWith": {"productDiscounts": False, "orderDiscounts": False, "shippingDiscounts": True}}})
        print(r)
        if r["discountAutomaticAppCreate"]["userErrors"]:
            sys.exit("ERROR: " + str(r["discountAutomaticAppCreate"]["userErrors"]))
        print("Creado, con inicio en +2 días (inactivo).")
    elif cmd in ("activar", "desactivar"):
        if not did:
            sys.exit("No existe: ejecuta crear.")
        r = base.gql(token, M_UPDATE, {"id": did, "d": {"startsAt": iso(0) if cmd == "activar" else iso(2)}})
        print(r)
        if r["discountAutomaticAppUpdate"]["userErrors"]:
            sys.exit("ERROR: " + str(r["discountAutomaticAppUpdate"]["userErrors"]))
        print("Activo desde ahora." if cmd == "activar" else "Desactivado (inicio en +2 días).")
    else:
        sys.exit("Comando desconocido")


if __name__ == "__main__":
    main()
