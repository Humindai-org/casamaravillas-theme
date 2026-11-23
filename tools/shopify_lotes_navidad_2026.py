#!/usr/bin/env python3
"""
Lotes de Navidad (22/11/2026, decisión de Jorge). TODO EN BORRADOR: este script no publica nada ni toca ningún canal.

  1. Retitula los 3 borradores seleccion-* (el handle NO cambia):
       Selección Bronce 46,90 -> «Lote de Navidad Cebo de Campo»  49,90 €   (handle seleccion-bronce, SIN cambiar: decisión 23/11)
       Selección Plata  56,90 -> «Lote de Navidad Bellota 50 %»   59,90 €   (handle seleccion-plata)
       Selección Oro    66,90 -> «Lote de Navidad Bellota 100 %»  69,90 €   (handle seleccion-oro)
  2. Crea 5 lotes nuevos (hoja de Kiara, Drive 1q5nXu4VARHkxFljOqOd0dwyPuTUhsYaPl5BRcZnEgyk, pestañas Lotes y Detalle):
       Dúo de Bellota 29,90 · Trío de Jamones Ibéricos 39,90 · Surtido Ibérico para Compartir 121,90 ·
       Lote de Embutidos Ibéricos 139,90 · Colección de Bellota 189,90 (sin «100 %» en el título: la ficha del lomito de presa no lo dice).
     «Pack Bellota» y «Pack Ibéricos» NO se crean: esperan al escandallo.
  Descripción: un bloque por producto con sus ingredientes y alérgenos.
    · Jamones y embutidos: etiquetas de planning/fichas-tecnicas/2026-11-17-whatsapp-luis-juan/ (01–08), «Alérgenos: NO».
    · Queso Manzer: planning/fichas-tecnicas/queso-manzer/README.md; manda la foto de la caja (etiqueta-caja.jpg), no el render.
      Añejo: leche y huevo. Vecchio: leche y puede contener trazas de huevo; colorante de la corteza E-133 (lo que se lee en la foto).
    · Turrón (solo los 3 lotes de Navidad): bloque marcado PENDIENTE hasta que conteste Luis Juan; datos de las fichas Carremi duro/blando.
  Todos: categoría Food Gift Baskets (IVA 10 %), sin vino, plantilla packs-regalo, perfil de envío por defecto (zona Península), BORRADOR.

Uso:  python3 -I tools/shopify_lotes_navidad_2026.py                       # simulacro (solo lee)
      python3 -I tools/shopify_lotes_navidad_2026.py --apply               # copia de seguridad + escribe + verifica
      python3 -I tools/shopify_lotes_navidad_2026.py --sin-nuevos [--apply]  # solo los 3 borradores seleccion-* (los 5 nuevos esperan: SKU 519–523 ocupados)
      python3 -I tools/shopify_lotes_navidad_2026.py --rollback _backup/lotes_navidad_XXXX.json --apply   # deja todo como estaba
"""
import glob, importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base
BK = os.path.join(HERE, "..", "_backup")
CATEGORY = "gid://shopify/TaxonomyCategory/fb-2-8"   # Food Gift Baskets: IVA 10 % (comprobado con los packs con vino y con los 3 de Navidad)

