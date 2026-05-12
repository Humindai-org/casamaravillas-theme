# Guía de Selección de Iconos

Este documento explica cómo cambiar y personalizar los iconos en tu tienda Shopify usando GitHub.

## Sistema Centralizado

Hemos implementado un **sistema centralizado de iconos** que permite cambiarlos desde el editor de Shopify de forma sencilla. El sistema funciona así:

1. **Los iconos se definen en el código** de cada sección Liquid
2. **Cambias el nombre del icono** en la variable correspondiente
3. **Haces push a GitHub** y Shopify se sincroniza automáticamente

## Iconos Disponibles

Tienes 16 archivos SVG disponibles:

```
formato.svg
icon-bellota.svg
icon-cata.svg
icon-cereales.svg
icon-conservacion.svg
icon-consumo.svg
icon-curacion.svg
icon-envio.svg
icon-garantia.svg
icon-info.svg
icon-origen.svg
icon-pasto.svg
icon-peso.svg
icon-raza.svg
icon-refrigerado.svg
info_nutricional.svg
```

## Cómo Cambiar Iconos por Sección

### 1. Banda de Confianza (trust-band.liquid)

**Ubicación de cambio:** `sections/trust-band.liquid`, línea 7

```liquid
{%- assign icons = 'icon-envio.svg|icon-garantia.svg|icon-conservacion.svg|icon-peso.svg|formato.svg' | split: '|' -%}
```

**Estructura:** Los iconos van en orden, separados por `|`
- Icono 1 (Envío gratis): `icon-envio.svg`
- Icono 2 (Calidad garantizada): `icon-garantia.svg`
- Icono 3 (Embalaje especial): `icon-conservacion.svg`
- Icono 4 (Packaging regalo): `icon-peso.svg`
- Icono 5 (Múltiples formatos): `formato.svg`

**Ejemplo:** Para cambiar el ícono de "Envío gratis" a `icon-info.svg`:
```liquid
{%- assign icons = 'icon-info.svg|icon-garantia.svg|icon-conservacion.svg|icon-peso.svg|formato.svg' | split: '|' -%}
```

---

### 2. Tarjetas de Información del Producto (product-information.liquid)

**Ubicación de cambios:** `sections/product-information.liquid`, líneas 11-12

```liquid
{%- assign icon_card1 = 'info_nutricional.svg' -%}
{%- assign icon_card2 = 'icon-consumo.svg' -%}
```

- **Card 1 (Información Nutricional):** `icon_card1`
- **Card 2 (Conservación y Consumo):** `icon_card2`

**Ejemplo:** Para cambiar el ícono de "Información Nutricional" a `icon-info.svg`:
```liquid
{%- assign icon_card1 = 'icon-info.svg' -%}
{%- assign icon_card2 = 'icon-consumo.svg' -%}
```

---

### 3. Tarjetas de Detalles del Producto (product-detail-cards.liquid)

**Ubicación de cambios:** `sections/product-detail-cards.liquid`, líneas 651-680 (presets)

Cada tarjeta tiene su icono configurado en los presets:

```json
{
  "type": "detail_card",
  "settings": {
    "enabled": true,
    "label": "Raza",
    "icon": "icon-raza.svg",
    ...
  }
}
```

**Tarjetas disponibles en el preset por defecto:**
- Raza: `icon-raza.svg`
- Alimentación (dinámica): `icon-bellota.svg`, `icon-pasto.svg`, `icon-cereales.svg`
- Origen: `icon-origen.svg`
- Curación: `icon-curacion.svg`

**Ejemplo:** Para cambiar el ícono de "Raza" a `icon-info.svg`:
```json
{
  "type": "detail_card",
  "settings": {
    "label": "Raza",
    "icon": "icon-info.svg",
    ...
  }
}
```

---

## Flujo de Cambio (GitHub → Shopify)

1. **Edita el archivo** en tu editor local o en GitHub
2. **Cambia el nombre del icono** (usa exactamente el nombre del archivo SVG)
3. **Haz commit y push:**
   ```bash
   git add sections/trust-band.liquid
   git commit -m "feat: cambiar icono de banda de confianza"
   git push
   ```
4. **Espera 30 segundos** a que Shopify sincronice los cambios
5. **Recarga la página del producto** en tu navegador (Ctrl+Shift+R para limpiar caché)

---

## Resolución de Problemas

### Los iconos no aparecen después de hacer push

**Solución:**
1. Fuerza recarga en el navegador: **Ctrl+Shift+R** (Windows) o **Cmd+Shift+R** (Mac)
2. Espera 1-2 minutos a que Shopify sincronice
3. Verifica que el nombre del icono esté escrito **exactamente igual** al archivo SVG (incluyendo `.svg`)

### El nombre del icono no es reconocido

**Causa:** Escribiste mal el nombre del archivo

**Solución:**
1. Copia el nombre exacto de la lista de "Iconos Disponibles" arriba
2. Incluye la extensión `.svg`
3. Respetar mayúsculas/minúsculas (ej: `icon-origen.svg` NO `icon-Origen.svg`)

---

## Snippet Reutilizable

El sistema usa un snippet llamado `icon-selector.liquid` que:
- Detecta automáticamente si el nombre es un archivo SVG (contiene `.svg`)
- Si es SVG, lo carga como imagen desde assets
- Si no, lo carga como icono inline del snippet `svg-icon`

No necesitas editar este snippet, solo cambia los nombres en cada sección.

---

## Notas Técnicas

- El sistema **no usa selectores del editor de Shopify** porque la sincronización es problemática
- **En su lugar, usamos variables en Liquid** que son simples de cambiar en el código
- Los cambios se sincronizan automáticamente cuando haces push a GitHub
- Todos los 16 iconos están en `/assets/` y ya disponibles en Shopify
