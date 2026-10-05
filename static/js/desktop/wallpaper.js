(() => {
    const svg = document.querySelector('[data-desktop-wallpaper]');
    if (!svg) return;
    const paths = [...svg.querySelectorAll('path')];
    const originals = paths.map(path => path.getAttribute('d'));
    const motion = matchMedia('(prefers-reduced-motion: reduce)');
    const pointer = matchMedia('(min-width: 901px) and (hover: hover) and (pointer: fine)');
    const body = document.body;
    // Sample the same three cubic curves as the server-rendered wallpaper.
    // The field bends locally under the pointer; the page and content stay still.
    const curves = paths.map((_, i) => {
        const a = i * 18, b = i * 16;
        const segments = [
            [[-180, 620 + a], [140, 300 + a], [250, 900 + b], [720, 780 + b]],
            [[720, 780 + b], [1190, 660 + b], [1080, 540 + b], [1160, 280 + b]],
            [[1160, 280 + b], [1240, 20 + b], [1440, b], [1600, 120 + b]],
        ];
        return segments.flatMap((points, index) => Array.from({ length: 25 }, (_, step) => {
            if (index && step === 0) return null;
            const t = step / 24, u = 1 - t;
            return [0, 1].map(axis => u ** 3 * points[0][axis]
                + 3 * u ** 2 * t * points[1][axis]
                + 3 * u * t ** 2 * points[2][axis] + t ** 3 * points[3][axis]);
        }).filter(Boolean));
    });
    let frame = 0, lastTime = 0, strength = 0, targetStrength = 0;
    let x = 720, y = 450, targetX = x, targetY = y, scale = 1;
    let blocked = Boolean(document.querySelector('[data-window-active]'));
    const allowed = () => pointer.matches && !motion.matches && !document.hidden && !blocked;

    function restore() {
        cancelAnimationFrame(frame);
        frame = 0; lastTime = 0; strength = 0; targetStrength = 0;
        paths.forEach((path, i) => path.setAttribute('d', originals[i]));
    }
    function draw(time) {
        frame = 0;
        if (!allowed()) { restore(); return; }
        const dt = lastTime ? Math.min(time - lastTime, 40) : 16;
        lastTime = time;
        // Time-based damping gives the same settling time on different refresh rates.
        const ease = 1 - Math.exp(-dt / 85);
        x += (targetX - x) * ease; y += (targetY - y) * ease;
        strength += (targetStrength - strength) * ease;
        if (!targetStrength && strength < .002) { restore(); return; }
        const radius = 190 / scale, amplitude = 13 / scale * strength;
        paths.forEach((path, i) => {
            path.setAttribute('d', curves[i].map(([px, py], index) => {
                const dx = px - x, dy = py - y, distance = Math.hypot(dx, dy);
                const bend = amplitude * Math.exp(-(distance ** 2) / (radius ** 2));
                const divisor = Math.max(distance, 30 / scale);
                return `${index ? 'L' : 'M'}${(px + dx / divisor * bend).toFixed(2)} ${(py + dy / divisor * bend).toFixed(2)}`;
            }).join(' '));
        });
        const settling = Math.abs(targetX - x) + Math.abs(targetY - y) > .1
            || Math.abs(targetStrength - strength) > .002;
        if (settling) frame = requestAnimationFrame(draw);
        else {
            lastTime = 0;
            if (!targetStrength) restore();
        }
    }
    function schedule() { if (!frame && allowed()) frame = requestAnimationFrame(draw); }
    function release() { targetStrength = 0; schedule(); }
    document.addEventListener('pointermove', event => {
        if (!allowed() || event.pointerType !== 'mouse') return;
        if (event.buttons || event.target.closest('a, button, input, textarea, select, summary, dialog, [data-window-id]')) {
            release(); return;
        }
        const matrix = svg.getScreenCTM();
        if (!matrix) return;
        const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
        scale = Math.hypot(matrix.a, matrix.b) || 1;
        targetX = point.x; targetY = point.y;
        if (!strength) { x = targetX; y = targetY; }
        targetStrength = 1;
        schedule();
    }, { passive: true });
    document.documentElement.addEventListener('pointerleave', release);
    document.addEventListener('pointerdown', release, { passive: true });
    document.addEventListener('pointercancel', restore, { passive: true });
    window.addEventListener('blur', restore);
    window.addEventListener('resize', restore, { passive: true });
    document.addEventListener('visibilitychange', restore);
    motion.addEventListener('change', restore);
    pointer.addEventListener('change', restore);
    new MutationObserver(() => {
        blocked = Boolean(document.querySelector('[data-window-active]'));
        if (blocked) restore();
    }).observe(body, { subtree: true, attributes: true, attributeFilter: ['data-window-active'] });
})();
