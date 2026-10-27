#!/usr/bin/env python3
"""
Asigna una plantilla de tema (templateSuffix) a una colección.

Reutiliza la auth (Keychain, client credentials) de shopify_update_ingredients.py.
Tienda: variable SHOPIFY_SHOP (p. ej. jbtugu-s0.myshopify.com).

Uso:
  SHOPIFY_SHOP=... python3 tools/shopify_set_collection_template.py loncheados loncheados           # dry-run
  SHOPIFY_SHOP=... python3 tools/shopify_set_collection_template.py loncheados loncheados --apply   # aplica
  (argumentos: handle de la colección, sufijo de plantilla; '' para volver a la plantilla por defecto)
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

Q = """query($h:String!){ collectionByHandle(handle:$h){ id title handle templateSuffix } }"""
M = """mutation($i:CollectionInput!){ collectionUpdate(input:$i){ collection{ handle templateSuffix } userErrors{ field message } } }"""

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    handle, suffix = args
    token, _ = base.get_token()
    col = base.gql(token, Q, {"h": handle})["collectionByHandle"]
    if not col:
        sys.exit(f"No existe la colección '{handle}'.")
    print(f"{col['title']} ({col['handle']}): plantilla actual = {col['templateSuffix']!r} -> {suffix!r}")
    if "--apply" not in sys.argv:
        print("Dry-run: no se ha cambiado nada (usa --apply).")
        return
    res = base.gql(token, M, {"i": {"id": col["id"], "templateSuffix": suffix or None}})["collectionUpdate"]
    if res["userErrors"]:
        sys.exit(f"Errores: {res['userErrors']}")
    print("Hecho:", res["collection"])

main()
