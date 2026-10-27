#!/usr/bin/env python3
"""
Jamón loncheado: separa "a mano" y "a máquina" en dos productos, con título, handle y textos propios.
Las imágenes NO se tocan (el producto nuevo copia las del actual).

  --fase crear      Crea los 3 productos "a mano" como BORRADOR (no visibles en la tienda). Los actuales no se tocan.
  --fase textos     Vuelve a aplicar título/handle/textos/SEO a los 3 productos "a mano" ya creados (no cambia estado ni imágenes).
  --fase publicar   Pasa los 3 productos actuales a "a máquina" (quita la variante a mano, nuevo título/handle/textos,
                    redirección del handle antiguo) y activa los 3 "a mano". Es lo que se ve en la tienda: hazlo al publicar.

Reutiliza la auth (Keychain, client credentials) de shopify_update_ingredients.py.

Uso:
  python3 tools/shopify_loncheados_mano_maquina.py --fase crear            # dry-run
  python3 tools/shopify_loncheados_mano_maquina.py --fase crear --apply
  python3 tools/shopify_loncheados_mano_maquina.py --fase publicar         # dry-run
  python3 tools/shopify_loncheados_mano_maquina.py --fase publicar --apply
"""
import importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "shopify_update_ingredients.py"))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

MANO_VALUE, MAQ_VALUE = "Cortado a Mano · 80 g", "Cortado a Máquina · 100 g"

# Un producto por selección. 'actual' = handle del producto existente (pasará a "a máquina").
PRODUCTS = [
    {
        "actual": "jamon-cebo-de-campo-50-iberico-cortado-a-mano",
        "base": "jamon-cebo-de-campo-50-iberico-loncheado",
        "nombre": "Jamón Cebo de Campo 50% Ibérico", "corto": "Cebo de Campo 50%", "seo_core": "Jamón Cebo de Campo 50% Ibérico", "seo_short": "Jamón Cebo de Campo 50%",
        "intro": "Jamón de Cebo de Campo 50% Ibérico con precinto verde, {corte}",
        "carácter": "Criado en libertad y alimentado con piensos naturales y pastos, este jamón ofrece un sabor limpio, equilibrado y de carácter ibérico.",
        "curacion": "una curación mínima de <strong>30 meses</strong>", "curacion_seo": "+30 meses",
        "extra_bullet": None,
        "mano": {"price": "12.60", "sku": "459"}, "maq": {"price": "11.20", "sku": "465"},
    },
    {
        "actual": "jamon-bellota-50-iberico-cortado-a-mano",
        "base": "jamon-bellota-50-iberico-loncheado",
        "nombre": "Jamón Bellota 50% Ibérico", "corto": "Bellota 50%", "seo_core": "Jamón de Bellota 50% Ibérico", "seo_short": "Jamón de Bellota 50%",
        "intro": "Jamón ibérico de bellota al 50% con precinto rojo, {corte}",
        "carácter": "Cada loncha muestra el veteado de grasa infiltrada característico del ibérico de bellota.",
        "curacion": "más de <strong>36 meses de curación</strong>", "curacion_seo": "+36 meses",
        "extra_bullet": None,
        "mano": {"price": "16.00", "sku": "461"}, "maq": {"price": "15.60", "sku": "467"},
    },
    {
        "actual": "jamon-bellota-100-iberico-cortado-a-mano",
        "base": "jamon-bellota-100-iberico-loncheado",
        "nombre": "Jamón Bellota 100% Ibérico", "corto": "Bellota 100%", "seo_core": "Jamón de Bellota 100% Ibérico", "seo_short": "Jamón de Bellota 100%",
        "intro": "Jamón 100% ibérico de bellota con precinto negro, {corte}",
        "carácter": "Cada loncha muestra el veteado de grasa infiltrada característico del ibérico puro de bellota.",
        "curacion": "más de <strong>36 meses de curación</strong>", "curacion_seo": "+36 meses",
        "extra_bullet": "Cerdo 100% ibérico de bellota",
        "mano": {"price": "18.00", "sku": "463"}, "maq": {"price": "17.70", "sku": "469"},
    },
]

