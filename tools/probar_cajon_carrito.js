#!/usr/bin/env node
/*
 * Prueba de regresión del cajón del carrito y de la ficha de producto (navegador real, carrito de PRUEBA
 * anónimo: no llega al checkout ni crea pedidos).
 *
 * Comprueba:
 *   1. El encabezado del cajón sigue siendo "TU CESTA (n)" tras añadir desde una ficha (antes quedaba en "5"
 *      porque updateCartCount() pisaba .cart-count) y tras escribir un código de descuento.
 *   2. El cajón no muestra el peso de envío ("0.1 kg").
 *   3. La ficha dice "IVA incluido" y no "Impuestos añadidos".
 *
 * Requisitos: node, Google Chrome y el paquete playwright-core. El paquete no está en el repo; instálalo
 * fuera de él, p. ej.:   mkdir -p /tmp/pw && cd /tmp/pw && npm i playwright-core
 * Uso:
 *   NODE_PATH=/tmp/pw/node_modules node tools/probar_cajon_carrito.js
 *   PREVIEW_THEME_ID=123456 NODE_PATH=... node tools/probar_cajon_carrito.js     # contra un tema sin publicar
 * Variables: BASE (def. https://casamaravillas.com), CHROME (def. ruta de macOS), HANDLE, UDS.
 */
const { chromium } = require('playwright-core');

const BASE = process.env.BASE || 'https://casamaravillas.com';
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const HANDLE = process.env.HANDLE || 'chorizo-bellota-iberico-loncheado';
const UDS = parseInt(process.env.UDS || '5', 10);
const PREVIEW = process.env.PREVIEW_THEME_ID;

const fallos = [];
const check = (ok, texto, dato) => { console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${texto}${dato ? '  → ' + dato : ''}`); if (!ok) fallos.push(texto); };

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await (await browser.newContext({ locale: 'es-ES' })).newPage();
  if (PREVIEW) await page.goto(`${BASE}/?preview_theme_id=${PREVIEW}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  console.log(`Tienda: ${BASE}${PREVIEW ? ' (tema sin publicar ' + PREVIEW + ')' : ' (tema publicado)'} | producto: ${HANDLE} x${UDS}`);

  await page.goto(`${BASE}/products/${HANDLE}`, { waitUntil: 'networkidle', timeout: 60000 });
  const nota = await page.evaluate(() => (document.querySelector('.cm-pdp__tax-note') || {}).innerText || '');
  check(/IVA incluido/.test(nota) && !/a[ñn]adidos/i.test(nota), 'La ficha dice "IVA incluido"', JSON.stringify(nota.trim()));

  await page.evaluate(n => { const i = document.querySelector('input[id^="cm-qty-"]'); i.value = n; i.dispatchEvent(new Event('input', { bubbles: true })); i.dispatchEvent(new Event('change', { bubbles: true })); }, UDS);
  await page.click('button[id^="cm-add-"]');
  await page.waitForTimeout(2500);

  const cabecera = () => page.evaluate(() => { const e = document.querySelector('#cart-drawer .cart-count'); return e ? e.innerText.trim() : null; });
  const esperado = `TU CESTA (${UDS})`;
  const c1 = await cabecera();
  check(c1 === esperado, `Encabezado del cajón tras añadir = "${esperado}"`, JSON.stringify(c1));

  const campo = await page.$('#discount-code');
  if (campo) {
    await campo.fill('PRUEBA');
    await page.waitForTimeout(400);
    const c2 = await cabecera();
    check(c2 === esperado, 'Encabezado del cajón tras escribir un código (sin aplicar)', JSON.stringify(c2));
  } else {
    check(false, 'Existe el campo de código del cajón (#discount-code)');
  }

  /* El peso solo se pintaba cuando el cajón venía del servidor (Liquid), no al repintarlo con JS:
     se comprueba en las dos situaciones (justo tras añadir y tras recargar la página). */
  const leerLineas = () => page.evaluate(() => Array.from(document.querySelectorAll('#cart-drawer .cart-item-info .cart-variant')).map(e => e.innerText.trim()));
  const l1 = await leerLineas();
  check(!l1.some(t => /\d\s*kg\b/i.test(t)), 'El cajón no muestra peso de envío (kg) tras añadir', JSON.stringify(l1));
  await page.reload({ waitUntil: 'networkidle', timeout: 60000 });
  const l2 = await leerLineas();
  check(!l2.some(t => /\d\s*kg\b/i.test(t)), 'El cajón no muestra peso de envío (kg) tras recargar', JSON.stringify(l2));
  const c3 = await cabecera();
  check(c3 === esperado, 'Encabezado del cajón tras recargar', JSON.stringify(c3));

  await browser.close();
  console.log(fallos.length ? `${fallos.length} comprobación(es) FALLIDA(S).` : 'Todo OK.');
  process.exit(fallos.length ? 1 : 0);
})().catch(e => { console.error('ERROR', e.message.split('\n')[0]); process.exit(2); });
