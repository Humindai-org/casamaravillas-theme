#!/usr/bin/env python3
"""
Etiqueta "con-alcohol" en los productos que llevan vino o vermut (los packs de regalos-ibericos), para
poder excluirlos de las sugerencias (Combina tu compra, relacionados, recomendaciones de la ficha y del
carrito) mientras el IVA del 21 % de esos packs no esté resuelto (Fase 0 del plan de Navidad).

- Revisa TODOS los productos (activos, borrador y archivados), uno a uno.
- Añade solo la etiqueta (tagsAdd): no toca el resto de etiquetas ni ningún otro campo.
- Si el conjunto detectado no coincide con la lista esperada, aborta sin escribir.

Reutiliza la auth de shopify_update_precios_embutido.py (Keychain, client credentials).

Uso:
  python3 -I tools/shopify_tag_con_alcohol.py            # dry-run (solo lee)
  python3 -I tools/shopify_tag_con_alcohol.py --apply    # aplica (backup en _backup/)
  python3 -I tools/shopify_tag_con_alcohol.py --rollback _backup/tag_con_alcohol_XXXX.json --apply
"""
import importlib.util, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base

TAG = "con-alcohol"
# Resultado de la revisión producto a producto (25/10/2026): los 10 miembros de regalos-ibericos
# (9 activos + pack-iberico-cebo en BORRADOR). Ningún producto archivado lleva alcohol.
EXPECTED = {
    "pack-aperitivo", "pack-chacinas-y-quesos", "pack-dehesa-y-mar", "pack-dehesa-y-vinedo",
    "pack-esencia-iberica", "pack-iberico-bellota-100", "pack-iberico-bellota-50", "pack-iberico-campo",
    "pack-sibarita", "pack-iberico-cebo",
}
OPTION_RE = re.compile(r"vino|vermut|vermú|licor|cava", re.I)
TAG_RE = re.compile(r"^vino|vermut|vermú|alcohol", re.I)
DESC_RE = re.compile(r"\b(vinos?|vermut|vermú|vermouth)\b", re.I)

Q = """query($c:String){ products(first:50, after:$c){ pageInfo{hasNextPage endCursor} nodes{
  id handle title status tags descriptionHtml options{ name optionValues{ name } }
  variants(first:20){ nodes{ title } } } } }"""
M_ADD = """mutation($id:ID!,$t:[String!]!){ tagsAdd(id:$id, tags:$t){ userErrors{ field message } } }"""
M_REM = """mutation($id:ID!,$t:[String!]!){ tagsRemove(id:$id, tags:$t){ userErrors{ field message } } }"""


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


def fetch_all(token):
    out, cur = [], None
    while True:
        r = base.gql(token, Q, {"c": cur})["products"]
        out += r["nodes"]
        if not r["pageInfo"]["hasNextPage"]:
            return out
        cur = r["pageInfo"]["endCursor"]


def evidence(p):
    """Pruebas fuertes (opción de vino/vermut o etiqueta de vino) y débiles (solo texto de la descripción)."""
    strong, weak = [], []
    for o in p["options"]:
        names = [o["name"]] + [v["name"] for v in o["optionValues"]]
        if any(OPTION_RE.search(n) for n in names):
            strong.append(f"opción '{o['name']}': {', '.join(v['name'] for v in o['optionValues'])}")
    strong += [f"etiqueta '{t}'" for t in p["tags"] if TAG_RE.search(t)]
    if DESC_RE.search(re.sub(r"<[^>]+>", " ", p["descriptionHtml"] or "")):
        weak.append("descripción menciona vino/vermut")
    return strong, weak


def main():
    args = sys.argv[1:]
    apply = "--apply" in args
    token, scopes = base.get_token()
    print(f"Tienda: {base.SHOP} | write_products: {'write_products' in scopes.split(',')}")

    if "--rollback" in args:
        bk = json.load(open(args[args.index("--rollback") + 1]))
        todo = [p for p in bk["products"] if not p["had_tag"]]
        print(f"Rollback: quitar '{TAG}' de {len(todo)} productos (los que no la tenían antes)")
        for p in todo:
            print("  ", p["handle"])
        if not apply:
            print("(dry-run) añade --apply")
            return
        for p in todo:
            check(base.gql(token, M_REM, {"id": p["id"], "t": [TAG]}), "tagsRemove")
        print("Restaurado.")
        return

    prods = fetch_all(token)
    by_status = {s: sum(1 for p in prods if p["status"] == s) for s in ("ACTIVE", "DRAFT", "ARCHIVED")}
    print(f"\nProductos revisados: {len(prods)} {by_status}\n")
    detected, review = {}, []
    for p in sorted(prods, key=lambda p: (p["status"], p["handle"])):
        strong, weak = evidence(p)
        if strong:
            detected[p["handle"]] = (p, strong)
        elif weak:
            review.append((p, weak))

    print(f"{'producto':28} {'estado':9} {'ya tiene la etiqueta':>20}  prueba")
    for h, (p, strong) in detected.items():
        print(f"  {h:26} {p['status']:9} {str(TAG in p['tags']):>20}  {'; '.join(strong)[:120]}")
    print()
    for p, weak in review:
        print(f"  A REVISAR (solo texto, NO se etiqueta): {p['handle']} ({p['status']}): {', '.join(weak)}")
    if set(detected) != EXPECTED:
        print("\n¡El conjunto detectado no coincide con el esperado!")
        print("  Sobran :", sorted(set(detected) - EXPECTED))
        print("  Faltan :", sorted(EXPECTED - set(detected)))
        sys.exit("Abortado: revisar a mano antes de etiquetar.")
    archived = [h for h, (p, _) in detected.items() if p["status"] == "ARCHIVED"]
    print(f"\n  Coincide con la lista esperada ({len(EXPECTED)} productos). Archivados con alcohol: {archived or 'ninguno'}.")
    todo = [p for p, _ in detected.values() if TAG not in p["tags"]]
    print(f"  Se añadirá '{TAG}' a {len(todo)} productos; el resto de etiquetas no se toca.")

    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar.")
        return
    if not todo:
        print("\nNada que aplicar.")
        return
    os.makedirs(os.path.join(HERE, "..", "_backup"), exist_ok=True)
    bpath = os.path.join(HERE, "..", "_backup", f"tag_con_alcohol_{time.strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"tag": TAG, "products": [{"id": p["id"], "handle": p["handle"], "status": p["status"], "tags": p["tags"],
                                         "had_tag": TAG in p["tags"]} for p, _ in detected.values()]},
              open(bpath, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", bpath)
    for p in todo:
        check(base.gql(token, M_ADD, {"id": p["id"], "t": [TAG]}), "tagsAdd")
        print("  OK", p["handle"])
    print("\nRelectura:")
    after = {p["handle"]: p for p in fetch_all(token)}
    bad = False
    for h, (p, _) in detected.items():
        a = after[h]
        ok = TAG in a["tags"] and sorted(set(a["tags"]) - {TAG}) == sorted(set(p["tags"]) - {TAG})
        bad = bad or not ok
        print(f"  {h:28} {'OK' if ok else '¡REVISAR!'}")
    extra = [h for h, a in after.items() if TAG in a["tags"] and h not in detected]
    print("Aplicado." if not bad and not extra else f"Aplicado, pero hay diferencias: {extra}")


if __name__ == "__main__":
    main()
