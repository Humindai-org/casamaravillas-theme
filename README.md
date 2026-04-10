# Casa Maravillas — Shopify Theme

Tema Shopify OS 2.0 para [casamaravillas.com](https://casamaravillas.com).
Diseño: T2 White & Gold Modern. Desarrollado por HumindAI.

## Despliegue

### Opción A — Subir ZIP al admin (recomendada para primera instalación)

1. Comprimir toda la carpeta `theme/` en un ZIP:
   ```bash
   cd /path/to/casamaravillas-ecommerce
   zip -r casa-maravillas-theme.zip theme/
   ```
2. En Shopify Admin → **Tienda online** → **Temas** → **Añadir tema** → **Subir archivo ZIP**
3. Seleccionar `casa-maravillas-theme.zip`
4. Una vez subido: **Personalizar** para configurar logos, imágenes y textos

### Opción B — Shopify CLI (para desarrollo activo)

```bash
npm install -g @shopify/cli @shopify/theme
cd theme/
shopify theme dev --store=casamaravillas.myshopify.com
```

### Opción C — GitHub sync

1. Subir la carpeta `theme/` a un repositorio GitHub
2. En Shopify Admin → **Tienda online** → **Temas** → **Añadir tema** → **Conectar desde GitHub**

---

## Estructura

```
theme/
├── assets/
│   ├── base.css          ← Variables CSS, reset, utilidades globales
│   └── theme.js          ← Mobile nav, sticky header, cart count
├── config/
│   ├── settings_schema.json   ← Opciones del customizer
│   └── settings_data.json     ← Valores por defecto
├── layout/
│   └── theme.liquid      ← HTML wrapper principal
├── locales/
│   └── es.default.json   ← Traducciones en español
├── sections/
│   ├── announcement-bar.liquid   ← Barra top navy
│   ├── header.liquid             ← Nav sticky con logo centrado
│   ├── hero-split.liquid         ← Hero 2 columnas
│   ├── trust-band.liquid         ← 4 pilares de confianza
│   ├── featured-product.liquid   ← Producto destacado (fondo navy)
│   ├── product-grid.liquid       ← Grid de 4 productos
│   ├── about-split.liquid        ← Historia + stats
│   ├── marquee-strip.liquid      ← Texto animado dorado
│   ├── newsletter.liquid         ← Suscripción email
│   ├── footer.liquid             ← Footer completo
│   ├── header-group.json         ← Grupo OS 2.0 para cabecera
│   └── footer-group.json         ← Grupo OS 2.0 para footer
├── snippets/
│   ├── product-card.liquid   ← Tarjeta de producto reutilizable
│   ├── meta-tags.liquid      ← OG/Twitter meta tags
│   └── icon-sprite.liquid    ← (pendiente — SVG icons)
└── templates/
    ├── index.json        ← Homepage con todas las secciones
    ├── product.json      ← Página de producto
    ├── collection.json   ← Colección/categoría
    ├── cart.json         ← Carrito
    ├── page.json         ← Páginas estáticas
    ├── blog.json         ← Blog index
    ├── article.json      ← Post del blog
    └── 404.json          ← Error 404
```

## Logos

- **Nav (fondo blanco):** subir `Logos/logo2.png` en Customizer → Cabecera → Logo
- **Footer (fondo navy):** subir `Logos/logo1.png` en Customizer → Footer → Logo versión clara

## Paleta de colores

| Token | Hex | Uso |
|-------|-----|-----|
| Navy | `#0D1B2A` | Fondo oscuro, nav, footer |
| Gold | `#B8903A` | Acentos, botones, eyebrows |
| Gold hover | `#D4AB5E` | Estados hover del gold |
| Off-white | `#FAFAF7` | Fondo secundario |
| Text | `#1A1814` | Texto principal |
| Text muted | `#6A6560` | Texto secundario |
| Border | `#E8E5DF` | Líneas divisorias |

## Tipografía

- **Títulos:** Libre Baskerville (Google Fonts, 400 regular + italic)
- **Cuerpo:** Outfit (Google Fonts, 200–600)

## Notas importantes

- Las secciones `main-product`, `main-collection`, `main-cart`, `main-page`, `main-blog`, `main-article`, `main-404` las provee el tema base Fabric. Solo se sobreescriben los estilos via `base.css` y se añaden las secciones personalizadas.
- El formulario de newsletter usa el sistema nativo de Shopify Customers. Para conectarlo con Brevo/Mailchimp, configurar la integración desde el admin de Shopify.
