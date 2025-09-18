// static/js/scroll.js
document.addEventListener('DOMContentLoaded', () => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('opacity-100', 'translate-y-0');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.scroll-item').forEach(el => {
    el.classList.add(
      'opacity-0',       // invisible al inicio
      'translate-y-10',  // desplazado hacia abajo
      'transition-all', 
      'duration-700', 
      'ease-out'
    );
    observer.observe(el);
  });
});
