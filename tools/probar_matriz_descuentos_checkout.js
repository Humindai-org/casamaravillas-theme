/* Matriz de descuentos de la cesta y BIENVENIDA10 (27/10/2026): carrito, cajón y checkout hasta la página de pago
   (dirección de Alicante, SIN pagar: no se hace ningún pedido). Casos a–h (ver CASOS abajo). Cada caso usa un navegador
   nuevo, vacía el carrito al terminar y deja un checkout abandonado con prueba-claude@example.com.
   Uso:  NODE_PATH=/tmp/pw/node_modules node tools/probar_matriz_descuentos_checkout.js
         PREVIEW_THEME_ID=<id> CASOS=a,b SIN_CHECKOUT=1 SHOTDIR=/tmp/capturas  (todas opcionales)
   Esperado (regla: el cliente recibe siempre el mayor descuento, sin acumular): con cookie BIENVENIDA10 gana siempre al 5 %
   de la cesta; sin código y con 3 de la cesta, 5 %; con 2, nada. Solo lee y navega. */
const { chromium } = require('playwright-core');
const PREVIEW = process.env.PREVIEW_THEME_ID;           // vacío = tema publicado
const ONLY = (process.env.CASOS || 'a,b,c,d,e,f,g,h').split(',');
const BASE = 'https://casamaravillas.com';
const EUR = n => (n / 100).toFixed(2).replace('.', ',') + ' €';
const P = { lomo: 'lomo-bellota-iberico', chorizo: 'chorizo-bellota-iberico', jamon: 'jamon-bellota-100-iberico-loncheado-a-maquina',
  mano: 'jamon-bellota-50-iberico-loncheado-a-mano', chorizoL: 'chorizo-bellota-iberico-loncheado' };
const CESTA = { 'Cesta': 'Tu pack personalizado', '_cesta_id': 'prueba-claude-3' };

const CASOS = {
  a: { desc: 'por /discount/BIENVENIDA10 con 1 producto', cookie: true, items: [[P.chorizo, 1]] },
  b: { desc: 'cookie + 3 productos de la cesta', cookie: true, items: [[P.lomo, 1, CESTA], [P.chorizo, 1, CESTA], [P.jamon, 1, CESTA]] },
  c: { desc: 'cookie + 3 de la cesta y quitando 1', cookie: true, items: [[P.lomo, 1, CESTA], [P.chorizo, 1, CESTA], [P.jamon, 1, CESTA]], quitar: true },
  d: { desc: 'sin código + 3 de la cesta (debe dar el 5 %)', cookie: false, items: [[P.lomo, 1, CESTA], [P.chorizo, 1, CESTA], [P.jamon, 1, CESTA]] },
  e: { desc: 'sin código + 2 de la cesta', cookie: false, items: [[P.lomo, 1, CESTA], [P.chorizo, 1, CESTA]] },
  f: { desc: 'cookie + 5 chorizos loncheados (el volumen no se suma)', cookie: true, items: [[P.chorizoL, 5]] },
  h: { desc: 'los dos códigos puestos a la vez (BIENVENIDA10,CESTA5-K7Q2) sin cookie, 3 de la cesta', cookie: false, codigos: 'BIENVENIDA10,CESTA5-K7Q2', items: [[P.lomo, 1, CESTA], [P.chorizo, 1, CESTA], [P.jamon, 1, CESTA]] },
  g: { desc: 'EXTRA sin código + 5 chorizos loncheados dentro de la cesta (¿se suman cesta y volumen?)', cookie: false, items: [[P.chorizoL, 5, CESTA]] },
};

