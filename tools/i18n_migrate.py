#!/usr/bin/env python3
"""Migra texto fijo en español de secciones .liquid a claves cm.* (es/en/fr).
  extract  -> escribe worklist.json {key: es} (solo lectura sobre el tema)
  apply    -> con translations.json {key: {en, fr}} reescribe los .liquid y añade las claves a locales/*.json
Uso: python3 tools/i18n_migrate.py extract|apply WORKDIR"""
import re, sys, json, os, hashlib, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {  # archivo -> namespace de claves (cm.<ns>.*)
    "sections/devoluciones-content.liquid": "dev", "sections/envios-content.liquid": "ship", "sections/policy-body.liquid": "ship",
    "sections/contact-section.liquid": "contact",
    "sections/iberico-guide-hero.liquid": "guide", "sections/iberico-serrano-diff.liquid": "guide", "sections/iberico-denominaciones.liquid": "guide",
    "sections/iberico-tiers.liquid": "guide", "sections/iberico-toc.liquid": "guide", "sections/iberico-quality-guide.liquid": "guide",
    "sections/shopify-guia-iberico-section.liquid": "guide",
    "sections/nosotros-toc.liquid": "nos", "sections/nosotros-statement.liquid": "nos", "sections/nosotros-hero.liquid": "nos",
    "sections/main-blog.liquid": "ui", "sections/header.liquid": "ui", "sections/cart-drawer.liquid": "ui", "sections/product-grid.liquid": "ui",
    "sections/main-product.liquid": "ui", "sections/product-details-accordion.liquid": "ui", "sections/collection-main.liquid": "ui",
    "snippets/free-shipping-bar.liquid": "ui",
}
ES = re.compile(r"[áéíóúñ¿¡ÁÉÍÓÚÑ]|\b(el|la|los|las|del|con|para|tu|tus|una|en|ver|más|envío|gratis|desde|todos|sin|por|que|como|nuestr\w+|producto\w*|elige|selecciona|buscar|zona|teléfono|calidad|jamón|sabor|raza|descripción|fecha|pedido|email|iva|selección|estándar|opción|otros|reducir|aumentar|cantidad|anterior|siguiente|guía|ibérico|consulta|regalo|problema|motivo|calidad|tiempo|experiencia|excepcional|diferenciador)\b", re.I)
ELEM = re.compile(r"(?P<open><(?P<tag>[a-z][a-z0-9]*)(?P<attrs>(?:\s[^<>]*?)?)>)(?P<inner>[^<>{}\n][^\n]*?)(?P<close></(?P=tag)>)")
ATTR = re.compile(r'(?P<a>\b(?:aria-label|alt|placeholder|title))="(?P<v>[^"{}<>]+)"')
def regions(src):
    """Devuelve [(start,end)] de zonas traducibles: fuera de style/script/schema/comment."""
    bad = [m.span() for m in re.finditer(r"<style\b.*?</style>|<script\b.*?</script>|{%-?\s*schema.*?endschema\s*-?%}|{%-?\s*comment\s*-?%}.*?{%-?\s*endcomment\s*-?%}|{%-?\s*(?:stylesheet|javascript).*?end(?:stylesheet|javascript)\s*-?%}", src, re.S)]
    return bad
def inbad(bad, i): return any(a <= i < b for a, b in bad)
def slug(t):
    t = unicodedata.normalize("NFKD", re.sub(r"<[^>]+>|&\w+;", " ", t)).encode("ascii", "ignore").decode().lower()
    w = re.findall(r"[a-z0-9]+", t)[:4]
    return "_".join(w) or "txt"
