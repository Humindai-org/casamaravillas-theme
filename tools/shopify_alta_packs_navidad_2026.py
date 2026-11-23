#!/usr/bin/env python3
"""
Alta (22/11/2026) de los 3 packs de Navidad SIN vino ni alcohol, en BORRADOR, y de la página «navidad» sin publicar.
Contenido: comentario del 14/11 de la tarea ClickUp 123m57f4d84 (hoja de tarifa de Luis Juan, quitando el vino).
Ingredientes de los sobres: los metacampos custom.ingredients de los propios productos loncheados de la tienda.
Ingredientes/alérgenos del turrón: planning/fichas-tecnicas/2026-11-17-whatsapp-luis-juan/ (duro y blando; NO hay ficha del
«turrón a la piedra» de Plata y Oro). Queso: el comentario del 14/11 (leído de la foto del estuche, sin verificar con el original).

Como los packs con vino (pack-iberico-*): tipo «Packs Gourmet», categoría Food Gift Baskets (IVA 10 %, la colección
regalos-ibericos es inteligente por esa categoría y los recoge sola), plantilla packs-regalo, perfil de envío por defecto
(«General profile», que tiene la zona Peninsula). Sin etiqueta con-alcohol: la página navidad lista regalos-ibericos
excluyendo esa etiqueta.

Uso:  python3 -I tools/shopify_alta_packs_navidad_2026.py            # dry-run (solo lee)
      python3 -I tools/shopify_alta_packs_navidad_2026.py --apply    # crea (ledger en _backup/)
      python3 -I tools/shopify_alta_packs_navidad_2026.py --rollback _backup/packs_navidad_XXXX.json --apply   # borra lo creado
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base
BK = os.path.join(HERE, "..", "_backup")

CATEGORY = "gid://shopify/TaxonomyCategory/fb-2-8"   # Food Gift Baskets (la misma de los packs con vino)
WEIGHT_KG = 1.5       # peso de ENVÍO estimado: cualquier valor < 5 kg da la misma tarifa (tramo «hasta 5 kg»)
GRAMAJE = "980 g"     # DERIVADO: 80+100+100+100 (sobres, como en los packs antiguos) + 2×200 (quesos) + 200 (turrón)

# Ingredientes literales de los metacampos custom.ingredients de los productos loncheados de la tienda
ING = {
    "jamon_cebo": "Jamón de cebo campo ibérico, sal común, azúcar, corrector de acidez (E-331iii), conservadores (E-252, E-250), antioxidante (E-301).",
    "jamon_b50": "Jamón de bellota ibérico, sal común, azúcar, corrector de acidez (E-331iii), conservadores (E-252, E-250), antioxidante (E-301).",
    "jamon_b100": "Jamón de bellota 100% ibérico, sal común, azúcar, corrector de acidez (E-331iii), conservadores (E-252, E-250), antioxidante (E-301).",
    "lomo_cebo": "Lomo de cebo campo ibérico, sal, azúcar, antioxidante (E-301), conservadores (E-252, E-250), corrector de acidez (E-331iii), pimentón, ajo y orégano.",
    "lomo_b100": "Lomo de bellota 100% ibérico, sal, azúcar, antioxidante (E-301), conservadores (E-252, E-250), corrector de acidez (E-331iii), pimentón, ajo y orégano.",
    "lomito": "Presa de bellota ibérico, sal, azúcar, antioxidante (E-301), conservadores (E-252, E-250), corrector de acidez (E-331iii), pimentón, ajo y orégano.",
    "chorizo": "Magro y tocino de bellota ibérico, sal, pimentón, dextrina, proteína de cerdo, dextrosa, antioxidante (E-316), conservadores (E-250, E-252), ajo y orégano.",
    "salchichon": "Magro y tocino de bellota ibérico, sal, almidón, especias, dextrosa, corrector de acidez (E-331), conservadores (E-252, E-250), proteína de cerdo, dextrina y ajo.",
    # Comentario 14/11 (foto del estuche; verificar con el original). Colorante de la corteza del Vecchio: fotos que no coinciden -> no se declara.
    "anejo": "Leche cruda de oveja, sal, cuajo, fermentos lácticos, estabilizante E-509, conservador E-252 y lisozima (derivado del huevo). Corteza: conservadores E-235 y E-202 y colorante E-172.",
    "vecchio": "Leche pasteurizada de oveja, sal, cuajo, fermentos lácticos, estabilizante E-509. Puede contener trazas de huevo. Corteza: conservadores E-235 y E-202.",
    # Fichas técnicas del fabricante (Turrones de Alicante S.A., Villajoyosa), 29/02/2024
    "turron_duro": "Almendra tostada (60 %), azúcar, miel, jarabe de glucosa, clara de huevo y oblea de recubrimiento (fécula de patata y aceite vegetal de girasol). Puede contener trazas de otros frutos de cáscara.",
    "turron_blando": "Almendra tostada (64 %), azúcar, miel, clara de huevo y emulgente: E-471. Puede contener trazas de otros frutos de cáscara.",
}
ING["turron_piedra"] = "PENDIENTE de la ficha técnica del fabricante (no hay ficha del turrón a la piedra)."
ALERG_QUESO = "leche y huevo (quesos). Alérgenos del turrón a la piedra: PENDIENTES de la ficha técnica"
PACKS = [
    {"handle": "seleccion-bronce", "title": "Selección Bronce (Cebo de Campo)", "price": "46.90", "sku": "516",
     "tags": ["cebo-de-campo", "embutido-iberico", "jamon-iberico", "pack-gourmet", "queso", "regalo", "navidad"],
     "nivel": "Cebo de Campo 50 % Ibérico",
     "items": ["1 sobre de jamón Cebo de Campo 50 % Ibérico", "1 sobre de lomo de Cebo de Campo Ibérico 50 %",
               "1 sobre de chorizo de bellota ibérico", "1 sobre de salchichón de bellota ibérico",
               "2 cuñas de queso de oveja (Añejo y Vecchio, Manzer), 2 × 200 g", "1 turrón de almendra, duro o blando (200 g)"],
     "ing": [("Sobre de jamón", "jamon_cebo"), ("Sobre de lomo de cebo de campo", "lomo_cebo"), ("Sobre de chorizo", "chorizo"),
             ("Sobre de salchichón", "salchichon"), ("Queso Añejo", "anejo"), ("Queso Vecchio", "vecchio"),
             ("Turrón duro", "turron_duro"), ("Turrón blando", "turron_blando")],
     "alerg": "Contiene: leche y huevo (quesos); huevo y frutos de cáscara: almendra (turrón). Puede contener trazas de otros frutos de cáscara (turrón).",
     "seo": ("Selección Bronce: pack de Navidad ibérico de cebo de campo | Casa Maravillas",
             "Pack de Navidad con sobres de jamón y embutidos ibéricos de cebo de campo, dos quesos de oveja y turrón de almendra."),
     "extra_tags": []},
    {"handle": "seleccion-plata", "title": "Selección Plata (Bellota 50 %)", "price": "56.90", "sku": "517",
     "tags": ["bellota", "bellota-50", "embutido-iberico", "jamon-iberico", "pack-gourmet", "queso", "regalo", "navidad"],
     "nivel": "Bellota 50 % Ibérico",
     "items": ["1 sobre de jamón Bellota 50 % Ibérico", "1 sobre de lomo de bellota 100 % ibérico",
               "1 sobre de chorizo de bellota ibérico", "1 sobre de salchichón de bellota ibérico",
               "2 cuñas de queso de oveja (Añejo y Vecchio, Manzer), 2 × 200 g", "1 turrón a la piedra"],
     "ing": [("Sobre de jamón", "jamon_b50"), ("Sobre de lomo de bellota", "lomo_b100"), ("Sobre de chorizo", "chorizo"),
             ("Sobre de salchichón", "salchichon"), ("Queso Añejo", "anejo"), ("Queso Vecchio", "vecchio"),
             ("Turrón a la piedra", "turron_piedra")],
     "alerg": "Contiene: " + ALERG_QUESO + ".",
     "seo": ("Selección Plata: pack de Navidad ibérico de bellota 50 % | Casa Maravillas",
             "Pack de Navidad con sobres de jamón y embutidos ibéricos de bellota, dos quesos de oveja y turrón a la piedra."),
     "extra_tags": ["pendiente-ficha-turron"]},
    {"handle": "seleccion-oro", "title": "Selección Oro (Bellota 100 %)", "price": "66.90", "sku": "518",
     "tags": ["bellota", "bellota-100", "embutido-iberico", "jamon-iberico", "pack-gourmet", "queso", "regalo", "navidad"],
     "nivel": "Bellota 100 % Ibérico",
     "items": ["1 sobre de jamón Bellota 100 % Ibérico", "1 sobre de lomito de presa de bellota ibérico",
               "1 sobre de chorizo de bellota ibérico", "1 sobre de salchichón de bellota ibérico",
               "2 cuñas de queso de oveja (Añejo y Vecchio, Manzer), 2 × 200 g", "1 turrón a la piedra"],
     "ing": [("Sobre de jamón", "jamon_b100"), ("Sobre de lomito de presa", "lomito"), ("Sobre de chorizo", "chorizo"),
             ("Sobre de salchichón", "salchichon"), ("Queso Añejo", "anejo"), ("Queso Vecchio", "vecchio"),
             ("Turrón a la piedra", "turron_piedra")],
     "alerg": "Contiene: " + ALERG_QUESO + ".",
     "seo": ("Selección Oro: pack de Navidad ibérico de bellota 100 % | Casa Maravillas",
             "Pack de Navidad con sobres de jamón y embutidos ibéricos 100 % de bellota, dos quesos de oveja y turrón a la piedra."),
     "extra_tags": ["pendiente-ficha-turron"]},
]
PAGE = {"title": "Navidad 2026", "handle": "navidad", "templateSuffix": "navidad", "isPublished": False, "body": ""}

M_PROD = """mutation($p:ProductCreateInput!){ productCreate(product:$p){ product{ id handle status variants(first:3){ nodes{ id } } } userErrors{ field message } } }"""
M_VAR = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){ productVariants{ id sku price } userErrors{ field message } } }"""
M_META = """mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ metafields{ key } userErrors{ field message } } }"""
M_PAGE = """mutation($p:PageCreateInput!){ pageCreate(page:$p){ page{ id handle isPublished templateSuffix } userErrors{ field message } } }"""
M_DEL_P = "mutation($i:ProductDeleteInput!){ productDelete(input:$i){ deletedProductId userErrors{ field message } } }"
M_DEL_PAGE = "mutation($id:ID!){ pageDelete(id:$id){ deletedPageId userErrors{ field message } } }"
Q_EXIST = """query($q:String){ products(first:5, query:$q){ nodes{ handle } } pages(first:5, query:$q){ nodes{ handle } } }"""
Q_DEFS = """{ metafieldDefinitions(first:10, ownerType:PRODUCT, namespace:"custom", key:"%s"){ nodes{ key type{ name } } } }"""


