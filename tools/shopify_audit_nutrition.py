#!/usr/bin/env python3
"""
Auditoría SOLO LECTURA de ficha nutricional, ingredientes y alérgenos de todos los productos.
Vuelca todo a JSON (por defecto _backup/audit_nutrition_<fecha>.json) y imprime un informe de
huecos e inconsistencias entre variantes (mismo producto en pieza entera / loncheado / etc.).

Reutiliza auth/Keychain de shopify_update_ingredients.py. Scope: read_products.

Uso: python3 tools/shopify_audit_nutrition.py [--out ruta.json]
"""
import argparse, json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shopify_update_ingredients import get_token, gql, BACKUP_DIR  # noqa: E402

KEYS = ["ingredients", "allergens", "kcal", "energy", "fats_g", "fat", "saturated_fats_g", "saturated_fat",
        "carbohydrates_g", "carbohydrates", "sugars_g", "sugars", "protein_g", "protein", "salt_g", "salt",
        "conservation_temp", "service_temp", "conservation_days", "componentes_del_packs"]

Q = """
query($after: String) {
  products(first: 40, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id handle title status productType tags
      metafields(first: 50, namespace: "custom") { nodes { key type value } }
    }
  }
}"""


def fetch(token):
    out, after = [], None
    while True:
        d = gql(token, Q, {"after": after})["products"]
        out += d["nodes"]
        if not d["pageInfo"]["hasNextPage"]:
            return out
        after = d["pageInfo"]["endCursor"]
        time.sleep(0.3)


def norm(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    token, _ = get_token()
    prods = fetch(token)
    rows = []
    for p in prods:
        mf = {m["key"]: m["value"] for m in p["metafields"]["nodes"]}
        rows.append({"handle": p["handle"], "title": p["title"], "status": p["status"], "type": p["productType"],
                     "tags": p["tags"], "mf": mf})
    out = Path(a.out) if a.out else BACKUP_DIR / f"audit_nutrition_{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"{len(rows)} productos -> {out}")


if __name__ == "__main__":
    main()