LINE = re.compile(r"^(?P<ind>[ \t]*)(?P<open><(?P<tag>p|li|h[1-6]|span|div|a|th|td|summary|em|strong|button|label|option|legend)(?P<attrs>(?:\s[^<>]*?)?)>)(?P<inner>.+)(?P<close></(?P=tag)>)[ \t]*$", re.M)
BLOCK = re.compile(r"<(p|div|li|ul|ol|h[1-6]|table|tr|section|svg)\b", re.I)
ALL_FILES = {"sections/devoluciones-content.liquid", "sections/envios-content.liquid", "sections/policy-body.liquid"}  # todo el texto es español
BARE_FILES = {"sections/iberico-guide-hero.liquid"}
# Casos manuales: (archivo|None=todos, regex con grupo 'es', ámbito) -> el grupo 'es' se sustituye por {{ 'cm.clave' | t }}
RAW = [
    ("sections/devoluciones-content.liquid", r"(?P<es>Si tienes una incidencia[^\n]*?</a>\.)<br>", None),
    (None, r"(?P<es>Horario de atención: lunes a viernes, 9:00 – 18:00 h\.)", None),
    ("sections/envios-content.liquid", r"(?P<es>Teléfono): <a", None),
    ("sections/policy-body.liquid", r"(?P<es>Teléfono): <a", None),
    ("sections/iberico-guide-hero.liquid", r">(?P<es>TIEMPO)<", None),
    ("sections/iberico-guide-hero.liquid", r">(?P<es>EXPERIENCIA)<", None),
    ("sections/iberico-guide-hero.liquid", r"<em>(?P<es>Excepcional)</em>", None),
    ("sections/iberico-serrano-diff.liquid", r">(?P<es>— Diferenciador clave)<", None),
    ("sections/main-product.liquid", r"(?P<es>Selecciona tu vino)\n", None),
    ("sections/main-product.liquid", r"\n\s*(?P<es>Punto de Curación)\n", None),
    ("sections/cart-drawer.liquid", r"shipping-label\">\s*(?P<es>Envío)\s*<svg", None),
]
def covered(spans, a, b): return any(x <= a and b <= y for x, y in spans)
def candidates(src, f=None):
    bad = regions(src); out = []; spans = []
    def add(kind, a, b, txt):
        if not covered(spans, a, b) and not any(a < y and x < b for x, y in spans):
            out.append((kind, a, b, txt)); spans.append((a, b))
    def ok(inner):
        if "{%" in inner or "{{" in inner or BLOCK.search(inner) or 'href="/pages/' in inner: return False
        plain = re.sub(r"<[^>]+>|&\w+;", " ", inner).strip()
        if not re.search(r"[A-Za-zÁ-úñ]{3}", plain): return False
        if f in ALL_FILES: return not (("@" in plain and " " not in plain) or plain.lower() == "email")
        return bool(ES.search(plain))
    for m in LINE.finditer(src):
        if not inbad(bad, m.start()) and ok(m.group("inner")): add("elem", m.start("inner"), m.end("inner"), m.group("inner"))
    for m in ELEM.finditer(src):
        inner = m.group("inner")
        if not inbad(bad, m.start()) and ok(inner): add("elem", m.start("inner"), m.end("inner"), inner)
    for m in ATTR.finditer(src):
        if not inbad(bad, m.start()) and ES.search(m.group("v")): add("attr", m.start("v"), m.end("v"), m.group("v"))
    if f in BARE_FILES:
        for m in re.finditer(r"^[ \t]*(?P<t>[^<>{}\n]{3,}?)[ \t]*$", src, re.M):
            t = m.group("t")
            if not inbad(bad, m.start()) and re.search(r"[A-Za-zÁ-úñ]{3}", t) and (ES.search(t) or t.isupper()) and not re.match(r"^[\w.#:\-\s,]*[{};]", t):
                add("bare", m.start("t"), m.end("t"), t)
    for rf, rx, _ in RAW:
        if rf not in (None, f): continue
        for m in re.finditer(rx, src):
            if not inbad(bad, m.start()): add("raw", m.start("es"), m.end("es"), m.group("es"))
    return out
def key_for(ns, es, table):
    for k, v in table.items():
        if v == es: return k
    suf = "_html" if "<" in es else ""
    base = f"{ns}.{slug(es)}"; k = base + suf; n = 2
    while k in table and table[k] != es: k = f"{base}_{n}{suf}"; n += 1
    return k
def extract(work):
    table = {}
    for f, ns in FILES.items():
        src = open(os.path.join(ROOT, f)).read()
        for kind, a, b, txt in candidates(src, f): table.setdefault(key_for(ns, txt, table), txt)
    ex = os.path.join(work, "extras.json")
    if os.path.exists(ex): table.update(json.load(open(ex)))
    json.dump(table, open(os.path.join(work, "worklist.json"), "w"), ensure_ascii=False, indent=1)
    print(len(table), "cadenas ->", os.path.join(work, "worklist.json"))
def load_loc(p):
    s = open(p).read(); return s
def insert_keys(path, table, lang):
    s = open(path).read()
    groups = {}
    for k, v in table.items():
        ns, rest = k.split(".", 1); groups.setdefault(ns, {})[rest] = v[lang]
    # no pisa grupos existentes: se añaden grupos nuevos justo tras  "cm": {
    block = ""
    for ns, d in sorted(groups.items()):
        if re.search(r'\n\s*"%s": \{' % ns, s[s.index('"cm": {'):]): raise SystemExit(f"grupo cm.{ns} ya existe en {path}")
        items = ",\n".join(f'      {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}' for k, v in d.items())
        block += f'\n    "{ns}": {{\n{items}\n    }},'
    s = s.replace('"cm": {', '"cm": {' + block, 1)
    open(path, "w").write(s)
def apply(work):
    wl = json.load(open(os.path.join(work, "worklist.json"))); tr = json.load(open(os.path.join(work, "translations.json")))
    missing = [k for k in wl if k not in tr or not tr[k].get("en") or not tr[k].get("fr")]
    if missing: raise SystemExit(f"faltan traducciones: {missing[:10]} ({len(missing)})")
    inv = {v: k for k, v in wl.items()}
    total = 0
    for f in FILES:
        p = os.path.join(ROOT, f); src = open(p).read()
        cands = sorted(candidates(src, f), key=lambda c: -c[1])
        for kind, a, b, txt in cands:
            k = inv[txt]; src = src[:a] + "{{ 'cm.%s' | t }}" % k + src[b:]; total += 1
        open(p, "w").write(src)
    table = {k: {"es": wl[k], "en": tr[k]["en"], "fr": tr[k]["fr"]} for k in wl}
    for path, lang in (("locales/es.default.json", "es"), ("locales/en.json", "en"), ("locales/fr.json", "fr")):
        insert_keys(os.path.join(ROOT, path), table, lang)
    print(total, "sustituciones;", len(table), "claves añadidas a es/en/fr")
if __name__ == "__main__":
    {"extract": extract, "apply": apply}[sys.argv[1]](sys.argv[2])
