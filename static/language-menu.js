(() => {
  const menu = document.querySelector('.language-menu');
  if (!menu) return;

  const closeMenu = () => menu.removeAttribute('open');

  const closeFromOutside = event => {
    const path = typeof event.composedPath === 'function' ? event.composedPath() : [];
    if (menu.open && !path.includes(menu) && !menu.contains(event.target)) closeMenu();
  };
  window.addEventListener('pointerdown', closeFromOutside, true);
  window.addEventListener('click', closeFromOutside, true);

  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !menu.open) return;
    closeMenu();
    menu.querySelector('summary')?.focus();
  });

  if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    let closeTimer;
    menu.addEventListener('mouseenter', () => window.clearTimeout(closeTimer));
    menu.addEventListener('mouseleave', () => {
      closeTimer = window.setTimeout(closeMenu, 120);
    });
  }
})();
