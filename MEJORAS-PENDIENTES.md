# Ideas de mejora — backlog de mantenimiento

Documento vivo para ir picando durante el mantenimiento mensual. No son bugs urgentes — son mejoras que se decidió posponer conscientemente para tratarlas con más calma. Añadir fecha al lado de cada ítem cuando se complete.

---

## 1. Wishlist con carpetas personalizadas

**Contexto:** en julio 2026 se construyó una wishlist v1 (cajón lateral, una sola lista, guardado en `localStorage` del navegador). El cliente pidió después poder crear varias listas/carpetas propias (ej. "Favoritos", "Para Navidad", "Regalo mamá") en vez de una lista única.

**Qué implica:**
- Rediseñar el almacenamiento: de un array simple de handles (`cm_wishlist`) a un objeto `{ "nombre-lista": [handles...] }`, con soporte para crear/renombrar/borrar listas desde la UI.
- UI para elegir a qué lista añadir un producto desde la ficha (hoy es un solo corazón; con varias listas necesita un menú/selector).
- Migración de los datos ya guardados por clientes reales bajo el formato v1 (`cm_wishlist` array) al nuevo formato multi-lista, sin perder lo que ya tengan guardado.
- Mejora visual del cajón (el cliente pidió explícitamente "mejorar el UI para que se vea mejor" — vale la pena revisar el diseño completo, no solo añadir pestañas).

**Archivos implicados:** `assets/wishlist-drawer.js`, `assets/wishlist-drawer.css`, `sections/wishlist-drawer.liquid`, `assets/main-product.js` (botón de guardar en PDP).

---

## 2. Wishlist persistente por cliente (entre dispositivos)

**Contexto:** hoy la wishlist vive en el navegador (localStorage) — si el cliente entra desde el móvil no ve lo guardado en el ordenador. Esta tienda usa las cuentas de cliente nuevas de Shopify (hosted accounts), y el tema no tiene forma de leer/escribir en esa cuenta sin una app/backend propio.

**Qué implica (proyecto grande, no es una tarea de tema):**
- Construir una Shopify App (con App Proxy o Storefront API + token de cliente) que lea/escriba metafields del cliente.
- Hosting propio para esa app/backend.
- Solo tiene sentido si el punto 1 (multi-lista) ya está resuelto, para no duplicar trabajo de UI.

**Cuándo abordarlo:** cuando el cliente esté dispuesto a invertir en una app/backend dedicado. No es una mejora incremental de tema.

---

## 3. Envío según zona real (conectado a tarifas de Shopify)

**Contexto:** el cajón del carrito hoy muestra "Calculado en el checkout" para el envío (texto genérico, sin promesa de precio — así se dejó en julio 2026 tras detectar que el umbral fijo de 80€ no reflejaba las tarifas reales por zona: Baleares tiene un umbral distinto de 150€, otras zonas internacionales no tienen envío gratis en absoluto, ver `sections/policy-body.liquid` / `envios-content.liquid` para el detalle real de tarifas).

**Qué implica:**
- Conectar el cajón del carrito a la estimación de envío real de Shopify (Storefront API `cart` con `deliveryGroups`, o el endpoint de shipping rates) según el país/código postal que el cliente indique.
- Esto da un dato siempre exacto, sin mantenimiento manual de umbrales hardcodeados en el tema.
- Alternativa más simple: al menos detectar el país del cliente (Shopify Markets ya lo hace) y mostrar el umbral correcto por zona en texto, sin cálculo de tarifa exacta.

**Archivos implicados:** `sections/cart-drawer.liquid`, `assets/cart-drawer.js`.

---

## 4. Fase 3 del refactor de rendimiento: extraer CSS/JS de las colecciones

**Contexto:** en julio 2026 se extrajo el CSS/JS inline de `main-product.liquid` y `product-information.liquid` a archivos estáticos cacheables (ver Fases 1-2 del plan de esa fecha). Quedó pendiente a propósito `iberico-collection.liquid` y `jamones-collection.liquid` por ser más arriesgado: sus hojas de estilo tienen `{{ section.id }}` incrustado en ~86-87 selectores CSS cada una (no un simple wrapper), así que la extracción requiere reescribir esos selectores a mano con cuidado (opción B ya decidida: clase fija + variable CSS para el único valor dinámico real, `products_per_row`).

**Impacto de no hacerlo:** esas dos páginas de colección siguen re-descargando ~680 líneas de CSS y ~280-360 líneas de JS en cada carga en vez de servirlas desde caché — no es grave, pero es la misma ganancia de rendimiento que ya se aplicó al resto.

---

## 5. Traducciones en inglés incompletas

