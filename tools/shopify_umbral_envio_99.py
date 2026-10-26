#!/usr/bin/env python3
"""
Umbral de envío gratis: de 80 € a 99 €.

Dos fases, en este orden (así la tienda nunca promete 99 € mientras regala el envío desde 80 € al revés):
  a) TODO lo que anuncia el umbral: archivos del tema (sobre la versión PUBLICADA), política de envíos de
     Shopify y traducciones EN/FR de los textos del tema.
  c) Descuento automático "Envío gratis desde 80 €": mínimo 99 € y título "Envío gratis desde 99 €".
Entre a) y c) se comprueba la tienda publicada (tools/probar_envio_gratis.py --umbral 99 --ficha y navegador).

NO toca templates/collection.packs-regalo.json ("Desde €80" es el tramo de precio de un pack, no el envío)
ni lo que cae fuera de Shopify (Forms, Merchant Center, Meta, TikTok).

Uso:
  python3 -I tools/shopify_umbral_envio_99.py --fase a                 # dry-run de la fase a (solo lee)
  python3 -I tools/shopify_umbral_envio_99.py --fase a --apply         # aplica la fase a (backup en _backup/)
  python3 -I tools/shopify_umbral_envio_99.py --fase t [--apply]       # solo las traducciones (reanudar la fase a)
  python3 -I tools/shopify_umbral_envio_99.py --fase c                 # dry-run del descuento
  python3 -I tools/shopify_umbral_envio_99.py --fase c --apply
  python3 -I tools/shopify_umbral_envio_99.py --fase a --rollback _backup/umbral_a_XXXX --apply
  python3 -I tools/shopify_umbral_envio_99.py --fase c --rollback _backup/umbral_c_XXXX.json --apply
"""
import importlib.util, json, os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base

STORE, LIVE_ID = "jbtugu-s0.myshopify.com", "199321256274"
OLD, NEW = "80", "99"
SP = r"(?:\s|&nbsp;| )?"
# Formas del umbral: "80 €", "80&euro;", "€80", "8000" (céntimos)
RE_NUM_EUR = re.compile(r"(?<![\d.,])80(?=(?:[.,]00)?" + SP + r"(?:€|&euro;|eur\b|euros?))", re.I)
RE_EUR_NUM = re.compile(r"(€" + SP + r")80(?![\d.,])")
RE_CENTS = re.compile(r"(?<![\d.,])8000(?![\d])")
ANY = re.compile(RE_NUM_EUR.pattern + "|" + RE_EUR_NUM.pattern + "|" + RE_CENTS.pattern, re.I)

# archivo -> nº de sustituciones esperado (si no cuadra, aborta)
THEME_FILES = {
    "snippets/free-shipping-bar.liquid": 2, "snippets/json-ld-product.liquid": 2,
    "sections/envios-content.liquid": 2, "sections/announcement-bar.liquid": 1, "sections/header-group.json": 1,
    "sections/policy-body.liquid": 1, "sections/cart-checkout.liquid": 2,
    "sections/trust-band.liquid": 2, "sections/trust-band-embutidos.liquid": 2,
    "templates/index.json": 1, "templates/product.embutidos.json": 1, "templates/product.jamones.json": 1,
    "templates/product.json": 1, "templates/product.packs-regalo.json": 1,
}
SKIP_TRANSLATION_KEYS = ("cat2_label",)        # "Desde €80" del pack Selección: no es el envío
TRANSLATION_TYPES = ("ONLINE_STORE_THEME_JSON_TEMPLATE", "ONLINE_STORE_THEME_SECTION_GROUP")
LOCALES = ("en", "fr")
DISCOUNT_TITLE_OLD, DISCOUNT_TITLE_NEW = "Envío gratis desde 80 €", "Envío gratis desde 99 €"


def swap(text):
    out = RE_NUM_EUR.sub(NEW, text)
    out = RE_EUR_NUM.sub(lambda m: m.group(1) + NEW, out)
    return RE_CENTS.sub("9900", out)


def run(cmd, timeout=280):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        sys.exit(f"ERROR en {' '.join(cmd[:4])}…: {(r.stdout + r.stderr)[-400:]}")
    return r.stdout


def pull_live(dest, files=None):
    cmd = ["shopify", "theme", "pull", "--store", STORE, "--theme", LIVE_ID, "--path", dest, "--force", "--no-color"]
    for f in files or []:
        cmd += ["--only", f]
    run(cmd)


def push_live(src, files):
    cmd = ["shopify", "theme", "push", "--store", STORE, "--theme", LIVE_ID, "--allow-live", "--nodelete", "--path", src, "--no-color"]
    for f in files:
        cmd += ["--only", f]
    run(cmd)