CORTES = {
    "mano": {
        "etq": "a Mano", "handle": "a-mano", "gramos": "80 g",
        "corte": "<strong>loncheado a mano</strong> y envasado al vacío en estuches de <strong>80 g</strong>.",
        "corte_p": "Cada estuche se corta a mano por maestros cortadores. El corte a mano mantiene los sabores originales del jamón: cada loncha permite extraer toda su textura, su grasa y su aroma.",
        "bullets": ["Loncheado a mano · estuche de 80 g", "Mantiene los sabores originales del jamón", "Loncha irregular que libera toda su textura, grasa y aroma"],
        "seo_desc": "{seo_core} loncheado a mano, estuche de 80 g. Mantiene el sabor original: toda la textura, grasa y aroma. {curacion_seo}. Envío a Europa.",
        "otro": ("a máquina", "¿Prefieres una loncha uniforme y práctica para el día a día? Descubre el <a href=\"/products/{otro_handle}\">{nombre_min} loncheado a máquina</a>."),
        "tips": ("Saca el estuche del frigorífico y déjalo atemperar 10-15 minutos antes de abrir. Sirve las lonchas directamente en el plato, "
                 "sin apilarlas demasiado: al ser irregulares, se aprecia mejor su aroma si quedan sueltas. No uses tenedor ni pinzas — el calor "
                 "de las manos ayuda a que la grasa brille. Una vez abierto, consume en el mismo día para disfrutar de toda su frescura."),
        "weight_info": "Estuche de 80 g · packs de 1 o 10 estuches",
    },
    "maq": {
        "etq": "a Máquina", "handle": "a-maquina", "gramos": "100 g",
        "corte": "<strong>loncheado a máquina</strong> y envasado al vacío en estuches de <strong>100 g</strong>.",
        "corte_p": "Cada estuche se corta a máquina: loncha uniforme y regular, práctica para tostas, bocadillos y tablas y para el día a día.",
        "bullets": ["Loncheado a máquina · estuche de 100 g", "Loncha uniforme, ideal para el día a día"],
        "seo_desc": "{seo_core} loncheado a máquina, estuche de 100 g. Loncha uniforme, ideal para el día a día. {curacion_seo} de curación. Envío a Europa.",
        "otro": ("a mano", "¿Buscas el corte más artesanal? Descubre el <a href=\"/products/{otro_handle}\">{nombre_min} loncheado a mano</a>."),
        "tips": ("Saca el estuche del frigorífico y déjalo atemperar 10-15 minutos antes de abrir. Sirve las lonchas directamente en el plato "
                 "o úsalas en tostas, bocadillos y tablas: al ser uniformes, se manejan y se combinan con facilidad. No uses tenedor ni pinzas — "
                 "el calor de las manos ayuda a que la grasa brille. Una vez abierto, consume en el mismo día para disfrutar de toda su frescura."),
        "weight_info": "Estuche de 100 g · packs de 1 o 10 estuches",
    },
}


def textos(p, kind):
    c = CORTES[kind]
    otro_kind = "maq" if kind == "mano" else "mano"
    otro_handle = f"{p['base']}-{CORTES[otro_kind]['handle']}"
    bullets = ([f"<li>{p['extra_bullet']}</li>"] if p["extra_bullet"] else []) + \
              [f"<li>{b}</li>" for b in c["bullets"]] + ["<li>Envasado al vacío, listo para servir o regalar</li>"]
    html = (f"<p>{p['intro'].format(corte=c['corte'])} {p['carácter']}</p>"
            f"<p>{c['corte_p']} Con {p['curacion']}.</p>"
            f"<ul>{''.join(bullets)}</ul>"
            f"<p>{c['otro'][1].format(otro_handle=otro_handle, nombre_min=p['nombre'].replace('Jamón ', 'jamón '))}</p>")
    return {
        "title": f"{p['nombre']} — Loncheado {c['etq']}",
        "handle": f"{p['base']}-{c['handle']}",
        "html": html,
        "seo_title": f"{p['seo_short']} Loncheado {c['etq']} | Casa Maravillas",
        "seo_desc": c["seo_desc"].format(seo_core=p["seo_core"], curacion_seo=p["curacion_seo"]),
        "tips": c["tips"], "weight_info": c["weight_info"],
    }


