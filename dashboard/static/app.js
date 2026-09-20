// Shared utilities used across dashboard pages
const setActive = () => {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === path);
  });
};
document.addEventListener('DOMContentLoaded', setActive);
