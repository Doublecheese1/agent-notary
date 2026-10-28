(() => {
  const foundMenus = [...document.querySelectorAll('.language-menu')];
  const fallbackMenu = document.querySelector('.language-menu');
  const menus = foundMenus.length ? foundMenus : (fallbackMenu ? [fallbackMenu] : []);
  if (!menus.length) return;
  menus.forEach(menu => { menu.dataset.dismissBehavior = 'ready'; });

  const closeMenu = menu => menu.removeAttribute('open');
  const closeAll = except => menus.forEach(menu => {
    if (menu !== except) closeMenu(menu);
  });

  const closeFromOutside = event => {
    const path = typeof event.composedPath === 'function' ? event.composedPath() : [];
    menus.forEach(menu => {
      if (menu.open && !path.includes(menu) && !menu.contains(event.target)) closeMenu(menu);
    });
  };
  window.addEventListener('pointerdown', closeFromOutside, true);
  window.addEventListener('click', closeFromOutside, true);
  document.querySelectorAll('.hero-grid, main, footer').forEach(area => {
    area.addEventListener('click', () => closeAll(), true);
  });

  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const openMenu = menus.find(menu => menu.open);
    if (!openMenu) return;
    closeMenu(openMenu);
    openMenu.querySelector('summary')?.focus();
  });

  menus.forEach(menu => {
    menu.addEventListener('toggle', () => {
      if (menu.open) closeAll(menu);
    });
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    let closeTimer;
    menu.addEventListener('mouseenter', () => window.clearTimeout(closeTimer));
    menu.addEventListener('mouseleave', () => {
      closeTimer = window.setTimeout(() => closeMenu(menu), 120);
    });
  });
})();