Q_FULL = """query($h:String!){ productByHandle(handle:$h){ id title handle status tags templateSuffix
  options{ id name } variants(first:5){ nodes{ id title sku price selectedOptions{ name value } } }
  metafields(first:60){ nodes{ namespace key type value } }
  resourcePublications(first:10){ nodes{ publication{ id } isPublished } } } }"""
M_DUP = """mutation($id:ID!,$t:String!){ productDuplicate(productId:$id, newTitle:$t, newStatus:DRAFT, includeImages:true){
  newProduct{ id handle } userErrors{ field message } } }"""
M_UPD = """mutation($i:ProductUpdateInput!){ productUpdate(product:$i){ product{ id handle } userErrors{ field message } } }"""
M_VDEL = """mutation($p:ID!,$v:[ID!]!){ productVariantsBulkDelete(productId:$p, variantsIds:$v){ userErrors{ field message } } }"""
M_ODEL = """mutation($p:ID!,$o:[ID!]!){ productOptionsDelete(productId:$p, options:$o){ userErrors{ field message } } }"""
M_VUPD = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){ userErrors{ field message } } }"""
M_MF = """mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }"""
M_PUB = """mutation($id:ID!,$i:[PublicationInput!]!){ publishablePublish(id:$id, input:$i){ userErrors{ field message } } }"""


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def to_single_variant(token, pid, drop_value, keep_price, keep_sku):
    """Deja el producto con una sola variante (quita la opción Corte): borra la variante 'drop_value' y la opción."""
    q = base.gql(token, """query($id:ID!){ product(id:$id){ options{ id name } variants(first:5){ nodes{ id selectedOptions{ name value } } } } }""", {"id": pid})["product"]
    drop = [v["id"] for v in q["variants"]["nodes"] if v["selectedOptions"][0]["value"] == drop_value]
    keep = [v["id"] for v in q["variants"]["nodes"] if v["selectedOptions"][0]["value"] != drop_value]
    if len(drop) != 1 or len(keep) != 1:
        sys.exit(f"Variantes inesperadas en {pid}: quitar {drop}, conservar {keep}")
    check(base.gql(token, M_VDEL, {"p": pid, "v": drop}), "productVariantsBulkDelete")
    check(base.gql(token, M_ODEL, {"p": pid, "o": [o["id"] for o in q["options"] if o["name"] == "Corte"]}), "productOptionsDelete")
    q2 = base.gql(token, """query($id:ID!){ product(id:$id){ variants(first:5){ nodes{ id } } } }""", {"id": pid})["product"]
    check(base.gql(token, M_VUPD, {"p": pid, "v": [{"id": q2["variants"]["nodes"][0]["id"], "price": keep_price,
          "inventoryItem": {"sku": keep_sku}}]}), "productVariantsBulkUpdate")


def apply_texts(token, pid, t, tags=None, redirect=False, status=None):
    inp = {"id": pid, "title": t["title"], "handle": t["handle"], "descriptionHtml": t["html"],
           "seo": {"title": t["seo_title"], "description": t["seo_desc"]}, "templateSuffix": "jamones"}
    if redirect:
        inp["redirectNewHandle"] = True
    if tags is not None:
        inp["tags"] = tags
    if status:
        inp["status"] = status
    check(base.gql(token, M_UPD, {"i": inp}), "productUpdate")
    check(base.gql(token, M_MF, {"m": [
        {"ownerId": pid, "namespace": "custom", "key": "cutting_tips", "type": "multi_line_text_field", "value": t["tips"]},
        {"ownerId": pid, "namespace": "custom", "key": "weight_info", "type": "single_line_text_field", "value": t["weight_info"]}]}), "metafieldsSet")


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    fase = args[args.index("--fase") + 1] if "--fase" in args else None
    if fase not in ("crear", "publicar", "textos"):
        sys.exit("Indica --fase crear | publicar | textos")
    token, _ = base.get_token()

    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    print(f"== FASE {fase.upper()} ==")
    plan = []
    for p in PRODUCTS:
        src = base.gql(token, Q_FULL, {"h": p["actual"]})["productByHandle"]
        if not src:
            sys.exit(f"No existe {p['actual']}")
        tm, tq = textos(p, "mano"), textos(p, "maq")
        plan.append((p, src, tm, tq))
        print(f"\n  {p['nombre']}")
        print(f"    A MANO    : {tm['title']}  /products/{tm['handle']}   {p['mano']['price']} €  sku {p['mano']['sku']}")
        print(f"                SEO: {tm['seo_title']}\n                META: {tm['seo_desc']}")
        print(f"    A MÁQUINA : {tq['title']}  /products/{tq['handle']}   {p['maq']['price']} €  sku {p['maq']['sku']}"
              + ("   (hoy: " + src["handle"] + ")" if fase == "publicar" else ""))
    if not apply:
        print("\nTextos completos de la primera ficha:")
        p, src, tm, tq = plan[0]
        for k, t in (("A MANO", tm), ("A MÁQUINA", tq)):
            print(f"\n--- {k} · descripción ---\n{t['html']}\n--- cutting_tips ---\n{t['tips']}\n--- weight_info ---\n{t['weight_info']}")
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return

    bk = os.path.join(HERE, "..", "_backup", f"loncheados_split_{fase}_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump([s for _, s, _, _ in plan], open(bk, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bk)

    for p, src, tm, tq in plan:
        if fase == "textos":
            nuevo = base.gql(token, Q_FULL, {"h": tm["handle"]})["productByHandle"]
            if not nuevo:
                sys.exit(f"No existe {tm['handle']}: ejecuta antes --fase crear")
            apply_texts(token, nuevo["id"], tm)
            print("  OK textos actualizados:", tm["handle"], f"(estado: {nuevo['status']})")
        elif fase == "crear":
            r = base.gql(token, M_DUP, {"id": src["id"], "t": tm["title"]})["productDuplicate"]
            if r["userErrors"]:
                sys.exit(f"ERROR en productDuplicate: {r['userErrors']}")
            nid = r["newProduct"]["id"]
            to_single_variant(token, nid, MAQ_VALUE, p["mano"]["price"], p["mano"]["sku"])
            apply_texts(token, nid, tm, tags=src["tags"])
            # copia los metacampos del actual (productDuplicate puede no copiarlos); los textos propios ya están puestos
            own = {"cutting_tips", "weight_info"}
            mf = [{"ownerId": nid, "namespace": m["namespace"], "key": m["key"], "type": m["type"], "value": m["value"]}
                  for m in src["metafields"]["nodes"]
                  if not (m["namespace"] == "custom" and m["key"] in own) and m["namespace"] != "global"]
            for i in range(0, len(mf), 25):
                check(base.gql(token, M_MF, {"m": mf[i:i + 25]}), "metafieldsSet")
            print("  OK borrador creado:", tm["handle"])
        else:
            # 1) el producto actual pasa a "a máquina"
            to_single_variant(token, src["id"], MANO_VALUE, p["maq"]["price"], p["maq"]["sku"])
            tags = [("cortado a máquina" if t == "cortado a mano" else t) for t in src["tags"]]
            apply_texts(token, src["id"], tq, tags=tags, redirect=True)
            # 2) se activa y publica el nuevo "a mano" (creado en la fase 'crear')
            nuevo = base.gql(token, Q_FULL, {"h": tm["handle"]})["productByHandle"]
            if not nuevo:
                sys.exit(f"Falta el borrador {tm['handle']}: ejecuta antes --fase crear")
            check(base.gql(token, M_UPD, {"i": {"id": nuevo["id"], "status": "ACTIVE"}}), "productUpdate")
            pubs = [{"publicationId": x["publication"]["id"]} for x in src["resourcePublications"]["nodes"] if x["isPublished"]]
            if pubs:
                check(base.gql(token, M_PUB, {"id": nuevo["id"], "i": pubs}), "publishablePublish")
            print("  OK publicado:", tm["handle"], "| actual ->", tq["handle"])
    print("Aplicado.")


if __name__ == "__main__":
    main()
