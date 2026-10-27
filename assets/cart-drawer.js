function initCartDrawer() {
  'use strict';

  /* ---- OPEN / CLOSE ---- */

  function openCart(showConfirm) {
    var drawer = document.getElementById('cart-drawer');
    if (!drawer) return;
    drawer.classList.add('active');
    document.body.style.overflow = 'hidden';
    var confirm = document.getElementById('cart-added-confirm');
    if (confirm) confirm.style.display = showConfirm ? 'flex' : 'none';
  }

  function closeCart() {
    var drawer = document.getElementById('cart-drawer');
    if (!drawer) return;
    drawer.classList.remove('active');
    document.body.style.overflow = '';
  }

  /* ---- FETCH & RENDER CART ---- */

  function fetchAndRenderCart() {
    return fetch('/cart.js')
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        renderCartItems(cart);
        updateCartCount(cart.item_count);
        updateCartTotals(cart);
        if (cart.items.length > 0) {
          fetchRecommendations(cart.items[0].product_id);
        }
      })
      .catch(function (err) {
        console.error('[cart-drawer] fetch error:', err);
      });
  }

  function renderCartItems(cart) {
    var container = document.getElementById('cart-items-container');
    if (!container) {
      console.error('[renderCartItems] cart-items-container not found!');
      return;
    }

    if (!cart || !cart.items) {
      console.error('[renderCartItems] cart or cart.items is undefined!');
      return;
    }

    if (cart.items.length === 0) {
      container.innerHTML =
        '<div class="cart-empty">' +
          '<p>' + cmT('cart_empty', 'Tu cesta está vacía.') + '</p>' +
          '<a href="' + ((window.Shopify && Shopify.routes && Shopify.routes.root) || '/') + 'collections/all">' + cmT('keep_shopping', 'Seguir comprando') + '</a>' +
        '</div>';
      return;
    }

    /* Agrupa las líneas de una cesta personalizada (_cesta_id) bajo una "Caja de regalo" */
    var boxes = {};
    var boxOrder = [];
    var html = '';
    cart.items.forEach(function (item) {
      var boxId = item.properties && item.properties._cesta_id;
      if (!boxId) {
        html += itemHtml(item);
        return;
      }
      if (!boxes[boxId]) {
        boxes[boxId] = { id: boxId, lines: [], gift: null };
        boxOrder.push(boxId);
        html += '<!--box:' + boxId + '-->';
      }
      if (item.properties._cesta_caja) boxes[boxId].gift = item;
      else boxes[boxId].lines.push(item);
    });

    boxOrder.forEach(function (id) {
      html = html.replace('<!--box:' + id + '-->', boxHtml(boxes[id]));
    });

    container.innerHTML = html;
  }

  /* Descuento total de una línea: automáticos y códigos (p. ej. el 5% de la cesta) */
  function lineDiscount(item) {
    return (item.discounts || []).reduce(function (n, d) { return n + (d.amount || 0); }, 0);
  }

  function itemHtml(item) {
    /* Resize Shopify CDN image to 160×160 crop center */
    var imageUrl = item.image
      ? item.image.replace(/(\.(jpg|jpeg|png|webp|gif))(\?|$)/i, '_80x80_crop_center$1$3')
      : '';

    var variantHtml = (item.variant_title && item.variant_title !== 'Default Title')
      ? '<p class="cart-variant">' + escapeHtml(item.variant_title) + '</p>'
      : '';

    var priceHtml;
    var lineDisc = lineDiscount(item);
    if (lineDisc > 0) {
      var pct = Math.round(lineDisc * 100 / item.original_line_price);
      priceHtml =
        '<div class="cart-price-wrap">' +
          '<span class="cart-price-compare">' + formatMoney(item.original_line_price) + '</span>' +
          '<span class="cart-price cart-price--sale">' + formatMoney(item.original_line_price - lineDisc) + '</span>' +
          '<span class="cart-discount-badge">-' + pct + '%</span>' +
        '</div>';
    } else {
      priceHtml = '<span class="cart-price">' + formatMoney(item.line_price) + '</span>';
    }

    return (
      '<div class="cart-item" data-key="' + item.key + '">' +
        '<a href="' + item.url + '" class="cart-item-image-link">' +
          (imageUrl
            ? '<img src="' + imageUrl + '" alt="' + escapeHtml(item.title) + '" class="cart-item-img" width="80" height="80" loading="lazy">'
            : '<div class="cart-item-img"></div>'
          ) +
        '</a>' +
        '<div class="cart-item-info">' +
          '<a href="' + item.url + '" class="cart-title">' + escapeHtml(item.product_title || item.title) + '</a>' +
          variantHtml +
          '<div class="cart-qty">' +
            '<button class="cart-qty-btn" onclick="updateQty(\'' + item.key + '\',' + (item.quantity - 1) + ')" aria-label="Reducir cantidad">−</button>' +
            '<input class="cart-qty-num" type="number" inputmode="numeric" min="0" max="999" value="' + item.quantity + '" aria-label="Cantidad de ' + escapeHtml(item.title) + '" onchange="cmSetCartQty(\'' + item.key + '\', this)" onfocus="this.select()">' +
            '<button class="cart-qty-btn" onclick="updateQty(\'' + item.key + '\',' + (item.quantity + 1) + ')" aria-label="Aumentar cantidad">+</button>' +
          '</div>' +
        '</div>' +
        '<div class="cart-item-right">' +
          priceHtml +
          '<button class="cart-remove" onclick="removeItem(\'' + item.key + '\')" aria-label="Eliminar">' +
            '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">' +
              '<path d="M2 4h12M6 4V2h4v2M5 4l.5 9h5L11 4" stroke="#6B6050" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>' +
            '</svg>' +
          '</button>' +
        '</div>' +
      '</div>'
    );
  }

  function boxHtml(box) {
    var keys = box.lines.map(function (l) { return l.key; });
    if (box.gift) keys.push(box.gift.key);
    var count = box.lines.reduce(function (n, l) { return n + l.quantity; }, 0);
    var total = box.lines.reduce(function (n, l) { return n + l.original_line_price - lineDiscount(l); }, 0);
    var inner = box.lines.map(itemHtml).join('');
    return (
      '<div class="cart-box" data-box="' + escapeHtml(box.id) + '">' +
        '<div class="cart-box-head">' +
          '<div>' +
            '<p class="cart-box-eyebrow">Caja de regalo</p>' +
            '<p class="cart-box-title">Tu pack personalizado</p>' +
            '<p class="cart-box-meta">' + count + ' producto' + (count === 1 ? '' : 's') + ' · ' + formatMoney(total) + '</p>' +
          '</div>' +
          '<button class="cart-box-remove" onclick="removeBox(\'' + keys.join(',') + '\')" aria-label="Eliminar cesta completa">Quitar cesta</button>' +
        '</div>' +
        inner +
      '</div>'
    );
  }

  function removeBox(keysCsv) {
    var updates = {};
    keysCsv.split(',').forEach(function (k) { updates[k] = 0; });
    fetch('/cart/update.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates: updates })
    })
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        renderCartItems(cart);
        updateCartCount(cart.item_count);
        updateCartTotals(cart);
      })
      .catch(function (err) {
        console.error('[cart-drawer] removeBox error:', err);
      });
  }

  function updateCartCount(count) {
    /* Counter inside the drawer */
    var countEl = document.getElementById('cart-item-count');
    if (countEl) countEl.textContent = count;

    /* Header badge (.site-header__cart-count) */
    var cartLink = document.querySelector('.site-header__cart');
    if (cartLink) {
      var badge = cartLink.querySelector('.site-header__cart-count');
      if (count > 0) {
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'site-header__cart-count';
          cartLink.appendChild(badge);
        }
        badge.textContent = count;
        badge.setAttribute('aria-label', cmT('cart_items_count_aria', '{n} artículos', { n: count }));
      } else if (badge) {
        badge.remove();
      }
    }
  }

  function updateCartTotals(cart) {
    var subtotalEl = document.getElementById('cart-subtotal');
    var totalEl    = document.getElementById('cart-total');
    var discRow    = document.getElementById('cart-discount-row');
    var discEl     = document.getElementById('cart-discount');
    var formatted  = formatMoney(cart.total_price);
    /* Subtotal sin descuentos, descuentos aparte y total con ellos (también el código de la cesta) */
    if (subtotalEl) subtotalEl.textContent = formatMoney(cart.original_total_price);
    if (discRow)    discRow.hidden = !(cart.total_discount > 0);
    if (discEl)     discEl.textContent = '−' + formatMoney(cart.total_discount);
    if (totalEl)    totalEl.textContent    = formatted;
    updateShippingBar(cart);
    /* El código de la cesta solo debe estar puesto mientras haya una cesta completa en el carrito */
    if (window.cmSyncCestaCode) window.cmSyncCestaCode(cart);
    /* Avisa a otras piezas (p. ej. la barra de envío gratis de la ficha) de que el carrito cambió */
    document.dispatchEvent(new CustomEvent('cm:cart-updated', { detail: { cart: cart } }));
  }

  /* ---- BARRA DE ENVÍO GRATIS ---- */

  function updateShippingBar(cart) {
    var bar = document.querySelector('#cart-drawer [data-cm-shipbar]');
    if (!bar) return;
    var threshold = parseInt(bar.getAttribute('data-threshold'), 10);
    var eligible  = bar.getAttribute('data-eligible') === 'true';
    var remaining = Math.max(threshold - cart.total_price, 0);
    var percent   = Math.min(Math.round(cart.total_price * 100 / threshold), 100);
    var text  = bar.querySelector('[data-cm-shipbar-text]');
    var fill  = bar.querySelector('[data-cm-shipbar-fill]');
    var track = bar.querySelector('[role="progressbar"]');
    bar.hidden = !(eligible && cart.item_count > 0);
    bar.classList.toggle('is-complete', remaining === 0);
    if (text) {
      text.innerHTML = remaining === 0
        ? cmT('shipbar_free_html', '¡Tienes <strong>envío gratis</strong>!')
        : cmT('shipbar_remaining_html', 'Te faltan <strong>{amount}</strong> para el envío gratis', { amount: formatMoney(remaining) });
    }
    if (fill)  fill.style.width = percent + '%';
    if (track) track.setAttribute('aria-valuenow', percent);
  }

  /* ---- DIÁLOGO PROPIO (sustituye confirm/alert del navegador) ---- */

  function cmPackDialog(opts) {
    return new Promise(function (resolve) {
      var prevFocus = document.activeElement;
      var wrap = document.createElement('div');
      wrap.className = 'cm-dialog';
      wrap.innerHTML =
        '<div class="cm-dialog__box" role="alertdialog" aria-modal="true" aria-labelledby="cm-dialog-title" aria-describedby="cm-dialog-text">' +
          '<p class="cm-dialog__eyebrow">' + escapeHtml(opts.eyebrow || 'Tu pack') + '</p>' +
          '<h3 class="cm-dialog__title" id="cm-dialog-title">' + escapeHtml(opts.title) + '</h3>' +
          '<p class="cm-dialog__text" id="cm-dialog-text">' + escapeHtml(opts.text) + '</p>' +
          '<div class="cm-dialog__actions">' +
            (opts.cancelLabel ? '<button type="button" class="cm-dialog__btn cm-dialog__btn--ghost" data-dialog="no">' + escapeHtml(opts.cancelLabel) + '</button>' : '') +
            '<button type="button" class="cm-dialog__btn cm-dialog__btn--main" data-dialog="yes">' + escapeHtml(opts.confirmLabel || 'Entendido') + '</button>' +
          '</div>' +
        '</div>';

      function close(result) {
        document.removeEventListener('keydown', onKey, true);
        wrap.classList.remove('is-open');
        setTimeout(function () { wrap.remove(); }, 180);
        if (prevFocus && prevFocus.focus) prevFocus.focus();
        resolve(result);
      }
      function onKey(e) {
        if (e.key === 'Escape') { e.stopPropagation(); close(false); }
      }
      wrap.addEventListener('click', function (e) {
        if (e.target === wrap) return close(false);
        var b = e.target.closest('[data-dialog]');
        if (b) close(b.dataset.dialog === 'yes');
      });
      document.addEventListener('keydown', onKey, true);
      document.body.appendChild(wrap);
      requestAnimationFrame(function () {
        wrap.classList.add('is-open');
        var main = wrap.querySelector('[data-dialog="yes"]');
        if (main) main.focus();
      });
    });
  }

  /* ---- PACK: MÍNIMO DE PRODUCTOS ---- */

  var PACK_MIN = 2;
  var PACK_MSG = 'Un pack necesita mínimo ' + PACK_MIN + ' productos.';

  /* Unidades (sin contar la caja de regalo) por cada _cesta_id del carrito */
  function packSummary(cart, key, newQty) {
    var boxes = {};
    cart.items.forEach(function (it) {
      var id = it.properties && it.properties._cesta_id;
      if (!id) return;
      var b = boxes[id] = boxes[id] || { id: id, units: 0, keys: [] };
      b.keys.push(it.key);
      if (!it.properties._cesta_caja) b.units += (it.key === key ? newQty : it.quantity);
    });
    return boxes;
  }

  function changeLine(key, quantity) {
    return fetch('/cart/change.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: key, quantity: quantity })
    })
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        renderCartItems(cart);
        updateCartCount(cart.item_count);
        updateCartTotals(cart);
      })
      .catch(function (err) {
        console.error('[cart-drawer] change error:', err);
      });
  }

  /* Si el cambio dejaría un pack con menos del mínimo, ofrece quitar el pack completo */
  function guardedChange(key, quantity) {
    return fetch('/cart.js')
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        var item = cart.items.filter(function (it) { return it.key === key; })[0];
        var id = item && item.properties && item.properties._cesta_id;
        if (id && !item.properties._cesta_caja && quantity < item.quantity) {
          var box = packSummary(cart, key, quantity)[id];
          if (box.units < PACK_MIN) {
            return cmPackDialog({
              title: 'Un pack necesita mínimo ' + PACK_MIN + ' productos',
              text: 'Si quitas este producto, tu pack se quedaría con menos de ' + PACK_MIN + '. ¿Quieres quitar el pack completo?',
              confirmLabel: 'Quitar el pack',
              cancelLabel: 'Mantener mi pack'
            }).then(function (ok) { if (ok) removeBox(box.keys.join(',')); });
          }
        }
        return changeLine(key, quantity);
      })
      .catch(function (err) {
        console.error('[cart-drawer] guard error:', err);
      });
  }

  /* ---- UPDATE QTY ---- */

  /* Cantidad escrita a mano en el cajón: vacío o inválido vuelve a la cantidad anterior */
  function cmSetCartQty(key, input) {
    var n = parseInt(input.value, 10);
    if (isNaN(n) || n < 0) { input.value = input.defaultValue; return; }
    updateQty(key, Math.min(n, 999));
  }

  function updateQty(key, quantity) {
    if (quantity < 0) quantity = 0;
    guardedChange(key, quantity);
  }

  /* ---- REMOVE ITEM ---- */

  function removeItem(key) {
    guardedChange(key, 0);
  }

  /* ---- APPLY DISCOUNT ---- */

  function applyDiscount() {
    var input = document.getElementById('discount-code');
    if (!input || !input.value.trim()) return;
    window.location.href = '/checkout?discount=' + encodeURIComponent(input.value.trim());
  }

  /* ---- GO TO CHECKOUT ---- */

  function goToCheckout() {
    fetch('/cart.js')
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        var boxes = packSummary(cart, null, 0);
        var bad = Object.keys(boxes).some(function (id) { return boxes[id].units < PACK_MIN; });
        if (bad) {
          return cmPackDialog({
            title: 'Falta un producto en tu pack',
            text: 'Un pack necesita mínimo ' + PACK_MIN + ' productos. Añade más productos o quita el pack para continuar.',
            confirmLabel: 'Entendido'
          });
        }
        window.location.href = '/checkout';
      })
      .catch(function () { window.location.href = '/checkout'; });
  }

  /* ---- ADD TO CART INTERCEPT ---- */

  document.addEventListener('submit', function (e) {
    var form = e.target;
    /* Detect product forms by [name="add"] button — works regardless of action query params */
    var addBtn = form.querySelector('[name="add"]');
    if (!form || !addBtn) return;
    e.preventDefault();

    var submitBtn = form.querySelector('[name="add"]');
    var originalText = submitBtn ? submitBtn.textContent : '';
    if (submitBtn) {
      submitBtn.disabled    = true;
      submitBtn.textContent = cmT('adding', 'Añadiendo…');
    }

    /* Convert form data to URL-encoded string for Shopify cart API */
    var formData = new FormData(form);
    var params = new URLSearchParams();
    for (var pair of formData.entries()) {
      params.append(pair[0], pair[1]);
    }

    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params.toString()
    })
      .then(function (res) {
        if (!res.ok) {
          throw new Error('HTTP ' + res.status);
        }
        return res.json();
      })
      .then(function () {
        return fetchAndRenderCart().then(function () {
          openCart(true);
        });
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

  /* ---- KEYBOARD: ESC closes drawer ---- */

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeCart();
  });

  /* ---- HELPERS ---- */

  function formatMoney(cents) {
    return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(cents / 100);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /* ---- RECOMMENDATIONS ---- */

  function fetchRecommendations(productId) {
    if (!productId) return;
    /* Se piden 8 y se muestran 4 tras quitar los packs con vino/vermut (etiqueta "con-alcohol", IVA 21 %) */
    fetch('/recommendations/products.json?product_id=' + productId + '&limit=8&intent=related')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var sinAlcohol = (data.products || []).filter(function (p) {
          return !(p.tags || []).some(function (t) { return String(t).trim().toLowerCase() === 'con-alcohol'; });
        });
        renderRecommendations(sinAlcohol.slice(0, 4));
      })
      .catch(function (err) {
        console.error('[cart-drawer] recommendations error:', err);
      });
  }

  function renderRecommendations(products) {
    var section = document.getElementById('cart-recommendations');
    var grid    = document.getElementById('cart-rec-grid');
    if (!section || !grid) return;

    if (!products || products.length === 0) {
      section.style.display = 'none';
      return;
    }

    var html = '';
    products.forEach(function (p) {
      var imgSrc = p.featured_image
        ? p.featured_image.replace(/(\.(jpg|jpeg|png|webp|gif))(\?|$)/i, '_240x240_crop_center$1$3')
        : '';
      html +=
        '<a href="' + p.url + '" class="cart-rec-item">' +
          (imgSrc
            ? '<img src="' + imgSrc + '" alt="' + escapeHtml(p.title) + '" class="cart-rec-img" loading="lazy">'
            : '<div class="cart-rec-img"></div>'
          ) +
          '<div class="cart-rec-info">' +
            '<span class="cart-rec-name">' + escapeHtml(p.title) + '</span>' +
            '<span class="cart-rec-price">' + formatMoney(p.price_min) + '</span>' +
          '</div>' +
        '</a>';
    });

    grid.innerHTML = html;
    section.style.display = 'block';
  }

  /* ---- EXPOSE GLOBALS (used by inline onclick in .liquid) ---- */

  window.openCart            = openCart;
  window.closeCart           = closeCart;
  window.updateQty           = updateQty;
  window.removeItem          = removeItem;
  window.removeBox           = removeBox;
  window.cmPackDialog        = cmPackDialog;
  window.cmSetCartQty        = cmSetCartQty;
  window.applyDiscount       = applyDiscount;
  window.goToCheckout        = goToCheckout;
  window.fetchAndRenderCart  = fetchAndRenderCart;

  /* Si el HTML del servidor trae una cesta, la pinta el JS (agrupada) */
  var pending = document.getElementById('cart-items-container');
  if (pending && pending.hasAttribute('data-needs-render')) fetchAndRenderCart();
}

// Initialize when DOM is ready or immediately if already loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    initCartDrawer();
  });
} else {
  initCartDrawer();
}
