function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
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
