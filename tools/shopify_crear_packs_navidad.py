#!/usr/bin/env python3
"""
Packs de Navidad 2026: crea en borrador los 7 lotes nuevos y migra Bronce/Plata/Oro (Jorge).

  * Cada producto del pack es un metaobjeto `componente_pack` (nombre, formato, ingredientes, alérgenos)
    referenciado desde custom.componentes_del_packs. No hace falta que el queso/turrón/picos se vendan sueltos.
  * Los textos de ingredientes/alérgenos de sobres, embutidos y jamones se copian de los PRODUCTOS REALES
    (custom.ingredients / custom.allergens), buscados por SKU. Los componentes antiguos no se tocan.
  * Quesos Manchego / oveja / oveja con romero y turrón a la piedra no tienen ficha: van marcados PENDIENTE.
  * Bronce/Plata/Oro: sus ingredientes/alérgenos se sacan de la descripción a componentes y se limpia la descripción.
  * Un pack nuevo = una sola variante (precio y SKU 519+). Los PVP son los de la hoja (provisionales).

Reutiliza la auth (Keychain) de shopify_update_ingredients.py.

Uso:
  python3 tools/shopify_crear_packs_navidad.py            # dry-run (solo lee)
  python3 tools/shopify_crear_packs_navidad.py --apply
  python3 tools/shopify_crear_packs_navidad.py --rollback _backup/packs_navidad_XXXX.json --apply
"""
import importlib.util, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

BACKUP_DIR = os.path.join(HERE, "..", "_backup")
SUFFIX = "-nav26"          # sufijo de handle para no chocar con los componentes antiguos
PENDING = "PENDIENTE de la ficha técnica del fabricante."

# ── Componentes ─────────────────────────────────────────────────────────────────
# key -> (nombre, formato, SKU del producto real del que salen los textos | None, texto fijo)
# Texto fijo = (ingredientes, alérgenos)
JAM = "Sobre 80 g"; EMB = "Sobre 100 g"
COMPONENTS = {
    "jamon-verde":   ("Jamón de Cebo de Campo 50% Ibérico — Precinto Verde", JAM, "459", None),
    "jamon-rojo":    ("Jamón de Bellota 50% Ibérico — Precinto Rojo", JAM, "461", None),
    "jamon-negro":   ("Jamón de Bellota 100% Ibérico — Precinto Negro", JAM, "463", None),
    "lomo-cebo-s":   ("Lomo de Cebo de Campo Ibérico 50%", EMB, "480", None),
    "lomo-bell-s":   ("Lomo de Bellota Ibérico", EMB, "482", None),
    "lomito-s":      ("Lomito de Presa de Bellota Ibérico", EMB, "484", None),
    "chorizo-s":     ("Chorizo de Bellota Ibérico", EMB, "476", None),
    "salchichon-s":  ("Salchichón de Bellota Ibérico", EMB, "478", None),
    "chorizo-e":     ("Chorizo de Bellota Ibérico — Pieza entera", "Pieza entera 600–800 g", "495", None),
    "salchichon-e":  ("Salchichón de Bellota Ibérico — Pieza entera", "Pieza entera 600–800 g", "496", None),
    "lomo-cebo-e":   ("Lomo de Cebo de Campo Ibérico 50% — Pieza entera", "Pieza entera 600–800 g", "497", None),
    "lomo-bell-e":   ("Lomo de Bellota Ibérico — Pieza entera", "Pieza entera 600–800 g", "498", None),
    "lomito-e":      ("Lomito de Presa de Bellota Ibérico — Pieza entera", "Pieza entera 350–550 g", "499", None),
    # Picos: dato ya verificado en los packs antiguos
    "picos": ("Picos Rústicos Premium", "Bolsa 150 g", None, (
        "Harina de trigo (gluten), agua, masa madre de trigo, aceite de oliva virgen extra (2%), sal, levadura y harina de centeno.",
        "Gluten (trigo, centeno). Puede contener trazas de: sésamo, mostaza y soja.")),
    # Quesos de Jorge (fichas de Manzer)
    "queso-anejo": ("Queso Añejo de Oveja (Manzer)", "Cuña 200 g", None, (
        "Leche cruda de oveja, sal, cuajo, fermentos lácticos, estabilizante E-509, conservador E-252 y lisozima (derivado del huevo). Corteza: conservadores E-235 y E-202 y colorante E-172.",
        "Contiene leche y huevo (lisozima).")),
    "queso-vecchio": ("Queso Vecchio de Oveja (Manzer)", "Cuña 200 g", None, (
        "Leche pasteurizada de oveja, sal, cuajo, fermentos lácticos, estabilizante E-509. Corteza: conservadores E-235 y E-202.",
        "Contiene leche. Puede contener trazas de huevo.")),
    # Quesos sin ficha
    "queso-manchego": ("Queso Curado de Oveja DOP Manchego", "Cuña 200 g", None, (
        PENDING, "Contiene leche. Resto de alérgenos: " + PENDING)),
    "queso-oveja": ("Queso Curado de Oveja", "Cuña 200 g", None, (
        PENDING, "Contiene leche. Resto de alérgenos: " + PENDING)),
    "queso-romero": ("Queso Curado de Oveja con Romero", "Cuña 200 g", None, (
        PENDING, "Contiene leche. Resto de alérgenos: " + PENDING)),
    # Turrones
    "turron-duro": ("Turrón Duro de Almendra", "200 g", None, (
        "Almendra tostada (60 %), azúcar, miel, jarabe de glucosa, clara de huevo y oblea de recubrimiento (fécula de patata y aceite vegetal de girasol).",
        "Contiene frutos de cáscara (almendra) y huevo. Puede contener trazas de otros frutos de cáscara.")),
    "turron-blando": ("Turrón Blando de Almendra", "200 g", None, (
        "Almendra tostada (64 %), azúcar, miel, clara de huevo y emulgente: E-471.",
        "Contiene frutos de cáscara (almendra) y huevo. Puede contener trazas de otros frutos de cáscara.")),
    "turron-piedra": ("Turrón a la Piedra", "200 g", None, (PENDING, PENDING)),
}