# ---- Ingredientes y alérgenos por producto -----------------------------------------------------------------------------
ETQ = "Ninguno declarado en la etiqueta (Alérgenos: NO)."
JAMON = "{}, sal común, azúcar, corrector de acidez (E-331iii), conservadores (E-252, E-250), antioxidante (E-301)."
LOMO = "{}, sal, azúcar, antioxidante (E-301), conservadores (E-252, E-250), corrector de acidez (E-331iii), pimentón, ajo y orégano."
COMP = {
    "j_cebo": ("Sobre de jamón cortado a mano · Cebo de Campo 50 % Ibérico (80 g)", JAMON.format("Jamón de cebo campo ibérico"), ETQ),
    "j_b50": ("Sobre de jamón cortado a mano · Bellota 50 % Ibérico (80 g)", JAMON.format("Jamón de bellota ibérico"), ETQ),
    "j_b100": ("Sobre de jamón cortado a mano · Bellota 100 % Ibérico (80 g)", JAMON.format("Jamón de bellota 100% ibérico"), ETQ),
    "lomo_cebo": ("Lomo de cebo de campo ibérico", LOMO.format("Lomo de cebo campo ibérico"), ETQ),
    "lomo_b100": ("Lomo de bellota 100 % ibérico", LOMO.format("Lomo de bellota 100% ibérico"), ETQ),
    "lomito": ("Lomito de presa de bellota ibérico", LOMO.format("Presa de bellota ibérico"), ETQ),
    "chorizo": ("Chorizo de bellota ibérico", "Magro y tocino de bellota ibérico, sal, pimentón, dextrina, proteína de cerdo, dextrosa, antioxidante (E-316), conservadores (E-250, E-252), ajo y orégano.", ETQ),
    "salchichon": ("Salchichón de bellota ibérico", "Magro y tocino de bellota ibérico, sal, almidón, especias, dextrosa, corrector de acidez (E-331), conservadores (E-252, E-250), proteína de cerdo, dextrina y ajo.", ETQ),
    # Foto de la caja (etiqueta-caja.jpg), 22/11/2026. Manzer, Industrias Lácteas Manzano S.A.
    "anejo": ("Queso de oveja Añejo, Manzer (200 g)",
              "Leche cruda de oveja, sal, cuajo, fermentos lácticos (leche), estabilizante E-509 y conservadores E-252 y lisozima (derivado del huevo). Origen de la leche: España. Corteza (no comestible): conservadores de superficie E-235 y E-202 y colorante E-172.",
              "leche y huevo."),
    "vecchio": ("Queso de oveja Vecchio, Manzer (200 g)",
                "Queso de oveja madurado. Leche pasteurizada de oveja, sal, cuajo, fermentos lácticos (leche) y estabilizante E-509. Origen de la leche: España. Corteza (no comestible): conservadores de superficie E-235 y E-202 y colorante E-133.",
                "leche. Puede contener trazas de huevo."),
}
TURRON = ("<p><strong>Turrón: PENDIENTE de confirmar con Luis Juan (no publicar así).</strong><br>"
          "Todavía no está cerrado qué turrón lleva el lote. Datos de las fichas técnicas del fabricante (Turrones de Alicante S.A., Carremi, 29/02/2024):</p>\n"
          "<ul>\n<li><strong>Turrón duro de almendra (calidad suprema):</strong> almendra tostada (60 %), azúcar, miel, jarabe de glucosa, clara de huevo y oblea de recubrimiento (fécula de patata y aceite vegetal de girasol). "
          "Alérgenos: huevo y almendra (fruto de cáscara); puede contener trazas de otros frutos de cáscara.</li>\n"
          "<li><strong>Turrón blando de almendra (calidad suprema):</strong> almendra tostada (64 %), azúcar, miel, clara de huevo y emulgente E-471. "
          "Alérgenos: huevo y almendra (fruto de cáscara); puede contener trazas de otros frutos de cáscara.</li>\n</ul>")
TURRON_PIEDRA = "<p>Este lote figura con turrón a la piedra, del que no hay ficha técnica: ingredientes y alérgenos PENDIENTES.</p>\n"
ALERG_NAV = "Quesos: leche y huevo (Vecchio: puede contener trazas de huevo). Turrón: PENDIENTE de confirmar con Luis Juan. Jamones y embutidos: ninguno."
ALERG_SIN = "Ninguno declarado en las etiquetas de los productos (Alérgenos: NO)."