def ok(res, key):
    e = res[key].get("userErrors") or []
    if e:
        sys.exit(f"ERROR en {key}: {e}")
    return res[key]


def description(p):
    li = "\n".join(f"<li>{i}</li>" for i in p["items"])
    ing = "\n".join(f"<li><strong>{n}:</strong> {ING[k]}</li>" for n, k in p["ing"])
    return (f"<p>Pack de Navidad de la gama {p['nivel']}: sobres loncheados de jamón y embutidos ibéricos, dos quesos de oveja y turrón.</p>\n"
            f"<p><strong>Incluye:</strong></p>\n<ul>\n{li}\n</ul>\n"
            f"<p><strong>Ingredientes:</strong></p>\n<ul>\n{ing}\n</ul>\n"
            f"<p><strong>Alérgenos:</strong> {p['alerg'].replace('Contiene: ', '')}</p>")


def main():
    a = sys.argv[1:]
    apply = "--apply" in a
    token, scopes = base.get_token()
    sc = scopes.split(",")
    print(f"Tienda: {base.SHOP} | write_products: {'write_products' in sc} | write_content: {'write_content' in sc} | {'APPLY' if apply else 'dry-run'}\n")

    if "--rollback" in a:
        led = json.load(open(a[a.index("--rollback") + 1]))
        for pid in led.get("productos", {}).values():
            print("  borrar producto", pid)
            if apply:
                ok(base.gql(token, M_DEL_P, {"i": {"id": pid}}), "productDelete")
        if led.get("pagina"):
            print("  borrar página", led["pagina"])
            if apply:
                ok(base.gql(token, M_DEL_PAGE, {"id": led["pagina"]}), "pageDelete")
        print("Borrado." if apply else "(dry-run) añade --apply")
        return

    ml = {}
    for k in ("allergens", "gramaje"):      # custom.ingredients está restringido por categoría: no admite Food Gift Baskets
        d = base.gql(token, Q_DEFS % k)["metafieldDefinitions"]["nodes"]
        ml[k] = d[0]["type"]["name"] if d else None
    print("Tipos de metacampo:", ml)
    if not all(ml.values()):
        sys.exit("Falta la definición de algún metacampo (custom.ingredients / allergens / gramaje). Abortado.")
    for p in PACKS:
        if base.gql(token, Q_EXIST, {"q": f"handle:{p['handle']}"})["products"]["nodes"]:
            sys.exit(f"Ya existe un producto con handle {p['handle']}")
    if base.gql(token, Q_EXIST, {"q": "handle:navidad"})["pages"]["nodes"]:
        sys.exit("Ya existe la página navidad")

    for p in PACKS:
        print(f"== {p['handle']}: {p['title']} · {p['price']} € · SKU {p['sku']} · {WEIGHT_KG} kg · gramaje {GRAMAJE} · tags {p['tags'] + p['extra_tags']}")
        print("   incluye:", " | ".join(p["items"]))
        print("   alérgenos:", p["alerg"])
    print(f"== página: {PAGE}")
    if not apply:
        print("\n(dry-run) No se ha creado nada.")
        return

    led = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "productos": {}, "pagina": None}
    os.makedirs(BK, exist_ok=True)
    path = os.path.abspath(os.path.join(BK, f"packs_navidad_{time.strftime('%Y%m%d-%H%M%S')}.json"))
    save = lambda: json.dump(led, open(path, "w"), ensure_ascii=False, indent=1)
    save(); print("Ledger:", path)
    for p in PACKS:
        prod = ok(base.gql(token, M_PROD, {"p": {
            "title": p["title"], "handle": p["handle"], "status": "DRAFT", "vendor": "Casa Maravillas", "productType": "Packs Gourmet",
            "category": CATEGORY, "templateSuffix": "packs-regalo", "tags": p["tags"] + p["extra_tags"],
            "descriptionHtml": description(p), "seo": {"title": p["seo"][0], "description": p["seo"][1]}}}), "productCreate")["product"]
        led["productos"][p["handle"]] = prod["id"]; save()
        vid = prod["variants"]["nodes"][0]["id"]
        ok(base.gql(token, M_VAR, {"p": prod["id"], "v": [{"id": vid, "price": p["price"], "taxable": True, "inventoryPolicy": "DENY",
            "inventoryItem": {"sku": p["sku"], "tracked": False, "requiresShipping": True,
                              "measurement": {"weight": {"value": WEIGHT_KG, "unit": "KILOGRAMS"}}}}]}), "productVariantsBulkUpdate")
        metas = [{"ownerId": prod["id"], "namespace": "custom", "key": "gramaje", "type": ml["gramaje"], "value": GRAMAJE},
                 {"ownerId": prod["id"], "namespace": "custom", "key": "allergens", "type": ml["allergens"], "value": p["alerg"]}]
        ok(base.gql(token, M_META, {"m": metas}), "metafieldsSet")
        print("  creado", p["handle"], prod["id"].split("/")[-1])
    pg = ok(base.gql(token, M_PAGE, {"p": PAGE}), "pageCreate")["page"]
    led["pagina"] = pg["id"]; save()
    print("  página creada", pg["id"].split("/")[-1], pg["handle"], "publicada:", pg["isPublished"], "plantilla:", pg["templateSuffix"])
    print("Rollback: python3 -I tools/shopify_alta_packs_navidad_2026.py --rollback", os.path.relpath(path, os.path.join(HERE, "..")), "--apply")


if __name__ == "__main__":
    main()
