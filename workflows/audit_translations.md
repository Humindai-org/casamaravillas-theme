# Auditoría de traducciones EN/FR

Objetivo: que no queden textos en español en las versiones EN/FR.

## Dos orígenes de huecos
1. **Contenido de Shopify** (productos, opciones, menús, envíos, SEO, tema JSON): vive en Translate & Adapt.
   - Detectar: `python3 tools/shopify_audit_translations.py --json /tmp/audit.json` (solo lectura, todos los tipos de recurso).
   - Corregir: añadir una regla a `RULES` en `tools/shopify_fix_translations.py`, dry-run, luego `--apply` (backup en `_backup/`).
   - Ignorar: HTML de Judge.me en metacampos (lo gestiona la app), `Title`/`Default Title` (nunca se muestran), nota interna del producto "Servicio de preparación".
2. **Textos del tema** (hardcoded o `default` del schema): Translate & Adapt NO los ve.
   - Detectar: `python3 tools/audit_theme_i18n.py` (defaults en español usados por una plantilla que no define ese ajuste).
   - Corregir: quitar el `default` del schema y pintar `{% if setting != blank %}…{% else %}{{ 'cm.xxx' | t }}{% endif %}` con la clave en es/en/fr.
   - Un ajuste vacío `""` en la plantilla es intencional (oculta el texto): no tocar.

## Causa raíz típica
Una sección nueva/plantilla alternativa (p. ej. `product.jamones.json`) no define un ajuste → Shopify usa el `default` del schema en español, que no es traducible.
`tools/audit_theme_i18n.py` lo detecta; ejecutarlo al crear plantillas o secciones nuevas.

## Pendiente de decisión humana
- Páginas legales (aviso legal, términos, política de devoluciones/envíos) EN/FR: marcadas `outdated`/`missing`; conviene traducción revisada, no automática.
- Idioma `it` existe pero no está publicado.

## Actualización 2026-11-15 — migración completa a cm.* y herramientas nuevas
- `tools/audit_rendered_pages.py [BASE]`: rastrea ES/EN/FR contra `shopify theme dev` (127.0.0.1:9292) y marca texto EN/FR idéntico al español. Los ajustes de plantillas JSON salen "sin traducir" en un tema de desarrollo (las traducciones de T&A van por ID de tema): se comprueban con `tools/audit_theme_json_texts.py`, que compara el JSON del repo con el contenido traducible del tema vivo.
- `tools/i18n_extract.py` (lista texto fijo) y `tools/i18n_migrate.py extract|apply WORKDIR` (pasa elementos de una línea y atributos a `{{ 'cm.<ns>.<clave>' | t }}` + es/en/fr). Casos con enlaces o variables se hacen a mano (`url:` como argumento de `t`; no se permiten filtros dentro de los argumentos).
- `tools/shopify_translate_legal.py` + `shopify_legal_translations_data.py`: traducción por nodo de texto HTML de páginas y políticas (PAGE, SHOP_POLICY). Dry-run por defecto.
- Trampas: nombres de opción y valores de variante llegan TRADUCIDOS a Liquid y a `product.options | json`; comparar con `'peso', 'weight', 'poids'` y no solo con el español. `'{x}'` dentro de `{{ }}` rompe la subida del tema: usar variables `ph_*`.
- Defaults en `| default: 'Texto'` solo se traducen si el ajuste existe en la plantilla; si está vacío se muestra el español.
