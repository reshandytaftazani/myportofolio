(() => {
    const header = document.querySelector('.desktop-page .desktop-menubar');
    if (!header) return;
    const menu = header.querySelector('.desktop-window-menu');
    const workspace = document.querySelector('.desktop-workspace');
    const compact = matchMedia('(max-width: 1100px)');
    let frame = 0;

    // Desktop windows scroll internally; mobile windows use document scrolling.
    function updateSurface() {
        frame = 0;
        const content = workspace?.querySelector('[data-window-active] > .container');
        header.toggleAttribute('data-header-scrolled', window.scrollY > 16 || (content?.scrollTop || 0) > 16);
    }
    function scheduleSurface() {
        if (!frame) frame = requestAnimationFrame(updateSurface);
    }
    document.addEventListener('scroll', scheduleSurface, { capture: true, passive: true });
    if (workspace) new MutationObserver(scheduleSurface).observe(workspace, {
        subtree: true, attributes: true, attributeFilter: ['data-window-active', 'hidden']
    });

    function closeMenu(restoreFocus = false) {
        if (!menu?.open) return;
        menu.open = false;
        if (restoreFocus) menu.querySelector('summary').focus();
    }
    header.addEventListener('click', event => {
        if (event.target.closest('.desktop-menu-panel a, .desktop-menu-panel button')) closeMenu();
    });
    document.addEventListener('click', event => {
        if (!menu?.contains(event.target)) closeMenu();
    });
    menu?.addEventListener('keydown', event => {
        if (event.key === 'Escape' && menu.open) {
            event.preventDefault();
            event.stopPropagation();
            closeMenu(true);
        }
    });
    menu?.addEventListener('focusout', event => {
        if (!menu.contains(event.relatedTarget)) closeMenu();
    });
    compact.addEventListener('change', () => closeMenu(true));
    window.addEventListener('pageshow', scheduleSurface);
    window.addEventListener('pagehide', () => { cancelAnimationFrame(frame); frame = 0; });
    updateSurface();
})();
