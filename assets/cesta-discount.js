/* Descuento de "Crea tu cesta": un código que se pone al carrito mientras haya una cesta con, al menos,
   el mínimo de productos, y se quita cuando deja de haberla. Así no se arrastra a compras que no son cesta.
   Regla: el cliente recibe siempre el mayor descuento, así que BIENVENIDA10 (10 %) gana siempre a la cesta (5 %).
   Si el cliente llegó con ese código (cookie discount_code, o ya puesto en el carrito) nunca se pisa: con una cesta
   completa se mandan los dos códigos a la vez (BIENVENIDA10,CESTA5-...) y Shopify aplica el mejor; así, si en el
   checkout rechaza el de bienvenida (ya usado por ese cliente), el de la cesta sigue puesto.
   Cuando la cesta deja de dar descuento se queda solo BIENVENIDA10, en vez de dejar el carrito sin código.
   Config: window.cmCestaDiscount = { code, qty } (Ajustes del tema > Crea tu cesta);
           window.cmCestaDiscount.welcome (opcional) cambia el código de bienvenida. */
(function () {
  'use strict';
  var cfg = window.cmCestaDiscount;
  if (!cfg || !cfg.code) return;
  var FLAG = 'cm-cesta-code';
  var WELCOME = String(cfg.welcome || 'BIENVENIDA10').toUpperCase();
  var CESTA = String(cfg.code).toUpperCase();
  var busy = false;
  var lastTry = '';
  var welcomeBad = false; /* Shopify lo marcó no aplicable en esta página: no insistir */

  function flag(on) {
    try { if (on) localStorage.setItem(FLAG, '1'); else localStorage.removeItem(FLAG); } catch (e) {}
  }
  function flagged() {
    try { return localStorage.getItem(FLAG) === '1'; } catch (e) { return false; }
  }
  /* Cookie que deja /discount/BIENVENIDA10 (la URL de la tarjeta); Shopify la guarda tal cual se escribió */
  function welcomeCookie() {
    var m = document.cookie.match(/(?:^|;\s*)discount_code=([^;]*)/);
    if (!m) return false;
    try { return decodeURIComponent(m[1]).toUpperCase() === WELCOME; } catch (e) { return false; }
  }
  /* Unidades de las líneas que vienen del constructor (marca _cesta_id) */
  function cestaUnits(cart) {
    return (cart.items || []).reduce(function (n, i) {
      var p = i.properties || {};
      return n + (p._cesta_id && !p._cesta_caja ? i.quantity : 0);
    }, 0);
  }
  /* Códigos que lleva el carrito, aunque Shopify no aplique alguno (p. ej. el de la cesta cuando gana el de bienvenida) */
  function codesOf(cart) {
    return (cart.discount_codes || []).map(function (d) { return String(d.code || '').toUpperCase(); });
  }
  /* Shopify marca applicable:false un código que no vale para este carrito: no insistimos con él */
  function welcomeRejected(cart) {
    return (cart.discount_codes || []).some(function (d) {
      return String(d.code || '').toUpperCase() === WELCOME && d.applicable === false;
    });
  }
  function setCode(code) {
    return fetch('/cart/update.js', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ discount: code })
    }).then(function (r) { return r.json(); });
  }
  function refreshUi() {
    if (window.fetchAndRenderCart) return window.fetchAndRenderCart();
  }

  /* Códigos que debe llevar el carrito: bienvenida si el cliente la trae (y, con cesta completa, también el de la
     cesta como respaldo), si no la cesta si llega al mínimo */
  function target(cart) {
    var codes = codesOf(cart);
    if (welcomeRejected(cart)) welcomeBad = true;
    var welcome = (welcomeCookie() || codes.indexOf(WELCOME) >= 0) && !welcomeBad;
    var cesta = cestaUnits(cart) >= (cfg.qty || 3);
    var want = [];
    if (welcome) want.push(WELCOME);
    if (cesta) want.push(CESTA);
    return want;
  }

  function same(a, b) {
    return a.length === b.length && a.every(function (c) { return b.indexOf(c) >= 0; });
  }

  function change(want, cart) {
    /* sin reintentos con el mismo carrito: si Shopify no acepta los códigos, no entramos en bucle con el cajón */
    var sig = want.join(',') + '|' + cart.items.map(function (i) { return i.key + ':' + i.quantity; }).join(',');
    if (sig === lastTry) return Promise.resolve();
    lastTry = sig;
    busy = true;
    return setCode(want.join(',')).then(function () { flag(want.indexOf(CESTA) >= 0); return refreshUi(); })
      .catch(function () {}).then(function () { busy = false; });
  }

  function sync(cart) {
    if (busy || !cart || !cart.items || !cart.items.length) return Promise.resolve();
    var want = target(cart);
    var codes = codesOf(cart);
    /* solo nos importan nuestros dos códigos: los que ya lleva el carrito de ellos frente a los que tocan */
    var have = codes.filter(function (c) { return c === WELCOME || c === CESTA; });
    if (same(have, want)) {
      flag(want.indexOf(CESTA) >= 0);
      lastTry = '';
      return Promise.resolve();
    }
    /* ya no toca ninguno y no pusimos el de la cesta: el carrito lleva un código ajeno, no se toca */
    if (!want.length && !have.length && !flagged()) { lastTry = ''; return Promise.resolve(); }
    return change(want, cart);
  }

  /* sin argumento: lee el carrito; con carrito: lo usa tal cual (lo llama el cajón al actualizarse) */
  window.cmSyncCestaCode = function (cart) {
    if (cart) return sync(cart);
    return fetch('/cart.js').then(function (r) { return r.json(); }).then(sync);
  };

  /* Al cargar cualquier página: si pusimos el código antes, o llegó con la cookie de bienvenida,
     comprueba que el carrito lleva el código que toca */
  if (flagged() || welcomeCookie()) window.cmSyncCestaCode().catch(function () {});
})();
