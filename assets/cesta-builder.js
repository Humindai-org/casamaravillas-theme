/* Crea tu pack — lógica del constructor */
(function () {
  'use strict';

  var root = document.querySelector('[data-cesta-builder]');
  if (!root) return;

  var d = root.dataset;
  var MIN = parseInt(d.min, 10) || 2;
  var FREE = parseInt(d.freeShipping, 10) || 0;
  var GIFT = (d.giftHandle || '').trim();
  var EXCLUDE = (d.excludeHandles || '').split(',').map(function (h) { return h.trim(); }).filter(Boolean);
  if (GIFT) EXCLUDE.push(GIFT);
  var MILESTONES = [{ qty: MIN, label: 'Pack<br>listo' }];
  var discPct = parseInt(d.discPct, 10) || 0;
  var DISC_QTY = parseInt(d.discQty, 10) || 0;
  if (discPct > 0) MILESTONES.push({ qty: parseInt(d.discQty, 10), label: '−' + discPct + '%<br>dto.' });
  if (d.gift1Label) MILESTONES.push({ qty: parseInt(d.gift1Qty, 10), label: esc(d.gift1Label).replace(' ', '<br>') });
  if (d.gift2Label) MILESTONES.push({ qty: parseInt(d.gift2Qty, 10), label: esc(d.gift2Label).replace(' ', '<br>') });
  MILESTONES = MILESTONES.filter(function (m) { return m.qty > 0; }).sort(function (a, b) { return a.qty - b.qty; });
  var MAXQ = MILESTONES.length ? MILESTONES[MILESTONES.length - 1].qty : MIN;

  var STORE_KEY = 'cm-pack-v2';
  var CURINGS = ['Más tierno', 'Equilibrado', 'Más curado'];
  var CATS = [
    { id: 'lonchado-jamon', label: 'Jamón Ibérico Lonchado' },
    { id: 'jamon', label: 'Jamón Ibérico' },
    { id: 'embutido', label: 'Embutidos Ibéricos' },
    { id: 'lonchado-emb', label: 'Embutidos Lonchados' },
    { id: 'all', label: 'Todo' }
  ];

  var $ = function (sel) { return root.querySelector(sel); };
  var el = {
    tabs: $('[data-cb-tabs]'), search: $('[data-cb-search]'), searchClear: $('[data-cb-search-clear]'),
    grid: $('[data-cb-grid]'), count: $('[data-cb-count]'), dsub: $('[data-cb-dsub]'),
    track: $('[data-cb-track]'), fill: $('[data-cb-fill]'),
    lines: $('[data-cb-lines]'), empty: $('[data-cb-empty]'),
    shipText: $('[data-cb-ship-text]'), shipBar: $('[data-cb-ship-bar]'),
    total: $('[data-cb-total]'), save: $('[data-cb-save]'), add: $('[data-cb-add]'), clear: $('[data-cb-clear]'), min: $('[data-cb-min]'),
    modal: $('[data-cb-modal]')
  };

  var products = [];
  var byVariant = {};
  var basket = {};          /* key "variantId|curing" -> {vid, curing, qty} */
  var selVariant = {};      /* productId -> variantId */
  var selCuring = {};       /* productId -> curing */
  var activeCat = 'lonchado-jamon';
  var term = '';

  /* ---------- helpers ---------- */
  function money(c) { return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(c / 100); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function img(src, w) {
    return src ? src.replace(/(\.(jpg|jpeg|png|webp|gif))(\?|$)/i, '_' + w + 'x' + w + '_crop_center$1$3') : '';
  }
  function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(basket)); } catch (e) {} }
  function load() {
    try { basket = JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch (e) { basket = {}; }
  }
  function key(vid, curing) { return vid + '|' + (curing || ''); }

  function classify(p) {
    var t = (p.title + ' ' + p.type).toLowerCase();
    var sliced = /loncha|loncheado|lonchado/.test(t);
    var ham = /jam[oó]n|paleta/.test(t);
    if (sliced) return ham ? 'lonchado-jamon' : 'lonchado-emb';
    return ham ? 'jamon' : 'embutido';
  }
  function hasCuring(p) { return /pieza entera|entero|deshuesad/.test(p.title.toLowerCase()); }

  function totals() {
    var count = 0, cents = 0;
    Object.keys(basket).forEach(function (k) {
      var b = basket[k], hit = byVariant[b.vid];
      if (!hit) return;
      count += b.qty;
      cents += b.qty * hit.variant.price;
    });
    return { count: count, cents: cents };
  }
  /* Descuento por cantidad de los loncheados (automático en Shopify): -10% desde 10 uds de un mismo jamón loncheado
     o 5 uds de un mismo embutido loncheado. Shopify no suma descuentos: aplica el que más ahorra en todo el carrito. */
  var AUTO_PCT = 10;
  function autoThreshold(p) {
    if (p.tags.indexOf('loncheado') !== -1) return 5;
    if (p.tags.some(function (t) { return t.indexOf('cortado') !== -1; })) return 10;
    return 0;
  }
  function discountInfo(t) {
    var perProduct = {};
    Object.keys(basket).forEach(function (k) {
      var b = basket[k], hit = byVariant[b.vid];
      if (!hit) return;
      var e = perProduct[hit.product.id] || (perProduct[hit.product.id] = { p: hit.product, units: 0, cents: 0 });
      e.units += b.qty; e.cents += b.qty * hit.variant.price;
    });
    var auto = 0;
    Object.keys(perProduct).forEach(function (id) {
      var e = perProduct[id], th = autoThreshold(e.p);
      if (th && e.units >= th) auto += Math.round(e.cents * AUTO_PCT / 100);
    });
    var code = (discPct > 0 && DISC_QTY > 0 && t.count >= DISC_QTY) ? Math.round(t.cents * discPct / 100) : 0;
    return { auto: auto, code: code, best: Math.max(auto, code), qty: auto > code ? 'auto' : 'code' };
  }
  function productQty(p) {
    var n = 0;
    Object.keys(basket).forEach(function (k) {
      var h = byVariant[basket[k].vid];
      if (h && h.product.id === p.id) n += basket[k].qty;
    });
    return n;
  }

  /* ---------- catálogo ---------- */
  function normalize(p) {
    var o = {
      id: p.id, handle: p.handle, title: p.title, type: p.product_type || '',
      tags: (p.tags || []).map(function (t) { return String(t).toLowerCase(); }),
      image: p.images && p.images[0] ? p.images[0].src : '',
      options: (p.options || []).map(function (op) { return { name: op.name, position: op.position, values: op.values || [] }; }),
      variants: p.variants.map(function (v) {
        return { id: String(v.id), title: v.title, price: Math.round(parseFloat(v.price) * 100), available: v.available !== false,
                 o: [v.option1, v.option2, v.option3] };
      }).filter(function (v) { return v.available; })
    };
    o.cat = classify(o);
    o.curing = hasCuring(o);
    return o;
  }

  function loadProducts() {
    return fetch('/collections/all/products.json?limit=250')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        products = (data.products || [])
          .filter(function (p) { return EXCLUDE.indexOf(p.handle) === -1; })
          .map(normalize)
          .filter(function (p) { return p.variants.length; });
        products.forEach(function (p) {
          p.variants.forEach(function (v) { byVariant[v.id] = { product: p, variant: v }; });
        });
      });
  }

  function curVariant(p) {
    var id = selVariant[p.id] || p.variants[0].id;
    return p.variants.filter(function (v) { return v.id === id; })[0] || p.variants[0];
  }
  function curCuring(p) { return selCuring[p.id] || 'Equilibrado'; }

  /* Opciones a la vista (botones): una fila por opción con más de un valor (Peso, Formato, Corte…) */
  function prettyOpt(val) {
    var m = String(val).match(/^(\d+(?:\.\d+)?)\s*kg\s*-\s*(\d+(?:\.\d+)?)\s*kg$/i);
    return m ? parseFloat(m[1]) + '–' + parseFloat(m[2]) + ' kg' : val;
  }
  function optRows(p, v) {
    return p.options.filter(function (op) { return op.values.length > 1; }).map(function (op) {
      var i = op.position - 1;
      var avail = p.variants.map(function (x) { return x.o[i]; });
      return '<div><p class="cb-lab">' + esc(op.name) + '</p><div class="cb-opts" role="radiogroup" aria-label="' + esc(op.name) + ' de ' + esc(p.title) + '">' +
        op.values.filter(function (val) { return avail.indexOf(val) !== -1; }).map(function (val) {
          return '<label><input type="radio" name="opt-' + p.id + '-' + i + '" value="' + esc(val) + '" data-opt="' + p.id + '" data-pos="' + i + '"' +
            (v.o[i] === val ? ' checked' : '') + '><span>' + esc(prettyOpt(val)) + '</span></label>';
        }).join('') + '</div></div>';
    }).join('');
  }
  function pickVariant(p, pos, val) {
    var cur = curVariant(p);
    var exact = p.variants.filter(function (x) {
      return x.o.every(function (ov, k) { return k === pos ? ov === val : ov === cur.o[k]; });
    })[0];
    return exact || p.variants.filter(function (x) { return x.o[pos] === val; })[0] || cur;
  }

  /* ---------- render ---------- */
  function renderTabs() {
    var counts = { all: products.length };
    products.forEach(function (p) { counts[p.cat] = (counts[p.cat] || 0) + 1; });
    var cats = CATS.filter(function (c) { return c.id === 'all' || counts[c.id]; });
    if (!cats.some(function (c) { return c.id === activeCat; })) activeCat = cats[0].id;
    el.tabs.innerHTML = cats.map(function (c) {
      return '<button type="button" role="tab" class="cb-tab' + (c.id === activeCat ? ' cb-on' : '') +
        '" data-cat="' + c.id + '" aria-selected="' + (c.id === activeCat) + '">' + esc(c.label) + '</button>';
    }).join('');
  }

  function renderGrid() {
    var list = products.filter(function (p) {
      return (activeCat === 'all' || p.cat === activeCat) && (!term || p.title.toLowerCase().indexOf(term) !== -1);
    });
    if (!list.length) { el.grid.innerHTML = '<p class="cb-status">No hay productos que coincidan.</p>'; return; }
    el.grid.innerHTML = list.map(function (p) {
      var v = curVariant(p);
      var q = productQty(p);
      var ck = key(v.id, p.curing ? curCuring(p) : '');
      var here = basket[ck] ? basket[ck].qty : 0;
      var variants = p.variants.length > 1 ? optRows(p, v) : '';
      var curing = p.curing
        ? '<div><p class="cb-lab">Punto de curación</p><div class="cb-curing">' +
            CURINGS.map(function (c) {
              return '<label><input type="radio" name="cur-' + p.id + '" value="' + c + '" data-curing="' + p.id + '"' +
                (c === curCuring(p) ? ' checked' : '') + '><span>' + c + '</span></label>';
            }).join('') + '</div></div>'
        : '';
      return (
        '<article class="cb-card' + (q > 0 ? ' cb-in' : '') + '">' +
          '<div class="cb-ph">' + (p.image ? '<img src="' + esc(img(p.image, 600)) + '" alt="' + esc(p.title) + '" loading="lazy" width="300" height="300">' : '') + '</div>' +
          '<div class="cb-body">' +
            '<h3 class="cb-name">' + esc(p.title) + '</h3>' +
            '<p class="cb-price">' + money(v.price) + '</p>' +
            variants + curing +
            '<button type="button" class="cb-add" data-add="' + ck + '" data-vid="' + v.id + '" data-cur="' + esc(p.curing ? curCuring(p) : '') + '">Añadir al pack</button>' +
            '<div class="cb-step-q">' +
              '<button type="button" class="cb-rb" data-dec="' + ck + '" aria-label="Quitar uno">−</button>' +
              '<input class="cb-qn" type="number" min="0" max="99" inputmode="numeric" data-qty="' + ck + '" data-vid="' + v.id + '" data-cur="' + esc(p.curing ? curCuring(p) : '') + '" value="' + here + '" aria-label="Cantidad">' +
              '<button type="button" class="cb-rb cb-plus" data-add="' + ck + '" data-vid="' + v.id + '" data-cur="' + esc(p.curing ? curCuring(p) : '') + '" aria-label="Añadir uno">+</button>' +
            '</div>' +
          '</div>' +
        '</article>'
      );
    }).join('');
  }

  function renderMilestones() {
    el.track.querySelectorAll('.cb-ms').forEach(function (n) { n.remove(); });
    MILESTONES.forEach(function (m) {
      var n = document.createElement('div');
      n.className = 'cb-ms';
      n.dataset.qty = m.qty;
      n.style.left = (m.qty / MAXQ * 100) + '%';
      n.innerHTML = '<i>' + m.qty + '</i><span>' + m.label + '</span>';
      el.track.appendChild(n);
    });
  }

  function renderPack() {
    var t = totals();
    var keys = Object.keys(basket).filter(function (k) { return basket[k].qty > 0 && byVariant[basket[k].vid]; });
    el.count.textContent = t.count + ' producto' + (t.count === 1 ? '' : 's');
    /* Descuento de la cesta: se cobra al pagar (código), aquí solo se muestra */
    var di = discountInfo(t), disc = di.best;
    el.total.textContent = money(t.cents - disc);
    el.save.hidden = disc === 0;
    if (disc) {
      el.save.innerHTML = (di.qty === 'auto'
        ? 'Descuento por cantidad (−' + AUTO_PCT + '%) aplicado, mejor que el −' + discPct + '% de la cesta'
        : '−' + discPct + '% de la cesta aplicado') + ' · ahorras <strong>' + money(disc) + '</strong>';
    }
    el.empty.hidden = keys.length > 0;
    el.clear.hidden = keys.length === 0;
    el.lines.innerHTML = keys.map(function (k) {
      var b = basket[k], h = byVariant[b.vid];
      var meta = [];
      if (h.variant.title && h.variant.title !== 'Default Title') meta.push(esc(h.variant.title));
      if (b.curing) meta.push(esc(b.curing));
      return '<li><span>' + esc(h.product.title) + '<small>' + b.qty + ' ×' + (meta.length ? ' · ' + meta.join(' · ') : '') + '</small></span><span>' + money(b.qty * h.variant.price) + '</span></li>';
    }).join('');

    var pct = Math.min(t.count / MAXQ, 1) * 100;
    el.fill.style.width = pct + '%';
    el.track.setAttribute('aria-valuenow', Math.round(pct));
    el.track.querySelectorAll('.cb-ms').forEach(function (n) { n.classList.toggle('cb-ok', t.count >= +n.dataset.qty); });

    var next = MILESTONES.filter(function (m) { return t.count < m.qty; })[0];
    if (!next) {
      el.dsub.innerHTML = '¡Has desbloqueado <strong>todos los regalos</strong>!';
    } else {
      var what = next.qty === MIN && t.count < MIN ? 'para crear tu pack' : 'para <strong>' + next.label.replace('<br>', ' ') + '</strong>';
      el.dsub.innerHTML = 'Añade <strong>' + (next.qty - t.count) + ' más</strong> ' + what;
    }

    var rem = Math.max(FREE - t.cents, 0);
    if (FREE > 0) {
      el.shipText.innerHTML = rem === 0
        ? '¡Envío gratis en península!'
        : 'A ' + money(FREE).replace(',00', '') + ' envío gratis en península · te faltan <strong>' + money(rem) + '</strong>';
      el.shipBar.style.width = Math.min(t.cents / FREE, 1) * 100 + '%';
    }
    el.add.disabled = t.count < MIN;
  }

  function refresh() { renderGrid(); renderPack(); }

  /* ---------- interacciones ---------- */
  function setQty(vid, curing, qty) {
    var k = key(vid, curing);
    qty = Math.max(0, Math.min(99, qty));
    if (qty === 0) delete basket[k]; else basket[k] = { vid: vid, curing: curing, qty: qty };
    save();
    refresh();
  }
  function getQty(vid, curing) { var b = basket[key(vid, curing)]; return b ? b.qty : 0; }

  root.addEventListener('click', function (e) {
    var t = e.target.closest('[data-add],[data-dec],[data-cat],[data-cb-clear],[data-cb-add],[data-cb-no],[data-cb-yes],[data-cb-search-clear],.cb-tl-step');
    if (!t) return;
    if (t.matches('[data-add]')) return setQty(t.dataset.vid, t.dataset.cur, getQty(t.dataset.vid, t.dataset.cur) + 1);
    if (t.matches('[data-dec]')) {
      var k = t.dataset.dec, b = basket[k];
      return b && setQty(b.vid, b.curing, b.qty - 1);
    }
    if (t.matches('[data-cat]')) { activeCat = t.dataset.cat; renderTabs(); return renderGrid(); }
    if (t.hasAttribute('data-cb-clear')) { el.modal.hidden = false; return $('[data-cb-no]').focus(); }
    if (t.hasAttribute('data-cb-no')) { el.modal.hidden = true; return; }
    if (t.hasAttribute('data-cb-yes')) { basket = {}; save(); el.modal.hidden = true; return refresh(); }
    if (t.hasAttribute('data-cb-add')) return addToCart();
    if (t.hasAttribute('data-cb-search-clear')) {
      el.search.value = ''; term = ''; el.searchClear.hidden = true; renderGrid(); return el.search.focus();
    }
    if (t.classList.contains('cb-tl-step')) { setStep(+t.dataset.s); playTl(); }
  });

  root.addEventListener('change', function (e) {
    var t = e.target;
    if (t.matches('[data-opt]')) {
      var prod = products.filter(function (x) { return String(x.id) === t.dataset.opt; })[0];
      if (prod) { selVariant[prod.id] = pickVariant(prod, parseInt(t.dataset.pos, 10), t.value).id; }
      return renderGrid();
    }
    if (t.matches('[data-curing]')) { selCuring[t.dataset.curing] = t.value; return renderGrid(); }
    if (t.matches('[data-qty]')) return setQty(t.dataset.vid, t.dataset.cur, parseInt(t.value, 10) || 0);
  });

  el.search.addEventListener('input', function () {
    term = el.search.value.trim().toLowerCase();
    el.searchClear.hidden = !term;
    renderGrid();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') el.modal.hidden = true; });

  /* ---------- timeline del banner ---------- */
  var steps = [].slice.call(root.querySelectorAll('.cb-tl-step'));
  var tlFill = $('[data-cb-tl-fill]'), tl = $('[data-cb-tl]'), cur = 0, timer;
  function setStep(n) {
    cur = n;
    steps.forEach(function (s, i) { s.classList.toggle('cb-on', i === n); s.classList.toggle('cb-done', i < n); });
    var pct = n / (steps.length - 1) * 100;
    tlFill.style.width = pct + '%';
    tl.style.setProperty('--h', pct + '%');
  }
  function playTl() {
    clearInterval(timer);
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    timer = setInterval(function () { setStep((cur + 1) % steps.length); }, 2600);
  }

  /* ---------- añadir al carrito ---------- */
  function boxId() { return 'cesta-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

  function giftVariantId() {
    if (!GIFT) return Promise.resolve(null);
    return fetch('/products/' + encodeURIComponent(GIFT) + '.js')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (p) {
        var v = p && p.variants.filter(function (x) { return x.available; })[0];
        return v ? v.id : null;
      })
      .catch(function () { return null; });
  }

  function addToCart() {
    if (totals().count < MIN) return;
    var id = boxId();
    var label = el.add.textContent;
    el.add.disabled = true;
    el.add.textContent = 'Añadiendo…';

    giftVariantId().then(function (giftId) {
      var items = Object.keys(basket).filter(function (k) { return basket[k].qty > 0 && byVariant[basket[k].vid]; }).map(function (k) {
        var b = basket[k];
        var props = { 'Cesta': 'Tu pack personalizado', '_cesta_id': id };
        if (b.curing) props['Punto de curación'] = b.curing;
        return { id: Number(b.vid), quantity: b.qty, properties: props };
      });
      if (giftId) items.push({ id: giftId, quantity: 1, properties: { 'Cesta': 'Caja de regalo', '_cesta_id': id, '_cesta_caja': '1' } });
      return fetch('/cart/add.js', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items: items })
      });
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (x) { throw new Error(x.description || x.message || 'Error al añadir'); });
        return r.json();
      })
      .then(function () {
        /* el descuento de la cesta es un código: cesta-discount.js lo pone (o lo quita) según el carrito */
        return window.cmSyncCestaCode ? window.cmSyncCestaCode().catch(function () {}) : null;
      })
      .then(function () {
        basket = {}; save(); refresh();
        if (window.fetchAndRenderCart) {
          return window.fetchAndRenderCart().then(function () { if (window.openCart) window.openCart(true); });
        }
        window.location.href = '/cart';
      })
      .catch(function (err) { el.min.textContent = err.message || 'No se pudo añadir el pack. Inténtalo de nuevo.'; })
      .finally(function () {
        el.add.textContent = label;
        el.add.disabled = totals().count < MIN;
      });
  }

  /* ---------- init ---------- */
  load();
  renderMilestones();
  setStep(0);
  playTl();
  renderPack();
  loadProducts()
    .then(function () {
      Object.keys(basket).forEach(function (k) { if (!byVariant[basket[k].vid]) delete basket[k]; });
      renderTabs();
      refresh();
    })
    .catch(function () {
      el.grid.innerHTML = '<p class="cb-status">No se pudieron cargar los productos. Recarga la página.</p>';
    });
})();
