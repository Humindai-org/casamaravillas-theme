---
name: Shopify Dev Setup - Casamaravillas
description: Comandos y configuración del entorno de desarrollo Shopify para Casamaravillas
type: reference
---

**Tienda:** casa-maravillas-2.myshopify.com
**Cuenta admin:** adminweb@casamaravillas.com
**Theme ID en dev:** 199052525906
**Preview URL:** https://casa-maravillas-2.myshopify.com/?preview_theme_id=199052525906

**Contraseña del storefront:** guardada en macOS Keychain
- Recuperar: `security find-generic-password -a "shopify-casamaravillas" -s "shopify-theme-password" -w`

**Comando para arrancar dev server (correr en terminal interactiva del usuario):**
```bash
cd "/Users/giorgio/Jorge/AI Automation/HumindAI/Claude Code/web/casamaravillas-theme"
shopify theme dev --store casa-maravillas-2.myshopify.com
```
- El `--password` del storefront NO es necesario para el dev server (causa conflicto con auth)
- Dev server corre en localhost:9292 pero usar siempre la preview URL de Shopify para revisar cambios
- Si aparece error 401: `shopify auth logout` + `shopify auth login`

**Push/Pull:**
```bash
shopify theme push --store casa-maravillas-2.myshopify.com
shopify theme pull --store casa-maravillas-2.myshopify.com
```

**Notas auth:**
- La cuenta adminweb@casamaravillas.com es staff account vinculada a Partners — funciona con OAuth directo a la tienda, NO con token de custom app
- La tienda es development store de Partners, por eso no permite crear custom apps con token directo desde el admin

**Assets:**
- logo2-sin-bg.png — logo navy sobre fondo transparente (para header blanco)
- logo3-sin-bg.png — logo blanco sobre fondo transparente (para footer/hero oscuro)