async function cartInfo(page) {
  return page.evaluate(async () => {
    const c = await (await fetch('/cart.js')).json();
    return { sub: c.original_total_price, total: c.total_price, dto: c.total_discount,
      codigos: (c.discount_codes || []).map(d => d.code + (d.applicable === false ? '(no aplicable)' : '')),
      apps: [...(c.cart_level_discount_applications || []).map(a => a.type + ':' + a.title + ' ' + a.total_allocated_amount / 100),
             ...[...new Set(c.items.flatMap(i => (i.discounts || []).map(d => 'línea:' + d.title)))]] };
  });
}
async function drawer(page) {
  await page.evaluate(async () => { await window.fetchAndRenderCart(); window.openCart && window.openCart(true); });
  await page.waitForTimeout(2500);
  return page.evaluate(() => { const g = id => (document.getElementById(id) || {}).textContent; const r = document.getElementById('cart-discount-row');
    return { subtotal: g('cart-subtotal'), descuento: r && !r.hidden ? g('cart-discount') : '(sin fila)', total: g('cart-total') }; });
}
async function checkout(page, shot) {
  await page.goto(BASE + '/checkout', { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(6000);
  const fill = async (sel, v) => { const l = page.locator(sel).first(); if (await l.count()) { await l.fill(v).catch(() => {}); } };
  await fill('input[name="email"]', 'prueba-claude@example.com');
  const sel = page.locator('select[name="countryCode"]'); if (await sel.count()) await sel.selectOption('ES').catch(() => {});
  await page.waitForTimeout(1500);
  await fill('input[name="firstName"]', 'Prueba'); await fill('input[name="lastName"]', 'Claude');
  await fill('input[name="address1"]', 'Calle Castaños 10'); await fill('input[name="postalCode"]', '03001'); await fill('input[name="city"]', 'Alicante');
  const z = page.locator('select[name="zone"]'); if (await z.count()) await z.selectOption({ label: 'Alicante' }).catch(() => z.selectOption('A').catch(() => {}));
  await fill('input[name="phone"]', '600000000');
  await page.waitForTimeout(4000);
  const resumen = async () => { const t = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ')); let i = t.search(/Subtotal/); if (i < 0) i = t.search(/Resumen de costos/); return i < 0 ? "(sin resumen) " + t.slice(0, 120) : t.slice(i, i + 330); };
  const out = { info: await resumen() };
  await page.getByRole('button', { name: /Continuar con envíos/ }).click().catch(() => {});
  await page.waitForTimeout(7000);
  let t = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' '));
  const j = t.search(/Método de envío|Métodos de envío/);
  out.envioOpciones = j >= 0 ? t.slice(j, j + 260) : '(no llegó al paso de envío) ' + t.slice(0, 160);
  out.envio = await resumen();
  if (shot) await page.screenshot({ path: shot.replace('.png', '_envio.png'), fullPage: true });
  await page.getByRole('button', { name: /Continuar con el pago|Continuar al pago/ }).click().catch(() => {});
  await page.waitForTimeout(7000);
  t = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' '));
  out.enPago = /Pago|Tarjeta de crédito|Número de tarjeta/.test(t) && /Pagar ahora|Número de tarjeta|Tarjeta/.test(t);
  out.pago = await resumen();
  if (shot) await page.screenshot({ path: shot.replace('.png', '_pago.png'), fullPage: true });
  return out;
}

(async () => {
  const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
  for (const k of ONLY) {
    const caso = CASOS[k]; if (!caso) continue;
    const ctx = await b.newContext({ locale: 'es-ES', viewport: { width: 1280, height: 1100 } });
    const page = await ctx.newPage(); const errs = []; page.on('pageerror', e => errs.push(e.message.slice(0, 80)));
    await page.goto(BASE + '/' + (PREVIEW ? '?preview_theme_id=' + PREVIEW : ''), { waitUntil: 'networkidle', timeout: 60000 });
    const tema = await page.evaluate(() => Shopify.theme.id);
    if (caso.cookie) await page.goto(BASE + '/discount/BIENVENIDA10?redirect=/collections/regalos-ibericos', { waitUntil: 'networkidle', timeout: 60000 });
    await page.evaluate(async (items) => {
      for (const [h, q, props] of items) {
        const v = (await (await fetch('/products/' + h + '.js')).json()).variants[0].id;
        await fetch('/cart/add.js', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: v, quantity: q, properties: props || undefined }) });
      }
    }, caso.items);
    if (caso.codigos) await page.evaluate(async (c) => { await fetch('/cart/update.js', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ discount: c }) }); }, caso.codigos);
    let d = await drawer(page);               // lo mismo que hace el cajón al abrirse (fetchAndRenderCart → cmSyncCestaCode)
    await page.waitForTimeout(1500); d = await drawer(page);
    if (caso.quitar) { await page.evaluate(async () => { await fetch('/cart/change.js', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ line: 1, quantity: 0 }) }); });
      d = await drawer(page); await page.waitForTimeout(1500); d = await drawer(page); }
    const c = await cartInfo(page);
    console.log(`\n(${k}) ${caso.desc} [tema ${tema}]`);
    console.log('   carrito:', JSON.stringify({ subtotal: EUR(c.sub), descuento: EUR(c.dto), total: EUR(c.total), codigos: c.codigos, apps: c.apps, updates: global.__n }));
    console.log('   cajón  :', JSON.stringify(d));
    if (!process.env.SIN_CHECKOUT) { const ck = await checkout(page, process.env.SHOTDIR ? `${process.env.SHOTDIR}/checkout_${k}.png` : null); console.log('   checkout (info)  :', ck.info); console.log('   checkout (envío):', ck.envioOpciones); console.log('   checkout (envío, resumen):', ck.envio); console.log('   checkout (pago, en pago=' + ck.enPago + '):', ck.pago); }
    console.log('   errores JS:', errs.length ? [...new Set(errs)] : 'ninguno');
    await page.evaluate(async () => { await fetch('/cart/clear.js', { method: 'POST' }); });
    await ctx.close();
  }
  await b.close();
})().catch(e => { console.error('ERROR', e.message.split('\n')[0]); process.exit(1); });