def check(res, key):
    errs = res[key]["userErrors"]
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")


# ───────────────────────── fase a: tema ─────────────────────────
def plan_theme(root):
    plan = {}
    for f, expected in THEME_FILES.items():
        text = open(os.path.join(root, f), encoding="utf-8").read()
        n = len(ANY.findall(text))
        if n != expected:
            sys.exit(f"{f}: {n} menciones del umbral y se esperaban {expected}. Abortado.")
        plan[f] = (text, swap(text))
    return plan


def show_theme(plan):
    print("== A1. TEMA (sobre la versión publicada)")
    total = 0
    for f, (old, new) in plan.items():
        for a, b in zip(old.split("\n"), new.split("\n")):
            if a != b:
                total += 1
                print(f"  {f}\n     - {a.strip()[:130]}\n     + {b.strip()[:130]}")
    print(f"  → {total} líneas en {len(plan)} archivos. templates/collection.packs-regalo.json NO se toca.")


# ───────────────────────── fase a: política ─────────────────────────
Q_POL = "{ shop{ shopPolicies{ type title body } } }"
M_POL = "mutation($p:ShopPolicyInput!){ shopPolicyUpdate(shopPolicy:$p){ userErrors{ field message } } }"


def get_policy(token):
    pol = next(p for p in base.gql(token, Q_POL)["shop"]["shopPolicies"] if p["type"] == "SHIPPING_POLICY")
    return pol["body"]


def show_policy(body):
    n = len(ANY.findall(body))
    if n != 1:
        sys.exit(f"Política de envíos: {n} menciones del umbral y se esperaba 1. Abortado.")
    m = ANY.search(body)
    ctx = lambda t: re.sub(r"\s+", " ", t[max(0, m.start() - 60): m.end() + 40])
    print("\n== A2. POLÍTICA DE ENVÍOS (Configuración → Políticas)")
    print(f"     - …{ctx(body)}…\n     + …{ctx(swap(body))}…")


# ───────────────────────── fase a: traducciones ─────────────────────────
Q_TRANS = """query($t:TranslatableResourceType!,$c:String){ translatableResources(first:40, after:$c, resourceType:$t){
  pageInfo{hasNextPage endCursor} nodes{ resourceId translatableContent{ key value digest }
  en: translations(locale:"en"){ key value } fr: translations(locale:"fr"){ key value } } } }"""
M_TRANS = """mutation($id:ID!,$t:[TranslationInput!]!){ translationsRegister(resourceId:$id, translations:$t){ userErrors{ field message } } }"""


def scan_resources(token):
    """Nodos de las plantillas JSON y grupos de secciones, con sus textos y traducciones."""
    nodes = []
    for t in TRANSLATION_TYPES:
        cur = None
        while True:
            r = base.gql(token, Q_TRANS, {"t": t, "c": cur})["translatableResources"]
            nodes += r["nodes"]
            if not r["pageInfo"]["hasNextPage"]:
                break
            cur = r["pageInfo"]["endCursor"]
    return nodes


def owners_of(nodes):
    """clave -> (resourceId propietario, digest actual). Una traducción solo se puede registrar en el recurso
    cuyo texto traducible lleva esa clave; el mismo recurso puede LISTAR traducciones de otras plantillas."""
    return {c["key"]: (n["resourceId"], c["digest"]) for n in nodes for c in n["translatableContent"]}


def collect_translations(token):
    """[(resourceId propietario, locale, key, valor actual)] con el umbral, salvo las claves excluidas."""
    nodes = scan_resources(token)
    owners = owners_of(nodes)
    seen, out = set(), []
    for node in nodes:
        for loc in LOCALES:
            for tr in node[loc]:
                if not ANY.search(tr["value"] or "") or any(x in tr["key"] for x in SKIP_TRANSLATION_KEYS):
                    continue
                if (loc, tr["key"]) in seen:
                    continue
                seen.add((loc, tr["key"]))
                if tr["key"] not in owners:
                    print(f"  (aviso) traducción huérfana, sin texto de origen: [{loc}] {tr['key'][:70]}")
                    continue
                out.append((owners[tr["key"]][0], loc, tr["key"], tr["value"]))
    return out


def show_translations(items):
    print(f"\n== A3. TRADUCCIONES EN/FR ({len(items)} valores)")
    seen = set()
    for rid, loc, key, val in items:
        k = (loc, swap(val))
        if k in seen:
            continue
        seen.add(k)
        print(f"  [{loc}] {key.split(':')[0][:78]}\n       - {re.sub(chr(10), ' ', val)[:110]}\n       + {re.sub(chr(10), ' ', swap(val))[:110]}")
    print(f"  ({len(items)} claves en total; solo se muestran los textos distintos)")


