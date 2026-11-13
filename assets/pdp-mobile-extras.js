/*
  Ficha de producto, borrador 2026-11-12 (análisis Clarity):
  1) Móvil: la descripción se pliega como un acordeón («Descripción +»).
  2) Piezas enteras: la barra fija de compra no añade al carrito hasta que se ha
     elegido peso/formato; la primera vez lleva al selector y lo resalta.
*/
(function () {
  'use strict';

  /* ── 1) Descripción plegable en móvil ── */
  var mq = window.matchMedia('(max-width: 900px)');

  function setupDescription() {
    var desc = document.querySelector('.cm-pdp__desc');
    if (!desc) return;
    var toggle = desc.querySelector('.cm-pdp__desc-toggle');

    if (mq.matches) {
      if (!toggle) {
        toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'cm-pdp__desc-toggle';
        toggle.textContent = desc.getAttribute('data-title') || 'Descripción';
        toggle.addEventListener('click', function () {
          var open = desc.classList.toggle('is-open');
          toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        desc.insertBefore(toggle, desc.firstChild);
      }
      desc.classList.add('is-collapsible');
      toggle.setAttribute('aria-expanded', desc.classList.contains('is-open') ? 'true' : 'false');
    } else {
      desc.classList.remove('is-collapsible', 'is-open');
      if (toggle) toggle.remove();
    }
  }

  /* ── 2) Barra fija en piezas enteras ── */
  function setupStickyGuard() {
    var btn = document.querySelector('.cm-sticky-atc__btn[data-require-options="true"]');
    var variants = document.querySelector('.cm-pdp__variants');
    if (!btn || !variants) return;

    var chooseLabel = btn.getAttribute('data-choose-label') || btn.textContent.trim();
    var addLabel = btn.getAttribute('data-add-label') || '';
    var touched = false;

    function markTouched() {
      if (touched) return;
      touched = true;
      btn.removeAttribute('data-require-options');
      if (addLabel) btn.textContent = addLabel;
    }
    variants.addEventListener('click', function (e) {
      if (e.target.closest('.cm-pdp__opt, select')) markTouched();
    });
    variants.addEventListener('change', markTouched);

    /* main-product.js reescribe el texto del botón al cambiar de variante: mientras no se
       haya elegido nada, se mantiene el texto «Selecciona peso y formato». */
    new MutationObserver(function () {
      if (!touched && btn.textContent.trim() !== chooseLabel) btn.textContent = chooseLabel;
    }).observe(btn, { childList: true, characterData: true, subtree: true });
    btn.textContent = chooseLabel;

    /* Fase de captura: se ejecuta antes que el «añadir al carrito» de main-product.js. */
    document.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('.cm-sticky-atc__btn');
      if (!b || touched) return;
      e.preventDefault();
      e.stopImmediatePropagation();
      variants.scrollIntoView({ behavior: 'smooth', block: 'center' });
      variants.classList.remove('is-attn');
      void variants.offsetWidth;
      variants.classList.add('is-attn');
      setTimeout(function () { variants.classList.remove('is-attn'); }, 1600);
    }, true);
  }

  function init() {
    setupDescription();
    setupStickyGuard();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  if (mq.addEventListener) mq.addEventListener('change', setupDescription);
  else if (mq.addListener) mq.addListener(setupDescription);
})();
