#!/usr/bin/env python3
"""
Actualiza el metacampo custom.ingredients de productos de Casa Maravillas
desde un CSV (columna "Ingredientes (product.metafields.custom.ingredients)").

Auth: app "HumindIA Analytics" (Dev Dashboard) con client credentials.
Client ID y secret se leen del Keychain de macOS DENTRO de este script; nunca se
imprimen, ni se escriben a disco, ni van por argumentos de línea de comandos.

Nombres de servicio del Keychain (cámbialos con variables de entorno si difieren):
  SHOPIFY_KC_CLIENT_ID      (def. casamaravillas-shopify-client-id)
  SHOPIFY_KC_CLIENT_SECRET  (def. casamaravillas-shopify-client-secret)

Uso:
  python3 tools/shopify_update_ingredients.py CSV                 # dry-run (solo lee)
  python3 tools/shopify_update_ingredients.py CSV --apply         # aplica
  python3 tools/shopify_update_ingredients.py --rollback _backup/ingredients_XXXX.json --apply

Scopes necesarios: read_products (dry-run) y write_products (--apply).
"""
import argparse, csv, getpass, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

SHOP = os.environ.get("SHOPIFY_SHOP", "casamaravillas.myshopify.com")
API = "2025-07"
ING_COL = "Ingredientes (product.metafields.custom.ingredients)"
KC_ID = os.environ.get("SHOPIFY_KC_CLIENT_ID", "casamaravillas-shopify-client-id")
KC_SECRET = os.environ.get("SHOPIFY_KC_CLIENT_SECRET", "casamaravillas-shopify-client-secret")
BACKUP_DIR = Path(__file__).resolve().parent.parent / "_backup"

# Productos a tocar. Si se omite, se actualizan todos los handles cuyo texto difiera.
HANDLES = [
    "jamon-bellota-50-iberico-pieza-entera",
    "lomo-bellota-iberico", "lomo-bellota-iberico-loncheado-2",
    "lomo-cebo-campo-50-iberico", "lomo-cebo-campo-50-iberico-loncheado",
    "salchichon-bellota-iberico", "salchichon-bellota-iberico-loncheado",
    "chorizo-bellota-iberico", "chorizo-bellota-iberico-loncheado",
    "lomito-presa-bellota", "lomo-bellota-iberico-loncheado-1",
]


def keychain(service):
    r = subprocess.run(["security", "find-generic-password", "-a", getpass.getuser(), "-s", service, "-w"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"No encuentro '{service}' en el Keychain (ajusta SHOPIFY_KC_CLIENT_ID / SHOPIFY_KC_CLIENT_SECRET).")
    return r.stdout.strip()


def http(url, body, headers):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        # No volcamos el cuerpo completo: solo el código y el mensaje de error de Shopify.
        sys.exit(f"HTTP {e.code} en {urllib.parse.urlparse(url).path}: {e.read().decode()[:300]}")


def get_token():
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": keychain(KC_ID),
        "client_secret": keychain(KC_SECRET),
    }).encode()
    res = http(f"https://{SHOP}/admin/oauth/access_token", data,
               {"Content-Type": "application/x-www-form-urlencoded"})
    tok = res.get("access_token")
    if not tok:
        sys.exit("La respuesta de auth no trae access_token.")
    scopes = res.get("scope", "")
    return tok, scopes


def gql(token, query, variables=None):
    res = http(f"https://{SHOP}/admin/api/{API}/graphql.json",
               json.dumps({"query": query, "variables": variables or {}}).encode(),
               {"Content-Type": "application/json", "X-Shopify-Access-Token": token})
    if res.get("errors"):
        sys.exit("GraphQL errors: " + json.dumps(res["errors"])[:500])
    return res["data"]


Q_PRODUCT = """
query($h: String!) {
  productByHandle(handle: $h) {
    id title
    metafield(namespace: "custom", key: "ingredients") { value type }
  }
}"""

M_SET = """
mutation($m: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $m) {
    metafields { key value }
    userErrors { field message code }
  }
}"""


def load_csv(path):
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = (r.get(ING_COL) or "").strip()
            if v and r["Handle"] not in out:
                out[r["Handle"]] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--apply", action="store_true", help="escribe en Shopify (sin esto es dry-run)")
    ap.add_argument("--rollback", metavar="JSON", help="restaura desde un backup generado por --apply")
    a = ap.parse_args()

    token, scopes = get_token()
    print(f"Conectado a {SHOP}. Scopes: {scopes or '(no informados)'}")
    if a.apply and "write_products" not in scopes:
        sys.exit("Falta el scope write_products en la app. Añádelo, publica versión y reinstala.")

    # Construye la lista deseada: {handle: nuevo_valor}
    if a.rollback:
        desired = {h: d["antes"] for h, d in json.load(open(a.rollback)).items() if d["antes"] is not None}
    else:
        if not a.csv:
            sys.exit("Falta el CSV.")
        csv_vals = load_csv(a.csv)
        desired = {h: csv_vals[h] for h in HANDLES if h in csv_vals}
        for h in HANDLES:
            if h not in csv_vals:
                print(f"AVISO: {h} no tiene Ingredientes en el CSV")

    plan, backup = [], {}
    for h, new in desired.items():
        p = gql(token, Q_PRODUCT, {"h": h})["productByHandle"]
        if not p:
            print(f"AVISO: {h} no existe en la tienda"); continue
        cur = (p["metafield"] or {}).get("value")
        mtype = (p["metafield"] or {}).get("type", "multi_line_text_field")
        if cur == new:
            print(f"= {h}: sin cambios"); continue
        print(f"\n~ {h}\n    antes:   {cur}\n    después: {new}")
        plan.append({"ownerId": p["id"], "namespace": "custom", "key": "ingredients", "type": mtype, "value": new})
        backup[h] = {"id": p["id"], "antes": cur, "despues": new}

    print(f"\n{len(plan)} producto(s) a cambiar.")
    if not a.apply:
        print("DRY-RUN: no se ha escrito nada. Repite con --apply para aplicar.")
        return
    if not plan:
        return

    BACKUP_DIR.mkdir(exist_ok=True)
    bpath = BACKUP_DIR / f"ingredients_{time.strftime('%Y%m%d-%H%M%S')}.json"
    bpath.write_text(json.dumps(backup, ensure_ascii=False, indent=2))
    print(f"Backup: {bpath}")

    for i in range(0, len(plan), 25):
        res = gql(token, M_SET, {"m": plan[i:i + 25]})["metafieldsSet"]
        if res["userErrors"]:
            sys.exit("userErrors: " + json.dumps(res["userErrors"], ensure_ascii=False))
    print("OK: aplicado. Rollback: python3 tools/shopify_update_ingredients.py --rollback", bpath, "--apply")


if __name__ == "__main__":
    main()
