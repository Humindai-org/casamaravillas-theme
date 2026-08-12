function initWishlistDrawer() {
  'use strict';

  var STORAGE_KEY = 'cm_wishlist';

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

  /* ---- STORAGE ---- */

  function migrateLegacyFlags() {
    try {
      if (localStorage.getItem(STORAGE_KEY) !== null) return;
      /* Formato antiguo: cm_wishlist_<productId> = '1'. No se puede resolver el handle
         desde solo el ID numérico sin una llamada extra por clave, así que esta migración
         limpia esas claves sueltas y arranca la lista nueva vacía en vez de arrastrarlas. */
      var keysToRemove = [];
      for (var i = 0; i < localStorage.length; i++) {
        var key = localStorage.key(i);
        if (key && key.indexOf('cm_wishlist_') === 0) keysToRemove.push(key);
      }
      keysToRemove.forEach(function(k) { localStorage.removeItem(k); });
      localStorage.setItem(STORAGE_KEY, JSON.stringify([]));
    } catch (e) {}
  }

  function getWishlist() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function saveWishlist(list) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    } catch (e) {}
  }

  function isInWishlist(handle) {
    if (!handle) return false;
    return getWishlist().indexOf(handle) !== -1;
  }

  function toggleWishlistItem(handle) {
    if (!handle) return false;
    var list = getWishlist();
    var idx = list.indexOf(handle);
    var nowActive;
    if (idx === -1) {
      list.push(handle);
      nowActive = true;
    } else {
      list.splice(idx, 1);
      nowActive = false;
    }
    saveWishlist(list);
    updateWishlistCount();
    var drawer = document.getElementById('wishlist-drawer');
    if (drawer && drawer.classList.contains('active')) {
      renderWishlistItems();
    }
    return nowActive;
  }

  function removeFromWishlist(handle) {
    var list = getWishlist().filter(function(h) { return h !== handle; });
    saveWishlist(list);
    updateWishlistCount();
    renderWishlistItems();
  }

  /* ---- UI ---- */

  function updateWishlistCount() {
    var count = getWishlist().length;
    var headerBadge = document.querySelector('.site-header__wishlist-count');
    if (headerBadge) {
      headerBadge.textContent = count;
      headerBadge.style.display = count > 0 ? '' : 'none';
    }
    var drawerCount = document.getElementById('wishlist-item-count');
    if (drawerCount) drawerCount.textContent = count;
  }

  function openWishlist() {
    var drawer = document.getElementById('wishlist-drawer');
    if (!drawer) return;
    drawer.classList.add('active');
    document.body.style.overflow = 'hidden';
    renderWishlistItems();
  }

  function closeWishlist() {
    var drawer = document.getElementById('wishlist-drawer');
    if (!drawer) return;
    drawer.classList.remove('active');
    document.body.style.overflow = '';
  }

  function emptyStateHtml() {
    return (
      '<div class="wishlist-empty">' +
        '<p>Aún no has guardado ningún producto.</p>' +
        '<a href="/collections/all">Seguir comprando</a>' +
      '</div>'
    );
  }

  function renderWishlistItems() {
    var container = document.getElementById('wishlist-items-container');
    if (!container) return;
    var handles = getWishlist();

    if (handles.length === 0) {
      container.innerHTML = emptyStateHtml();
      return;
    }

    Promise.all(handles.map(function(handle) {
      return fetch('/products/' + handle + '.js')
        .then(function(res) { return res.ok ? res.json() : null; })
        .catch(function() { return null; });
    })).then(function(products) {
      var html = '';
      products.forEach(function(product) {
        if (!product) return;
        var variant = product.variants && product.variants[0];
        if (!variant) return;
        var imageUrl = product.featured_image
          ? product.featured_image.replace(/(\.(jpg|jpeg|png|webp|gif))(\?|$)/i, '_160x160_crop_center$1$3')
          : '';
        html +=
          '<div class="wishlist-item" data-handle="' + product.handle + '">' +
            '<a href="' + product.url + '" class="wishlist-item-image-link">' +
              (imageUrl
                ? '<img src="' + imageUrl + '" alt="' + escapeHtml(product.title) + '" class="wishlist-item-img" width="80" height="80" loading="lazy">'
                : '<div class="wishlist-item-img"></div>'
              ) +
            '</a>' +
            '<div class="wishlist-item-info">' +
              '<a href="' + product.url + '" class="wishlist-title">' + escapeHtml(product.title) + '</a>' +
              '<span class="wishlist-price">' + formatMoney(variant.price) + '</span>' +
              '<button type="button" class="wishlist-add-btn" data-variant-id="' + variant.id + '"' + (!variant.available ? ' disabled' : '') + '>' +
                (variant.available ? 'Añadir a la cesta' : 'Agotado') +
              '</button>' +
            '</div>' +
            '<button type="button" class="wishlist-remove" data-handle="' + product.handle + '" aria-label="Quitar ' + escapeHtml(product.title) + '">' +
              '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">' +
                '<path d="M2 4h12M6 4V2h4v2M5 4l.5 9h5L11 4" stroke="#6B6050" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>' +
              '</svg>' +
            '</button>' +
          '</div>';
      });

      container.innerHTML = html || emptyStateHtml();
    });
  }

  /* ---- EVENTS (delegados, el contenido se pinta dinámicamente) ---- */

  document.addEventListener('click', function(e) {
    var removeBtn = e.target.closest('.wishlist-remove');
    if (removeBtn) {
      e.preventDefault();
      removeFromWishlist(removeBtn.dataset.handle);
      return;
    }

    var addBtn = e.target.closest('#wishlist-items-container .wishlist-add-btn');
    if (addBtn) {
      e.preventDefault();
      var variantId = addBtn.dataset.variantId;
      if (!variantId) return;
      var originalText = addBtn.textContent;
      addBtn.disabled = true;
      addBtn.textContent = 'Añadiendo…';
      fetch('/cart/add.js', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ id: parseInt(variantId, 10), quantity: 1 })
      })
        .then(function(res) { if (!res.ok) throw new Error('HTTP ' + res.status); return res.json(); })
        .then(async function() {
          if (typeof window.fetchAndRenderCart === 'function') {
            await window.fetchAndRenderCart();
          }
          closeWishlist();
          if (typeof window.openCart === 'function') {
            window.openCart(true);
          }
        })
        .catch(function() {
          addBtn.disabled = false;
          addBtn.textContent = originalText;
        });
    }
  });

  /* ---- EXPOSE GLOBALS (usados por el botón de la ficha de producto y el header) ---- */

  window.openWishlist = openWishlist;
  window.closeWishlist = closeWishlist;
  window.getWishlist = getWishlist;
  window.isInWishlist = isInWishlist;
  window.toggleWishlistItem = toggleWishlistItem;
  window.removeFromWishlist = removeFromWishlist;

  migrateLegacyFlags();
  updateWishlistCount();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    initWishlistDrawer();
  });
} else {
  initWishlistDrawer();
}
