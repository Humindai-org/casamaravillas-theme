"""
Jamón de pieza entera con servicio de preparación: helpers compartidos (bundles de variante de Shopify).

Cada variante de corte/deshuesado («7.0kg - 8.0kg / Corte a máquina y envasado») es una variante PADRE con
2 componentes: la variante «Pieza entera» del mismo peso (IVA 10 %, categoría de alimentación) y una variante
del producto «Servicio de preparación del jamón» (IVA 21 %: SIN categoría, Shopify aplica la tasa general).
Invariante: precio del padre = precio de la pieza + precio del servicio.

NOTA IMPORTANTE: Los precios de los jamones se cambian con tools/actualizar_precio_jamon.py (usa la app
HumindAI Analytics), no desde el editor masivo ni CSV. Los productos con bundles no admiten edición masiva,
import/export, y si cambia el SKU de un componente hay que rehacer el bundle.

Auth: la de shopify_update_precios_embutido.py (Keychain, client credentials). Nunca se imprime el token.
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pre", os.path.join(HERE, "shopify_update_precios_embutido.py"))
pre = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pre)
base = pre.base

ADDR_ALICANTE = {"countryCode": "ES", "provinceCode": "A", "city": "Alicante", "zip": "03001", "address1": "Calle Prueba 1"}

M_PRODUCT = """mutation($p:ProductCreateInput!){ productCreate(product:$p){ product{ id handle status
  options{ id name optionValues{ name } } variants(first:10){ nodes{ id title } } } userErrors{ field message } } }"""
M_VARS_CREATE = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkCreate(productId:$p, variants:$v){
    productVariants{ id title sku price } userErrors{ field message } } }"""
M_VARS_UPDATE = """mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){
  productVariantsBulkUpdate(productId:$p, variants:$v){ productVariants{ id title } userErrors{ field message } } }"""
M_LINK = """mutation($i:[ProductVariantRelationshipUpdateInput!]!){ productVariantRelationshipBulkUpdate(input:$i){
  parentProductVariants{ id title requiresComponents productVariantComponents(first:5){ nodes{ quantity productVariant{ id title sku } } } }
  userErrors{ code field message } } }"""
M_CALC = """mutation($i:DraftOrderInput!){ draftOrderCalculate(input:$i){ userErrors{ field message }
  calculatedDraftOrder{ taxesIncluded subtotalPriceSet{ shopMoney{ amount } } totalTaxSet{ shopMoney{ amount } }
    totalPriceSet{ shopMoney{ amount } }
    taxLines{ title ratePercentage priceSet{ shopMoney{ amount } } } } } }"""
Q_PUBS = "{ publications(first:20){ nodes{ id name } } }"
M_PUBLISH = """mutation($id:ID!,$i:[PublicationInput!]!){ publishablePublish(id:$id, input:$i){ userErrors{ field message } } }"""
M_DELETE = "mutation($i:ProductDeleteInput!){ productDelete(input:$i){ deletedProductId userErrors{ field message } } }"


def ok(res, key, sub=None):
    node = res[key]
    errs = node.get("userErrors") or []
    if errs:
        sys.exit(f"ERROR en {key}: {errs}")
    return node


def crear_producto(token, titulo, estado, categoria, opcion, variantes, tags=None, descripcion=""):
    """variantes: [{valor, precio, sku, rastrear, peso_kg, envio}]. Devuelve el producto y sus variantes por valor."""
    p = {"title": titulo, "status": estado, "descriptionHtml": descripcion, "tags": tags or [],
         "productOptions": [{"name": opcion, "values": [{"name": variantes[0]["valor"]}]}]}
    if categoria:
        p["category"] = categoria
    prod = ok(base.gql(token, M_PRODUCT, {"p": p}), "productCreate")["product"]
    def _in(v, con_valor):
        d = {"price": v["precio"], "taxable": True, "inventoryPolicy": "DENY",
             "inventoryItem": {"sku": v["sku"], "tracked": v.get("rastrear", False),
                               "requiresShipping": v.get("envio", True),
                               "measurement": {"weight": {"value": v.get("peso_kg", 0.0), "unit": "KILOGRAMS"}}}}
        if con_valor:
            d["optionValues"] = [{"optionName": opcion, "name": v["valor"]}]
        return d

    # productCreate ya genera la variante del primer valor de la opción: se actualiza; el resto se crea.
    primera = dict(_in(variantes[0], False), id=prod["variants"]["nodes"][0]["id"])
    ok(base.gql(token, M_VARS_UPDATE, {"p": prod["id"], "v": [primera]}), "productVariantsBulkUpdate")
    out = {variantes[0]["valor"]: {"id": primera["id"], "title": variantes[0]["valor"]}}
    if len(variantes) > 1:
        creadas = ok(base.gql(token, M_VARS_CREATE, {"p": prod["id"], "v": [_in(v, True) for v in variantes[1:]]}),
                     "productVariantsBulkCreate")["productVariants"]
        out.update({v["title"]: v for v in creadas})
    return prod, out


def publicar_tienda_online(token, product_id):
    pubs = {n["name"]: n["id"] for n in base.gql(token, Q_PUBS)["publications"]["nodes"]}
    ok(base.gql(token, M_PUBLISH, {"id": product_id, "i": [{"publicationId": pubs["Online Store"]}]}), "publishablePublish")


def enlazar(token, padre_id, componentes):
    """componentes: [(variant_id, cantidad)]. Convierte la variante padre en bundle."""
    rel = [{"id": vid, "quantity": q} for vid, q in componentes]
    inp = {"parentProductVariantId": padre_id, "productVariantRelationshipsToCreate": rel}
    return ok(base.gql(token, M_LINK, {"i": [inp]}), "productVariantRelationshipBulkUpdate")["parentProductVariants"][0]


def calcular_impuestos(token, lineas, descuento=None, direccion=ADDR_ALICANTE):
    """lineas: [(variant_id, qty)]. draftOrderCalculate NO crea ningún pedido borrador."""
    inp = {"lineItems": [{"variantId": v, "quantity": q} for v, q in lineas], "shippingAddress": direccion}
    if descuento:
        inp["appliedDiscount"] = descuento
    return ok(base.gql(token, M_CALC, {"i": inp}), "draftOrderCalculate")["calculatedDraftOrder"]


def borrar_producto(token, product_id):
    ok(base.gql(token, M_DELETE, {"i": {"id": product_id}}), "productDelete")
