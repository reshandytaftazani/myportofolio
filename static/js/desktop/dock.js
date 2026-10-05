(() => {
    'use strict';
    const dock = document.querySelector('.desktop-page .desktop-dock');
    if (!dock) return;
    const links = [...dock.querySelectorAll('a')];
    const divider = dock.querySelector('.dock-divider');
    const compact = matchMedia('(max-width: 900px)');
    const motion = matchMedia('(min-width: 901px) and (hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)');
    const items = links.map(link => ({ link, center: 0, size: 48, value: 0, target: 0 }));
    let pointer = null, frame = 0, previousTime = 0;

    function measure() {
        const left = dock.getBoundingClientRect().left;
        items.forEach(item => {
            // Read layout positions, never the transformed hover position.
            item.center = left + item.link.offsetLeft + item.link.offsetWidth / 2;
            item.size = item.link.querySelector('.dock-icon').offsetWidth;
        });
    }
    function paint() {
        const growth = items.map(item => item.size * .46 * item.value);
        const total = growth.reduce((sum, value) => sum + value, 0);
        let prefix = 0;
        items.forEach((item, index) => {
            // The separator follows the same accumulated expansion as this boundary.
            if (item.link.previousElementSibling === divider) {
                divider.style.setProperty('--dock-shift', `${prefix - total / 2}px`);
            }
            const lift = 10 * item.value;
            item.link.style.setProperty('--dock-scale', String(1 + .46 * item.value));
            item.link.style.setProperty('--dock-lift', `${-lift}px`);
            item.link.style.setProperty('--dock-shift', `${prefix + growth[index] / 2 - total / 2}px`);
            item.link.style.setProperty('--dock-rise', `${growth[index] + lift}px`);
            prefix += growth[index];
        });
    }
    function tick(time) {
        // Time-based damping gives the same response on 60Hz and 120Hz displays.
        const elapsed = previousTime ? Math.min(time - previousTime, 64) : 16;
        previousTime = time;
        const blend = 1 - Math.exp(-elapsed / 65);
        let unsettled = false;
        items.forEach(item => {
            item.value += (item.target - item.value) * blend;
            if (Math.abs(item.target - item.value) < .001) item.value = item.target;
            else unsettled = true;
        });
        paint();
        if (unsettled) frame = requestAnimationFrame(tick);
        else {
            frame = 0;
            previousTime = 0;
            dock.removeAttribute('data-dock-animating');
        }
    }
    function aim() {
        if (!motion.matches || document.hidden) return;
        const focused = items.find(item => item.link.matches(':focus-visible'));
        const x = pointer ?? focused?.center;
        items.forEach(item => {
            const distance = x == null ? 1 : Math.min(Math.abs(x - item.center) / 120, 1);
            item.target = (1 + Math.cos(Math.PI * distance)) / 2;
        });
        if (!frame) {
            dock.setAttribute('data-dock-animating', '');
            frame = requestAnimationFrame(tick);
        }
    }
    function reset() {
        cancelAnimationFrame(frame);
        frame = 0;
        previousTime = 0;
        pointer = null;
        items.forEach(item => {
            item.value = item.target = 0;
            ['--dock-scale', '--dock-lift', '--dock-shift', '--dock-rise'].forEach(name => item.link.style.removeProperty(name));
        });
        dock.removeAttribute('data-dock-animating');
        divider?.style.removeProperty('--dock-shift');
    }
    function refresh() {
        reset();
        dock.toggleAttribute('data-dock-motion', motion.matches);
        measure();
    }
    dock.addEventListener('pointermove', event => {
        if (event.pointerType !== 'mouse') return;
        dock.removeAttribute('data-tooltip-dismissed');
        if (!motion.matches) return;
        pointer = event.clientX;
        aim();
    }, { passive: true });
    dock.addEventListener('pointerleave', () => { pointer = null; aim(); });
    dock.addEventListener('pointercancel', reset);
    dock.addEventListener('focusin', () => { dock.removeAttribute('data-tooltip-dismissed'); aim(); });
    dock.addEventListener('focusout', () => queueMicrotask(aim));
    document.addEventListener('keydown', event => {
        if (event.key === 'Tab') { pointer = null; aim(); }
        if (event.key !== 'Escape' || event.defaultPrevented || compact.matches || document.querySelector('dialog[open]') || dock.hasAttribute('data-tooltip-dismissed')) return;
        if (!dock.querySelector('a:hover, a:focus-visible')) return;
        dock.setAttribute('data-tooltip-dismissed', '');
        event.preventDefault();
        event.stopPropagation();
    }, { capture: true });
    motion.addEventListener('change', refresh);
    window.addEventListener('resize', refresh, { passive: true });
    window.addEventListener('blur', () => { reset(); dock.setAttribute('data-tooltip-dismissed', ''); });
    document.addEventListener('visibilitychange', reset);
    window.addEventListener('pagehide', reset);
    window.addEventListener('pageshow', refresh);
    refresh();
})();
