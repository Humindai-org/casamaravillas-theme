(function () {
  'use strict';

  /* ─── STATE ─── */
  let currentStep = 1;
  const SHIPPING_FREE_THRESHOLD = 8000;
  const SHIPPING_EXPRESS_COST   = 990;
  const SHIPPING_REGALO_COST    = 1490;

  const state = {
    total_price:     0,
    shipping_cost:   0,
    discount_amount: 0,
    discount_code:   '',
    items:           []
  };

  /* ─── PROVINCES ES (CP prefix) ─── */
  const PROVINCES = {
    ES: {
      'Álava':['01'],'Albacete':['02'],'Alicante':['03'],'Almería':['04'],
      'Ávila':['05'],'Badajoz':['06'],'Baleares':['07'],'Barcelona':['08'],
      'Burgos':['09'],'Cáceres':['10'],'Cádiz':['11'],'Castellón':['12'],
      'Ciudad Real':['13'],'Córdoba':['14'],'A Coruña':['15'],'Cuenca':['16'],
      'Girona':['17'],'Granada':['18'],'Guadalajara':['19'],'Gipuzkoa':['20'],
      'Huelva':['21'],'Huesca':['22'],'Jaén':['23'],'León':['24'],
      'Lleida':['25'],'La Rioja':['26'],'Lugo':['27'],'Madrid':['28'],
      'Málaga':['29'],'Murcia':['30'],'Navarra':['31'],'Ourense':['32'],
      'Asturias':['33'],'Palencia':['34'],'Las Palmas':['35'],'Pontevedra':['36'],
      'Salamanca':['37'],'S.C. de Tenerife':['38'],'Cantabria':['39'],
      'Segovia':['40'],'Sevilla':['41'],'Soria':['42'],'Tarragona':['43'],
      'Teruel':['44'],'Toledo':['45'],'Valencia':['46'],'Valladolid':['47'],
      'Bizkaia':['48'],'Zamora':['49'],'Zaragoza':['50'],'Ceuta':['51'],'Melilla':['52']
    },
    PT: ['Lisboa','Porto','Braga','Faro','Aveiro','Coimbra','Setúbal','Évora','Funchal','Ponta Delgada'],
    FR: ['París','Marsella','Lyon','Toulouse','Burdeos','Nantes','Estrasburgo','Lille','Niza','Montpellier'],
    DE: ['Berlín','Múnich','Hamburgo','Colonia','Fráncfort','Stuttgart','Düsseldorf','Leipzig','Bremen','Dresde'],
    IT: ['Roma','Milán','Nápoles','Turín','Palermo','Génova','Bolonia','Florencia','Bari','Catania'],
    GB: ['Londres','Birmingham','Manchester','Glasgow','Liverpool','Edimburgo','Bristol','Leeds','Sheffield','Cardiff'],
    CH: ['Zúrich','Ginebra','Basilea','Berna','Lausana','Winterthur','Lucerna','St. Gallen','Lugano','Friburgo'],
    AT: ['Viena','Graz','Linz','Salzburgo','Innsbruck','Klagenfurt','Villach','Wels','St. Pölten','Dornbirn'],
    BE: ['Bruselas','Amberes','Gante','Brujas','Lieja','Namur','Lovaina','Mons','Aalst','Hasselt'],
    BG: ['Sofía','Plovdiv','Varna','Burgas','Rousse','Stara Zagora','Pleven','Sliven','Dobrich','Shumen'],
    HR: ['Zagreb','Split','Rijeka','Osijek','Zadar','Slavonski Brod','Pula','Karlovac','Sisak','Varaždin'],
    CY: ['Nicosia','Limassol','Larnaca','Famagusta','Pafos'],
    CZ: ['Praga','Brno','Ostrava','Plzeň','Liberec','Olomouc','Ústí nad Labem','České Budějovice','Hradec Králové','Pardubice'],
    DK: ['Copenhague','Aarhus','Odense','Aalborg','Esbjerg','Randers','Kolding','Horsens','Vejle','Roskilde'],
    EE: ['Tallin','Tartu','Narva','Pärnu','Kohtla-Järve'],
    FI: ['Helsinki','Espoo','Tampere','Vantaa','Oulu','Turku','Jyväskylä','Lahti','Kuopio','Pori'],
    GR: ['Atenas','Tesalónica','Patras','Heraclión','Larisa','Volos','Rodas','Janina','Alexandrópolis','Kavala'],
    HU: ['Budapest','Debrecen','Miskolc','Szeged','Pécs','Győr','Nyíregyháza','Kecskemét','Székesfehérvár','Szombathely'],
    IE: ['Dublín','Cork','Limerick','Galway','Waterford','Drogheda','Dundalk','Swords','Bray','Navan'],
    LV: ['Riga','Daugavpils','Liepāja','Jelgava','Jūrmala','Ventspils','Rēzekne','Valmiera'],
    LT: ['Vilna','Kaunas','Klaipėda','Šiauliai','Panevėžys','Alytus','Marijampolė','Mažeikiai'],
    LU: ['Luxemburgo ciudad','Esch-sur-Alzette','Differdange','Dudelange','Ettelbruck'],
    MT: ['La Valeta','Birkirkara','Qormi','Mosta','Żabbar','San Pawl il-Baħar','Fgura','Żejtun'],
    NL: ['Ámsterdam','Rotterdam','La Haya','Utrecht','Eindhoven','Tilburg','Groninga','Almere','Breda','Nimega'],
    PL: ['Varsovia','Cracovia','Lodz','Wroclaw','Poznan','Gdansk','Szczecin','Bydgoszcz','Lublin','Katowice'],
    RO: ['Bucarest','Cluj-Napoca','Timișoara','Iași','Constanța','Craiova','Brașov','Galați','Ploiești','Oradea'],
    SK: ['Bratislava','Košice','Prešov','Žilina','Banská Bystrica','Nitra','Trnava','Martin','Trenčín','Poprad'],
    SI: ['Liubliana','Maribor','Celje','Kranj','Velenje','Koper','Novo Mesto','Ptuj','Trbovlje','Kamnik'],
    SE: ['Estocolmo','Gotemburgo','Malmö','Uppsala','Sollentuna','Västerås','Örebro','Linköping','Helsingborg','Jönköping']
  };

  /* ─── INIT ─── */
  function init() {
    if (!document.querySelector('.co-wrapper')) return;
    fetchCart();
    bindStepNavigation();
    bindQtyControls();
    bindRemoveItems();
    bindCountryCitySelect();
    bindCPValidation();
    bindShippingOptions();
    bindGiftMessage();
    bindCardFormatting();
    bindDiscountCode();
    bindInvoiceToggle();
    bindNewsletter();
    bindCheckoutForm();
  }

  /* ─── FETCH CART ─── */
  function fetchCart() {
    fetch('/cart.js')
      .then(r => r.json())
      .then(cart => {
        state.total_price = cart.total_price;
        state.items = cart.items;
        updateSummaryTotals();
      })
      .catch(() => {});
  }

  /* ─── STEP NAVIGATION ─── */
  function bindStepNavigation() {
    document.querySelectorAll('[data-next]').forEach(btn => {
      btn.addEventListener('click', () => {
        const target = parseInt(btn.dataset.next, 10);
        if (validateStep(currentStep)) goToStep(target);
      });
    });

    document.querySelectorAll('[data-prev]').forEach(btn => {
      btn.addEventListener('click', () => {
        goToStep(parseInt(btn.dataset.prev, 10));
      });
    });

    document.querySelectorAll('.co-step').forEach(step => {
      step.addEventListener('click', function (e) {
        if (!this.classList.contains('completed')) return;
        if (e.target.closest('button,a,input,select,textarea')) return;
        goToStep(parseInt(this.dataset.step, 10));
      });
    });
  }

  function goToStep(target) {
    const steps = document.querySelectorAll('.co-step');
    const navItems = document.querySelectorAll('.co-step-indicator');

    steps.forEach(step => {
      const n = parseInt(step.dataset.step, 10);
      step.classList.remove('active');
      if (n < target) step.classList.add('completed');
      else step.classList.remove('completed');
    });

    const targetEl = document.getElementById('step-' + target);
    if (targetEl) {
      targetEl.classList.add('active');
      targetEl.classList.remove('completed');
    }

    navItems.forEach(nav => {
      const n = parseInt(nav.dataset.stepNav, 10);
      nav.classList.remove('active', 'completed');
      if (n === target) nav.classList.add('active');
      else if (n < target) nav.classList.add('completed');
    });

    currentStep = target;
    if (targetEl) scrollToStep(targetEl);
    if (target === 3) updateShippingCost();
    if (target === 4) updateSummaryTotals();
  }

  function scrollToStep(el) {
    const top = el.getBoundingClientRect().top + window.scrollY - 100;
    window.scrollTo({ top, behavior: 'smooth' });
  }

  /* ─── VALIDATION ─── */
  function validateStep(step) {
    if (step === 1 || step === 3) return true;

    if (step === 2) {
      const fields = [
        { id: 'co-email',     errId: 'co-email-error',     type: 'email',  label: 'Correo electrónico' },
        { id: 'co-nombre',    errId: 'co-nombre-error',    type: 'text',   label: 'Nombre' },
        { id: 'co-apellidos', errId: 'co-apellidos-error', type: 'text',   label: 'Apellidos' },
        { id: 'co-direccion', errId: 'co-direccion-error', type: 'text',   label: 'Dirección' },
        { id: 'co-pais',      errId: 'co-pais-error',      type: 'select', label: 'País' },
        { id: 'co-ciudad',    errId: 'co-ciudad-error',    type: 'select', label: 'Ciudad' },
        { id: 'co-cp',        errId: 'co-cp-error',        type: 'postal', label: 'Código postal' },
        { id: 'co-telefono',  errId: 'co-telefono-error',  type: 'phone',  label: 'Teléfono' }
      ];

      let valid = true;
      fields.forEach(f => {
        const el  = document.getElementById(f.id);
        const err = document.getElementById(f.errId);
        if (!el || !err) return;

        const val = el.value.trim();
        let msg = '';

        if (!val) {
          msg = f.label + ' es obligatorio';
        } else if (f.type === 'email' && !validEmail(val)) {
          msg = 'Introduce un correo válido';
        } else if (f.type === 'phone' && !validPhone(val)) {
          msg = 'Introduce un teléfono válido';
        } else if (f.type === 'postal') {
          const pais   = document.getElementById('co-pais')?.value;
          const ciudad = document.getElementById('co-ciudad')?.value;
          const res = validateCP(val, pais, ciudad);
          if (!res.ok) msg = res.msg;
        }

        if (msg) {
          valid = false;
          el.classList.add('error');
          err.textContent = msg;
        } else {
          el.classList.remove('error');
          err.textContent = '';
        }
      });
      return valid;
    }
    return true;
  }

  function validEmail(v) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v); }
  function validPhone(v) { return /^[\+]?[\d\s\-\(\)]{7,18}$/.test(v); }

  function validateCP(cp, country, city) {
    if (!cp) return { ok: false, msg: 'El código postal es obligatorio' };
    if (country === 'ES') {
      if (!/^\d{5}$/.test(cp)) return { ok: false, msg: 'El código postal debe tener 5 dígitos' };
      const num = parseInt(cp.substring(0, 2), 10);
      if (num < 1 || num > 52) return { ok: false, msg: 'Código postal español no válido' };
      if (city && PROVINCES.ES[city]) {
        const prefixes = PROVINCES.ES[city];
        if (prefixes.length && !prefixes.includes(cp.substring(0, 2))) {
          return { ok: false, msg: 'El código postal no corresponde a ' + city };
        }
      }
    } else if (country === 'PT') {
      if (!/^\d{4}-\d{3}$/.test(cp) && !/^\d{7}$/.test(cp)) return { ok: false, msg: 'Formato: 0000-000' };
    } else if (country === 'US') {
      if (!/^\d{5}(-\d{4})?$/.test(cp)) return { ok: false, msg: 'Formato: 00000 o 00000-0000' };
    }
    return { ok: true };
  }

  /* ─── COUNTRY → CITY CASCADE ─── */
  function bindCountryCitySelect() {
    const paisEl   = document.getElementById('co-pais');
    const ciudadEl = document.getElementById('co-ciudad');
    if (!paisEl || !ciudadEl) return;

    paisEl.addEventListener('change', () => {
      populateCities(paisEl.value, ciudadEl);
      const cpEl = document.getElementById('co-cp');
      if (cpEl) { cpEl.value = ''; cpEl.classList.remove('error'); }
      setErr('co-cp-error', '');
    });

    populateCities(paisEl.value, ciudadEl);
  }

  function populateCities(country, selectEl) {
    selectEl.innerHTML = '<option value="">Selecciona una ciudad / provincia</option>';
    const data = PROVINCES[country];
    if (!data) return;
    const list = Array.isArray(data) ? data : Object.keys(data);
    list.sort().forEach(city => {
      const opt = document.createElement('option');
      opt.value = city;
      opt.textContent = city;
      selectEl.appendChild(opt);
    });
  }

  /* ─── POSTAL CODE LIVE VALIDATION ─── */
  function bindCPValidation() {
    const cpEl     = document.getElementById('co-cp');
    const paisEl   = document.getElementById('co-pais');
    const ciudadEl = document.getElementById('co-ciudad');
    if (!cpEl) return;

    cpEl.addEventListener('blur', () => {
      const res = validateCP(cpEl.value.trim(), paisEl?.value, ciudadEl?.value);
      if (!res.ok) { cpEl.classList.add('error'); setErr('co-cp-error', res.msg); }
      else { cpEl.classList.remove('error'); setErr('co-cp-error', ''); }
    });

    cpEl.addEventListener('input', () => {
      if (!cpEl.classList.contains('error')) return;
      const res = validateCP(cpEl.value.trim(), paisEl?.value, ciudadEl?.value);
      if (res.ok) { cpEl.classList.remove('error'); setErr('co-cp-error', ''); }
    });
  }

  /* ─── QTY CONTROLS ─── */
  function bindQtyControls() {
    const container = document.getElementById('co-cart-items');
    if (!container) return;

    container.addEventListener('click', e => {
      const btn = e.target.closest('.co-qty-btn');
      if (!btn) return;
      const input = btn.closest('.co-cart-item__qty-wrap')?.querySelector('.co-qty-input');
      if (!input) return;
      let qty = parseInt(input.value, 10) || 0;
      if (btn.dataset.action === 'decrease') qty = Math.max(0, qty - 1);
      if (btn.dataset.action === 'increase') qty += 1;
      input.value = qty;
      cartChange(parseInt(input.dataset.line, 10), qty, input.dataset.key);
    });

    container.addEventListener('change', e => {
      const input = e.target.closest('.co-qty-input');
      if (!input) return;
      const qty = Math.max(0, parseInt(input.value, 10) || 0);
      input.value = qty;
      cartChange(parseInt(input.dataset.line, 10), qty, input.dataset.key);
    });
  }

  /* ─── REMOVE ITEMS ─── */
  function bindRemoveItems() {
    const container = document.getElementById('co-cart-items');
    if (!container) return;

    container.addEventListener('click', e => {
      const btn = e.target.closest('.co-cart-item__remove');
      if (!btn) return;
      const itemEl = btn.closest('.co-cart-item');
      if (itemEl) { itemEl.style.opacity = '0.4'; itemEl.style.pointerEvents = 'none'; }
      cartChange(parseInt(btn.dataset.line, 10), 0, btn.dataset.key);
    });
  }

  function cartChange(line, quantity, key) {
    fetch('/cart/change.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ line, quantity })
    })
      .then(r => r.json())
      .then(cart => {
        state.total_price = cart.total_price;
        state.items       = cart.items;
        rebuildCartItems(cart);
        rebuildSummaryItems(cart);
        updateSummaryTotals();
      })
      .catch(() => {
        const el = document.querySelector(`[data-key="${key}"]`);
        if (el) { el.style.opacity = '1'; el.style.pointerEvents = ''; }
      });
  }

  function rebuildCartItems(cart) {
    const c = document.getElementById('co-cart-items');
    if (!c) return;
    if (!cart.item_count) {
      c.innerHTML = '<p style="text-align:center;padding:32px 0;color:var(--co-text-mid);font-family:var(--co-sans);font-size:14px;">Tu carrito está vacío</p>';
      return;
    }
    c.innerHTML = cart.items.map((item, i) => {
      const img = item.image
        ? `<img class="co-cart-item__img" src="${item.image.split('?')[0]}?width=160" alt="${esc(item.product_title)}" width="80" height="80" loading="lazy">`
        : `<div class="co-cart-item__img co-cart-item__img--empty"></div>`;
      const variant = item.variant_title && item.variant_title !== 'Default Title'
        ? `<p class="co-cart-item__variant">${esc(item.variant_title)}</p>` : '';
      return `
        <div class="co-cart-item" data-key="${item.key}" data-line="${i+1}" style="animation:co-fade-in 0.3s ease forwards">
          <div class="co-cart-item__img-wrap">${img}</div>
          <div class="co-cart-item__info">
            <p class="co-cart-item__name">${esc(item.product_title)}</p>${variant}
            <div class="co-cart-item__qty-wrap">
              <button class="co-qty-btn" type="button" data-action="decrease" aria-label="Reducir">−</button>
              <input class="co-qty-input" type="number" value="${item.quantity}" min="0" data-line="${i+1}" data-key="${item.key}" aria-label="Cantidad">
              <button class="co-qty-btn" type="button" data-action="increase" aria-label="Aumentar">+</button>
            </div>
            <button class="co-cart-item__remove" type="button" data-key="${item.key}" data-line="${i+1}">Eliminar</button>
          </div>
          <div class="co-cart-item__price-wrap">
            <span class="co-cart-item__price">${money(item.final_line_price)}</span>
          </div>
        </div>`;
    }).join('');
  }

  function rebuildSummaryItems(cart) {
    const c = document.getElementById('co-summary-items');
    if (!c) return;
    c.innerHTML = cart.items.map(item => {
      const img = item.image
        ? `<img class="co-summary__item-img" src="${item.image.split('?')[0]}?width=80" alt="${esc(item.product_title)}" width="40" height="40">` : '';
      const variant = item.variant_title && item.variant_title !== 'Default Title'
        ? `<p class="co-summary__item-variant">${esc(item.variant_title)}</p>` : '';
      return `
        <div class="co-summary__item" data-key="${item.key}">
          <div class="co-summary__item-img-wrap">${img}<span class="co-summary__item-qty">${item.quantity}</span></div>
          <div class="co-summary__item-info"><p class="co-summary__item-name">${esc(item.product_title)}</p>${variant}</div>
          <span class="co-summary__item-price">${money(item.final_line_price)}</span>
        </div>`;
    }).join('');
  }

  /* ─── SHIPPING OPTIONS ─── */
  function bindShippingOptions() {
    document.querySelectorAll('.co-shipping-radio').forEach(r => {
      r.addEventListener('change', updateShippingCost);
    });
  }

  function updateShippingCost() {
    const selected = document.querySelector('.co-shipping-radio:checked');
    if (!selected) return;
    const method = selected.value;
    let cost = 0;

    if (method === 'standard') {
      cost = state.total_price >= SHIPPING_FREE_THRESHOLD ? 0 : 490;
    } else if (method === 'express') {
      cost = SHIPPING_EXPRESS_COST;
    } else if (method === 'regalo') {
      cost = SHIPPING_REGALO_COST;
    }

    state.shipping_cost = cost;
    animateValue('co-shipping-cost', cost === 0 ? 'Gratis' : money(cost));
    updateSummaryTotals();
  }

  /* ─── GIFT MESSAGE ─── */
  function bindGiftMessage() {
    const wrap    = document.getElementById('co-gift-wrap');
    const msg     = document.getElementById('co-gift-message');
    const counter = document.getElementById('co-gift-char');
    if (!wrap) return;

    document.querySelectorAll('.co-shipping-radio').forEach(r => {
      r.addEventListener('change', () => {
        const show = r.value === 'regalo' && r.checked;
        wrap.classList.toggle('active', show);
        wrap.setAttribute('aria-hidden', String(!show));
        if (show && msg) msg.focus();
      });
    });

    if (msg && counter) {
      msg.addEventListener('input', () => { counter.textContent = msg.value.length; });
    }
  }

  /* ─── CARD FORMATTING ─── */
  function bindCardFormatting() {
    const num    = document.getElementById('co-card-number');
    const expiry = document.getElementById('co-card-expiry');

    if (num) {
      num.addEventListener('input', () => {
        const v = num.value.replace(/\D/g, '').substring(0, 16);
        num.value = v.replace(/(\d{4})(?=\d)/g, '$1 ');
      });
    }

    if (expiry) {
      expiry.addEventListener('input', () => {
        let v = expiry.value.replace(/\D/g, '').substring(0, 4);
        if (v.length >= 3) v = v.substring(0, 2) + ' / ' + v.substring(2);
        expiry.value = v;
      });
    }
  }

  /* ─── DISCOUNT CODE ─── */
  function bindDiscountCode() {
    const btn      = document.getElementById('co-discount-apply');
    const input    = document.getElementById('co-discount-code');
    const msgEl    = document.getElementById('co-discount-msg');
    const row      = document.getElementById('co-discount-row');
    const amountEl = document.getElementById('co-discount-amount');
    if (!btn || !input) return;

    const CODES = { 'IBERICO10': 0.10, 'BELLOTA15': 0.15, 'CASA20': 0.20 };

    btn.addEventListener('click', () => {
      const code = input.value.trim().toUpperCase();
      if (!code) { showMsg(msgEl, 'Introduce un código de descuento', 'error'); return; }

      btn.disabled = true;
      btn.textContent = 'Aplicando...';

      setTimeout(() => {
        if (CODES[code]) {
          const pct = CODES[code];
          state.discount_amount = Math.round(state.total_price * pct);
          state.discount_code   = code;
          if (row) row.style.display = 'flex';
          if (amountEl) animateValue(amountEl.id, '−' + money(state.discount_amount));
          updateSummaryTotals();
          showMsg(msgEl, `Código "${code}" aplicado (${Math.round(pct * 100)}% de descuento)`, 'success');
          input.disabled    = true;
          btn.textContent   = '✓ Aplicado';
        } else {
          state.discount_amount = 0;
          showMsg(msgEl, 'Código no válido o expirado', 'error');
          btn.disabled    = false;
          btn.textContent = 'Aplicar';
        }
      }, 800);
    });
  }

  /* ─── INVOICE TOGGLE ─── */
  function bindInvoiceToggle() {
    const check  = document.getElementById('co-invoice-check');
    const fields = document.getElementById('co-invoice-fields');
    if (!check || !fields) return;

    check.addEventListener('change', () => {
      fields.classList.toggle('active', check.checked);
      fields.setAttribute('aria-hidden', String(!check.checked));
    });
  }

  /* ─── NEWSLETTER ─── */
  function bindNewsletter() {
    const btn   = document.getElementById('co-newsletter-btn');
    const input = document.getElementById('co-newsletter-email');
    const msg   = document.getElementById('co-newsletter-msg');
    if (!btn || !input) return;

    btn.addEventListener('click', () => {
      const email = input.value.trim();
      if (!validEmail(email)) { showMsg(msg, 'Introduce un correo válido', 'error'); input.focus(); return; }
      btn.disabled    = true;
      btn.textContent = 'Enviando...';

      fetch('/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `form_type=customer&email=${encodeURIComponent(email)}&contact[tags]=newsletter`
      })
        .finally(() => {
          showMsg(msg, '¡Gracias! Ya estás suscrito.', 'success');
          input.value     = '';
          btn.textContent = '✓ Suscrito';
        });
    });
  }

  /* ─── CHECKOUT FORM ─── */
  function bindCheckoutForm() {
    const form     = document.getElementById('co-checkout-form');
    const btn      = document.getElementById('co-checkout-btn');
    const terms    = document.getElementById('co-terms');
    const termsErr = document.getElementById('co-terms-error');
    if (!form || !btn) return;

    form.addEventListener('submit', e => {
      if (!terms?.checked) {
        e.preventDefault();
        if (termsErr) termsErr.textContent = 'Debes aceptar los términos y condiciones';
        terms?.focus();
        return;
      }
      if (termsErr) termsErr.textContent = '';

      mapHidden('hidden-email',      'co-email');
      mapHidden('hidden-first-name', 'co-nombre');
      mapHidden('hidden-last-name',  'co-apellidos');
      mapHidden('hidden-address1',   'co-direccion');
      mapHidden('hidden-address2',   'co-apartamento');
      mapHidden('hidden-country',    'co-pais');
      mapHidden('hidden-city',       'co-ciudad');
      mapHidden('hidden-zip',        'co-cp');
      mapHidden('hidden-phone',      'co-telefono');

      btn.classList.add('loading');
      btn.disabled = true;
    });
  }

  function mapHidden(hiddenId, srcId) {
    const h = document.getElementById(hiddenId);
    const s = document.getElementById(srcId);
    if (h && s) h.value = s.value;
  }

  /* ─── TOTALS UPDATE ─── */
  function updateSummaryTotals() {
    const subtotal = state.total_price;
    const shipping = state.shipping_cost || 0;
    const discount = state.discount_amount || 0;
    const total    = Math.max(0, subtotal + shipping - discount);
    const iva      = Math.round(total * 0.0909);

    animateValue('co-subtotal', money(subtotal));
    animateValue('co-total',    money(total));
    animateValue('co-iva',      money(iva));
    animateValue('co-shipping-cost', shipping === 0 ? 'Gratis' : money(shipping));
  }

  /* ─── HELPERS ─── */
  function money(cents) {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency', currency: 'EUR', minimumFractionDigits: 2
    }).format(cents / 100);
  }

  function esc(str) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(str || ''));
    return d.innerHTML;
  }

  function setErr(id, msg) {
    const el = document.getElementById(id);
    if (el) el.textContent = msg;
  }

  function showMsg(el, text, type) {
    if (!el) return;
    el.textContent  = text;
    el.className    = (el.className.split(' ')[0] || '') + ' ' + type;
  }

  function animateValue(id, newText) {
    const el = typeof id === 'string' ? document.getElementById(id) : id;
    if (!el) return;
    el.style.opacity   = '0';
    el.style.transform = 'translateY(4px)';
    el.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
    setTimeout(() => {
      el.textContent = newText;
      el.style.opacity   = '1';
      el.style.transform = 'translateY(0)';
    }, 150);
  }

  /* ─── BOOT ─── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
