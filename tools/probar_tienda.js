#!/usr/bin/env node
/*
 * Comprobaciones de la tienda publicada desde un NAVEGADOR REAL (Chrome vía playwright-core), con carritos de
 * PRUEBA de la Storefront API (cartCreate: no crea pedidos ni checkouts). Equivale a probar_descuentos_embutido.py
 * y probar_envio_gratis.py, pero con el cliente de un cliente real: la tienda limita (429 "local_rate_limited")
 * a los clientes HTTP de scripts cuando se les da mucho tráfico.
 *
 * Modos:
 *   descuentos --esperado 5 [--ficha]     descuento por volumen del embutido (5|10) y, con --ficha, que la ficha
 *                                         publicada promete lo mismo (lee main-product.js)
 *   envio --umbral 99 [--ficha]           envío gratis con carritos de ~85 € y ~99,50 €, con y sin BIENVENIDA10
 *                                         (el umbral se mide DESPUÉS de los descuentos); con --ficha, que la
 *                                         tienda anuncia el umbral (portada, /pages/envios) y no el antiguo
 *
 * Requisitos: node, Google Chrome y playwright-core fuera del repo (p. ej. mkdir /tmp/pw && cd /tmp/pw && npm i playwright-core).
 *   NODE_PATH=/tmp/pw/node_modules node tools/probar_tienda.js descuentos --esperado 5 --ficha
 *   NODE_PATH=/tmp/pw/node_modules node tools/probar_tienda.js envio --umbral 99 --ficha
 * Variables: BASE (def. https://casamaravillas.com), CHROME (def. ruta de macOS).
 */
const { chromium } = require('playwright-core');

const BASE = process.env.BASE || 'https://casamaravillas.com';
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const WELCOME = 'BIENVENIDA10';
const args = process.argv.slice(2);
const modo = args[0];
const opt = n => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : undefined; };
const flag = n => args.includes('--' + n);
let fallos = 0;
const out = (ok, txt) => { if (!ok) fallos++; console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${txt}`); };
const r2 = x => Math.round(x * 100) / 100;

// Total que cobra Shopify: redondea el descuento de CADA unidad al céntimo (mitades hacia abajo)
const conDto = (precioCents, uds, pct) => uds * (precioCents - Math.floor((precioCents * pct + 49) / 100)) / 100;

async function iniciar() {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  const page = await (await browser.newContext({ locale: 'es-ES' })).newPage();
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  return { browser, page };
}

// Llamadas desde la propia página (mismo origen), como hace el tema
const variante = (page, handle) => page.evaluate(async h => {
  const p = await (await fetch(`/products/${h}.js`)).json();
  return { id: p.variants[0].id, price: p.variants[0].price };
}, handle);

const carrito = (page, lines, codes = []) => page.evaluate(async ({ lines, codes }) => {
  const Q = `mutation($i:CartInput!){ cartCreate(input:$i){ cart{ cost{ subtotalAmount{amount} totalAmount{amount} }
    discountCodes{ code applicable }
    discountAllocations{ __typename discountedAmount{ amount } ... on CartAutomaticDiscountAllocation{ title } ... on CartCodeDiscountAllocation{ code } } } userErrors{ message } } }`;
  const i = { lines: lines.map(l => ({ merchandiseId: `gid://shopify/ProductVariant/${l.id}`, quantity: l.q })), discountCodes: codes,
    buyerIdentity: { countryCode: 'ES', deliveryAddressPreferences: [{ deliveryAddress: { address1: 'Calle Mayor 1', city: 'Madrid', zip: '28013', country: 'ES', province: 'M' } }] } };
  const r = await (await fetch('/api/2025-07/graphql.json', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: Q, variables: { i } }) })).json();
  const c = r.data.cartCreate.cart;
  const esEnvio = a => a.title && a.title.includes('nvío');
  const dtoPedido = c.discountAllocations.filter(a => !esEnvio(a)).reduce((s, a) => s + parseFloat(a.discountedAmount.amount), 0);
  return { total: parseFloat(c.cost.totalAmount.amount), neto: parseFloat(c.cost.subtotalAmount.amount) - dtoPedido,
           envioGratis: c.discountAllocations.some(esEnvio), titulo: c.discountAllocations.filter(esEnvio).map(a => a.title), codigos: c.discountCodes };
}, { lines, codes });

