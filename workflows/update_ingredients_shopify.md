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

## Nutrición provisional (2026-11-09) — `tools/shopify_set_nutrition_avg.py`
Hasta tener la ficha del fabricante, la tabla nutricional (custom.energy/fat/saturated_fat/carbohydrates/sugars/protein/salt)
es la MEDIA de competidores, idéntica en todas las variantes del mismo producto. Backup: `_backup/nutrition_avg_*.json`.
Fuentes por 100 g: Enrique Tomás (sobres 80 g), Joselito (pieza/chorizo/salchichón/caña de lomo), Revisan vía Jamonería
Morcillo (fichas PDF), Montechico (lomo 50 %), 5J (ficha jamón). Baja confianza: jamón cebo (2 fuentes, muy dispares),
lomo cebo y presa (1 fuente cada uno), jamón 50 % (copia del 100 %). Packs no tocados (dados de baja).
Ingredientes/alérgenos NO se han tocado. **Sustituir todo por la ficha del fabricante cuando llegue.**
Lección: el campo energy debe llevar "kJ / N kcal" completo (el tema no añade sufijo si ya hay kcal/kJ).

Actualización 2026-11-09 (2): jamón cebo, lomo cebo de campo, lomito de presa, jamón bellota 50 %, chorizo y salchichón
pasan a usar los valores medios por 100 g aportados por el equipo (ya no la media de competidores). Siguen con la media:
jamón bellota 100 % y lomo bellota 100 %. Salchichón: sal 7.5 g (valor alto, confirmar con fabricante).

Actualización 2026-11-10: los 4 jamones (bellota 100 %, bellota 50 %, cebo, cebo de campo) usan los datos del cliente
(`~/Desktop/LuisJuan/Jamones_Descripciones/*.docx`): bellota 1716 kJ / 410 kcal, 32/13/1.3/1/30/6.5; cebo 1448 kJ / 348 kcal,
24/9/0/0/31/4. Ingredientes del cliente = los ya publicados. Por confirmar: los docs de bellota 100 % y 75 % son idénticos
(posible copia y pega) y sal 6.5 g es alta frente a la competencia (2.8–4.1 g).
