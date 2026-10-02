const toggle = document.querySelector('.menu-toggle');
toggle?.addEventListener('click', () => {
  const expanded = toggle.getAttribute('aria-expanded') === 'true';
  toggle.setAttribute('aria-expanded', String(!expanded));
  document.getElementById('navigation').classList.toggle('open', !expanded);
});
document.querySelectorAll('.print-button').forEach(button => button.addEventListener('click', () => window.print()));
document.querySelectorAll('.navigation a').forEach(link => {
  if (link.pathname === window.location.pathname) link.setAttribute('aria-current', 'page');
});