QUESOS = ["2 cuñas de queso de oveja Manzer (Añejo y Vecchio), 2 × 200 g"]
LOTES = [
    # --- los 3 borradores existentes (se renombran) ---
    {"viejo": "seleccion-bronce", "handle": "seleccion-bronce", "title": "Lote de Navidad Cebo de Campo", "price": "49.90", "sku": "516",
     "intro": "Lote de Navidad de la gama Cebo de Campo 50 % Ibérico: sobres de jamón y embutidos ibéricos, dos quesos de oveja y turrón.",
     "items": ["1 sobre de jamón cortado a mano Cebo de Campo 50 % Ibérico", "1 sobre de lomo de cebo de campo ibérico", "1 sobre de chorizo de bellota ibérico",
               "1 sobre de salchichón de bellota ibérico"] + QUESOS + ["1 turrón de 200 g (pendiente de confirmar con Luis Juan)"],
     "comp": ["j_cebo", "lomo_cebo", "chorizo", "salchichon", "anejo", "vecchio"], "turron": TURRON, "alerg": ALERG_NAV, "kg": 1.5,
     "tags": ["cebo-de-campo", "embutido-iberico", "jamon-iberico", "pack-gourmet", "queso", "regalo", "navidad", "pendiente-ficha-turron"],
     "seo": ("Lote de Navidad Cebo de Campo: jamón y embutidos ibéricos, queso y turrón | Casa Maravillas",
             "Lote de Navidad con sobres de jamón y embutidos ibéricos de cebo de campo, dos quesos de oveja y turrón.")},
    {"viejo": "seleccion-plata", "handle": "seleccion-plata", "title": "Lote de Navidad Bellota 50 %", "price": "59.90", "sku": "517",
     "intro": "Lote de Navidad de la gama Bellota 50 % Ibérico: sobres de jamón y embutidos ibéricos, dos quesos de oveja y turrón.",
     "items": ["1 sobre de jamón cortado a mano Bellota 50 % Ibérico", "1 sobre de lomo de bellota 100 % ibérico", "1 sobre de chorizo de bellota ibérico",
               "1 sobre de salchichón de bellota ibérico"] + QUESOS + ["1 turrón a la piedra (pendiente de confirmar con Luis Juan)"],
     "comp": ["j_b50", "lomo_b100", "chorizo", "salchichon", "anejo", "vecchio"], "turron": TURRON + TURRON_PIEDRA, "alerg": ALERG_NAV, "kg": 1.5,
     "tags": ["bellota", "bellota-50", "embutido-iberico", "jamon-iberico", "pack-gourmet", "queso", "regalo", "navidad", "pendiente-ficha-turron"],
     "seo": ("Lote de Navidad Bellota 50 %: jamón y embutidos ibéricos, queso y turrón | Casa Maravillas",
             "Lote de Navidad con sobres de jamón y embutidos ibéricos de bellota, dos quesos de oveja y turrón.")},
    {"viejo": "seleccion-oro", "handle": "seleccion-oro", "title": "Lote de Navidad Bellota 100 %", "price": "69.90", "sku": "518",
     "intro": "Lote de Navidad de la gama Bellota 100 % Ibérico: sobres de jamón y embutidos ibéricos, dos quesos de oveja y turrón.",
     "items": ["1 sobre de jamón cortado a mano Bellota 100 % Ibérico", "1 sobre de lomito de presa de bellota ibérico", "1 sobre de chorizo de bellota ibérico",
               "1 sobre de salchichón de bellota ibérico"] + QUESOS + ["1 turrón a la piedra (pendiente de confirmar con Luis Juan)"],
     "comp": ["j_b100", "lomito", "chorizo", "salchichon", "anejo", "vecchio"], "turron": TURRON + TURRON_PIEDRA, "alerg": ALERG_NAV, "kg": 1.5,
     "tags": ["bellota", "bellota-100", "embutido-iberico", "jamon-iberico", "pack-gourmet", "queso", "regalo", "navidad", "pendiente-ficha-turron"],
     "seo": ("Lote de Navidad Bellota 100 %: jamón y embutidos ibéricos, queso y turrón | Casa Maravillas",
             "Lote de Navidad con sobres de jamón y embutidos ibéricos de bellota 100 % ibérico, dos quesos de oveja y turrón.")},
    # --- 5 nuevos (hoja de Kiara) ---
    {"handle": "duo-de-bellota", "title": "Dúo de Bellota", "price": "29.90", "sku": "519",
     "intro": "Dos sobres de jamón ibérico cortado a mano para probar la bellota: Bellota 50 % Ibérico y Bellota 100 % Ibérico.",
     "items": ["1 sobre de jamón cortado a mano Bellota 50 % Ibérico (80 g)", "1 sobre de jamón cortado a mano Bellota 100 % Ibérico (80 g)"],
     "comp": ["j_b50", "j_b100"], "alerg": ALERG_SIN, "gramaje": "160 g", "kg": 0.3,
     "tags": ["bellota", "jamon-iberico", "pack-gourmet", "regalo"],
     "seo": ("Dúo de Bellota: dos sobres de jamón ibérico de bellota | Casa Maravillas", "Dos sobres de jamón ibérico cortado a mano: Bellota 50 % y Bellota 100 %.")},
    {"handle": "trio-de-jamones-ibericos", "title": "Trío de Jamones Ibéricos", "price": "39.90", "sku": "520",
     "intro": "Un sobre de jamón ibérico cortado a mano de cada nivel de la gama: Cebo de Campo 50 %, Bellota 50 % y Bellota 100 %.",
     "items": ["1 sobre de jamón cortado a mano Cebo de Campo 50 % Ibérico (80 g)", "1 sobre de jamón cortado a mano Bellota 50 % Ibérico (80 g)",
               "1 sobre de jamón cortado a mano Bellota 100 % Ibérico (80 g)"],
     "comp": ["j_cebo", "j_b50", "j_b100"], "alerg": ALERG_SIN, "gramaje": "240 g", "kg": 0.45,
     "tags": ["jamon-iberico", "pack-gourmet", "regalo"],
     "seo": ("Trío de Jamones Ibéricos: cebo de campo y bellota | Casa Maravillas", "Tres sobres de jamón ibérico cortado a mano: Cebo de Campo 50 %, Bellota 50 % y Bellota 100 %.")},
    {"handle": "surtido-iberico-para-compartir", "title": "Surtido Ibérico para Compartir", "price": "121.90", "sku": "521",
     "intro": "Seis sobres de jamón ibérico cortado a mano (dos de cada nivel de la gama) y un chorizo y un salchichón de bellota ibérico enteros.",
     "items": ["2 sobres de jamón cortado a mano Cebo de Campo 50 % Ibérico (80 g)", "2 sobres de jamón cortado a mano Bellota 50 % Ibérico (80 g)",
               "2 sobres de jamón cortado a mano Bellota 100 % Ibérico (80 g)", "1 chorizo de bellota ibérico entero (600–800 g)", "1 salchichón de bellota ibérico entero (600–800 g)"],
     "comp": ["j_cebo", "j_b50", "j_b100", "chorizo", "salchichon"], "alerg": ALERG_SIN, "kg": 2.3,
     "tags": ["bellota", "embutido-iberico", "jamon-iberico", "pack-gourmet", "regalo", "pendiente-confirmar-pieza"],
     "seo": ("Surtido Ibérico para Compartir: jamón, chorizo y salchichón | Casa Maravillas", "Seis sobres de jamón ibérico cortado a mano, chorizo y salchichón de bellota ibérico enteros.")},
    {"handle": "lote-de-embutidos-ibericos", "title": "Lote de Embutidos Ibéricos", "price": "139.90", "sku": "522",
     "intro": "Cuatro embutidos ibéricos enteros: chorizo y salchichón de bellota, lomo de cebo de campo y lomo de bellota 100 % ibérico.",
     "items": ["1 chorizo de bellota ibérico entero (600–800 g)", "1 salchichón de bellota ibérico entero (600–800 g)",
               "1 lomo de cebo de campo ibérico entero (600–800 g)", "1 lomo de bellota 100 % ibérico entero (600–800 g)"],
     "comp": ["chorizo", "salchichon", "lomo_cebo", "lomo_b100"], "alerg": ALERG_SIN, "kg": 2.8,
     "tags": ["embutido-iberico", "pack-gourmet", "regalo", "pendiente-confirmar-pieza"],
     "seo": ("Lote de Embutidos Ibéricos: chorizo, salchichón y lomos | Casa Maravillas", "Chorizo y salchichón de bellota ibérico y lomo de cebo de campo y de bellota ibérico, todos enteros.")},
    {"handle": "coleccion-de-bellota", "title": "Colección de Bellota", "price": "189.90", "sku": "523",
     "intro": "Seis sobres de jamón ibérico cortado a mano de bellota, un lomo de bellota ibérico entero y un lomito de presa de bellota ibérico entero.",
     "items": ["6 sobres de jamón cortado a mano Bellota 100 % Ibérico (80 g)", "1 lomo de bellota 100 % ibérico entero (600–800 g)", "1 lomito de presa de bellota ibérico entero"],
     "comp": ["j_b100", "lomo_b100", "lomito"], "alerg": ALERG_SIN, "kg": 2.1,
     "tags": ["bellota", "embutido-iberico", "jamon-iberico", "pack-gourmet", "regalo", "pendiente-confirmar-pieza"],
     "seo": ("Colección de Bellota: jamón, lomo y lomito de presa | Casa Maravillas", "Seis sobres de jamón ibérico de bellota cortado a mano, lomo de bellota y lomito de presa de bellota ibérico enteros.")},
]
NOTA_IMAGEN = "<p><em>Imagen orientativa: la presentación puede variar</em></p>"
PROHIBIDO = ("vino", "caja de regalo", "alcohol")

