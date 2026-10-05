(() => {
    window.initDesktopIcons = () => {
        const grid = document.querySelector('[data-icon-grid]');
        if (!grid) return;
        const nodes = [...grid.querySelectorAll('[data-icon-id]')];
        const storageKey = 'desk:icon-pos:v1';
        const desktop = matchMedia('(min-width: 901px) and (pointer: fine)');
        const defaults = () => Object.fromEntries(nodes.map((node, index) => [node.dataset.iconId, { col: index % 2 + 1, row: Math.floor(index / 2) + 1 }]));
        let positions = defaults(), drag, suppressClick = false;
        const valid = cell => cell && Number.isInteger(cell.col) && Number.isInteger(cell.row) && cell.col >= 1 && cell.col <= 2 && cell.row >= 1 && cell.row <= 5;
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey));
            const occupied = new Set();
            if (saved?.version === 1 && nodes.every(node => {
                const cell = saved.positions?.[node.dataset.iconId], key = cell && `${cell.col}:${cell.row}`;
                if (!valid(cell) || occupied.has(key)) return false;
                occupied.add(key); return true;
            })) positions = saved.positions;
        } catch (_) { /* Invalid or blocked storage uses the default grid. */ }
        function apply() {
            nodes.forEach(node => {
                const cell = positions[node.dataset.iconId];
                node.style.gridColumn = desktop.matches ? String(cell.col) : '';
                node.style.gridRow = desktop.matches ? String(cell.row) : '';
            });
        }
        function save() { try { localStorage.setItem(storageKey, JSON.stringify({ version: 1, positions })); } catch (_) { /* Optional persistence. */ } }
        function occupied(cell, id) { return nodes.find(node => node.dataset.iconId !== id && positions[node.dataset.iconId].col === cell.col && positions[node.dataset.iconId].row === cell.row); }
        function say(message) { const region = document.querySelector('[data-window-announcement]'); if (region) region.textContent = message; }
        function finish(cancel = false) {
            if (!drag) return;
            cancelAnimationFrame(drag.frame);
            if (drag.moved && !cancel && valid(drag.cell) && !occupied(drag.cell, drag.node.dataset.iconId)) {
                positions[drag.node.dataset.iconId] = drag.cell; save();
            }
            suppressClick = drag.moved;
            drag.node.style.transform = ''; drag.node.classList.remove('icon-dragging'); drag.ghost?.remove();
            if (drag.node.hasPointerCapture(drag.pointer)) drag.node.releasePointerCapture(drag.pointer);
            drag = undefined; apply();
            setTimeout(() => { suppressClick = false; }, 0);
        }
        grid.addEventListener('click', event => { if (suppressClick) { event.preventDefault(); event.stopPropagation(); } }, true);
        nodes.forEach(node => {
            node.addEventListener('pointerdown', event => {
                if (!desktop.matches || event.button !== 0 || document.querySelector('dialog[open]')) return;
                drag = { node, pointer: event.pointerId, x: event.clientX, y: event.clientY, moved: false };
            });
            node.addEventListener('pointermove', event => {
                if (!drag || drag.node !== node || drag.pointer !== event.pointerId) return;
                const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
                if (!drag.moved && Math.hypot(dx, dy) < 7) return;
                drag.moved = true; node.classList.add('icon-dragging');
                if (!node.hasPointerCapture(event.pointerId)) node.setPointerCapture(event.pointerId);
                if (!drag.ghost) { drag.ghost = document.createElement('li'); drag.ghost.className = 'icon-ghost'; drag.ghost.setAttribute('aria-hidden', 'true'); grid.append(drag.ghost); }
                const rect = grid.getBoundingClientRect();
                const col = Math.floor((event.clientX - rect.left) / 108) + 1;
                const row = Math.floor((event.clientY - rect.top) / 108) + 1;
                drag.cell = { col, row };
                drag.ghost.hidden = !valid(drag.cell) || Boolean(occupied(drag.cell, node.dataset.iconId));
                drag.ghost.style.setProperty('--ghost-col', String(col)); drag.ghost.style.setProperty('--ghost-row', String(row));
                drag.dx = dx; drag.dy = dy;
                if (!drag.frame) drag.frame = requestAnimationFrame(() => {
                    if (!drag) return;
                    node.style.transform = `translate(${drag.dx}px, ${drag.dy}px)`; drag.frame = undefined;
                });
            });
            node.addEventListener('pointerup', () => finish()); node.addEventListener('pointercancel', () => finish(true));
            node.addEventListener('lostpointercapture', () => { if (drag) finish(true); });
            node.addEventListener('dragstart', event => event.preventDefault());
            node.querySelector('a').addEventListener('keydown', event => {
                const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
                if (!delta || !desktop.matches) return;
                event.preventDefault();
                const cell = positions[node.dataset.iconId], next = { col: cell.col + delta[0], row: cell.row + delta[1] };
                if (!valid(next)) return;
                const other = occupied(next, node.dataset.iconId);
                if (event.altKey) {
                    if (other) positions[other.dataset.iconId] = cell;
                    positions[node.dataset.iconId] = next; apply(); save(); say(`${node.textContent.trim()} dipindahkan`);
                } else other?.querySelector('a').focus();
            });
        });
        document.querySelector('[data-reset-icons]')?.addEventListener('click', () => { finish(true); positions = defaults(); apply(); save(); say('Susunan ikon dirapikan'); });
        desktop.addEventListener('change', () => { finish(true); apply(); });
        apply();
    };
})();