# ── Packs nuevos ────────────────────────────────────────────────────────────────
# (título, handle, sku, precio, tags, intro, [(cantidad, texto, componente)])
NEW_PACKS = [
    ("Dúo Ibérico", "duo-iberico", "519", "29.90", ["bellota", "bellota-50", "bellota-100"],
     "Dos sobres de jamón ibérico de bellota cortado a mano para empezar a probar: el rojo (50 %) y el negro (100 %).",
     [(1, "Sobre de jamón Bellota 50 % Ibérico — Precinto Rojo (80 g)", "jamon-rojo"),
      (1, "Sobre de jamón Bellota 100 % Ibérico — Precinto Negro (80 g)", "jamon-negro")]),
    ("Cata de Orígenes", "cata-de-origenes", "520", "39.90", ["cebo-de-campo", "bellota", "bellota-50", "bellota-100"],
     "Una cata de tres sobres de jamón cortado a mano, uno de cada tipo: Cebo de Campo 50 %, Bellota 50 % y Bellota 100 %.",
     [(1, "Sobre de jamón Cebo de Campo 50 % Ibérico — Precinto Verde (80 g)", "jamon-verde"),
      (1, "Sobre de jamón Bellota 50 % Ibérico — Precinto Rojo (80 g)", "jamon-rojo"),
      (1, "Sobre de jamón Bellota 100 % Ibérico — Precinto Negro (80 g)", "jamon-negro")]),
    ("Esencia Bellota", "esencia-bellota", "521", "47.90", ["bellota", "bellota-50", "bellota-100", "embutido-iberico", "queso"],
     "Dos sobres de jamón de bellota, chorizo y salchichón loncheados, queso curado y picos rústicos.",
     [(1, "Sobre de jamón Bellota 50 % Ibérico — Precinto Rojo (80 g)", "jamon-rojo"),
      (1, "Sobre de jamón Bellota 100 % Ibérico — Precinto Negro (80 g)", "jamon-negro"),
      (1, "Sobre de chorizo de bellota ibérico (100 g)", "chorizo-s"),
      (1, "Sobre de salchichón de bellota ibérico (100 g)", "salchichon-s"),
      (1, "Cuña de queso curado de oveja DOP Manchego (200 g)", "queso-manchego"),
      (1, "Picos rústicos premium", "picos")]),
    ("Tradición Ibérica", "tradicion-iberica", "522", "52.90", ["bellota", "embutido-iberico", "queso"],
     "Chorizo y salchichón de bellota ibérico enteros, una cuña de queso de oveja curado y turrón a la piedra.",
     [(1, "Chorizo de bellota ibérico entero (600–800 g)", "chorizo-e"),
      (1, "Salchichón de bellota ibérico entero (600–800 g)", "salchichon-e"),
      (1, "Cuña de queso curado de oveja (200 g)", "queso-oveja"),
      (1, "Turrón a la piedra (200 g)", "turron-piedra")]),
    ("Herencia de Dehesa", "herencia-de-dehesa", "523", "121.90", ["cebo-de-campo", "bellota", "bellota-50", "bellota-100", "embutido-iberico", "cata-vertical"],
     "Una cata vertical doble: dos sobres de cada categoría de jamón (Verde, Rojo y Negro) más chorizo y salchichón enteros.",
     [(2, "Sobres de jamón Cebo de Campo 50 % Ibérico — Precinto Verde (80 g)", "jamon-verde"),
      (2, "Sobres de jamón Bellota 50 % Ibérico — Precinto Rojo (80 g)", "jamon-rojo"),
      (2, "Sobres de jamón Bellota 100 % Ibérico — Precinto Negro (80 g)", "jamon-negro"),
      (1, "Chorizo de bellota ibérico entero (600–800 g)", "chorizo-e"),
      (1, "Salchichón de bellota ibérico entero (600–800 g)", "salchichon-e")]),
    ("El Arte del Embutido", "el-arte-del-embutido", "524", "139.90", ["cebo-de-campo", "bellota", "bellota-100", "embutido-iberico"],
     "Cuatro embutidos ibéricos enteros: chorizo, salchichón, lomo de cebo de campo y lomo de bellota.",
     [(1, "Chorizo de bellota ibérico entero (600–800 g)", "chorizo-e"),
      (1, "Salchichón de bellota ibérico entero (600–800 g)", "salchichon-e"),
      (1, "Lomo de cebo de campo ibérico 50 % entero (600–800 g)", "lomo-cebo-e"),
      (1, "Lomo de bellota 100 % ibérico entero (600–800 g)", "lomo-bell-e")]),
    ("Selección Maestra", "seleccion-maestra", "525", "189.90", ["bellota", "bellota-100", "embutido-iberico"],
     "Seis sobres de jamón de bellota 100 % ibérico cortado a mano, lomo de bellota entero y lomito de presa entero.",
     [(6, "Sobres de jamón Bellota 100 % Ibérico — Precinto Negro (80 g)", "jamon-negro"),
      (1, "Lomo de bellota 100 % ibérico entero (600–800 g)", "lomo-bell-e"),
      (1, "Lomito de presa ibérico entero (350–550 g)", "lomito-e")]),
]
COMMON_TAGS = ["pack-gourmet", "navidad", "regalo", "jamon-iberico"]