Q_PROD = """query($q:String){ products(first:5, query:$q){ nodes{ id handle title status tags descriptionHtml productType templateSuffix category{ id } seo{ title description }
  resourcePublicationsCount{ count } variants(first:3){ nodes{ id sku price inventoryItem{ measurement{ weight{ value } } } } }
  metafields(first:10, namespace:"custom"){ nodes{ key value type } } } } }"""
Q_DEFS = """{ metafieldDefinitions(first:10, ownerType:PRODUCT, namespace:"custom", key:"%s"){ nodes{ type{ name } } } }"""
Q_SKU = """query($q:String){ productVariants(first:5, query:$q){ nodes{ sku product{ handle } } } }"""
M_UPD = """mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ product{ id handle status } userErrors{ field message } } }"""
M_CRE = """mutation($p:ProductCreateInput!){ productCreate(product:$p){ product{ id handle status variants(first:3){ nodes{ id } } } userErrors{ field message } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){ productVariants{ id } userErrors{ field message } } }"""
M_META = """mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ metafields{ key } userErrors{ field message } } }"""
M_MDEL = """mutation($m:[MetafieldIdentifierInput!]!){ metafieldsDelete(metafields:$m){ deletedMetafields{ key } userErrors{ field message } } }"""
M_DEL = "mutation($i:ProductDeleteInput!){ productDelete(input:$i){ deletedProductId userErrors{ field message } } }"
M_TAX = """mutation($i:DraftOrderInput!){ draftOrderCalculate(input:$i){ calculatedDraftOrder{ taxLines{ ratePercentage } } userErrors{ field message } } }"""


