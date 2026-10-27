/* Descuento de "Crea tu cesta": un código que se pone al carrito mientras haya una cesta con, al menos,
   el mínimo de productos, y se quita cuando deja de haberla. Así no se arrastra a compras que no son cesta.
   Config: window.cmCestaDiscount = { code, qty } (Ajustes del tema > Crea tu cesta). */
(function () {
  'use strict';
  var cfg = window.cmCestaDiscount;
  if (!cfg || !cfg.code) return;
  var FLAG = 'cm-cesta-code';
  var busy = false;

  function flag(on) {
    try { if (on) localStorage.setItem(FLAG, '1'); else localStorage.removeItem(FLAG); } catch (e) {}
  }
  function flagged() {
    try { return localStorage.getItem(FLAG) === '1'; } catch (e) { return false; }
  }
  /* Unidades de las líneas que vienen del constructor (marca _cesta_id) */
  function cestaUnits(cart) {
    return (cart.items || []).reduce(function (n, i) {
      var p = i.properties || {};
      return n + (p._cesta_id && !p._cesta_caja ? i.quantity : 0);
    }, 0);
  }
  function applied(cart) {
    return (cart.cart_level_discount_applications || []).some(function (a) {
      return a.type === 'discount_code' && String(a.title || '').toUpperCase() === cfg.code.toUpperCase();
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

  function sync(cart) {
    if (busy || !cart || !cart.items) return Promise.resolve();
    var units = cestaUnits(cart);
    var want = units >= (cfg.qty || 3);
    var has = applied(cart);
    if (want && !has) {
      busy = true;
      return setCode(cfg.code).then(function () { flag(true); return refreshUi(); })
        .catch(function () {}).then(function () { busy = false; });
    }
    if (!want && (has || flagged())) {
      busy = true;
      return setCode('').then(function () { flag(false); return has ? refreshUi() : null; })
        .catch(function () {}).then(function () { busy = false; });
    }
    if (want) flag(true);
    return Promise.resolve();
  }

  /* sin argumento: lee el carrito; con carrito: lo usa tal cual (lo llama el cajón al actualizarse) */
  window.cmSyncCestaCode = function (cart) {
    if (cart) return sync(cart);
    return fetch('/cart.js').then(function (r) { return r.json(); }).then(sync);
  };

  /* Al cargar cualquier página: si pusimos el código antes, comprueba que la cesta sigue ahí */
  if (flagged()) window.cmSyncCestaCode().catch(function () {});
})();
