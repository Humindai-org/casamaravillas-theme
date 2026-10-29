/* Impuestos del checkout con 3 jamones loncheados a mano (41,97 €), 27/10/2026: modo «envio» (dirección de Alicante) y
   modo «retiro» (Retiro en tienda). Se llega hasta el paso de envío/pago SIN pagar y deja un checkout abandonado con
   prueba-claude@example.com. Resultado del 27/10: 7,28 € (21 %, estimación) antes de enviar la dirección; con la dirección
   de Alicante 4,63 € (3,81 € de producto al 10 % + 0,82 € del envío); con retiro en tienda 3,82 €.
   Uso:  NODE_PATH=/tmp/pw/node_modules node tools/probar_impuestos_checkout.js  (SHOTDIR=<carpeta> guarda capturas; opcional) */
const { chromium } = require('playwright-core');
const BASE = 'https://casamaravillas.com';
(async () => {
  const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
  for (const modo of ['envio', 'retiro']) {
    const ctx = await b.newContext({ locale: 'es-ES', viewport: { width: 1280, height: 1100 } }); const page = await ctx.newPage();
    await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    const car = await page.evaluate(async () => {
      const v = (await (await fetch('/products/jamon-bellota-50-iberico-loncheado-a-mano.js')).json()).variants[0];
      await fetch('/cart/add.js', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: v.id, quantity: 3 }) });
      const c = await (await fetch('/cart.js')).json(); return c.items.map(i => `${i.quantity} × ${i.product_title} SKU ${i.sku} = ${i.final_line_price / 100} €`).join(' | ') + ' | total ' + c.total_price / 100;
    });
    console.log(`\n== modo ${modo} == carrito:`, car);
    const res = async () => { const t = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ')); let i = t.search(/Subtotal/); return i < 0 ? '(sin resumen)' : t.slice(i, i + 200).replace(/Abre sitio.*/, ''); };
    await page.goto(BASE + '/checkout', { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(6000);
    console.log('1) checkout sin dirección :', await res());
    const fill = async (sel, v) => { const l = page.locator(sel).first(); if (await l.count()) await l.fill(v).catch(() => {}); };
    await fill('input[name="email"]', 'prueba-claude@example.com');
    if (modo === 'retiro') { await page.getByText('Retiro en tienda').first().click().catch(() => {}); await page.waitForTimeout(3000); }
    else {
      const sel = page.locator('select[name="countryCode"]'); if (await sel.count()) await sel.selectOption('ES').catch(() => {});
      await page.waitForTimeout(1500);
      await fill('input[name="firstName"]', 'Prueba'); await fill('input[name="lastName"]', 'Claude'); await fill('input[name="address1"]', 'Calle Castaños 10');
      await fill('input[name="postalCode"]', '03001'); await fill('input[name="city"]', 'Alicante');
      const z = page.locator('select[name="zone"]'); if (await z.count()) await z.selectOption({ label: 'Alicante' }).catch(() => {});
      await fill('input[name="phone"]', '600000000');
    }
    await page.waitForTimeout(4000);
    console.log('2) dirección rellena (aún en el paso de información):', await res());
    if (modo === 'retiro') { const t = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ')); const i = t.indexOf('Retiro en tienda'); console.log('   bloque retiro:', t.slice(i, i + 330)); if (process.env.SHOTDIR) await page.screenshot({ path: process.env.SHOTDIR + '/imp_retiro.png', fullPage: true }); }
    await page.getByRole('button', { name: /Continuar con envíos|Continuar con el pago|Continuar/ }).first().click().catch(() => {});
    await page.waitForTimeout(7000);
    const t3 = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ')); const j = t3.search(/Método de envío|Métodos de envío|Retiro en tienda/);
    console.log('3) paso siguiente:', t3.slice(j, j + 170));
    console.log('   resumen:', await res());
    if (process.env.SHOTDIR) await page.screenshot({ path: `${process.env.SHOTDIR}/imp_${modo}.png`, fullPage: true });
    await page.evaluate(async () => { await fetch('/cart/clear.js', { method: 'POST' }); });
    await ctx.close();
  }
  await b.close();
})().catch(e => { console.error('ERROR', e.message.split('\n')[0]); process.exit(1); });