# ── Packs de Jorge: handle -> componentes (en el orden de su descripción) ────────
JORGE = {
    "seleccion-bronce": ["jamon-verde", "lomo-cebo-s", "chorizo-s", "salchichon-s", "queso-anejo", "queso-vecchio", "turron-duro", "turron-blando"],
    "seleccion-plata":  ["jamon-rojo", "lomo-bell-s", "chorizo-s", "salchichon-s", "queso-anejo", "queso-vecchio", "turron-piedra"],
    "seleccion-oro":    ["jamon-negro", "lomito-s", "chorizo-s", "salchichon-s", "queso-anejo", "queso-vecchio", "turron-piedra"],
}

ALG_WORDS = ["leche", "huevo", "frutos de cáscara", "almendra", "gluten", "pescado", "moluscos", "sulfitos"]


def rich(text, bold_allergens=False):
    """rich_text de Shopify (JSON). En alérgenos pone en negrita los alérgenos de declaración."""
    parts = [text]
    if bold_allergens:
        pat = "(" + "|".join(ALG_WORDS) + ")"
        parts = [p for p in re.split(pat, text, flags=re.I) if p != ""]
    kids = []
    for p in parts:
        node = {"type": "text", "value": p}
        if bold_allergens and p.lower() in ALG_WORDS and not text.startswith("Sin "):
            node["bold"] = True
        kids.append(node)
    return json.dumps({"type": "root", "children": [{"type": "paragraph", "children": kids}]}, ensure_ascii=False)


Q_SKU = """query($q:String!){ products(first:5, query:$q){ nodes{ title variants(first:5){ nodes{ sku } }
  i: metafield(namespace:"custom",key:"ingredients"){ value } a: metafield(namespace:"custom",key:"allergens"){ value } } } }"""
Q_PROD = """query($q:String!){ products(first:1, query:$q){ nodes{ id title descriptionHtml templateSuffix
  variants(first:5){ nodes{ id sku price } } } } }"""
