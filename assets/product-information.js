function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    const track = modal.querySelector('[data-pack-carousel-track]');
    if (track) {
      requestAnimationFrame(function() { updatePackCarousel(track); });
    }
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
  }
}

function closeModalOnOverlay(event, modalId) {
  if (event.target.id === modalId) {
    closeModal(modalId);
  }
}

document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape') {
    const activeModals = document.querySelectorAll('.cm-modal.active');
    activeModals.forEach(modal => {
      modal.classList.remove('active');
    });
    document.body.style.overflow = 'auto';
  }
});

// `el.offsetLeft` es relativo al ancestro posicionado más cercano
// (offsetParent), que casi nunca es el propio carrusel con scroll — en los
// modales, por ejemplo, es .cm-modal__content (position: relative). Usarlo
// directo para calcular a dónde hacer scroll da un valor desplazado por el
// padding de ese ancestro, y las flechas terminan "atascadas" o saltando a
// un punto que no es el de la tarjeta. Esta función calcula la posición real
// del elemento dentro del sistema de coordenadas de scroll del propio track.
function offsetWithinTrack(track, el) {
  return el.getBoundingClientRect().left - track.getBoundingClientRect().left + track.scrollLeft;
}

// Carrusel de las 3 tarjetas (Nutrición / Alérgenos / Conservación) — no está
// dentro de un modal, así que no hace falta fase de captura aquí.
function updateInfoCardsArrows(track) {
  const wrap = track.closest('.cm-info-cards-wrap');
  if (!wrap) return;
  const prevBtn = wrap.querySelector('[data-info-cards-prev]');
  const nextBtn = wrap.querySelector('[data-info-cards-next]');
  // Igual que en updatePackCarousel: nunca usar `disabled` (bloquea clicks
  // nativamente) ni tocar el estado si el track aún no tiene layout.
  if (track.clientWidth === 0) return;
  const maxScroll = track.scrollWidth - track.clientWidth;
  if (prevBtn) prevBtn.classList.toggle('is-edge', track.scrollLeft <= 4);
  if (nextBtn) nextBtn.classList.toggle('is-edge', track.scrollLeft >= maxScroll - 4);
}

document.addEventListener('click', function(e) {
  const btn = e.target.closest('[data-info-cards-prev], [data-info-cards-next]');
  if (!btn) return;
  const wrap = btn.closest('.cm-info-cards-wrap');
  const track = wrap && wrap.querySelector('[data-info-cards-track]');
  const cards = track && track.querySelectorAll('.cm-info-card');
  if (!track || !cards || !cards.length) return;

  const current = track.scrollLeft;
  let target = null;
  if (btn.hasAttribute('data-info-cards-prev')) {
    for (let i = cards.length - 1; i >= 0; i--) {
      const pos = offsetWithinTrack(track, cards[i]);
      if (pos < current - 4) { target = pos; break; }
    }
    if (target === null) target = offsetWithinTrack(track, cards[0]);
  } else {
    for (let j = 0; j < cards.length; j++) {
      const pos = offsetWithinTrack(track, cards[j]);
      if (pos > current + 4) { target = pos; break; }
    }
    if (target === null) target = offsetWithinTrack(track, cards[cards.length - 1]);
  }
  track.scrollTo({ left: target, behavior: 'smooth' });
});

document.querySelectorAll('[data-info-cards-track]').forEach(function(track) {
  updateInfoCardsArrows(track);
  track.addEventListener('scroll', function() { updateInfoCardsArrows(track); }, { passive: true });
});
window.addEventListener('resize', function() {
  document.querySelectorAll('[data-info-cards-track]').forEach(updateInfoCardsArrows);
});

// Carrusel de componentes de pack (dentro del modal "Alérgenos e Ingredientes")
function updatePackCarousel(track) {
  const cards = track.querySelectorAll('[data-pack-carousel-card]');
  if (!cards.length) return;

  let current = 0;
  cards.forEach(function(card, i) {
    if (offsetWithinTrack(track, card) <= track.scrollLeft + 4) current = i;
  });

  // Título dinámico arriba del modal: qué producto del pack se está viendo
  const modal = track.closest('.cm-modal');
  const headerCurrent = modal && modal.querySelector('[data-pack-carousel-current]');
  if (headerCurrent) {
    const nameEl = cards[current].querySelector('.cm-pack-carousel__name');
    headerCurrent.textContent = nameEl ? nameEl.textContent : '';
  }

  const nav = track.parentElement.querySelector('.cm-pack-carousel__nav');
  if (!nav) return;

  const prevBtn = nav.querySelector('[data-pack-carousel-prev]');
  const nextBtn = nav.querySelector('[data-pack-carousel-next]');
  const counter = nav.querySelector('[data-pack-carousel-counter]');
  if (counter) counter.textContent = (current + 1) + ' / ' + cards.length;

  // Si el modal todavía no terminó su layout (clientWidth 0), no tocamos el
  // estado visual de las flechas: usar el atributo `disabled` aquí bloquearía
  // los clicks nativamente y, si esta medición sale mal justo al abrir el
  // modal, la flecha se quedaría "atascada" sin poder recuperarse.
  if (track.clientWidth === 0) return;
  const maxScroll = track.scrollWidth - track.clientWidth;
  if (prevBtn) prevBtn.classList.toggle('is-edge', track.scrollLeft <= 4);
  if (nextBtn) nextBtn.classList.toggle('is-edge', track.scrollLeft >= maxScroll - 4);
}

