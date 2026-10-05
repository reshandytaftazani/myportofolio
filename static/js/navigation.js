(() => {
    const nav = document.getElementById('nav-links');
    const burger = document.getElementById('burger-btn');
    const overlay = document.getElementById('nav-overlay');
    function closeMenu(restoreFocus = false) {
        const wasOpen = burger?.getAttribute('aria-expanded') === 'true';
        nav?.classList.remove('nav-active'); burger?.classList.remove('toggle');
        overlay?.classList.remove('active'); burger?.setAttribute('aria-expanded', 'false');
        if (restoreFocus && wasOpen) burger.focus();
    }
    burger?.setAttribute('aria-expanded', 'false');
    burger?.setAttribute('aria-controls', 'nav-links');
    burger?.addEventListener('click', () => {
        const expanded = !nav.classList.contains('nav-active');
        nav.classList.toggle('nav-active', expanded); burger.classList.toggle('toggle', expanded);
        overlay?.classList.toggle('active', expanded); burger.setAttribute('aria-expanded', String(expanded));
        if (expanded) nav.querySelector('a')?.focus();
    });
    overlay?.addEventListener('click', closeMenu);
    nav?.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
    document.querySelectorAll('.user-dropdown').forEach(menu => {
        const button = menu.querySelector('.user-btn');
        function close() { menu.classList.remove('open'); button.setAttribute('aria-expanded', 'false'); }
        button.addEventListener('click', () => {
            const open = button.getAttribute('aria-expanded') !== 'true';
            menu.classList.toggle('open', open); button.setAttribute('aria-expanded', String(open));
        });
        document.addEventListener('click', event => { if (!menu.contains(event.target)) close(); });
        menu.addEventListener('keydown', event => { if (event.key === 'Escape') { event.stopPropagation(); close(); button.focus(); } });
        menu.addEventListener('focusout', event => { if (!menu.contains(event.relatedTarget)) close(); });
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && burger?.getAttribute('aria-expanded') === 'true') {
            event.preventDefault(); closeMenu(true);
        }
    });
    document.body.setAttribute('data-navigation-ready', '');
})();
