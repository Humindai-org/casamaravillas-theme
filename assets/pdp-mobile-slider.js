/*
  Ficha de producto en móvil: hero a sangre con carrusel y puntos.
  Borrador 2026-11-12 (análisis Clarity). Se construye con las miniaturas que ya
  renderiza main-product.liquid (una sola fuente de datos: data-image-src, ajuste
  de encaje/zoom/posición). En escritorio no hace nada. Con una sola foto se
  deja la imagen principal tal cual.
*/
(function () {
  'use strict';

  var mq = window.matchMedia('(max-width: 900px)');

  function el(tag, cls) {
    var n = document.createElement(tag);
    n.className = cls;
    return n;
  }

  /* Clave estable de una imagen de Shopify: nombre de archivo sin tamaño ni query. */
  function imgKey(url) {
    try {
      return String(url).split('?')[0].split('/').pop().replace(/_\d+x\d*(?=\.)/, '').toLowerCase();
    } catch (e) {
      return '';
    }
  }

  function build(gallery) {
    if (!gallery || gallery.querySelector('.cm-pdp__slider')) return;

    var mainImg = gallery.querySelector('.cm-pdp__main-img');
    var thumbsBox = gallery.querySelector('.cm-pdp__thumbnails');
    var thumbs = Array.prototype.slice.call(gallery.querySelectorAll('.cm-pdp__thumb-btn'));
    if (thumbs.length < 2) return;

    var slider = el('div', 'cm-pdp__slider');
    slider.setAttribute('role', 'group');
    slider.setAttribute('aria-roledescription', 'carousel');
    var label = thumbsBox && thumbsBox.getAttribute('aria-label');
    if (label) slider.setAttribute('aria-label', label);

    var track = el('div', 'cm-pdp__slides');
    track.tabIndex = 0;

    var dotsBox = el('div', 'cm-pdp__dots');
    dotsBox.setAttribute('aria-hidden', 'true');

    thumbs.forEach(function (btn, i) {
      var d = btn.dataset;
      var slide = el('div', 'cm-pdp__slide');
      slide.setAttribute('data-key', imgKey(d.imageSrc));
      slide.setAttribute('aria-roledescription', 'slide');
      slide.setAttribute('aria-label', (i + 1) + ' / ' + thumbs.length);
      /* Mismo ajuste por foto (encaje, zoom, posición) que en escritorio: la foto llena todo el espacio. */
      if (d.imgFit) slide.style.setProperty('--gal-fit', d.imgFit);
      if (d.imgZoom) slide.style.setProperty('--gal-zoom', parseFloat(d.imgZoom) / 100);
      if (d.imgPosX) slide.style.setProperty('--gal-pos-x', d.imgPosX + '%');
      if (d.imgPosY) slide.style.setProperty('--gal-pos-y', d.imgPosY + '%');

      var img = new Image();
      /* La primera foto reutiliza la URL de la imagen principal (ya en caché);
         el resto, a 1000 px: una foto de 2000 px es innecesaria en un móvil. */
      img.src = i === 0 ? d.imageSrc : String(d.imageSrc).replace(/width=\d+/, 'width=1000');
      img.alt = d.imageAlt || '';
      img.loading = i === 0 ? 'eager' : 'lazy';
      img.decoding = 'async';
      img.draggable = false;
      slide.appendChild(img);
      track.appendChild(slide);

      dotsBox.appendChild(el('span', 'cm-pdp__dot' + (i === 0 ? ' is-active' : '')));
    });

    slider.appendChild(track);
    slider.appendChild(dotsBox);
    gallery.insertBefore(slider, gallery.firstChild);
    gallery.classList.add('cm-has-slider');

    /* Punto activo según la foto visible. */
    var dots = Array.prototype.slice.call(dotsBox.children);
    function setActive(idx) {
      dots.forEach(function (dot, j) { dot.classList.toggle('is-active', j === idx); });
    }
    var slides = Array.prototype.slice.call(track.children);
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) setActive(slides.indexOf(e.target));
        });
      }, { root: track, threshold: 0.6 });
      slides.forEach(function (s) { io.observe(s); });
    } else {
      track.addEventListener('scroll', function () {
        setActive(Math.round(track.scrollLeft / Math.max(track.clientWidth, 1)));
      }, { passive: true });
    }

    /* Cambio de variante: main-product.js cambia el src de la imagen principal
       (oculta en móvil); el carrusel sigue esa foto. */
    if (mainImg && 'MutationObserver' in window) {
      new MutationObserver(function () {
        var k = imgKey(mainImg.getAttribute('src'));
        for (var j = 0; j < slides.length; j++) {
          if (slides[j].getAttribute('data-key') === k) {
            track.scrollTo({ left: j * track.clientWidth, behavior: 'smooth' });
            break;
          }
        }
      }).observe(mainImg, { attributes: true, attributeFilter: ['src'] });
    }
  }

  function init() {
    if (mq.matches) build(document.querySelector('.cm-pdp__gallery'));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  if (mq.addEventListener) mq.addEventListener('change', init);
  else if (mq.addListener) mq.addListener(init);
})();
