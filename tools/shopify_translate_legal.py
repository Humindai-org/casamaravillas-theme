#!/usr/bin/env python3
"""Registra en Shopify (EN/FR) la traducción de las páginas y políticas legales, nodo a nodo, conservando el HTML.
Solo rellena huecos y 'outdated' del body_html/body de PAGE y SHOP_POLICY. Dry-run por defecto; --apply escribe (backup en _backup/).
Datos: tools/shopify_legal_translations_data.py  (MAP es -> (en, fr))."""
import argparse, html, json, re, sys, time
import shopify_update_ingredients as base
from shopify_legal_translations_data import MAP
Q = """query($t:TranslatableResourceType!,$after:String){translatableResources(first:50,resourceType:$t,after:$after){
 pageInfo{hasNextPage endCursor} nodes{resourceId translatableContent{key value digest}
 en: translations(locale:"en"){key value outdated} fr: translations(locale:"fr"){key value outdated}}}}"""
M_REG = "mutation($id:ID!,$t:[TranslationInput!]!){translationsRegister(resourceId:$id,translations:$t){userErrors{field message code}}}"
def norm(t): return " ".join(html.unescape(t).split())
def translate(src, idx):
    left = []
    return re.sub(r"(?s)(?<=>)([^<>]+)(?=<)", lambda m: _wrap(m, idx, left), src), left
def _wrap(m, idx, left):
    txt = m.group(1); n = norm(txt)
    if not re.search(r"[A-Za-zÁ-úñ]", n): return txt
    tr = MAP.get(n)
    if tr is None:
        if re.search(r"[áéíóúñ¿¡]|\b(el|la|los|las|del|con|para|que|por|y|o|de)\b", n) and not re.fullmatch(r"[\w.@:/ \-|+]+", n): left.append(n)
        return txt
    lead = txt[: len(txt) - len(txt.lstrip())]; trail = txt[len(txt.rstrip()):]
    return lead + html.escape(tr[idx], quote=False) + trail
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
    tok, scopes = base.get_token()
    if a.apply and "write_translations" not in scopes: sys.exit("Falta write_translations")
    plan, backup = [], []
    for rtype in ("PAGE", "SHOP_POLICY"):
        after = None
        while True:
            r = base.gql(tok, Q, {"t": rtype, "after": after})["translatableResources"]
            for n in r["nodes"]:
                for c in n["translatableContent"]:
                    if c["key"] not in ("body_html", "body") or not (c["value"] or "").strip(): continue
                    for loc, idx in (("en", 0), ("fr", 1)):
                        cur = next((x for x in n[loc] if x["key"] == c["key"]), None)
                        if cur and cur["value"].strip() and not cur["outdated"]: continue
                        new, left = translate(c["value"], idx)
                        rid = n["resourceId"].split("/")[-1]
                        print(f"~ [{loc}] {rtype} {rid} {len(c['value'])}c ({'outdated' if cur else 'nueva'}) sin traducir: {len(left)}")
                        for l in left[:6]: print("     ?", l[:110])
                        plan.append((n["resourceId"], {"key": c["key"], "value": new, "locale": loc, "translatableContentDigest": c["digest"]}))
                        backup.append({"id": n["resourceId"], "key": c["key"], "locale": loc, "antes": cur["value"] if cur else None})
            if not r["pageInfo"]["hasNextPage"]: break
            after = r["pageInfo"]["endCursor"]
    print(f"\n{len(plan)} traducciones a registrar.")
    if not a.apply: print("DRY-RUN: nada escrito."); return
    base.BACKUP_DIR.mkdir(exist_ok=True)
    bp = base.BACKUP_DIR / f"translations_legal_{time.strftime('%Y%m%d-%H%M%S')}.json"; bp.write_text(json.dumps(backup, ensure_ascii=False, indent=1))
    for rid, t in plan:
        res = base.gql(tok, M_REG, {"id": rid, "t": [t]})["translationsRegister"]
        if res["userErrors"]: sys.exit("userErrors: " + json.dumps(res["userErrors"], ensure_ascii=False))
    print("OK aplicado. Backup:", bp)
main()
