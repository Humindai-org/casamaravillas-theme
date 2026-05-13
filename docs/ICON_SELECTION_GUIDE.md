# Guía de Selección de Iconos

Este documento explica cómo cambiar y personalizar los iconos en tu tienda Shopify directamente desde el editor.

## Sistema Centralizado

Hemos implementado un **sistema centralizado de iconos** que permite cambiarlos desde el editor de Shopify de forma sencilla. El sistema funciona así:

1. **Abre el editor de Shopify**
2. **Selecciona la sección** que deseas personalizar
3. **Elige el icono** en el selector del editor
4. **Los cambios se aplican automáticamente**

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

## Cómo Cambiar Iconos desde el Editor de Shopify

### 1. Banda de Confianza (Trust Band)

La banda de confianza contiene 5 elementos con sus iconos asociados:

**Pasos:**
1. En el editor de Shopify, ve a **Secciones**
2. Busca y selecciona **"Banda de confianza"**
3. Para cada elemento (Envío gratis, Calidad garantizada, etc.):
   - Haz clic en el elemento dentro de la sección
   - En el panel derecho, selecciona el icono de la lista desplegable "Icono"
   - El cambio se aplica automáticamente en la vista previa

**Iconos disponibles:**
- Envío, Garantía, Conservación, Peso, Formato, Información, y más

---

### 2. Tarjetas de Información del Producto

Las tarjetas de información nutricional y conservación/consumo tienen selectores de iconos:

**Pasos:**
1. En el editor de Shopify, busca la sección **"Información del Producto"**
2. En el panel de configuración, encontrarás:
   - **Icono Tarjeta 1** (para Información Nutricional)
   - **Icono Tarjeta 2** (para Conservación y Consumo)
3. Selecciona el icono que prefieras de cada lista desplegable
4. Los cambios aparecen inmediatamente en la vista previa

---

### 3. Tarjetas de Detalles del Producto (Product Details)

Cada tarjeta de detalles (Raza, Alimentación, Origen, Curación) tiene su propio selector de icono:

**Pasos:**
1. En el editor de Shopify, busca la sección **"Product Detail Cards"**
2. Cada tarjeta incluye un selector **"Select Icon"**
3. Elige el icono que prefieras para esa tarjeta
4. Los cambios se aplican inmediatamente

**Nota:** Para la sección de Alimentación, el icono puede ser dinámico (cambia según el tipo de alimentación del producto)

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