Q_META = """query($h:String!){ metaobjectByHandle(handle:{type:"componente_pack", handle:$h}){ id handle } }"""
M_MO = """mutation($m:MetaobjectCreateInput!){ metaobjectCreate(metaobject:$m){ metaobject{ id handle } userErrors{ field message code } } }"""
M_PC = """mutation($p:ProductCreateInput!){ productCreate(product:$p){ product{ id handle variants(first:1){ nodes{ id } } } userErrors{ field message } } }"""
M_PU = """mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ id } userErrors{ field message } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""
M_MF = """mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }"""
M_DEL_MO = """mutation($id:ID!){ metaobjectDelete(id:$id){ userErrors{ message } } }"""
M_DEL_P = """mutation($i:ProductDeleteInput!){ productDelete(input:$i){ userErrors{ message } } }"""


def chk(res, key):
    e = res[key]["userErrors"]
    if e:
        sys.exit(f"ERROR en {key}: {e}")


def real_texts(token, sku):
    r = base.gql(token, Q_SKU, {"q": f"sku:{sku}"})["products"]["nodes"]
    for p in r:
        if any(v["sku"] == sku for v in p["variants"]["nodes"]):
            return p["title"], (p["i"] or {}).get("value"), (p["a"] or {}).get("value")
    sys.exit(f"No encuentro producto con SKU {sku}")


def build_components(token):
    out = {}
    for k, (nombre, fmt, sku, fixed) in COMPONENTS.items():
        if sku:
            src, ing, alg = real_texts(token, sku)
            if not ing:
                sys.exit(f"{src} (SKU {sku}) no tiene ingredientes")
            src = f"producto «{src}» SKU {sku}"
        else:
            ing, alg = fixed
            src = "texto fijo" + (" · PENDIENTE de ficha" if PENDING in ing + alg else "")
        out[k] = {"nombre": nombre, "formato": fmt, "ing": ing, "alg": alg or "", "src": src, "handle": k + SUFFIX}
    return out


def intro_and_includes(desc_html):
    """Para los packs de Jorge: conserva todo hasta <p><strong>Ingredientes:</strong></p>."""
    i = desc_html.find("<p><strong>Ingredientes:</strong></p>")
    return desc_html[:i].rstrip() if i > 0 else desc_html


def pack_html(intro, items):
    lis = "\n".join(f"<li>{q} {t}</li>" if q > 1 else f"<li>1 {t}</li>" for q, t, _ in items)
    return f"<p>{intro}</p>\n<p><strong>Incluye:</strong></p>\n<ul>\n{lis}\n</ul>"


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, scopes = base.get_token()
    if "metaobject" not in scopes:
        sys.exit("El token no tiene scopes de metaobjetos.")

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        print("Rollback: borra packs y componentes creados; restaura descripción de Bronce/Plata/Oro")
        if not apply:
            print("(dry-run) añade --apply"); return
        for pid in bk["products_created"]:
            chk(base.gql(token, M_DEL_P, {"i": {"id": pid}}), "productDelete")
        for mid in bk["components_created"]:
            chk(base.gql(token, M_DEL_MO, {"id": mid}), "metaobjectDelete")
        for j in bk["jorge"]:
            chk(base.gql(token, M_PU, {"p": {"id": j["id"], "descriptionHtml": j["descriptionHtml"]}}), "productUpdate")
            base.gql(token, M_MF, {"m": [{"ownerId": j["id"], "namespace": "custom", "key": "componentes_del_packs",
                                          "type": "list.metaobject_reference", "value": j["old_components"] or "[]"}]})
        print("Restaurado."); return

    comps = build_components(token)
    used = {c for *_, items in NEW_PACKS for _, _, c in items} | {c for v in JORGE.values() for c in v}
    print(f"== COMPONENTES A CREAR ({len(used)}) ==")
    for k in COMPONENTS:
        if k in used:
            c = comps[k]
            ex = base.gql(token, Q_META, {"h": c["handle"]})["metaobjectByHandle"]
            print(f"  {c['handle']:<28} {c['nombre']} · {c['formato']}  [{c['src']}]{'  (YA EXISTE)' if ex else ''}")
            print(f"       ING: {c['ing'][:110]}{'…' if len(c['ing']) > 110 else ''}")
            print(f"       ALG: {c['alg'][:110]}")

    ref = base.gql(token, Q_PROD, {"q": "title:'Pack Aperitivo'"})["products"]["nodes"][0]
    tsuf = ref["templateSuffix"]
    print(f"\n== PACKS NUEVOS (DRAFT, plantilla: {tsuf!r}) ==")
    for t, h, sku, price, tags, intro, items in NEW_PACKS:
        ex = base.gql(token, Q_PROD, {"q": f"handle:{h}"})["products"]["nodes"]
        print(f"  {t}  /{h}  SKU {sku}  {price} €{'  (YA EXISTE)' if ex else ''}")
        for q, text, c in items:
            print(f"      {q} × {text}  → {c}{SUFFIX}")
    print("\n== BRONCE / PLATA / ORO (migrar) ==")
    for h, cl in JORGE.items():
        p = base.gql(token, Q_PROD, {"q": f"handle:{h}"})["products"]["nodes"][0]
        print(f"  {p['title']}: {len(cl)} componentes; la descripción se queda en intro + «Incluye» y pierde Ingredientes/Alérgenos")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar."); return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = {"products_created": [], "components_created": [], "jorge": []}
    bpath = os.path.join(BACKUP_DIR, f"packs_navidad_{time.strftime('%Y%m%d-%H%M%S')}.json")

    def save():
        json.dump(bk, open(bpath, "w"), ensure_ascii=False, indent=1)

    ids = {}
    for k in COMPONENTS:
        if k not in used:
            continue
        c = comps[k]
        ex = base.gql(token, Q_META, {"h": c["handle"]})["metaobjectByHandle"]
        if ex:
            ids[k] = ex["id"]; continue
        res = base.gql(token, M_MO, {"m": {"type": "componente_pack", "handle": c["handle"], "fields": [
            {"key": "nombre", "value": c["nombre"]}, {"key": "formato", "value": c["formato"]},
            {"key": "ingredientes", "value": rich(c["ing"])},
            {"key": "alergenos", "value": rich(c["alg"], bold_allergens=True)}]}})
        chk(res, "metaobjectCreate")
        ids[k] = res["metaobjectCreate"]["metaobject"]["id"]
        bk["components_created"].append(ids[k]); save()
    print(f"Componentes: {len(ids)} listos")

    for t, h, sku, price, tags, intro, items in NEW_PACKS:
        if base.gql(token, Q_PROD, {"q": f"handle:{h}"})["products"]["nodes"]:
            print(f"  {t}: ya existe, lo salto"); continue
        inp = {"title": t, "handle": h, "status": "DRAFT", "productType": "Packs Gourmet",
               "tags": sorted(set(COMMON_TAGS + tags)), "descriptionHtml": pack_html(intro, items)}
        if tsuf:
            inp["templateSuffix"] = tsuf
        res = base.gql(token, M_PC, {"p": inp}); chk(res, "productCreate")
        pid = res["productCreate"]["product"]["id"]; vid = res["productCreate"]["product"]["variants"]["nodes"][0]["id"]
        bk["products_created"].append(pid); save()
        chk(base.gql(token, M_VAR, {"p": pid, "v": [{"id": vid, "price": price, "inventoryItem": {"sku": sku}}]}), "productVariantsBulkUpdate")
        order = []
        for _, _, c in items:
            if ids[c] not in order:
                order.append(ids[c])
        mf = [{"ownerId": pid, "namespace": "custom", "key": "componentes_del_packs",
               "type": "list.metaobject_reference", "value": json.dumps(order)}]
        chk(base.gql(token, M_MF, {"m": mf}), "metafieldsSet")
        print(f"  creado {t}")

    for h, cl in JORGE.items():
        p = base.gql(token, Q_PROD, {"q": f"handle:{h}"})["products"]["nodes"][0]
        old = base.gql(token, '''query($id:ID!){ product(id:$id){ metafield(namespace:"custom",key:"componentes_del_packs"){ value } } }''',
                       {"id": p["id"]})["product"]["metafield"]
        bk["jorge"].append({"id": p["id"], "descriptionHtml": p["descriptionHtml"], "old_components": old["value"] if old else None}); save()
        chk(base.gql(token, M_PU, {"p": {"id": p["id"], "descriptionHtml": intro_and_includes(p["descriptionHtml"])}}), "productUpdate")
        chk(base.gql(token, M_MF, {"m": [{"ownerId": p["id"], "namespace": "custom", "key": "componentes_del_packs",
                                          "type": "list.metaobject_reference", "value": json.dumps([ids[c] for c in cl])}]}), "metafieldsSet")
        print(f"  migrado {p['title']}")
    print("OK. Rollback: python3 tools/shopify_crear_packs_navidad.py --rollback", bpath, "--apply")


if __name__ == "__main__":
    main()