**Contexto:** `locales/en.json` tiene 204 claves vs. 62 en `locales/es.default.json` — pero le faltan algunas claves específicas que si el español (idioma real por defecto de la tienda) usa: `cart.general.subtotal`, `cart.general.total`, `blogs.general.title`, `customer.login.email`, `customer.register.email`. Si la tienda ofrece la versión en inglés, esos textos podrían aparecer vacíos o con el fallback de Shopify.

**Solo relevante si** la tienda realmente vende en inglés a día de hoy — confirmar antes de invertir tiempo aquí.

---

## 6. Selector de "Pack" / descuento por volumen para embutidos

**Contexto:** en julio 2026 se corrigió un bug donde el selector de cantidad "Cortado a Mano - Pack" aparecía también en productos de embutidos loncheados (salchichón, lomo, chorizo), causando líneas duplicadas en el carrito sin ningún descuento real detrás. Se limitó ese selector a mostrarse solo en productos "Cortado a Mano" (jamón).

**Si en el futuro se quiere ofrecer descuento por volumen también en embutidos loncheados** (comprar 10/20/30 unidades más barato, igual que ya existe para jamón cortado a mano), haría falta:
- Extender `updateVolumDiscount()` en `assets/main-product.js` para que también aplique a productos con tag `loncheado`, no solo `cortado`.
- Volver a mostrar el selector de pack en esos productos (revertir el cambio de `data-selector-type` en `sections/main-product.liquid`).
- Decidir los tramos de descuento reales para embutidos (hoy los tramos 10/20/30 → 5/7/10% son específicos de jamón cortado a mano).

---

## 7. Sección "related" vacía en la plantilla de producto genérica

**Contexto:** `templates/product.json` (la plantilla genérica, usada por productos que no encajan en jamones/embutidos/carnes-ibéricas/packs-regalo) tiene una sección "related" tipo `product-grid` sin ningún bloque de producto configurado — es decir, en esa plantilla la sección de "Productos relacionados" probablemente se renderiza vacía. Revisar si algún producto usa esta plantilla genérica y, si es así, fijar productos ahí también (mismo patrón que se corrigió en `product.jamones.json`).

---

## Notas de contexto (por si se retoma este documento más adelante)

- El repo `casamaravillas-theme` está sincronizado como tema **live** de la tienda vía GitHub — cualquier cambio en `main` se refleja en producción tras el sync. Probar siempre primero en un tema de vista previa (`shopify theme push --unpublished`) antes de fusionar.
- Convención de assets: cada sección grande carga su propio CSS/JS (`{{ 'archivo.css' | asset_url | stylesheet_tag }}` + `<script src="..." defer>`), no hay bundle único — seguir ese patrón para nuevos assets.
- Blob de datos Liquid→JS: `window['cmPDP_' + sectionId]` en `main-product.liquid` es la fuente de datos del producto para `main-product.js` (variantes, precio, tags, handle, id, etc.) — cualquier dato nuevo que el JS necesite del lado de Liquid debe añadirse ahí.

---

## 8. Correcciones de octubre 2026 (Luis Juan): pendientes y manual de scripts

Pendientes de código (traducción EN/FR de política, `/pages/envios`, barra del cajón e "IVA incluido"; metacampo `custom.gramaje`; deriva de "Nosotros"),
pendientes de Luis Juan, manual de `tools/` y el recordatorio del 15/11 (carritos de 80–99 € que no compran): ver **`TRASPASO-2026-10-26.md`** (rama `chore/tools-embutidos-y-stock`).
Relacionado con el punto 5 (traducciones en inglés incompletas).

---

## 9. Pendientes de código anotados el 27–28/10/2026

- **Aviso en «Crea tu pack»:** cuando la cesta tiene 2 productos, mostrar «añade un 3.º producto y te llevas un 5 %» (descuento CESTA5-K7Q2, mínimo 3). Código de Kiara (`sections/cesta-builder.liquid`, `assets/cesta-builder.js`).
- **`cart/add.js` con el jamón 9-10 kg agotado (SKU 458):** devuelve 200 (el 25/10 devolvía 422); el checkout lo bloquea («Agotado») y la ficha mantiene el botón desactivado, pero el carrito ya no lo rechaza. Revisar por qué (¿seguimiento de inventario con política DENY en el canal?) antes de depender de ello.
- **IVA del envío para la gestoría:** el envío sale con 0,82 € de IVA (10 %) en el checkout aunque «Charge sales tax on shipping» está desactivado.
- **«Punto de retiro»:** pestaña del checkout sin carrier ni tarifa detrás (no devuelve puntos). Jorge lo desactiva a mano en Ajustes → Envío y entrega.
- **Reglas de descuentos, truncado de céntimos, QR de la tarjeta y nota de los precios de los jamones** (solo con `tools/actualizar_precio_jamon.py`): ver `TRASPASO-2026-10-26.md`, sección 0b.

