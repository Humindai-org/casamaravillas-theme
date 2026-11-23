#!/usr/bin/env python3
"""
Escribe en custom.* la tabla nutricional PROVISIONAL (por 100 g) = media de fichas de competidores
(Enrique Tomás, Joselito, Revisan/Morcillo, Montechico, 5J), consultadas 2026-11-09, hasta tener la
ficha del fabricante. Mismo valor para todas las variantes de un producto (entero, loncheado, etc.).
Detalle de fuentes y cuentas: workflows/update_ingredients_shopify.md (sección Nutrición provisional).

Uso: python3 tools/shopify_set_nutrition_avg.py            # dry-run
     python3 tools/shopify_set_nutrition_avg.py --apply    # aplica + backup en _backup/
     python3 tools/shopify_set_nutrition_avg.py --rollback _backup/nutrition_avg_X.json --apply
Solo toca nutrición de handles listados; NO packs, NO ingredientes/alérgenos.
"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from shopify_update_ingredients import get_token, gql, BACKUP_DIR, M_SET  # noqa: E402

# energy, fat, saturated_fat, carbohydrates, sugars, protein, salt
T = {
    # Media de competidores (jamón y lomo bellota 100 %)
    # Jamones: datos del cliente (LuisJuan/Jamones_Descripciones, 2026-11-10)
    "jamon_bellota":    ("1716 kJ / 410 kcal", "32", "13", "1.3", "1", "30", "6.5"),
    "lomo_bellota":     ("1280 kJ / 306 kcal", "16.2", "5.4", "1.4", "0.8", "38.8", "3.3"),
    # Valores aportados por el cliente/equipo (2026-11-09), "valores medios por 100 g"
    "jamon_bellota_50": ("1716 kJ / 410 kcal", "32", "13", "1.3", "1", "30", "6.5"),
    "jamon_cebo":       ("1448 kJ / 348 kcal", "24", "9", "0", "0", "31", "4"),
    "lomo_cebo":        ("1469 kJ / 353 kcal", "24.0", "9.4", "0.5", "0.5", "35.0", "3.9"),
    "presa":            ("1324 kJ / 317 kcal", "18.52", "6.55", "0.19", "0.10", "37.40", "4.40"),
    "chorizo":          ("1909 kJ / 460 kcal", "36.6", "12.59", "2.0", "0.46", "31.3", "5.62"),
    "salchichon":       ("1790 kJ / 432 kcal", "35.8", "12.1", "0.69", "0.69", "26.7", "7.5"),
}
KEYS = ["energy", "fat", "saturated_fat", "carbohydrates", "sugars", "protein", "salt"]
G = {
    "jamon_bellota": ["jamon-bellota-100-iberico-pieza-entera", "jamon-bellota-100-iberico-deshuesado",
                      "jamon-bellota-100-iberico-loncheado-a-mano", "jamon-bellota-100-iberico-loncheado-a-maquina"],
    "jamon_bellota_50": ["jamon-bellota-50-iberico-pieza-entera", "jamon-bellota-50-iberico-deshuesado",
                         "jamon-bellota-50-iberico-loncheado-a-mano", "jamon-bellota-50-iberico-loncheado-a-maquina"],
    "jamon_cebo": ["jamon-cebo-50-iberico-pieza-entera", "jamon-cebo-50-iberico-deshuesado",
                   "jamon-cebo-50-iberico-cortado-a-mano", "jamon-cebo-de-campo-50-iberico-pieza-entera",
                   "jamon-cebo-de-campo-50-iberico-deshuesado", "jamon-cebo-de-campo-50-iberico-loncheado-a-mano",
                   "jamon-cebo-de-campo-50-iberico-loncheado-a-maquina"],
    "chorizo": ["chorizo-bellota-iberico", "chorizo-bellota-iberico-loncheado"],
    "salchichon": ["salchichon-bellota-iberico", "salchichon-bellota-iberico-loncheado"],
    "lomo_bellota": ["lomo-bellota-iberico", "lomo-bellota-iberico-loncheado-2"],
    "lomo_cebo": ["lomo-cebo-campo-50-iberico", "lomo-cebo-campo-50-iberico-loncheado"],
    "presa": ["lomito-presa-bellota", "lomo-bellota-iberico-loncheado-1"],
}
DESIRED = {h: dict(zip(KEYS, T[g])) for g, hs in G.items() for h in hs}

Q = """query($a:String){products(first:40,after:$a){pageInfo{hasNextPage endCursor}
 nodes{id handle metafields(first:50,namespace:"custom"){nodes{key type value}}}}}"""


def main():
    apply = "--apply" in sys.argv
    token, scopes = get_token()
    if apply and "write_products" not in scopes:
        sys.exit("Falta write_products")
    prods, after = {}, None
    while True:
        d = gql(token, Q, {"a": after})["products"]
        for p in d["nodes"]:
            prods[p["handle"]] = {"id": p["id"], "mf": {m["key"]: m for m in p["metafields"]["nodes"]}}
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]
    # tipo de metafield: el de energy/fat ya existente (carbohydrates puede no existir en embutidos)
    ref = prods["jamon-bellota-100-iberico-pieza-entera"]["mf"]
    typ = {k: ref[k]["type"] for k in KEYS if k in ref}
    missing = [k for k in KEYS if k not in typ]
    if missing:
        sys.exit(f"No conozco el tipo de {missing}")

    if "--rollback" in sys.argv:
        bk = json.load(open(sys.argv[sys.argv.index("--rollback") + 1]))
        plan = [(h, k, v) for h, ks in bk.items() for k, v in ks.items()]
        for h, k, v in plan:
            if v is None:
                print(f"AVISO rollback: {h}.{k} no existía antes (no se borra)")
        plan = [(h, k, v) for h, k, v in plan if v is not None]
    else:
        plan = [(h, k, v) for h, ks in DESIRED.items() for k, v in ks.items()]

    backup, writes = {}, []
    for h, k, new in plan:
        if h not in prods:
            print(f"AVISO: {h} no existe"); continue
        cur = prods[h]["mf"].get(k)
        old = cur["value"] if cur else None
        if old == new:
            continue
        print(f"{h:55} {k:14} {old!r} -> {new!r}")
        backup.setdefault(h, {})[k] = old
        writes.append({"ownerId": prods[h]["id"], "namespace": "custom", "key": k, "type": typ[k], "value": new})
    print(f"\n{len(writes)} cambios en {len(backup)} productos")
    if not apply or not writes:
        return
    BACKUP_DIR.mkdir(exist_ok=True)
    bf = BACKUP_DIR / f"nutrition_avg_{time.strftime('%Y%m%d-%H%M%S')}.json"
    bf.write_text(json.dumps(backup, ensure_ascii=False, indent=1))
    for i in range(0, len(writes), 25):
        r = gql(token, M_SET, {"m": writes[i:i + 25]})["metafieldsSet"]
        if r["userErrors"]:
            sys.exit("userErrors: " + json.dumps(r["userErrors"]))
    print(f"Aplicado. Backup: {bf}")


if __name__ == "__main__":
    main()
