document.addEventListener('DOMContentLoaded', function() {
(function() {
  'use strict';

  const SID = window.cmPDPSectionId;
  const data = window['cmPDP_' + SID];

  /* ── Utilidades ── */
  function $(id) { return document.getElementById(id); }
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
  function formatMoney(cents) {
    if (!data) return cents;
    const amount = (cents / 100).toFixed(2);
    return data.moneyFormat
      .replace('{' + '{amount}}', amount)
      .replace('{' + '{amount_with_comma_separator}}', amount.replace('.', ','))
      .replace('{' + '{amount_no_decimals}}', Math.round(cents / 100));
  }

  /* ── Galería — thumbnails ── */
  const mainImg = $('cm-main-img-' + SID);
  const imgWrap = mainImg ? mainImg.closest('.cm-pdp__main-img-wrap') : null;

  function applyThumbAdjust(btn) {
    if (!imgWrap || !btn) return;
    /* Los ajustes vienen del HTML (data-*), sobreviven re-renders del Editor */
    const fit  = btn.dataset.imgFit  || data.galFit;
    const zoom = (parseFloat(btn.dataset.imgZoom)  || data.galZoomRaw) / 100;
    const posX = (parseFloat(btn.dataset.imgPosX)  || data.galPosX) + '%';
    const posY = (parseFloat(btn.dataset.imgPosY)  || data.galPosY) + '%';
    imgWrap.style.setProperty('--gal-fit',   fit);
    imgWrap.style.setProperty('--gal-zoom',  zoom);
    imgWrap.style.setProperty('--gal-pos-x', posX);
    imgWrap.style.setProperty('--gal-pos-y', posY);
  }

  if (mainImg) {
    document.querySelectorAll('.cm-pdp__thumb-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        applyThumbAdjust(btn);
        mainImg.classList.add('is-loading');
        const newSrc = btn.dataset.imageSrc;
        const tempImg = new Image();
        tempImg.onload = () => {
          mainImg.src = newSrc;
          mainImg.alt = btn.dataset.imageAlt || '';
          mainImg.classList.remove('is-loading');
        };
        tempImg.src = newSrc;
        document.querySelectorAll('.cm-pdp__thumb-btn').forEach(t => t.classList.remove('is-active'));
        btn.classList.add('is-active');
      });
    });
  }

  /* Shopify Editor: al seleccionar un bloque image_adjust, saltar a su imagen automáticamente */
  document.addEventListener('shopify:block:select', function(evt) {
    var blockId = evt.detail && evt.detail.blockId;
    if (!blockId) return;
    var thumb = document.querySelector('.cm-pdp__thumb-btn[data-block-id="' + blockId + '"]');
    if (thumb) thumb.click();
  });

  /* ── Selector de curación (dropdown) ── */
  const curingSelect = document.querySelector('#cm-curing-' + SID + ' [data-curing-select]');
  const curingHint   = $('cm-curing-hint-' + SID);
  if (curingSelect) {
    curingSelect.addEventListener('change', function() {
      const opt = this.options[this.selectedIndex];
      if (curingHint) curingHint.textContent = opt.dataset.desc || '';
    });
  }

  /* ── Selector de cantidad ── */
  const qtyInput = $('cm-qty-' + SID);
  const qtyMinus = $('cm-qty-minus-' + SID);
  const qtyPlus  = $('cm-qty-plus-' + SID);

  function getQty() { return qtyInput ? parseInt(qtyInput.value, 10) || 1 : 1; }

  function updateVolumDiscount() {
    const tags = (data && data.tags) ? data.tags.map(t => String(t).trim().toLowerCase()) : [];
    const isCortado = tags.some(t => t.includes('cortado'));
    if (!isCortado) return;

    const qty = getQty();
    const variant = findVariant();
    if (!variant) return;

    const basePrice = variant.price;
    let discount = 0;

    if (qty >= 30) discount = 10;
    else if (qty >= 20) discount = 7;
    else if (qty >= 10) discount = 5;

    const volDiscEl = $('cm-volume-discount-' + SID);
    const origEl = $('cm-volume-discount-original-' + SID);
    const priceEl = $('cm-volume-discount-price-' + SID);
    const badgeEl = $('cm-volume-discount-badge-' + SID);
    const priceWrapEl = $('cm-price-wrap-' + SID);

    if (discount > 0) {
      const totalPrice = qty * basePrice;
      const discountedTotal = Math.round(totalPrice * (100 - discount) / 100);
      const origPrice = formatMoney(totalPrice);
      const discPrice = formatMoney(discountedTotal);

      if (origEl) origEl.textContent = origPrice;
      if (priceEl) priceEl.textContent = discPrice;
      if (badgeEl) badgeEl.textContent = '-' + discount + '%';
      if (volDiscEl) volDiscEl.style.display = '';
      if (priceWrapEl) priceWrapEl.style.display = 'none';
    } else {
      if (volDiscEl) volDiscEl.style.display = 'none';
      if (priceWrapEl) priceWrapEl.style.display = '';
    }
  }

  function setQty(v) {
    v = Math.max(1, v);
    if (qtyInput) qtyInput.value = v;
    const stickyVal = $('cm-sticky-qty-val-' + SID);
    if (stickyVal) stickyVal.value = v;
    updateVolumDiscount();
  }

  if (qtyInput) {
    qtyMinus?.addEventListener('click', () => setQty(getQty() - 1));
    qtyPlus?.addEventListener('click',  () => setQty(getQty() + 1));
    qtyInput.addEventListener('change', () => setQty(parseInt(qtyInput.value, 10)));
  }

  /* ── Pack selector (cortado a mano) ── */
  const packSelect = document.querySelector('[data-pack-select]');
  if (packSelect) {
    packSelect.addEventListener('change', () => {
      const packVal = packSelect.value.trim();
      const qtyMatch = packVal.match(/^(\d+)/);
      if (qtyMatch) {
        const qty = parseInt(qtyMatch[1], 10);
        setQty(qty);
      }
    });
  }

  /* ── Qty sticky sincronizada ── */
  const stickyQtyMinus = $('cm-sticky-qty-minus-' + SID);
  const stickyQtyPlus  = $('cm-sticky-qty-plus-' + SID);
  const stickyQtyInput = $('cm-sticky-qty-val-' + SID);
  stickyQtyMinus?.addEventListener('click', () => setQty(getQty() - 1));
  stickyQtyPlus?.addEventListener('click',  () => setQty(getQty() + 1));
  stickyQtyInput?.addEventListener('change', () => setQty(parseInt(stickyQtyInput.value, 10)));

  /* ── Selector de variantes ── */
  const selectedOptions = {};
  document.querySelectorAll('.cm-pdp__select[data-section="' + SID + '"]').forEach(sel => {
    selectedOptions[sel.dataset.optionIndex] = sel.value;
    sel.addEventListener('change', () => {
      selectedOptions[sel.dataset.optionIndex] = sel.value;
      updateVariant();
    });
  });

  function findVariant() {
    if (!data) return null;
    const hasSelectors = Object.keys(selectedOptions).length > 0;
    if (!hasSelectors) {
      return data.variants[0];
    }
    return data.variants.find(v => {
      const m1 = !v.option1 || v.option1 === selectedOptions[1];
      const m2 = !v.option2 || v.option2 === selectedOptions[2];
      const m3 = !v.option3 || v.option3 === selectedOptions[3];
      return m1 && m2 && m3;
    });
  }

  function updateWeightPackSelector() {
    const sectionEl = document.querySelector('#cm-pdp-' + SID);
    if (!sectionEl || !data) {
      return;
    }

    // Detectar formato desde product.tags
    let selectorType = 'entero';
    let formatLabel = 'Pieza Entera';
    const tags = data.tags || [];
    const tagsLower = tags.map(t => String(t).trim().toLowerCase());

    if (tagsLower.some(t => t.includes('loncheado'))) {
      selectorType = 'lonchado';
      formatLabel = 'Loncheado';
    } else if (tagsLower.some(t => t.includes('cortado'))) {
      selectorType = 'cortado';
      formatLabel = 'Cortado a Mano';
    } else if (tagsLower.some(t => t.includes('deshuesado'))) {
      selectorType = 'deshuesado';
      formatLabel = 'Deshuesado';
    } else if (tagsLower.some(t => t.includes('pieza'))) {
      selectorType = 'entero';
      formatLabel = 'Pieza Entera';
    }

    const selectors = sectionEl.querySelectorAll('[data-selector-type]');
    selectors.forEach(selector => {
      if (selector.getAttribute('data-selector-type') === selectorType) {
        selector.style.display = '';
      } else {
        selector.style.display = 'none';
      }
    });

    // Actualizar el elemento de formato en la banda de confianza
    const formatDescEl = document.querySelector('#cm-trust-formato-desc');
    const formatCell = document.querySelector('#cm-trust-formato');
    if (formatDescEl) {
      formatDescEl.textContent = formatLabel;
    }
    if (formatCell) {
      formatCell.setAttribute('data-format-type', selectorType);
    }

    // Mostrar/ocultar selector de curación según el tipo de producto
    const curingSelector = sectionEl.querySelector('.cm-curing-selector');
    if (curingSelector) {
      if (selectorType === 'entero') {
        curingSelector.style.display = '';
      } else {
        curingSelector.style.display = 'none';
      }
    }
  }

  /* Inicializar selector al cargar */
  updateWeightPackSelector();
  updateVolumDiscount();

  function updateVariant() {
    const variant = findVariant();
    if (!variant) return;

    /* ID oculto */
    const idInput = $('cm-variant-id-' + SID);
    if (idInput) idInput.value = variant.id;

    /* Precio */
    const priceEl  = $('cm-price-' + SID);
    const cmpEl    = $('cm-compare-price-' + SID);
    const badgeEl  = $('cm-discount-badge-' + SID);
    const stickyP  = $('cm-sticky-price-' + SID);

    if (priceEl) {
      priceEl.textContent = formatMoney(variant.price);
      priceEl.classList.toggle('cm-pdp__price--sale', variant.compare_at_price > variant.price);
    }
    if (cmpEl) {
      if (variant.compare_at_price > variant.price) {
        cmpEl.textContent = formatMoney(variant.compare_at_price);
        cmpEl.style.display = '';
      } else {
        cmpEl.style.display = 'none';
      }
    }
    if (badgeEl) {
      if (variant.compare_at_price > variant.price) {
        const pct = Math.round((variant.compare_at_price - variant.price) * 100 / variant.compare_at_price);
        badgeEl.textContent = '-' + pct + '%';
        badgeEl.style.display = '';
      } else {
        badgeEl.style.display = 'none';
      }
    }
    if (stickyP) stickyP.textContent = formatMoney(variant.price);

    /* Botón añadir */
    const addBtn  = $('cm-add-' + SID);
    const addText = $('cm-add-text-' + SID);
    const stickyBtn = $('cm-sticky-btn-' + SID);
    if (addBtn) {
      addBtn.disabled = !variant.available;
      if (addText) addText.textContent = variant.available ? 'Añadir a la cesta' : 'Agotado';
    }
    if (stickyBtn) {
      stickyBtn.disabled = !variant.available;
      stickyBtn.textContent = variant.available ? 'Añadir a la cesta' : 'Agotado';
    }

    /* Imagen de variante */
    if (variant.featured_image && mainImg) {
      mainImg.classList.add('is-loading');
      const tempImg = new Image();
      tempImg.onload = () => {
        mainImg.src = variant.featured_image.src;
        mainImg.classList.remove('is-loading');
      };
      tempImg.src = variant.featured_image.src;
    }

    /* Actualizar selectores de peso/pack según tipo de variante */
    updateWeightPackSelector();

    /* Actualizar descuento por volumen */
    updateVolumDiscount();
  }

  /* ── AJAX añadir al carrito ── */
  function loadCombinaProducts() {
    var track = document.getElementById('cm-combina-track');
    if (!track || track.dataset.loaded) return;
    track.dataset.loaded = 'true';

    var productId = data.productId;

    function renderProducts(products) {
      if (!products || products.length === 0) {
        track.innerHTML = '<p style="padding:8px 0;color:var(--text-secondary);font-family:var(--cm-font-sans);font-size:14px;">Sin productos relacionados disponibles.</p>';
        return;
      }
      track.innerHTML = '';
      products.forEach(function(p) {
        var cents = p.variants && p.variants[0] ? p.variants[0].price : 0;
        var price = (cents / 100).toFixed(2).replace('.', ',') + ' €';
        var img = p.featured_image || '';
        var card = document.createElement('a');
        card.href = p.url;
        card.className = 'cm-combina__card';
        card.innerHTML =
          '<img src="' + img + '" alt="' + escapeHtml(p.title) + '" class="cm-combina__card-img" loading="lazy">' +
          '<p class="cm-combina__card-title">' + escapeHtml(p.title) + '</p>' +
          '<p class="cm-combina__card-price">' + price + '</p>';
        track.appendChild(card);
      });

      var wrap = document.getElementById('cm-combina-wrap');
      var prevBtn = document.getElementById('cm-combina-prev');
      var nextBtn = document.getElementById('cm-combina-next');
      if (wrap && prevBtn && nextBtn) {
        function scrollByCard(dir) {
          var card = track.querySelector('.cm-combina__card');
          if (card) wrap.scrollLeft += dir * (card.offsetWidth + 16);
        }
        prevBtn.addEventListener('click', function() { scrollByCard(-1); });
        nextBtn.addEventListener('click', function() { scrollByCard(1); });
        wrap.addEventListener('scroll', function() {
          prevBtn.disabled = wrap.scrollLeft <= 0;
          nextBtn.disabled = wrap.scrollLeft >= wrap.scrollWidth - wrap.offsetWidth - 1;
        });
        prevBtn.disabled = true;
      }
    }

    fetch('/recommendations/products.json?product_id=' + productId + '&limit=8&intent=complementary')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.products && d.products.length > 0) {
          renderProducts(d.products);
        } else {
          return fetch('/recommendations/products.json?product_id=' + productId + '&limit=8&intent=related')
            .then(function(r) { return r.json(); })
            .then(function(d2) { renderProducts(d2.products); });
        }
      })
      .catch(function() {
        track.innerHTML = '<p style="padding:8px 0;color:var(--text-secondary);font-family:var(--cm-font-sans);font-size:14px;">No se pudieron cargar los productos.</p>';
      });
  }

  function revealCombina() {
    const el = document.getElementById('cm-combina-section');
    if (!el) return;
    el.style.display = 'block';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.classList.add('is-animating');
        setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
      });
    });
  }

  /* ── ATC en tarjetas de combina ── */
  var CHECK_PLUS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M5 12l5 5L20 7"/></svg>';
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.cm-combina__card-plus[data-variant-id]');
    if (!btn) return;
    e.preventDefault();
    var variantId = btn.dataset.variantId;
    var original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>';
    fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: parseInt(variantId), quantity: 1 })
    })
    .then(function(r) { if (!r.ok) throw new Error(); return r.json(); })
    .then(async function() {
      btn.innerHTML = CHECK_PLUS;
      btn.classList.add('is-added');
      updateCartCount();
      if (typeof window.fetchAndRenderCart === 'function') {
        await window.fetchAndRenderCart();
      }
      if (typeof window.openCart === 'function') {
        window.openCart(true);
      }
      setTimeout(function() {
        btn.innerHTML = original;
        btn.classList.remove('is-added');
        btn.disabled = false;
      }, 2000);
    })
    .catch(function() {
      btn.innerHTML = original;
      btn.disabled = false;
    });
  });

  function updateCartCount() {
    fetch('/cart.js')
      .then(r => r.json())
      .then(cart => {
        document.querySelectorAll('[data-cart-count], .cart-count, .header__cart-count, .js-cart-count').forEach(el => {
          el.textContent = cart.item_count;
          el.setAttribute('aria-label', cart.item_count + ' artículos en la cesta');
        });
      })
      .catch(() => {});
  }

  function setAddBtnState(state) {
    const addBtn    = $('cm-add-' + SID);
    const addText   = $('cm-add-text-' + SID);
    const stickyBtn = $('cm-sticky-btn-' + SID);
    const labels = { idle: 'Añadir a la cesta', loading: 'Añadiendo…', done: '✓ Añadido' };
    if (addBtn)    addBtn.disabled = (state !== 'idle');
    if (addText)   addText.textContent = labels[state] || labels.idle;
    if (stickyBtn) { stickyBtn.disabled = (state !== 'idle'); stickyBtn.textContent = labels[state] || labels.idle; }
  }

  const mainForm = $('cm-form-' + SID);
  let isSubmitting = false;

  async function addToCartAjax() {
    if (isSubmitting) return;
    isSubmitting = true;

    const variantId = $('cm-variant-id-' + SID)?.value;
    if (!variantId) { isSubmitting = false; return; }

    setAddBtnState('loading');

    try {
      const sectionEl = document.querySelector('#cm-pdp-' + SID);
      const curingSelectEl = sectionEl ? sectionEl.querySelector('[data-curing-select]') : null;
      const curingVal = curingSelectEl ? curingSelectEl.value : '';
      const packSelectEl = sectionEl ? sectionEl.querySelector('[data-pack-select]') : null;
      const packVal = packSelectEl ? packSelectEl.value : '';
      const cartBody = {
        id: variantId,
        quantity: getQty(),
        properties: {}
      };
      if (curingVal) cartBody.properties['Punto de curación'] = curingVal;
      if (packVal) cartBody.properties['Pack'] = packVal;

      const ctrl = new AbortController();
      const tOut = setTimeout(() => ctrl.abort(), 12000);

      const res = await fetch('/cart/add.js', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(cartBody),
        signal: ctrl.signal
      });
      clearTimeout(tOut);

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.description || 'HTTP ' + res.status);
      }

      /* Añadir upsell items seleccionados */
      const upsellChecks = document.querySelectorAll('#cm-upsell-' + SID + ' .cm-upsell__check:checked');
      for (const chk of upsellChecks) {
        const vid = chk.dataset.variantId;
        const disc = parseInt(chk.dataset.disc || '0', 10);
        if (!vid) continue;
        const upBody = { id: vid, quantity: 1, properties: {} };
        if (disc > 0) upBody.properties['Descuento bundle'] = '-' + disc + '%';
        await fetch('/cart/add.js', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(upBody)
        }).catch(() => {});
      }

      setAddBtnState('done');
      updateCartCount();
      revealCombina();

      // Wait for cart to be fetched and rendered before opening drawer
      try {
        if (typeof window.fetchAndRenderCart === 'function') {
          await window.fetchAndRenderCart();
        } else {
          console.warn('[main-product] fetchAndRenderCart not available');
        }
      } catch (e) {
        console.error('[main-product] Error fetching cart:', e);
      }

      // Always open cart to show the drawer
      if (typeof window.openCart === 'function') {
        window.openCart(true);
      } else {
        console.warn('[main-product] openCart not available');
      }

      setTimeout(() => setAddBtnState('idle'), 2500);
    } catch(err) {
      console.warn('[CM] Cart add failed:', err && err.message);
      setAddBtnState('idle');
    } finally {
      isSubmitting = false;
    }
  }

  if (mainForm) {
    mainForm.addEventListener('submit', (e) => {
      e.preventDefault();
      e.stopImmediatePropagation();
      addToCartAjax();
    });
  }

  /* ── Toggle descripción ── */
  const descToggle = $('cm-desc-toggle-' + SID);
  if (descToggle) {
    const fullEl    = $('cm-desc-full-' + SID);
    const previewEl = $('cm-desc-preview-' + SID);
    const moreText  = descToggle.querySelector('.cm-desc-toggle__more');
    const lessText  = descToggle.querySelector('.cm-desc-toggle__less');

    descToggle.addEventListener('click', () => {
      const expanded = descToggle.getAttribute('aria-expanded') === 'true';
      descToggle.setAttribute('aria-expanded', String(!expanded));
      if (fullEl)    {
        fullEl.classList.toggle('is-open', !expanded);
        fullEl.setAttribute('aria-hidden', String(expanded));
      }
      if (previewEl) previewEl.style.display = expanded ? '' : 'none';
      if (moreText)  moreText.style.display  = expanded ? '' : 'none';
      if (lessText)  lessText.style.display  = expanded ? 'none' : '';
    });
  }

  /* ── Sticky ATC ── */
  const addBtnEl  = $('cm-add-' + SID);
  const stickyAtc = $('cm-sticky-atc-' + SID);
  const stickyBtn = $('cm-sticky-btn-' + SID);

  if (addBtnEl && stickyAtc) {
    /* En el editor de Shopify siempre visible para poder diseñar */
    if (window.Shopify && Shopify.designMode) {
      stickyAtc.classList.add('is-visible');
      stickyAtc.setAttribute('aria-hidden', 'false');
    } else if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          const visible = !entry.isIntersecting;
          stickyAtc.classList.toggle('is-visible', visible);
          stickyAtc.setAttribute('aria-hidden', String(!visible));
        });
      }, { threshold: 0, rootMargin: '0px 0px -60px 0px' });
      observer.observe(addBtnEl);
    }
  }

  if (stickyBtn) {
    stickyBtn.addEventListener('click', () => addToCartAjax());
  }

  /* ── Scroll reveal ── */
  if ('IntersectionObserver' in window) {
    const revealObs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          revealObs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    document.querySelectorAll('.cm-reveal').forEach(el => revealObs.observe(el));
  } else {
    document.querySelectorAll('#cm-pdp-' + SID + ' .cm-reveal').forEach(el => el.classList.add('is-revealed'));
  }

  /* ── Wishlist toggle ── */
  const wishlistBtn = $('cm-wishlist-' + SID);
  if (wishlistBtn) {
    const wishlistHandle = data.productHandle;
    const wishlistText = wishlistBtn.querySelector('.cm-wishlist-text');

    function setWishlistState(active) {
      wishlistBtn.classList.toggle('is-active', active);
      wishlistBtn.setAttribute('aria-pressed', String(active));
      if (wishlistText) wishlistText.textContent = active ? 'Guardado en tu lista' : 'Añadir a la lista de deseos';
    }

    /* Lee localStorage directamente (no depende de que wishlist-drawer.js ya
       se haya ejecutado — ambos scripts son `defer` y este corre antes). */
    function readWishlistInitialState() {
      try {
        var raw = localStorage.getItem('cm_wishlist');
        var list = raw ? JSON.parse(raw) : [];
        return Array.isArray(list) && list.indexOf(wishlistHandle) !== -1;
      } catch (e) {
        return false;
      }
    }

    setWishlistState(readWishlistInitialState());

    wishlistBtn.addEventListener('click', () => {
      /* Al hacer click ya pasó DOMContentLoaded, así que wishlist-drawer.js
         (también defer) ya se ejecutó y expuso esta función globalmente. */
      if (typeof window.toggleWishlistItem === 'function') {
        setWishlistState(window.toggleWishlistItem(wishlistHandle));
      }
    });
  }

  /* ── Productos complementarios ── */
  const compEl = $('cm-comp-' + SID);
  if (compEl) {
    const compListEl = $('cm-comp-list-' + SID);
    const compProductId = compEl.dataset.productId;
    const compMax = parseInt(compEl.dataset.max || '3', 10);
    const compFallback = compEl.dataset.fallback || '';

    function compImgSrc(p) {
      var fi = p.featured_image;
      if (!fi) return '';
      return typeof fi === 'string' ? fi : (fi.src || '');
    }

    function renderCompItems(products) {
      if (!products || products.length === 0) {
        compEl.style.display = 'none';
        return;
      }
      compListEl.innerHTML = '';
      products.slice(0, compMax).forEach(function(p) {
        var variant = p.variants && p.variants[0];
        if (!variant) return;
        var available = variant.available !== false;
        var img = compImgSrc(p);
        var card = document.createElement('div');
        card.className = 'cm-comp__card';
        card.innerHTML =
          (img ? '<img class="cm-comp__card-img" src="' + img + '" alt="' + escapeHtml(p.title) + '" width="56" height="56" loading="lazy">' : '') +
          '<div class="cm-comp__card-body">' +
            '<p class="cm-comp__card-name">' + escapeHtml(p.title) + '</p>' +
            '<p class="cm-comp__card-price">' + formatMoney(variant.price) + '</p>' +
          '</div>' +
          '<button type="button" class="cm-comp__atc-btn" data-variant-id="' + variant.id + '"' + (!available ? ' disabled' : '') + '>' +
            (available ? 'Agregar a mi cesta' : 'Agotado') +
          '</button>';
        card.querySelector('.cm-comp__atc-btn').addEventListener('click', async function() {
          var btn = this;
          var vid = btn.dataset.variantId;
          btn.disabled = true;
          btn.textContent = 'A\xf1adiendo…';
          try {
            var res = await fetch('/cart/add.js', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
              body: JSON.stringify({ id: parseInt(vid, 10), quantity: 1 })
            });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            btn.textContent = '✓ A\xf1adido';
            updateCartCount();
            if (typeof window.fetchAndRenderCart === 'function') window.fetchAndRenderCart();
            if (typeof window.openCart === 'function') window.openCart(true);
            setTimeout(function() {
              btn.disabled = false;
              btn.textContent = 'Agregar a mi cesta';
            }, 2200);
          } catch(e) {
            btn.disabled = false;
            btn.textContent = 'Agregar a mi cesta';
          }
        });
        compListEl.appendChild(card);
      });
    }

    fetch('/recommendations/products.json?product_id=' + compProductId + '&limit=' + compMax + '&intent=complementary')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.products && d.products.length > 0) {
          renderCompItems(d.products);
        } else if (compFallback) {
          return fetch('/collections/' + compFallback + '/products.json?limit=' + (compMax + 1))
            .then(function(r) { return r.json(); })
            .then(function(d2) {
              renderCompItems((d2.products || []).filter(function(p) { return String(p.id) !== compProductId; }));
            });
        } else {
          compEl.style.display = 'none';
        }
      })
      .catch(function() { compEl.style.display = 'none'; });
  }

})();
}); // DOMContentLoaded