def ok(res, key):
    e = res[key].get("userErrors") or []
    if e:
        sys.exit(f"ERROR en {key}: {e}")
    return res[key]


def descripcion(l):
    li = "\n".join(f"<li>{i}</li>" for i in l["items"])
    bl = "\n".join(f"<p><strong>{COMP[k][0]}</strong><br>Ingredientes: {COMP[k][1]}<br>Alérgenos: {COMP[k][2]}</p>" for k in l["comp"])
    return (f"<p>{l['intro']}</p>\n<p><strong>Incluye:</strong></p>\n<ul>\n{li}\n</ul>\n"
            f"<p><strong>Ingredientes y alérgenos de cada producto:</strong></p>\n{bl}\n{l.get('turron', '')}\n{NOTA_IMAGEN}").strip()


def metas(pid, l, tipos):
    m = [{"ownerId": pid, "namespace": "custom", "key": "allergens", "type": tipos["allergens"], "value": l["alerg"]}]
    if "gramaje" in l:     # decisión 23/11: gramaje solo en el Dúo y el Trío
        m.append({"ownerId": pid, "namespace": "custom", "key": "gramaje", "type": tipos["gramaje"], "value": l["gramaje"]})
    return m


def producto(token, handle):
    n = base.gql(token, Q_PROD, {"q": f"handle:{handle}"})["products"]["nodes"]
    return next((p for p in n if p["handle"] == handle), None)


def validar():
    for l in LOTES:
        txt = (descripcion(l) + l["title"] + l["alerg"] + " ".join(l["tags"])).lower()
        for w in PROHIBIDO:
            if w in txt:
                sys.exit(f"ERROR: «{w}» aparece en {l['handle']}")
        if len(l["alerg"]) > 255 or len(l.get("gramaje", "")) > 255:
            sys.exit(f"ERROR: metacampo demasiado largo en {l['handle']}")
    if any("100" in l["title"] for l in LOTES if l["handle"] == "coleccion-de-bellota"):
        sys.exit("ERROR: «Colección de Bellota» no puede llevar «100 %» en el título")