def _register(token, items, transform):
    owners = owners_of(scan_resources(token))          # digests ACTUALES (tras cambiar el origen en el tema)
    by_res = {}
    for _rid, loc, key, val in items:
        if key not in owners:
            print(f"  (aviso) sin texto de origen, se omite: [{loc}] {key[:70]}")
            continue
        by_res.setdefault(owners[key][0], []).append({"locale": loc, "key": key, "value": transform(val),
                                                      "translatableContentDigest": owners[key][1]})
    for rid, payload in by_res.items():
        check(base.gql(token, M_TRANS, {"id": rid, "t": payload}), "translationsRegister")


def register_translations(token, items):
    _register(token, items, swap)


def restore_translations(token, items):
    _register(token, items, lambda v: v)


def fase_a(token, apply, rollback):
    if rollback:
        bk = rollback
        print(f"Rollback de la fase a desde {bk}")
        meta = json.load(open(os.path.join(bk, "estado.json")))
        print(f"  tema: {len(THEME_FILES)} archivos | política | {len(meta['translations'])} traducciones")
        if not apply:
            print("(dry-run) añade --apply")
            return
        tmp = tempfile.mkdtemp(); pull_live(tmp)
        for f in THEME_FILES:
            shutil.copy(os.path.join(bk, "tema", f), os.path.join(tmp, f))
        push_live(tmp, list(THEME_FILES)); shutil.rmtree(tmp)
        check(base.gql(token, M_POL, {"p": {"type": "SHIPPING_POLICY", "body": meta["policy"]}}), "shopPolicyUpdate")
        restore_translations(token, [tuple(x) for x in meta["translations"]])
        print("Restaurado.")
        return

    tmp = tempfile.mkdtemp()
    pull_live(tmp, list(THEME_FILES))
    plan = plan_theme(tmp)
    body = get_policy(token)
    items = collect_translations(token)
    show_theme(plan); show_policy(body); show_translations(items)
    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar la fase a.")
        shutil.rmtree(tmp); return

    bk = os.path.join(HERE, "..", "_backup", f"umbral_a_{time.strftime('%Y%m%d-%H%M%S')}")
    for f, (old, _) in plan.items():
        os.makedirs(os.path.dirname(os.path.join(bk, "tema", f)), exist_ok=True)
        open(os.path.join(bk, "tema", f), "w", encoding="utf-8").write(old)
    json.dump({"policy": body, "translations": items}, open(os.path.join(bk, "estado.json"), "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", os.path.abspath(bk))
    for f, (_, new) in plan.items():
        open(os.path.join(tmp, f), "w", encoding="utf-8").write(new)
    push_live(tmp, list(THEME_FILES)); shutil.rmtree(tmp)
    print("  OK tema (14 archivos)")
    check(base.gql(token, M_POL, {"p": {"type": "SHIPPING_POLICY", "body": swap(body)}}), "shopPolicyUpdate")
    print("  OK política de envíos")
    register_translations(token, items)
    print(f"  OK {len(items)} traducciones EN/FR")

    print("\nRelectura:")
    tmp = tempfile.mkdtemp(); pull_live(tmp, list(THEME_FILES))
    left = [f for f in THEME_FILES if ANY.search(open(os.path.join(tmp, f), encoding="utf-8").read())]
    shutil.rmtree(tmp)
    print(f"  tema: archivos que aún dicen 80 €: {left or 'ninguno'}")
    print(f"  política: menciones de 80 € que quedan: {len(ANY.findall(get_policy(token)))}")
    rest = collect_translations(token)
    print(f"  traducciones EN/FR con 80 €: {len(rest)}")
    print("Aplicado." if not left and not rest else "Aplicado, pero hay restos: revisar.")


def fase_t(token, apply, rollback):
    """Solo las traducciones EN/FR (para reanudar la fase a si se interrumpió tras el tema y la política)."""
    items = collect_translations(token)
    show_translations(items)
    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply.")
        return
    register_translations(token, items)
    rest = collect_translations(token)
    print(f"\nAplicado. Traducciones EN/FR que aún dicen 80 €: {len(rest)}")


# ───────────────────────── fase c: descuento ─────────────────────────
Q_DISC = """{ automaticDiscountNodes(first:100){ nodes{ id automaticDiscount{ __typename
  ... on DiscountAutomaticFreeShipping{ title status startsAt endsAt combinesWith{ orderDiscounts productDiscounts shippingDiscounts }
    minimumRequirement{ __typename ... on DiscountMinimumSubtotal{ greaterThanOrEqualToSubtotal{ amount } } }
    maximumShippingPrice{ amount } destinationSelection{ __typename ... on DiscountCountries{ countries includeRestOfWorld } } } } } } }"""
M_DISC = """mutation($id:ID!,$d:DiscountAutomaticFreeShippingInput!){
  discountAutomaticFreeShippingUpdate(id:$id, freeShippingAutomaticDiscount:$d){ userErrors{ field message } } }"""


def get_discount(token):
    nodes = [n for n in base.gql(token, Q_DISC)["automaticDiscountNodes"]["nodes"]
             if n["automaticDiscount"]["__typename"] == "DiscountAutomaticFreeShipping"]
    cand = [n for n in nodes if n["automaticDiscount"]["title"] in (DISCOUNT_TITLE_OLD, DISCOUNT_TITLE_NEW)]
    if len(cand) != 1:
        sys.exit(f"Se esperaba 1 descuento de envío gratis automático y hay {len(cand)}. Abortado.")
    d = cand[0]["automaticDiscount"]
    return {"id": cand[0]["id"], "title": d["title"], "status": d["status"], "startsAt": d["startsAt"], "endsAt": d["endsAt"],
            "combinesWith": d["combinesWith"], "min": float(d["minimumRequirement"]["greaterThanOrEqualToSubtotal"]["amount"]),
            "max": d["maximumShippingPrice"], "destino": d["destinationSelection"]}


def fase_c(token, apply, rollback):
    if rollback:
        old = json.load(open(rollback))
        print(f"Rollback: título {old['title']!r} y mínimo {old['min']:g} €")
        if not apply:
            print("(dry-run) añade --apply")
            return
        check(base.gql(token, M_DISC, {"id": old["id"], "d": {"title": old["title"],
              "minimumRequirement": {"subtotal": {"greaterThanOrEqualToSubtotal": f"{old['min']:.2f}"}}}}), "discountAutomaticFreeShippingUpdate")
        print("Restaurado.")
        return
    cur = get_discount(token)
    print("== C. DESCUENTO AUTOMÁTICO DE ENVÍO GRATIS")
    print(f"  título : {cur['title']!r} → {DISCOUNT_TITLE_NEW!r}")
    print(f"  mínimo : {cur['min']:g} € → 99 €   (subtotal tras descuentos)")
    print(f"  sin cambio: estado {cur['status']}, destinos {cur['destino'].get('countries')}, combina con "
          f"{[k for k, v in cur['combinesWith'].items() if v]}, fechas {cur['startsAt'][:10]}→{cur['endsAt']}")
    if not apply:
        print("\n(dry-run) No se ha cambiado nada. Añade --apply para aplicar la fase c.")
        return
    bk = os.path.join(HERE, "..", "_backup", f"umbral_c_{time.strftime('%Y%m%d-%H%M%S')}.json")
    os.makedirs(os.path.dirname(bk), exist_ok=True)
    json.dump(cur, open(bk, "w"), ensure_ascii=False, indent=1)
    print("\nBackup:", os.path.abspath(bk))
    check(base.gql(token, M_DISC, {"id": cur["id"], "d": {"title": DISCOUNT_TITLE_NEW,
          "minimumRequirement": {"subtotal": {"greaterThanOrEqualToSubtotal": "99.00"}}}}), "discountAutomaticFreeShippingUpdate")
    now = get_discount(token)
    same = {k: v for k, v in now.items() if k not in ("title", "min")} == {k: v for k, v in cur.items() if k not in ("title", "min")}
    ok = now["title"] == DISCOUNT_TITLE_NEW and abs(now["min"] - 99) < 1e-9 and same
    print(f"Relectura: título {now['title']!r}, mínimo {now['min']:g} €, resto sin cambios: {same}")
    print("Aplicado." if ok else "Aplicado, pero hay diferencias: revisar.")


def main():
    args = sys.argv[1:]
    if "--fase" not in args:
        sys.exit("Falta --fase a|t|c")
    fase = args[args.index("--fase") + 1]
    apply = "--apply" in args
    rollback = args[args.index("--rollback") + 1] if "--rollback" in args else None
    token, scopes = base.get_token()
    sc = scopes.split(",")
    print(f"Tienda: {base.SHOP} | write_legal_policies: {'write_legal_policies' in sc} | write_translations: "
          f"{'write_translations' in sc} | write_discounts: {'write_discounts' in sc}\n")
    {"a": fase_a, "t": fase_t, "c": fase_c}[fase](token, apply, rollback)


if __name__ == "__main__":
    main()
