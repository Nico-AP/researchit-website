// Fade-up on scroll (external file so the strict CSP needs no 'unsafe-inline').
// Loaded in <head> without `defer`: the class must be set before the first paint,
// or the content would flash visible and then disappear. Without JavaScript the
// class is never set and the content is shown (see base.scss).
(() => {
  if (!('IntersectionObserver' in window)) return;
  document.documentElement.classList.add('js-fade');

  document.addEventListener('DOMContentLoaded', () => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          observer.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });

    document.querySelectorAll('.fade-up').forEach((el) => observer.observe(el));
  });
})();