def main():
    a = sys.argv[1:]
    apply = "--apply" in a
    token, scopes = base.get_token()
    print(f"Tienda: {base.SHOP} | write_products: {'write_products' in scopes.split(',')} | {'APPLY' if apply else 'simulacro'}\n")

    if "--rollback" in a:
        bk = json.load(open(a[a.index("--rollback") + 1]))
        for h, pid in bk["creados"].items():
            print("  borrar", h, pid)
            if apply:
                ok(base.gql(token, M_DEL, {"i": {"id": pid}}), "productDelete")
        for h, p in bk["previos"].items():
            print("  restaurar", h, "->", p["handle"], p["title"], p["variants"]["nodes"][0]["price"])
            if apply:
                ok(base.gql(token, M_UPD, {"p": {"id": p["id"], "title": p["title"], "handle": p["handle"], "descriptionHtml": p["descriptionHtml"], "tags": p["tags"],
                    "seo": p["seo"], "redirectNewHandle": False}}), "productUpdate")
                v = p["variants"]["nodes"][0]
                ok(base.gql(token, M_VAR, {"p": p["id"], "v": [{"id": v["id"], "price": v["price"]}]}), "productVariantsBulkUpdate")
                ms = [{"ownerId": p["id"], "namespace": "custom", "key": m["key"], "type": m["type"], "value": m["value"]} for m in p["metafields"]["nodes"]]
                ok(base.gql(token, M_META, {"m": ms}), "metafieldsSet")
        print("Restaurado." if apply else "(simulacro) añade --apply")
        return

    validar()
    if "--verificar" in a:      # solo relee y comprueba (no escribe)
        verificar(token, [l for l in LOTES if "viejo" in l] if "--sin-nuevos" in a else LOTES, sorted(glob.glob(os.path.join(BK, "lotes_navidad_*.json")))[-1])
        return
    lotes = [l for l in LOTES if "viejo" in l] if "--sin-nuevos" in a else LOTES   # --sin-nuevos: solo retitula los 3 borradores seleccion-*
    tipos = {}
    for k in ("allergens", "gramaje"):
        d = base.gql(token, Q_DEFS % k)["metafieldDefinitions"]["nodes"]
        tipos[k] = d[0]["type"]["name"] if d else None
    if not all(tipos.values()):
        sys.exit(f"Falta la definición de un metacampo: {tipos}")
    previos, problemas = {}, []
    for l in lotes:
        if "viejo" in l:
            p = producto(token, l["viejo"])
            if not p:
                problemas.append(f"no existe el borrador {l['viejo']}")
                continue
            if p["status"] != "DRAFT" or p["resourcePublicationsCount"]["count"]:
                problemas.append(f"{l['viejo']} NO está en borrador sin canales: {p['status']}, canales {p['resourcePublicationsCount']['count']}")
            previos[l["viejo"]] = p
        else:
            if producto(token, l["handle"]):
                problemas.append(f"ya existe un producto con handle {l['handle']}")
            if base.gql(token, Q_SKU, {"q": f"sku:{l['sku']}"})["productVariants"]["nodes"]:
                problemas.append(f"el SKU {l['sku']} ya está en uso")
    if problemas:
        sys.exit("ABORTADO: " + "; ".join(problemas))

    print(f"{'handle (nuevo)':36} {'título':34} {'precio':>8}  {'estado':8} {'SKU':4} {'kg':>4}  acción")
    for l in lotes:
        antes = f"renombra {l['viejo']} ({previos[l['viejo']]['variants']['nodes'][0]['price']} €)" if "viejo" in l else "CREA"
        print(f"{l['handle']:36} {l['title']:34} {l['price']:>8}  {'BORRADOR':8} {l['sku']:4} {l['kg']:>4}  {antes}")
        print(f"     incluye: {' | '.join(l['items'])}")
        print(f"     gramaje: {l.get('gramaje', '(sin gramaje)')} · alérgenos: {l['alerg']} · etiquetas: {', '.join(l['tags'])}")
    print("\nTodos: categoría Food Gift Baskets, plantilla packs-regalo, sin canales de venta, sin vino ni «caja de regalo» (comprobado en los textos).")
    if not apply:
        print("\n(simulacro) No se ha escrito nada. Descripción completa de un lote de ejemplo (Lote de Navidad Bellota 100 %):\n")
        print(descripcion(lotes[min(2, len(lotes) - 1)]))
        return

    os.makedirs(BK, exist_ok=True)
    path = os.path.abspath(os.path.join(BK, f"lotes_navidad_{time.strftime('%Y%m%d-%H%M%S')}.json"))
    bk = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "previos": previos, "creados": {}}
    save = lambda: json.dump(bk, open(path, "w"), ensure_ascii=False, indent=1)
    save(); print("\nCopia de seguridad:", path)
    for l in lotes:
        seo = {"title": l["seo"][0], "description": l["seo"][1]}
        if "viejo" in l:
            p = previos[l["viejo"]]
            ok(base.gql(token, M_UPD, {"p": {"id": p["id"], "title": l["title"], "handle": l["handle"], "descriptionHtml": descripcion(l), "tags": l["tags"],
                "seo": seo, "redirectNewHandle": False}}), "productUpdate")
            pid, vid = p["id"], p["variants"]["nodes"][0]["id"]
            ok(base.gql(token, M_VAR, {"p": pid, "v": [{"id": vid, "price": l["price"]}]}), "productVariantsBulkUpdate")
        else:
            prod = ok(base.gql(token, M_CRE, {"p": {"title": l["title"], "handle": l["handle"], "status": "DRAFT", "vendor": "Casa Maravillas", "productType": "Packs Gourmet",
                "category": CATEGORY, "templateSuffix": "packs-regalo", "tags": l["tags"], "descriptionHtml": descripcion(l), "seo": seo}}), "productCreate")["product"]
            pid, vid = prod["id"], prod["variants"]["nodes"][0]["id"]
            bk["creados"][l["handle"]] = pid; save()
            ok(base.gql(token, M_VAR, {"p": pid, "v": [{"id": vid, "price": l["price"], "taxable": True, "inventoryPolicy": "DENY",
                "inventoryItem": {"sku": l["sku"], "tracked": False, "requiresShipping": True, "measurement": {"weight": {"value": l["kg"], "unit": "KILOGRAMS"}}}}]}), "productVariantsBulkUpdate")
        ok(base.gql(token, M_META, {"m": metas(pid, l, tipos)}), "metafieldsSet")
        if "gramaje" not in l and "viejo" in l:
            ok(base.gql(token, M_MDEL, {"m": [{"ownerId": pid, "namespace": "custom", "key": "gramaje"}]}), "metafieldsDelete")
        print("  hecho:", l["handle"])

    verificar(token, lotes, path)


