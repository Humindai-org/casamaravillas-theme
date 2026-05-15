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
    console.log('[cart-drawer] fetchAndRenderCart() called');
    return fetch('/cart.js')
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        console.log('[cart-drawer] /cart.js response:', cart);
        console.log('[cart-drawer] cart.items.length:', cart.items.length);
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
    console.log('[renderCartItems] Called with cart:', cart);
    var container = document.getElementById('cart-items-container');
    console.log('[renderCartItems] Container found:', !!container);
    if (!container) {
      console.error('[renderCartItems] cart-items-container not found!');
      return;
    }

    if (!cart || !cart.items) {
      console.error('[renderCartItems] cart or cart.items is undefined!');
      return;
    }

    console.log('[renderCartItems] cart.items.length:', cart.items.length);
    if (cart.items.length === 0) {
      container.innerHTML =
        '<div class="cart-empty">' +
          '<p>Tu cesta está vacía.</p>' +
          '<a href="/collections/all">Seguir comprando</a>' +
        '</div>';
      return;
    }

    var html = '';
    console.log('[renderCartItems] Starting to build HTML for items');
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

    console.log('[renderCartItems] HTML built, length:', html.length);
    console.log('[renderCartItems] First 300 chars:', html.substring(0, 300));
    console.log('[renderCartItems] Container before:', container.innerHTML.substring(0, 100));
    container.innerHTML = html;
    console.log('[renderCartItems] Container after:', container.innerHTML.substring(0, 100));
    console.log('[renderCartItems] HTML assigned successfully');
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

  console.log('[cart-drawer] initializing submit listener');

  document.addEventListener('submit', function (e) {
    var form = e.target;
    console.log('[cart-drawer] form submit detected:', form.tagName);
    /* Detect product forms by [name="add"] button — works regardless of action query params */
    var addBtn = form.querySelector('[name="add"]');
    console.log('[cart-drawer] has add button:', !!addBtn);
    if (!form || !addBtn) return;
    console.log('[cart-drawer] intercepting add-to-cart');
    e.preventDefault();

    var submitBtn = form.querySelector('[name="add"]');
    var originalText = submitBtn ? submitBtn.textContent : '';
    if (submitBtn) {
      submitBtn.disabled    = true;
      submitBtn.textContent = 'Añadiendo…';
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
        console.log('[cart-drawer] add response status:', res.status);
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
    fetch('/recommendations/products.json?product_id=' + productId + '&limit=4&intent=related')
      .then(function (res) { return res.json(); })
      .then(function (data) { renderRecommendations(data.products); })
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
  window.applyDiscount       = applyDiscount;
  window.goToCheckout        = goToCheckout;
  window.fetchAndRenderCart  = fetchAndRenderCart;
}

// Initialize when DOM is ready or immediately if already loaded
console.log('[cart-drawer] Script loaded, document.readyState:', document.readyState);
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    console.log('[cart-drawer] DOMContentLoaded firing, initializing...');
    initCartDrawer();
  });
} else {
  console.log('[cart-drawer] DOM already loaded, initializing immediately...');
  initCartDrawer();
}
console.log('[cart-drawer] Global functions exposed:', {
  openCart: typeof window.openCart,
  closeCart: typeof window.closeCart,
  fetchAndRenderCart: typeof window.fetchAndRenderCart
});