async function descuentos(page) {
  const pct = parseInt(opt('esperado'), 10);
  if (![5, 10].includes(pct)) throw new Error('Falta --esperado 5|10');
  const [jam, a, b] = await Promise.all([variante(page, 'jamon-bellota-100-iberico-loncheado-a-maquina'), variante(page, 'chorizo-bellota-iberico-loncheado'), variante(page, 'salchichon-bellota-iberico-loncheado')]);
  const casos = [
    ['4 chorizo loncheado (bajo el umbral)', [{ id: a.id, q: 4 }], [], r2(4 * a.price / 100)],
    [`5 chorizo loncheado (-${pct} %)`, [{ id: a.id, q: 5 }], [], r2(conDto(a.price, 5, pct))],
    [`5 chorizo + 5 salchichón (-${pct} % cada línea)`, [{ id: a.id, q: 5 }, { id: b.id, q: 5 }], [], r2(conDto(a.price, 5, pct) + conDto(b.price, 5, pct))],
    ['10 jamón a máquina (-10 %, no cambia)', [{ id: jam.id, q: 10 }], [], r2(conDto(jam.price, 10, 10))],
    [`5 chorizo + ${WELCOME} (gana el 10 % sobre todo el carrito)`, [{ id: a.id, q: 5 }], [WELCOME], r2(conDto(a.price, 5, 10))],
  ];
  for (const [txt, lines, codes, esperado] of casos) {
    const c = await carrito(page, lines, codes);
    // El total incluye el envío si no es gratis: se compara el neto de la compra
    out(Math.abs(c.neto - esperado) < 0.011, `${txt.padEnd(62)} neto ${c.neto.toFixed(2)} € (esperado ${esperado.toFixed(2)})${codes.length ? '  códigos ' + JSON.stringify(c.codigos.map(d => [d.code, d.applicable])) : ''}`);
  }
  if (flag('ficha')) {
    const ok = await page.evaluate(async ({ pct }) => {
      const html = await (await fetch('/products/chorizo-bellota-iberico-loncheado?cb=' + Date.now())).text();
      const m = html.match(/(?:https:)?\/\/[^"']*main-product\.js[^"']*/); if (!m) return false;
      const js = await (await fetch(m[0].startsWith('http') ? m[0] : 'https:' + m[0])).text();
      return new RegExp('embutido:\\s*\\{\\s*minQty:\\s*5,\\s*pct:\\s*' + pct + '\\s*\\}').test(js) && /jamon:\s*\{\s*minQty:\s*10,\s*pct:\s*10\s*\}/.test(js);
    }, { pct });
    out(ok, `ficha publicada: JS con embutido -${pct} % desde 5 uds y jamón -10 % desde 10 uds`);
  }
}

async function envio(page) {
  const umbral = parseInt(opt('umbral'), 10);
  if (!umbral) throw new Error('Falta --umbral 80|99');
  // Productos SIN descuento por volumen en estas cantidades máximas (el total es predecible)
  const CAT = [['lomo-bellota-iberico', 5], ['lomito-presa-bellota', 5], ['lomo-cebo-campo-50-iberico', 5], ['chorizo-bellota-iberico', 5],
               ['jamon-bellota-100-iberico-loncheado-a-maquina', 9], ['jamon-bellota-100-iberico-loncheado-a-mano', 9], ['chorizo-bellota-iberico-loncheado', 4]];
  const vs = []; for (const [h, mx] of CAT) vs.push({ h, mx, ...(await variante(page, h)) });
  const combo = objetivo => {
    let mejor = null; const cant = new Array(vs.length).fill(0);
    const rec = (i, total) => {
      if (i === vs.length) { if (cant.some(c => c) && (!mejor || Math.abs(total - objetivo) < Math.abs(mejor.total - objetivo))) mejor = { total, cant: [...cant] }; return; }
      for (let c = 0; c <= vs[i].mx; c++) { cant[i] = c; rec(i + 1, total + c * vs[i].price); if (mejor && mejor.total === objetivo) return; }
      cant[i] = 0;
    };
    rec(0, 0); return mejor;
  };
  console.log(`Umbral esperado: ${umbral} € (medido tras descuentos)`);
  for (const objetivo of [8500, 9950]) {
    const m = combo(objetivo);
    const lines = vs.map((v, i) => ({ id: v.id, q: m.cant[i], h: v.h })).filter(l => l.q);
    for (const codes of [[], [WELCOME]]) {
      const c = await carrito(page, lines.map(l => ({ id: l.id, q: l.q })), codes);
      const esperado = c.neto >= umbral;
      out(c.envioGratis === esperado, `bruto ${(m.total / 100).toFixed(2)} € | ${codes.length ? 'con ' + WELCOME : 'sin código  '} | neto ${c.neto.toFixed(2)} € | envío gratis: ${c.envioGratis ? 'SÍ' : 'no'} (esperado ${esperado ? 'SÍ' : 'no'})${c.titulo.length ? '  ' + JSON.stringify(c.titulo) : ''}`);
    }
    console.log('        carrito: ' + lines.map(l => `${l.q}×${l.h}`).join(' + '));
  }
  if (flag('ficha')) {
    const viejo = String(umbral === 99 ? 80 : 99);
    const r = await page.evaluate(async () => {
      let t = ''; for (const u of ['/', '/pages/envios', '/en', '/fr']) { const h = await (await fetch(u)).text(); t += ' ' + h.replace(/<script[\s\S]*?<\/script>/g, ' ').replace(/<[^>]+>/g, ' '); }
      return t;
    });
    const cuenta = n => (r.match(new RegExp('(?<![\\d.,])' + n + '(?:[.,]00)?\\s?(?:€|&euro;|euros?)|€\\s?' + n + '(?![\\d])', 'gi')) || []).length;
    out(cuenta(String(umbral)) > 0 && cuenta(viejo) === 0, `la tienda anuncia ${umbral} € (${cuenta(String(umbral))} menciones en portada, /pages/envios, /en y /fr) y ninguna dice ${viejo} €`);
  }
}

(async () => {
  if (!['descuentos', 'envio'].includes(modo)) { console.error('Uso: probar_tienda.js descuentos --esperado 5 [--ficha] | envio --umbral 99 [--ficha]'); process.exit(2); }
  const { browser, page } = await iniciar();
  try { await (modo === 'descuentos' ? descuentos : envio)(page); } finally { await browser.close(); }
  console.log(fallos ? `${fallos} comprobación(es) FALLIDA(S).` : 'Todo OK.');
  process.exit(fallos ? 1 : 0);
})().catch(e => { console.error('ERROR', e.message.split('\n')[0]); process.exit(2); });
