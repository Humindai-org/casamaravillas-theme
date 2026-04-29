(function () {
  'use strict';

  /* ── Mock discount codes ── */
  var DISCOUNTS = {
    'IBERICO10': 0.10,
    'BELLOTA15': 0.15,
    'CASA20':    0.20
  };

  var discountPct  = 0;
  var baseTotal    = 0; // cents, updated on every cart fetch

  /* ── Money format ── */
  var moneyFmt = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' });

  function formatMoney(cents) {
    return moneyFmt.format(cents / 100);
  }

  /* ───────────────────────────────
     Drawer open / close
  ─────────────────────────────── */
  function openCart(showSuccess) {
    var drawer = document.getElementById('cart-drawer');
    if (!drawer) return;
    drawer.classList.add('active');
    document.body.style.overflow = 'hidden';

    if (showSuccess) {
      var msg = document.getElementById('cart-success');
      if (msg) {
        msg.style.display = 'block';
        clearTimeout(msg._hideTimer);
        msg._hideTimer = setTimeout(function () {
          msg.style.display = 'none';
        }, 3000);
      }
    }
  }

  function closeCart() {
    var drawer = document.getElementById('cart-drawer');
    if (!drawer) return;
    drawer.classList.remove('active');
    document.body.style.overflow = '';
  }

  function goToCheckout() {
    window.location.href = '/checkout';
  }

  /* ───────────────────────────────
     Cart AJAX operations
  ─────────────────────────────── */
  function cartChange(key, quantity) {
    return fetch('/cart/change.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: key, quantity: quantity })
    })
      .then(function (r) { return r.json(); })
      .then(function (cart) {
        baseTotal = cart.total_price;
        refreshDrawer(cart);
        return cart;
      })
      .catch(function (err) {
        console.error('[cart-drawer] cartChange error:', err);
      });
  }

  function updateQty(key, delta) {
    var item = document.querySelector('.cart-item[data-key="' + key + '"]');
    var input = item ? item.querySelector('input[type="number"]') : null;
    var current = input ? parseInt(input.value, 10) : 1;
    var newQty = Math.max(0, current + delta);
    cartChange(key, newQty);
  }

  function setQty(key, qty) {
    var q = parseInt(qty, 10);
    if (isNaN(q) || q < 0) return;
    cartChange(key, q);
  }

  function removeItem(key) {
    cartChange(key, 0);
  }

  /* ───────────────────────────────
     Refresh drawer via Section Rendering API
     Only replaces the items list and totals;
     overlay state and discount UI are preserved.
  ─────────────────────────────── */
  function refreshDrawer(cartData) {
    updateHeaderCount(cartData.item_count);

    return fetch('/?sections=cart-drawer')
      .then(function (r) { return r.json(); })
      .then(function (sections) {
        var html = sections['cart-drawer'];
        if (!html) return;

        var parser = new DOMParser();
        var doc = parser.parseFromString(html, 'text/html');

        /* Items list */
        var newItems = doc.getElementById('cart-items-wrap');
        var curItems = document.getElementById('cart-items-wrap');
        if (newItems && curItems) curItems.innerHTML = newItems.innerHTML;

        /* Totals — apply active discount on top of Liquid-formatted values */
        var curSubtotal = document.getElementById('cd-subtotal');
        var curTotal    = document.getElementById('cd-total');
        var newSubtotal = doc.getElementById('cd-subtotal');

        if (curSubtotal && newSubtotal) {
          if (discountPct > 0) {
            var raw        = cartData.total_price;
            var discounted = Math.round(raw * (1 - discountPct));
            curSubtotal.textContent = formatMoney(raw);
            if (curTotal) curTotal.textContent = formatMoney(discounted);
          } else {
            curSubtotal.textContent = newSubtotal.textContent;
            var newTotal = doc.getElementById('cd-total');
            if (newTotal && curTotal) curTotal.textContent = newTotal.textContent;
          }
        }
      })
      .catch(function (err) {
        console.error('[cart-drawer] refreshDrawer error:', err);
      });
  }

  /* ───────────────────────────────
     Header cart count badge
  ─────────────────────────────── */
  function updateHeaderCount(count) {
    var cartLink = document.querySelector('.site-header__cart');
    if (!cartLink) return;
    var badge = cartLink.querySelector('.site-header__cart-count');

    if (count > 0) {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'site-header__cart-count';
        cartLink.appendChild(badge);
      }
      badge.textContent = count;
      badge.setAttribute('aria-label', count + ' artículos');
    } else if (badge) {
      badge.remove();
    }
  }

  /* ───────────────────────────────
     Intercept product "Add to cart" forms
  ─────────────────────────────── */
  document.addEventListener('submit', function (e) {
    var form = e.target;
    /* Detect Shopify product form by presence of [name="add"] button */
    if (!form.querySelector('[name="add"]')) return;
    e.preventDefault();

    var submitBtn = form.querySelector('[name="add"]');
    var originalText = submitBtn ? submitBtn.textContent : '';
    if (submitBtn) {
      submitBtn.disabled    = true;
      submitBtn.textContent = 'Añadiendo…';
    }

    fetch('/cart/add.js', {
      method: 'POST',
      body: new FormData(form)
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        return fetch('/cart.js').then(function (r) { return r.json(); });
      })
      .then(function (cart) {
        baseTotal = cart.total_price;
        refreshDrawer(cart);
        openCart(true);
      })
      .catch(function (err) {
        console.error('[cart-drawer] add-to-cart error:', err);
      })
      .finally(function () {
        if (submitBtn) {
          submitBtn.disabled    = false;
          submitBtn.textContent = originalText;
        }
      });
  });

  /* ───────────────────────────────
     Discount code
  ─────────────────────────────── */
  function initDiscount() {
    var applyBtn = document.getElementById('cd-apply');
    var input    = document.getElementById('cd-input');
    var msg      = document.getElementById('cd-msg');
    if (!applyBtn || !input) return;

    applyBtn.addEventListener('click', function () {
      var code = input.value.trim().toUpperCase();
      var pct  = DISCOUNTS[code];

      if (pct) {
        discountPct = pct;
        fetch('/cart.js')
          .then(function (r) { return r.json(); })
          .then(function (cart) {
            baseTotal = cart.total_price;
            var discounted = Math.round(cart.total_price * (1 - pct));
            var elSub = document.getElementById('cd-subtotal');
            var elTot = document.getElementById('cd-total');
            if (elSub) elSub.textContent = formatMoney(cart.total_price);
            if (elTot) elTot.textContent = formatMoney(discounted);
            if (msg) {
              msg.style.color   = '#3a7d3a';
              msg.textContent   = '✔ Descuento aplicado: -' + Math.round(pct * 100) + '%';
            }
          });
      } else {
        discountPct = 0;
        if (msg) {
          msg.style.color = '#c0392b';
          msg.textContent = 'Código no válido.';
        }
      }
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') applyBtn.click();
    });
  }

  /* ───────────────────────────────
     Cart icon in header opens drawer
  ─────────────────────────────── */
  function initHeaderCartLink() {
    var cartLink = document.querySelector('.site-header__cart');
    if (!cartLink) return;
    cartLink.addEventListener('click', function (e) {
      /* Only intercept if not on the /cart page */
      if (window.location.pathname === '/cart') return;
      e.preventDefault();
      openCart(false);
    });
  }

  /* ───────────────────────────────
     Keyboard: Escape closes drawer
  ─────────────────────────────── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeCart();
  });

  /* ───────────────────────────────
     Expose globals (used by inline onclick in liquid)
  ─────────────────────────────── */
  window.openCart    = openCart;
  window.closeCart   = closeCart;
  window.goToCheckout = goToCheckout;
  window.updateQty   = updateQty;
  window.setQty      = setQty;
  window.removeItem  = removeItem;

  /* ── Init ── */
  initDiscount();
  initHeaderCartLink();

})();
