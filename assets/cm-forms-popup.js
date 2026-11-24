/* Pop-up del 10 % (app Shopify Forms, <shopify-forms-embed> con shadow DOM abierto) — ajustes desde el tema.

   La app decide cuándo sale (Admin > Apps > Forms); el tema solo puede esconderla o reaccionar:
   1. No sale con el cajón del carrito abierto ni justo después de cerrarlo (Clarity lo grabó tapando el cajón los días
      14/11 y 16/11). Mientras el cajón está abierto, y COOLDOWN_MS después de cerrarlo, el elemento de la app se oculta
      (clase cm-forms-hold en <html>). El pop-up no se descarta: si le toca salir, sale cuando acaba la espera.
   2. Se oculta el cartel fijo «10 % off» (teaser) que se queda pegado abajo y tapa el botón de añadir de la ficha.
   3. Al pedir el código (la app muestra BIENVENIDA10) se aplica solo: se visita /discount/BIENVENIDA10, que guarda el
      código en la cookie del carrito y Shopify lo aplica al pagar (igual que el enlace de la tarjeta de bienvenida).
      Así el cliente no tiene que copiarlo. No se repite en la misma sesión.

   Los nombres de clase de la app llevan un sufijo generado (_teaserContainer_trejf_): se usan selectores por «contiene»
   para sobrevivir a sus actualizaciones. Si la app cambia su estructura, lo único que se pierde es esto (el pop-up sigue
   funcionando como antes). */
(function () {
  'use strict';

  var HOST_TAG = 'shopify-forms-embed';
  var HOLD_CLASS = 'cm-forms-hold';
  var COOLDOWN_MS = 25000;
  var WELCOME_CODE = 'BIENVENIDA10';
  var APPLIED_KEY = 'cm-welcome-applied';
  var html = document.documentElement;
  var holdTimer = null;

  /* ── CSS de la página (oculta la app mientras hay espera) ── */
  var pageStyle = document.createElement('style');
  pageStyle.textContent = 'html.' + HOLD_CLASS + ' ' + HOST_TAG + '{display:none!important}';
  document.head.appendChild(pageStyle);

  /* ── 1. Espera mientras el cajón está abierto y después de cerrarlo ── */
  function hold() {
    clearTimeout(holdTimer);
    html.classList.add(HOLD_CLASS);
  }
  function releaseLater() {
    clearTimeout(holdTimer);
    holdTimer = setTimeout(function () { html.classList.remove(HOLD_CLASS); }, COOLDOWN_MS);
  }
  function syncWithDrawer(drawer) {
    if (drawer.classList.contains('active')) hold(); else if (html.classList.contains(HOLD_CLASS)) releaseLater();
  }
  function watchDrawer() {
    var drawer = document.getElementById('cart-drawer');
    if (!drawer) return;
    syncWithDrawer(drawer);
    new MutationObserver(function () { syncWithDrawer(drawer); })
      .observe(drawer, { attributes: true, attributeFilter: ['class'] });
  }

  /* ── 2. Teaser fuera ── */
  var SHADOW_CSS = '[class*="teaserContainer"],[class*="teaserHeading"]{display:none!important}';
  function hideTeaser(shadow) {
    if (shadow.querySelector('style[data-cm-forms]')) return;
    var st = document.createElement('style');
    st.setAttribute('data-cm-forms', '');
    st.textContent = SHADOW_CSS;
    shadow.appendChild(st);
  }

  /* ── 3. Código aplicado solo ── */
  var NOTE = {
    es: 'Código aplicado a tu cesta: se descuenta solo al pagar.',
    en: 'Code applied to your cart: it is taken off automatically at checkout.',
    fr: 'Code appliqué à votre panier : il est déduit automatiquement au paiement.'
  };
  function noteText() {
    var lang = (html.lang || 'es').slice(0, 2).toLowerCase();
    return NOTE[lang] || NOTE.es;
  }
  function addNote(shadow) {
    var walker = document.createTreeWalker(shadow, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) {
      if (node.nodeValue.indexOf(WELCOME_CODE) === -1) continue;
      var host = node.parentElement;
      if (!host || host.tagName === 'STYLE' || host.parentElement.querySelector('[data-cm-forms-note]')) return;
      var p = document.createElement('p');
      p.setAttribute('data-cm-forms-note', '');
      p.textContent = noteText();
      p.style.cssText = 'margin:8px 0 0;font-size:13px;line-height:1.4;text-align:center';
      host.insertAdjacentElement('afterend', p);
      return;
    }
  }
  function applyWelcome(shadow) {
    try { if (sessionStorage.getItem(APPLIED_KEY)) return; } catch (e) { /* sin sessionStorage: se aplica igual */ }
    fetch('/discount/' + WELCOME_CODE + '?redirect=%2Fcart.js', { credentials: 'same-origin' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        try { sessionStorage.setItem(APPLIED_KEY, '1'); } catch (e) { /* ignorar */ }
        addNote(shadow);
      })
      .catch(function (err) { console.error('[cm-forms-popup] no se pudo aplicar ' + WELCOME_CODE + ':', err); });
  }
  function watchSuccess(shadow) {
    var done = false;
    function check() {
      if (done) return;
      if ((shadow.textContent || '').indexOf(WELCOME_CODE) === -1) return;
      done = true;
      applyWelcome(shadow);
    }
    new MutationObserver(check).observe(shadow, { childList: true, subtree: true, characterData: true });
    check();
  }

  /* ── El elemento de la app aparece tarde: se vigila ── */
  var seen = new WeakSet();
  function adopt(host) {
    if (seen.has(host) || !host.shadowRoot) return;
    seen.add(host);
    hideTeaser(host.shadowRoot);
    watchSuccess(host.shadowRoot);
  }
  function scan() {
    var hosts = document.getElementsByTagName(HOST_TAG);
    for (var i = 0; i < hosts.length; i++) adopt(hosts[i]);
  }
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  scan();
  watchDrawer();
})();
