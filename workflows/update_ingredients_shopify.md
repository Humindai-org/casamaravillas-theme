# Actualizar ingredientes en Shopify (metacampo custom.ingredients)

## Objetivo
Aplicar el campo "Ingredientes" de un CSV de productos directamente a la tienda, sin reimportar el CSV entero.

## Herramienta
`tools/shopify_update_ingredients.py` — app "HumindIA Analytics" (Dev Dashboard), flujo client credentials.

## Requisitos (una sola vez)
- Scopes de la app: `read_products` y `write_products`. Tras añadirlos: publicar versión nueva y reinstalar en la tienda.
- Keychain de macOS con el Client ID y el Client secret. Nombres por defecto:
  `casamaravillas-shopify-client-id` y `casamaravillas-shopify-client-secret`.
  Si tus entradas se llaman distinto: `export SHOPIFY_KC_CLIENT_ID=<nombre>` y `export SHOPIFY_KC_CLIENT_SECRET=<nombre>`.
- Nunca imprimir ni guardar los secretos. El script los lee del Keychain internamente.

## Pasos
1. Dry-run (solo lee): `python3 tools/shopify_update_ingredients.py <CSV>`
2. Revisar el antes/después impreso.
3. Aplicar: `python3 tools/shopify_update_ingredients.py <CSV> --apply` (guarda backup en `_backup/`, ignorado por git).
4. Verificar en la ficha del producto (modal "Saber más").

## Rollback
`python3 tools/shopify_update_ingredients.py --rollback _backup/ingredients_<fecha>.json --apply`

## Notas aprendidas
- El modal "Saber más" abre una viñeta por cada coma fuera de paréntesis (ver product-information.liquid).
- Las páginas pueden tardar minutos en reflejar el cambio por la caché de Shopify.
- 2026-10-16: aplicado `Productos_15-09-26_actualizado_v3.csv` (11 productos).
