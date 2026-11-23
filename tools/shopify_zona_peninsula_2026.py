#!/usr/bin/env python3
"""
Zona de envío «Península» (22/11/2026, decisión de Jorge): Luis Juan no envía a Baleares, Canarias, Ceuta ni Melilla.
Quita de la zona los códigos PM (Baleares), GC y TF (Canarias), CE (Ceuta) y ML (Melilla) en TODOS los perfiles de envío
que los tengan. Portugal se queda. No toca tarifas ni las demás zonas.

Es la misma regla que ya publica el tema (sections/envios-content.liquid y policy-body.liquid: «no realizamos envíos a
Islas Baleares, Islas Canarias, Ceuta ni Melilla»); hoy la zona las cubre y cotizan 8,94 € como la Península.

Uso:  python3 -I tools/shopify_zona_peninsula_2026.py                              # simulacro (solo lee)
      python3 -I tools/shopify_zona_peninsula_2026.py --apply                      # copia de seguridad + escribe + verifica
      python3 -I tools/shopify_zona_peninsula_2026.py --rollback _backup/zona_peninsula_XXXX.json --apply   # restaura
Tras escribir relee la zona y prueba carritos de PRUEBA (Storefront cartCreate, sin pagar): Palma, Las Palmas, Santa Cruz,
Ceuta y Melilla deben quedar SIN opciones de envío; Alicante, Madrid y Lisboa, a 8,94 €.
"""
import importlib.util, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
base = pre.base
BK = os.path.join(HERE, "..", "_backup")

QUITAR = {"PM": "Baleares", "GC": "Las Palmas (Canarias)", "TF": "Santa Cruz de Tenerife (Canarias)", "CE": "Ceuta", "ML": "Melilla"}
DOM, UA = "https://casamaravillas.com", {"User-Agent": "casamaravillas-prueba-zona/1.0"}
Q = """{ deliveryProfiles(first:20){ nodes{ id name default profileLocationGroups{ locationGroup{ id }
  locationGroupZones(first:30){ nodes{ zone{ id name countries{ code{ countryCode } provinces{ code } } }
    methodDefinitions(first:20){ nodes{ name active rateProvider{ ... on DeliveryRateDefinition{ price{ amount } } } } } } } } } } }"""
M = """mutation($id:ID!,$p:DeliveryProfileInput!){ deliveryProfileUpdate(id:$id, profile:$p){ profile{ id } userErrors{ field message } } }"""
CART = """mutation($i:CartInput!){ cartCreate(input:$i){ cart{ deliveryGroups(first:3){ nodes{ deliveryOptions{ title estimatedCost{ amount } } } } } userErrors{ message } } }"""
PRUEBAS = [("Palma", "07001", "PM", "ES", False), ("Las Palmas", "35001", "GC", "ES", False), ("Santa Cruz de Tenerife", "38001", "TF", "ES", False),
           ("Ceuta", "51001", "CE", "ES", False), ("Melilla", "52001", "ML", "ES", False),
           ("Alicante", "03001", "A", "ES", True), ("Madrid", "28001", "M", "ES", True), ("Lisboa", "1000-001", None, "PT", True)]


def leer(token):
    """Zonas con ES y alguna provincia a quitar: [{perfil, grupo, zona, nombre, paises:[{code, provincias[]}], tarifas}]."""
    out = []
    for p in base.gql(token, Q)["deliveryProfiles"]["nodes"]:
        for g in p["profileLocationGroups"]:
            for z in g["locationGroupZones"]["nodes"]:
                paises = [{"code": c["code"]["countryCode"], "provincias": [x["code"] for x in c["provinces"]]} for c in z["zone"]["countries"]]
                es = next((c for c in paises if c["code"] == "ES"), None)
                if es and QUITAR.keys() & set(es["provincias"]):
                    tarifas = [(m["name"], m["active"], (m["rateProvider"] or {}).get("price", {}).get("amount")) for m in z["methodDefinitions"]["nodes"]]
                    out.append({"perfil": p["id"], "perfil_nombre": p["name"], "grupo": g["locationGroup"]["id"], "zona": z["zone"]["id"],
                                "nombre": z["zone"]["name"], "paises": paises, "tarifas": tarifas})
    return out


def escribir(token, z, paises):
    cs = [{"code": c["code"], "provinces": [{"code": x} for x in c["provincias"]], "includeAllProvinces": False} if c["provincias"]
          else {"code": c["code"], "includeAllProvinces": True} for c in paises]
    r = base.gql(token, M, {"id": z["perfil"], "p": {"locationGroupsToUpdate": [{"id": z["grupo"], "zonesToUpdate": [{"id": z["zona"], "countries": cs}]}]}})
    e = r["deliveryProfileUpdate"]["userErrors"]
    if e:
        sys.exit(f"ERROR deliveryProfileUpdate: {e}")


