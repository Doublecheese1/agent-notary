(() => {
  const menu = document.querySelector('.language-menu');
  if (!menu) return;

  const closeMenu = () => menu.removeAttribute('open');

  document.addEventListener('pointerdown', event => {
    if (menu.open && !menu.contains(event.target)) closeMenu();
  });

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
