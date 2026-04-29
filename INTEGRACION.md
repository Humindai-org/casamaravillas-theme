# INSTRUCCIONES DE INTEGRACIÓN EN SHOPIFY
# ==========================================
# Pega estas líneas en theme.liquid exactamente donde se indica.
# NO modifiques el diseño ni el JS.

# ── 1. DENTRO DE <head> ── antes de </head>
{{ 'cart-drawer.css' | asset_url | stylesheet_tag }}

# ── 2. ANTES DE </body> ── al final del <body>
{% render 'cart-drawer' %}
<script src="{{ 'cart-drawer.js' | asset_url }}" defer></script>

# ── 3. BOTÓN DEL CARRITO EN EL HEADER ──
# Busca el botón/icono del carrito en tu header (normalmente en header.liquid
# o sections/header.liquid) y añádele: onclick="openCart()"
# Ejemplo:
<a href="/cart" onclick="event.preventDefault(); openCart();" aria-label="Abrir cesta">
  <!-- tu icono de carrito existente -->
</a>

# ── 4. ARCHIVOS A SUBIR ──
# Sube estos 3 archivos a Shopify:
#   cart-drawer.liquid  →  snippets/cart-drawer.liquid
#   cart-drawer.css     →  assets/cart-drawer.css
#   cart-drawer.js      →  assets/cart-drawer.js
