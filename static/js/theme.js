(() => {
    const root = document.documentElement;
    // Reserve a valid mobile deep link before the home grid can paint.
    // CSS still exposes ordinary server content when JavaScript is unavailable.
    const sections = ['about', 'tech-stack', 'education', 'contact', 'projects', 'skills', 'experience'];
    const initialSection = location.pathname === '/' ? location.hash.slice(1) : location.pathname.split('/').filter(Boolean)[0];
    if (sections.includes(initialSection)) root.dataset.desktopStartWindow = initialSection;
    const system = matchMedia('(prefers-color-scheme: dark)');
    let preference;
    try { preference = localStorage.getItem('theme'); } catch (_) { /* Storage is optional. */ }
    const valid = value => value === 'dark' || value === 'light';
    function apply(value) { root.dataset.theme = value; }
    apply(valid(preference) ? preference : system.matches ? 'dark' : 'light');
    system.addEventListener('change', event => {
        if (!valid(preference)) apply(event.matches ? 'dark' : 'light');
    });
    document.addEventListener('DOMContentLoaded', () => {
        // Boot either owns visibility now or has failed: both release the hint.
        root.removeAttribute('data-desktop-start-window');
        const checkbox = document.getElementById('theme-toggle-checkbox');
        if (checkbox) checkbox.checked = root.dataset.theme === 'dark';
        function change(value) {
            preference = value; apply(value);
            if (checkbox) checkbox.checked = value === 'dark';
            try { localStorage.setItem('theme', value); } catch (_) { /* Keep session theme. */ }
        }
        checkbox?.addEventListener('change', () => change(checkbox.checked ? 'dark' : 'light'));
        document.querySelectorAll('[data-theme-toggle]').forEach(button => {
            button.addEventListener('click', () => change(root.dataset.theme === 'dark' ? 'light' : 'dark'));
        });
    });
})();