def verificar(token, lotes, path):
    print("\nVerificación (relectura):")
    fallos = 0
    print(f"{'handle':36} {'precio':>8} {'estado':8} {'canales':>7} {'IVA':>5}  categoría / metacampos")
    for l in lotes:
        p = producto(token, l["handle"])
        v = p["variants"]["nodes"][0]
        iva = base.gql(token, M_TAX, {"i": {"lineItems": [{"variantId": v["id"], "quantity": 1}], "shippingAddress": {"countryCode": "ES", "city": "Alicante", "zip": "03001", "address1": "Calle Mayor 1", "provinceCode": "A"}}})
        r = (ok(iva, "draftOrderCalculate")["calculatedDraftOrder"]["taxLines"] or [{"ratePercentage": None}])[0]["ratePercentage"]
        mf = {m["key"]: m["value"] for m in p["metafields"]["nodes"]}
        bien = (p["status"] == "DRAFT" and not p["resourcePublicationsCount"]["count"] and abs(float(v["price"]) - float(l["price"])) < 0.001 and r == 10.0
                and p["category"] and p["category"]["id"] == CATEGORY and mf.get("gramaje") == l.get("gramaje") and sorted(p["tags"]) == sorted(l["tags"]) and p["descriptionHtml"].rstrip().endswith(NOTA_IMAGEN) and p["handle"] == l["handle"] and mf.get("allergens") == l["alerg"] and p["title"] == l["title"])
        fallos += not bien
        print(f"{p['handle']:36} {v['price']:>8} {p['status']:8} {p['resourcePublicationsCount']['count']:>7} {r if r is None else round(r):>4}%  {'OK' if bien else 'FALLO'} {mf.get('gramaje') or 'sin gramaje'}")
    print("\nTodo OK." if not fallos else f"\n{fallos} FALLO(S). Rollback: python3 -I tools/shopify_lotes_navidad_2026.py --rollback {os.path.relpath(path, os.path.join(HERE, '..'))} --apply")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