function scrollPackCarouselTo(track, cardOffsetLeft) {
  track.scrollTo({ left: cardOffsetLeft, behavior: 'smooth' });
}

// NOTA: se registra en fase de captura (tercer argumento `true`) porque
// .cm-modal__content hace event.stopPropagation() en la fase de burbuja
// (para que un click dentro del modal no lo cierre) — eso impediría que
// un listener delegado normal en `document` llegue a recibir el click.
document.addEventListener('click', function(e) {
  const btn = e.target.closest('.cm-pack-carousel__arrow');
  if (!btn) return;
  const nav = btn.closest('.cm-pack-carousel__nav');
  const section = nav && nav.closest('.cm-modal__section');
  const track = section && section.querySelector('[data-pack-carousel-track]');
  const cards = track && track.querySelectorAll('[data-pack-carousel-card]');
  if (!track || !cards || !cards.length) return;

  const current = track.scrollLeft;
  let target = null;
  if (btn.hasAttribute('data-pack-carousel-prev')) {
    for (let i = cards.length - 1; i >= 0; i--) {
      const pos = offsetWithinTrack(track, cards[i]);
      if (pos < current - 4) { target = pos; break; }
    }
    if (target === null) target = offsetWithinTrack(track, cards[0]);
  } else {
    for (let j = 0; j < cards.length; j++) {
      const pos = offsetWithinTrack(track, cards[j]);
      if (pos > current + 4) { target = pos; break; }
    }
    if (target === null) target = offsetWithinTrack(track, cards[cards.length - 1]);
  }
  scrollPackCarouselTo(track, target);
}, true);

document.querySelectorAll('[data-pack-carousel-track]').forEach(function(track) {
  track.addEventListener('scroll', function() { updatePackCarousel(track); }, { passive: true });
});
window.addEventListener('resize', function() {
  document.querySelectorAll('[data-pack-carousel-track]').forEach(updatePackCarousel);
});

// Buscador de componentes dentro del carrusel de packs
function normalizePackSearch(str) {
  return (str || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

document.addEventListener('input', function(e) {
  const input = e.target.closest('[data-pack-carousel-search]');
  if (!input) return;

  const wrap = input.closest('.cm-pack-carousel__search');
  const resultsList = wrap && wrap.querySelector('[data-pack-carousel-search-results]');
  const section = input.closest('.cm-modal__section');
  const track = section && section.querySelector('[data-pack-carousel-track]');
  if (!resultsList || !track) return;

  const query = normalizePackSearch(input.value);
  resultsList.innerHTML = '';

  if (!query) {
    resultsList.hidden = true;
    return;
  }

  const matches = [];
  track.querySelectorAll('[data-pack-carousel-card]').forEach(function(card) {
    const nameEl = card.querySelector('.cm-pack-carousel__name');
    const name = nameEl ? nameEl.textContent : '';
    if (normalizePackSearch(name).indexOf(query) !== -1) {
      matches.push({ card: card, name: name });
    }
  });

  if (!matches.length) {
    const li = document.createElement('li');
    li.className = 'cm-pack-carousel__search-empty';
    li.textContent = 'Sin resultados';
    resultsList.appendChild(li);
  } else {
    matches.forEach(function(match) {
      const li = document.createElement('li');
      li.className = 'cm-pack-carousel__search-result';
      li.textContent = match.name;
      li.tabIndex = 0;
      li.addEventListener('click', function() {
        scrollPackCarouselTo(track, offsetWithinTrack(track, match.card));
        resultsList.hidden = true;
        input.value = match.name;
      });
      resultsList.appendChild(li);
    });
  }

  resultsList.hidden = false;
});

document.addEventListener('keydown', function(e) {
  const input = e.target.closest('[data-pack-carousel-search]');
  if (!input || e.key !== 'Enter') return;
  e.preventDefault();
  const wrap = input.closest('.cm-pack-carousel__search');
  const firstResult = wrap && wrap.querySelector('.cm-pack-carousel__search-result');
  if (firstResult) firstResult.click();
});

// Fase de captura por el mismo motivo que el listener de las flechas (ver nota arriba).
document.addEventListener('click', function(e) {
  if (e.target.closest('.cm-pack-carousel__search')) return;
  document.querySelectorAll('[data-pack-carousel-search-results]').forEach(function(list) {
    list.hidden = true;
  });
}, true);

// Subtle parallax effect on scroll — desktop only
document.addEventListener('scroll', function() {
  if (window.innerWidth <= 768) return;
  const imageContainer = document.querySelector('.cm-info-image-container');
  if (imageContainer) {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const elementTop = imageContainer.offsetTop;
    const elementDistance = elementTop - scrollTop;

    if (elementDistance < window.innerHeight && elementDistance > -imageContainer.offsetHeight) {
      const parallaxValue = (scrollTop - elementTop) * 0.3;
      imageContainer.style.transform = 'translateY(' + parallaxValue + 'px)';
    }
  }
});

// Reset parallax transform on mobile resize
window.addEventListener('resize', function() {
  if (window.innerWidth <= 768) {
    const imageContainer = document.querySelector('.cm-info-image-container');
    if (imageContainer) imageContainer.style.transform = '';
  }
});

// Fade in sections on scroll
const observerOptions = {
  threshold: 0.1,
  rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, observerOptions);

document.querySelectorAll('.cm-info-card').forEach(card => {
  card.style.opacity = '0';
  card.style.transform = 'translateY(10px)';
  card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
  observer.observe(card);
});
