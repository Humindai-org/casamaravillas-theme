(function () {
  'use strict';

  /* ---- OPEN / CLOSE ---- */

  function openCart() {
    var drawer = document.getElementById('cart-drawer');
    if (!drawer) return;
    drawer.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeCart() {
    var drawer = document.getElementById('cart-drawer');
    if (!drawer) return;
    drawer.classList.remove('active');
    document.body.style.overflow = '';
  }

  /* ---- FETCH & RENDER CART ---- */

  function fetchAndRenderCart() {
    fetch('/cart.js')
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        renderCartItems(cart);
        updateCartCount(cart.item_count);
        updateCartTotals(cart);
      })
      .catch(function (err) {
        console.error('[cart-drawer] fetch error:', err);
      });
  }

  function renderCartItems(cart) {
    var container = document.getElementById('cart-items-container');
    if (!container) return;

    if (cart.items.length === 0) {
      container.innerHTML =
        '<div class="cart-empty">' +
          '<p>Tu cesta está vacía.</p>' +
          '<a href="/collections/all">Seguir comprando</a>' +
        '</div>';
      return;
    }

    var html = '';
    cart.items.forEach(function (item) {
      /* Resize Shopify CDN image to 160×160 crop center */
      var imageUrl = item.image
        ? item.image.replace(/(\.(jpg|jpeg|png|webp|gif))(\?|$)/i, '_80x80_crop_center$1$3')
        : '';

      var variantHtml = (item.variant_title && item.variant_title !== 'Default Title')
        ? '<p class="cart-variant">' + escapeHtml(item.variant_title) + '</p>'
        : '';

      html +=
        '<div class="cart-item" data-key="' + item.key + '">' +
          '<a href="' + item.url + '" class="cart-item-image-link">' +
            (imageUrl
              ? '<img src="' + imageUrl + '" alt="' + escapeHtml(item.title) + '" class="cart-item-img" width="80" height="80" loading="lazy">'
              : '<div class="cart-item-img"></div>'
            ) +
          '</a>' +
          '<div class="cart-item-info">' +
            '<a href="' + item.url + '" class="cart-title">' + escapeHtml(item.product_title) + '</a>' +
            variantHtml +
            '<div class="cart-qty">' +
              '<button class="cart-qty-btn" onclick="updateQty(\'' + item.key + '\',' + (item.quantity - 1) + ')" aria-label="Reducir cantidad">−</button>' +
              '<span class="cart-qty-num">' + item.quantity + '</span>' +
              '<button class="cart-qty-btn" onclick="updateQty(\'' + item.key + '\',' + (item.quantity + 1) + ')" aria-label="Aumentar cantidad">+</button>' +
            '</div>' +
          '</div>' +
          '<div class="cart-item-right">' +
            '<span class="cart-price">' + formatMoney(item.final_line_price) + '</span>' +
            '<button class="cart-remove" onclick="removeItem(\'' + item.key + '\')" aria-label="Eliminar">' +
              '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">' +
                '<path d="M2 4h12M6 4V2h4v2M5 4l.5 9h5L11 4" stroke="#6B6050" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>' +
              '</svg>' +
            '</button>' +
          '</div>' +
        '</div>';
    });

    container.innerHTML = html;
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
        badge.setAttribute('aria-label', count + ' artículos');
      } else if (badge) {
        badge.remove();
      }
    }
  }

  function updateCartTotals(cart) {
    var subtotalEl = document.getElementById('cart-subtotal');
    var totalEl    = document.getElementById('cart-total');
    var formatted  = formatMoney(cart.total_price);
    if (subtotalEl) subtotalEl.textContent = formatted;
    if (totalEl)    totalEl.textContent    = formatted;
  }

  /* ---- UPDATE QTY ---- */

  function updateQty(key, quantity) {
    if (quantity < 0) quantity = 0;
    fetch('/cart/change.js', {
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
        console.error('[cart-drawer] updateQty error:', err);
      });
  }

  /* ---- REMOVE ITEM ---- */

  function removeItem(key) {
    fetch('/cart/change.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: key, quantity: 0 })
    })
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        renderCartItems(cart);
        updateCartCount(cart.item_count);
        updateCartTotals(cart);
      })
      .catch(function (err) {
        console.error('[cart-drawer] removeItem error:', err);
      });
  }

  /* ---- APPLY DISCOUNT ---- */

  function applyDiscount() {
    var input = document.getElementById('discount-code');
    if (!input || !input.value.trim()) return;
    window.location.href = '/checkout?discount=' + encodeURIComponent(input.value.trim());
  }

  /* ---- GO TO CHECKOUT ---- */

  function goToCheckout() {
    window.location.href = '/checkout';
  }

  /* ---- ADD TO CART INTERCEPT ---- */

  document.addEventListener('submit', function (e) {
    var form = e.target;
    /* Detect product forms by [name="add"] button — works regardless of action query params */
    if (!form || !form.querySelector('[name="add"]')) return;
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
      .then(function (res) { return res.json(); })
      .then(function () {
        fetchAndRenderCart();
        openCart();
      })
      .catch(function (err) {
        console.error('[cart-drawer] add-to-cart error:', err);
        form.submit();
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

  /* ---- EXPOSE GLOBALS (used by inline onclick in .liquid) ---- */

  window.openCart      = openCart;
  window.closeCart     = closeCart;
  window.updateQty     = updateQty;
  window.removeItem    = removeItem;
  window.applyDiscount = applyDiscount;
  window.goToCheckout  = goToCheckout;

})();
