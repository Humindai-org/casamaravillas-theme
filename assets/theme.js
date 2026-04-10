/* ============================================================
   CASA MARAVILLAS — theme.js
   Mobile nav, sticky header, marquee, misc interactions
   ============================================================ */

(function () {
  'use strict';

  // ── MOBILE NAV DRAWER ──
  const hamburger = document.getElementById('hamburger-btn');
  const drawer = document.getElementById('mobile-drawer');
  const drawerClose = document.getElementById('drawer-close');
  const drawerOverlay = document.getElementById('drawer-overlay');

  function openDrawer() {
    if (!drawer) return;
    drawer.classList.add('is-open');
    drawer.setAttribute('aria-hidden', 'false');
    hamburger.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    drawerClose && drawerClose.focus();
  }

  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.remove('is-open');
    drawer.setAttribute('aria-hidden', 'true');
    hamburger && hamburger.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
    hamburger && hamburger.focus();
  }

  hamburger && hamburger.addEventListener('click', openDrawer);
  drawerClose && drawerClose.addEventListener('click', closeDrawer);
  drawerOverlay && drawerOverlay.addEventListener('click', closeDrawer);

  // Close drawer on Escape key
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && drawer && drawer.classList.contains('is-open')) {
      closeDrawer();
    }
  });

  // ── STICKY HEADER SHADOW ──
  const header = document.getElementById('site-header');

  if (header) {
    const scrollThreshold = 40;

    function updateHeaderState() {
      if (window.scrollY > scrollThreshold) {
        header.classList.add('is-scrolled');
      } else {
        header.classList.remove('is-scrolled');
      }
    }

    window.addEventListener('scroll', updateHeaderState, { passive: true });
    updateHeaderState();
  }

  // ── LANG TOGGLE (announcement bar) ──
  const langBtns = document.querySelectorAll('.announcement-bar__lang-btn');

  langBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      langBtns.forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      // Shopify i18n: redirect if locale routes are configured
      const lang = btn.getAttribute('data-lang');
      if (lang && window.Shopify && window.Shopify.routes) {
        // Optional: handle locale switch
      }
    });
  });

  // ── CART COUNT LIVE UPDATE ──
  // Shopify AJAX cart API: update count badge without page reload
  function updateCartCount() {
    fetch('/cart.js')
      .then(function (res) { return res.json(); })
      .then(function (cart) {
        const badge = document.querySelector('.site-header__cart-count');
        if (cart.item_count > 0) {
          if (badge) {
            badge.textContent = cart.item_count;
          } else {
            const cartLink = document.querySelector('.site-header__cart');
            if (cartLink) {
              const newBadge = document.createElement('span');
              newBadge.className = 'site-header__cart-count';
              newBadge.setAttribute('aria-label', cart.item_count + ' artículos');
              newBadge.textContent = cart.item_count;
              cartLink.appendChild(newBadge);
            }
          }
        } else if (badge) {
          badge.remove();
        }
      })
      .catch(function () {});
  }

  // Listen for cart updates from other scripts
  document.addEventListener('cart:updated', updateCartCount);

})();