def carritos():
    sobre = json.load(urllib.request.urlopen(urllib.request.Request(f"{DOM}/products/chorizo-bellota-iberico-loncheado.js", headers=UA), timeout=30))["variants"][0]["id"]
    fallos = 0
    for nombre, zip_, prov, pais, debe in PRUEBAS:
        a = {"address1": "Calle Mayor 1", "city": nombre, "zip": zip_, "country": pais, **({"province": prov} if prov else {})}
        body = {"query": CART, "variables": {"i": {"lines": [{"merchandiseId": f"gid://shopify/ProductVariant/{sobre}", "quantity": 1}],
                "buyerIdentity": {"countryCode": pais, "deliveryAddressPreferences": [{"deliveryAddress": a}]}}}}
        time.sleep(0.8)
        req = urllib.request.Request(f"{DOM}/api/2025-07/graphql.json", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **UA})
        c = json.load(urllib.request.urlopen(req, timeout=30))["data"]["cartCreate"]["cart"]
        ops = [(o["title"], o["estimatedCost"]["amount"]) for g in c["deliveryGroups"]["nodes"] for o in g["deliveryOptions"]]
        ok = bool(ops) == debe and (not debe or ops[0][1] == "8.94")
        fallos += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {nombre:24} {ops if ops else 'SIN opciones de envío (no se envía)'}   (esperado: {'8,94 €' if debe else 'no se envía'})")
    return fallos


def main():
    a = sys.argv[1:]
    apply = "--apply" in a
    token, scopes = base.get_token()
    print(f"Tienda: {base.SHOP} | write_shipping: {'write_shipping' in scopes.split(',')} | {'APPLY' if apply else 'simulacro'}\n")

    if "--rollback" in a:
        for z in json.load(open(a[a.index("--rollback") + 1]))["zonas"]:
            print(f"  restaurar zona {z['nombre']!r} del perfil {z['perfil_nombre']!r}: ES {len(next(c for c in z['paises'] if c['code']=='ES')['provincias'])} provincias")
            if apply:
                escribir(token, z, z["paises"])
        print("Restaurado." if apply else "(simulacro) añade --apply")
        return

    zonas = leer(token)
    perfiles = {p["id"] for p in base.gql(token, Q)["deliveryProfiles"]["nodes"]}
    print(f"Perfiles de envío en la tienda: {len(perfiles)}. Zonas con ES y alguna provincia a quitar: {len(zonas)}\n")
    for z in zonas:
        es = next(c for c in z["paises"] if c["code"] == "ES")
        nuevas = [p for p in es["provincias"] if p not in QUITAR]
        print(f"== perfil {z['perfil_nombre']!r} · zona {z['nombre']!r} ({z['zona'].split('/')[-1]})")
        print(f"   ES: {len(es['provincias'])} provincias -> {len(nuevas)}; se quitan: {', '.join(f'{k} {v}' for k, v in QUITAR.items() if k in es['provincias'])}")
        print("   Resto de países de la zona (no cambian):", [(c['code'], len(c['provincias'])) for c in z["paises"] if c["code"] != "ES"])
        print("   Tarifas (no cambian):", z["tarifas"])
    print("\nCarritos de prueba ANTES (hoy):")
    carritos()
    if not apply:
        print("\n(simulacro) No se ha escrito nada. Los FAIL de arriba son lo esperado antes de aplicar: hoy las islas cotizan 8,94 €.")
        return

    os.makedirs(BK, exist_ok=True)
    path = os.path.abspath(os.path.join(BK, f"zona_peninsula_{time.strftime('%Y%m%d-%H%M%S')}.json"))
    json.dump({"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "zonas": zonas}, open(path, "w"), ensure_ascii=False, indent=1)
    print("\nCopia de seguridad:", path)
    for z in zonas:
        nuevos = [{"code": c["code"], "provincias": [p for p in c["provincias"] if p not in QUITAR] if c["code"] == "ES" else c["provincias"]} for c in z["paises"]]
        escribir(token, z, nuevos)
        print("  escrito:", z["nombre"])
    print("\nRelectura:")
    if leer(token):
        sys.exit(f"ERROR: queda alguna zona con provincias a quitar. Rollback: --rollback {path} --apply")
    for z in zonas:
        for p in base.gql(token, Q)["deliveryProfiles"]["nodes"]:
            for g in p["profileLocationGroups"]:
                for zz in g["locationGroupZones"]["nodes"]:
                    if zz["zone"]["id"] != z["zona"]:
                        continue
                    paises = [(c["code"]["countryCode"], len(c["provinces"])) for c in zz["zone"]["countries"]]
                    tarifas = [(m["name"], m["active"], (m["rateProvider"] or {}).get("price", {}).get("amount")) for m in zz["methodDefinitions"]["nodes"]]
                    print(f"  zona {z['nombre']!r}: países {paises} | tarifas sin cambios: {tarifas == z['tarifas']}")
    print("\nCarritos de prueba DESPUÉS:")
    fallos = carritos()
    print("\nTodo OK." if not fallos else f"\n{fallos} comprobación(es) FALLIDA(S). Rollback: python3 -I tools/shopify_zona_peninsula_2026.py --rollback {os.path.relpath(path, os.path.join(HERE, '..'))} --apply")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
