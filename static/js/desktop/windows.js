(() => {
    'use strict';
    const mobile = matchMedia('(max-width: 900px)');
    const medium = matchMedia('(max-width: 1199px)');
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    const records = new Map();
    let stack = [], closedInitial = false, drag, opening = false, enabled = false;
    const modalKeyEvents = new WeakSet();
    const modalOpen = () => Boolean(document.querySelector('dialog[open]'));
    const announcement = message => {
        const region = document.querySelector('[data-window-announcement]');
        if (region) region.textContent = message;
    };
    function activeUrl(record) {
        return record.url.pathname + record.url.search + record.url.hash;
    }
    function appId(url) {
        if (url.origin !== location.origin) return;
        if (url.pathname === '/' && records.has(url.hash.slice(1))) return url.hash.slice(1);
        return [...records.values()].find(record => record.url.pathname !== '/' && record.url.pathname === url.pathname)?.id;
    }
    function rememberScroll(record) {
        if (!record) return;
        if (mobile.matches) record.mobileScroll = scrollY;
        else record.desktopScroll = record.element.querySelector(':scope > .container')?.scrollTop || 0;
    }
    function restoreScroll(record) {
        requestAnimationFrame(() => {
            if (stack.at(-1) !== record.id) return;
            if (mobile.matches) window.scrollTo({ top: record.mobileScroll || 0, behavior: 'instant' });
            else {
                const content = record.element.querySelector(':scope > .container');
                if (content) content.scrollTop = record.desktopScroll || 0;
            }
        });
    }
    function originRect(trigger) {
        const element = trigger?.querySelector('svg') || trigger;
        const rect = element?.getBoundingClientRect();
        if (!rect || !rect.width || !rect.height || rect.bottom < 0 || rect.top > innerHeight) return;
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, width: rect.width, height: rect.height };
    }
    function folder(record) {
        return document.querySelector(`.desktop-icon[data-app-id="${record.id}"]`);
    }
    function stopMotion(record, preserve = false) {
        let current;
        if (preserve && record.motion) {
            const style = getComputedStyle(record.element);
            current = { transform: style.transform, opacity: style.opacity, borderRadius: style.borderRadius };
        }
        if (record.motion) { record.motion.onfinish = null; record.motion.cancel(); }
        record.motion = undefined; record.finishMotion = undefined; record.exiting = false;
        record.element.removeAttribute('data-window-motion');
        return current;
    }
    function restingFrame(record) {
        return { transform: 'none', opacity: 1, borderRadius: getComputedStyle(record.element).borderRadius };
    }
    function foldedFrame(record, source) {
        if (mobile.matches || !source) return { transform: 'translateY(16px) scale(.98)', opacity: 0, borderRadius: '16px' };
        const rect = record.element.getBoundingClientRect();
        const scale = Math.max(.06, Math.min(.18, source.width / rect.width));
        const x = source.x - rect.left - rect.width / 2;
        const y = source.y - rect.top - rect.height / 2;
        return { transform: `translate(${x}px, ${y}px) scale(${scale})`, opacity: 0, borderRadius: '16px' };
    }
    function animate(record, frames, exiting, done = () => {}, duration) {
        if (reducedMotion.matches || !record.element.animate) { done(); return; }
        record.exiting = exiting;
        record.element.dataset.windowMotion = exiting ? 'closing' : 'opening';
        const animation = record.element.animate(frames, {
            duration: duration ?? (exiting ? (mobile.matches ? 160 : 230) : (mobile.matches ? 280 : 420)),
            easing: exiting ? 'cubic-bezier(.4, 0, .7, .2)' : 'cubic-bezier(.16, 1, .3, 1)',
            fill: 'both',
        });
        record.motion = animation;
        record.finishMotion = () => {
            if (record.motion !== animation) return;
            stopMotion(record); done();
        };
        animation.onfinish = record.finishMotion;
    }
    function update() {
        if (!enabled) return;
        stack = stack.filter(id => records.get(id)?.status === 'open');
        records.forEach(record => {
            record.element.hidden = record.status !== 'open' && !record.exiting;
            record.element.inert = record.status !== 'open';
            if (!record.exiting) {
                record.element.toggleAttribute('data-window-active', stack.at(-1) === record.id);
                record.element.style.setProperty('--win-z', String(100 + Math.max(0, stack.indexOf(record.id))));
            }
            record.element.toggleAttribute('data-maximized', record.maximized || (!mobile.matches && medium.matches));
            if (record.snap) record.element.dataset.windowSnap = record.snap;
            else delete record.element.dataset.windowSnap;
            const maximize = record.element.querySelector('[data-window-action="maximize"]');
            const isMaximized = record.element.hasAttribute('data-maximized');
            maximize?.setAttribute('aria-pressed', String(isMaximized));
            maximize?.setAttribute('aria-label', `${isMaximized ? 'Pulihkan' : 'Perbesar'} ${record.title}`);
            document.querySelectorAll(`[data-dock-id="${record.id}"]`).forEach(link => {
                link.toggleAttribute('data-running', record.status !== 'closed');
                link.dataset.windowState = record.status;
                if (record.status !== 'closed') link.setAttribute('aria-description', stack.at(-1) === record.id ? 'Jendela aktif' : record.status === 'minimized' ? 'Jendela diminimalkan' : 'Jendela terbuka');
                else link.removeAttribute('aria-description');
                if (stack.at(-1) === record.id) link.setAttribute('aria-current', 'location');
                else link.removeAttribute('aria-current');
            });
        });
        document.body.toggleAttribute('data-mobile-window', mobile.matches && (stack.length > 0 || [...records.values()].some(record => record.exiting)));
        document.body.classList.toggle('desktop-document', stack.length > 0);
    }
    function focus(record, title = false) {
        stack = stack.filter(id => id !== record.id); stack.push(record.id); update();
        if (title) record.element.querySelector('.window-titlebar h2')?.focus({ preventScroll: true });
    }
    function focusFromInteraction(record) {
        focus(record);
        if (!opening && location.href !== new URL(activeUrl(record), location.origin).href) {
            history.replaceState({ desktop: 1, active: record.id }, '', activeUrl(record));
        }
    }
    function open(id, trigger, historyMode = 'push') {
        if (!enabled || modalOpen()) return false;
        const record = records.get(id);
        if (!record) return false;
        if (!mobile.matches && record.status !== 'open' && stack.length >= 5) {
            if (historyMode !== 'none') { announcement('Tutup atau minimalkan satu jendela terlebih dahulu.'); return false; }
            // Back/Forward must reach its destination even when the desktop is full.
            const oldest = records.get(stack[0]);
            rememberScroll(oldest); stopMotion(oldest); oldest.status = 'minimized'; update();
        }
        finishDrag(true);
        const entering = record.status !== 'open';
        const source = originRect(trigger) || record.source || originRect(folder(record));
        const interrupted = entering ? stopMotion(record, true) : undefined;
        if (mobile.matches && stack.at(-1) !== id) rememberScroll(records.get(stack.at(-1)));
        if (mobile.matches) records.forEach(other => {
            if (other !== record && (other.status === 'open' || other.exiting)) { stopMotion(other); other.status = 'minimized'; }
        });
        record.status = 'open'; record.trigger = trigger || record.trigger;
        if (source) record.source = source;
        opening = true; focus(record, true); opening = false;
        if (entering) clamp(record);
        // Direct mobile links reserve their layout before boot; keep that first paint steady.
        if (entering && !(mobile.matches && !trigger && document.readyState !== 'complete')) {
            animate(record, [interrupted || foldedFrame(record, source), restingFrame(record)], false);
        }
        if (entering) restoreScroll(record);
        if (historyMode !== 'none' && location.href !== new URL(activeUrl(record), location.origin).href) {
            history[historyMode === 'push' ? 'pushState' : 'replaceState']({ desktop: 1, active: id }, '', activeUrl(record));
        }
        announcement(`Jendela ${record.title} dibuka`);
        record.element.dispatchEvent(new CustomEvent('desktop:open'));
        return true;
    }
    function dirty(record) {
        return [...record.element.querySelectorAll('form')].some(form => form.dataset.dirty === 'true');
    }
    function busy(record) {
        return Boolean(record.element.querySelector('form [type="submit"]:disabled'));
    }
    function canClose(record) {
        if (busy(record)) { announcement('Tunggu hingga formulir selesai disimpan.'); return false; }
        return !dirty(record) || confirm('Ada perubahan yang belum disimpan. Tutup jendela dan buang perubahan?');
    }
    function hide(record, status, changeUrl = true, checked = false) {
        if (modalOpen() || record.status !== 'open' || (status === 'closed' && !checked && !canClose(record))) return;
        finishDrag(true); rememberScroll(record);
        // A media-query change can precede the browser's resize notification.
        // Closing a mobile section must not reveal a previous desktop window.
        if (mobile.matches) records.forEach(other => {
            if (other !== record && other.status === 'open') { stopMotion(other); other.status = 'minimized'; }
        });
        if (status === 'closed') {
            record.element.querySelectorAll('form[data-dirty="true"]').forEach(form => { form.reset(); delete form.dataset.dirty; });
        }
        const target = status === 'minimized' ? document.querySelector(`[data-dock-id="${record.id}"]`) : record.trigger || folder(record);
        const source = originRect(target) || originRect(folder(record)) || record.source;
        const current = stopMotion(record, true) || restingFrame(record);
        const folded = foldedFrame(record, source);
        record.status = status; closedInitial = true;
        // Keep the same DOM visible during exit, but take it out of interaction immediately.
        record.exiting = !reducedMotion.matches && Boolean(record.element.animate);
        update();
        const returnFocus = () => (target?.isConnected && target.getClientRects().length ? target : document.querySelector('.desktop-brand'))?.focus({ preventScroll: true });
        const next = records.get(stack.at(-1));
        if (next) { opening = true; focus(next, true); opening = false; }
        else returnFocus();
        if (changeUrl) {
            const active = records.get(stack.at(-1));
            history.replaceState({ desktop: 1, active: active?.id || null }, '', active ? activeUrl(active) : '/');
        }
        animate(record, [current, folded], true, () => {
            update();
            // Do not steal focus if another window was opened during this exit.
            if (!stack.length) returnFocus();
        });
    }
    function reconcile() {
        if (modalOpen()) return;
        const url = new URL(location.href), id = appId(url);
        if (id) {
            const record = records.get(id);
            if (id === 'projects' && record.url.search !== url.search) {
                record.url.search = url.search;
                record.element.dispatchEvent(new CustomEvent('desktop:query', { detail: url.search }));
            }
            open(id, undefined, 'none');
        } else {
            rememberScroll(records.get(stack.at(-1)));
            records.forEach(record => { stopMotion(record); if (record.status === 'open') record.status = 'minimized'; });
            const initial = document.querySelector('[data-initial-window]')?.dataset.initialWindow || 'about';
            if (!closedInitial && !history.state?.desktop && initial !== 'about') open(initial, undefined, 'none');
            else update();
        }
    }
    function clamp(record) {
        if (mobile.matches || medium.matches || record.maximized || record.snap) return;
        const workspace = document.querySelector('.desktop-workspace');
        const width = workspace.clientWidth;
        const rect = record.element.getBoundingClientRect();
        const left = Math.max(8, Math.min(parseFloat(record.element.style.getPropertyValue('--win-left')) || width * .24, width - Math.min(rect.width || 720, width - 16) - 8));
        const top = Math.max(62, Math.min(parseFloat(record.element.style.getPropertyValue('--win-top')) || 86, Math.max(62, innerHeight - workspace.getBoundingClientRect().top - 100 - (rect.height || 220))));
        record.element.style.setProperty('--win-left', left + 'px');
        record.element.style.setProperty('--win-top', top + 'px');
    }
    function showPreview(snap) {
        const preview = document.querySelector('.window-snap-preview');
        if (!preview) return;
        preview.hidden = !snap;
        if (snap) preview.dataset.snap = snap;
        else delete preview.dataset.snap;
    }
    function place(record, snap, maximized = false, before) {
        stopMotion(record);
        before ||= record.element.getBoundingClientRect();
        record.snap = snap; record.maximized = maximized;
        update(); clamp(record);
        if (mobile.matches) return;
        const after = record.element.getBoundingClientRect();
        animate(record, [{ transform: `translate(${before.left - after.left + (before.width - after.width) / 2}px, ${before.top - after.top + (before.height - after.height) / 2}px) scale(${before.width / after.width}, ${before.height / after.height})`, opacity: 1 }, restingFrame(record)], false, () => {}, 300);
    }
    function finishDrag(cancel = false) {
        if (!drag) return;
        const finished = drag; drag = undefined;
        cancelAnimationFrame(finished.frame);
        const { record, handle, pointer } = finished;
        const before = record.element.getBoundingClientRect();
        if (!cancel) {
            record.element.style.setProperty('--win-left', (finished.left + finished.dx) + 'px');
            record.element.style.setProperty('--win-top', (finished.top + finished.dy) + 'px');
        }
        record.element.style.transform = '';
        record.element.removeAttribute('data-window-dragging');
        showPreview();
        if (handle.hasPointerCapture(pointer)) handle.releasePointerCapture(pointer);
        if (!cancel && finished.snap) {
            place(record, finished.snap === 'full' ? undefined : finished.snap, finished.snap === 'full', before);
            announcement(`${record.title}: ${finished.snap === 'full' ? 'layar penuh' : finished.snap === 'left' ? 'sisi kiri' : 'sisi kanan'}`);
        } else clamp(record);
    }
    function init() {
        const nodes = [...document.querySelectorAll('[data-window-id]')];
        if (!nodes.length) return false;
        nodes.forEach((element, index) => {
            const id = element.dataset.windowId;
            if (records.has(id)) throw new Error('Duplicate desktop window: ' + id);
            const title = element.querySelector('.window-titlebar h2').textContent;
            const record = { id, title, element, status: 'closed', maximized: false, trigger: undefined };
            record.url = new URL(document.querySelector(`.desktop-icon[data-app-id="${id}"]`).href);
            if (id === 'projects' && location.pathname === record.url.pathname) record.url.search = location.search;
            records.set(id, record);
            element.setAttribute('role', 'region');
            element.style.setProperty('--win-top', (86 + index * 18) + 'px');
            element.style.setProperty('--win-left', (document.querySelector('.desktop-workspace').clientWidth * .24 + index * 24) + 'px');
            element.addEventListener('pointerdown', event => {
                if (!enabled || modalOpen() || record.status !== 'open' || drag) return;
                focusFromInteraction(record);
                const handle = event.target.closest('[data-window-handle]');
                if (!handle || event.target.closest('button,a,input,select,textarea') || mobile.matches || medium.matches || event.button !== 0 || !event.isPrimary) return;
                stopMotion(record);
                const workspace = document.querySelector('.desktop-workspace').getBoundingClientRect();
                if (record.maximized || record.snap) {
                    const before = element.getBoundingClientRect();
                    const fraction = Math.min(1, Math.max(0, (event.clientX - before.left) / before.width));
                    record.maximized = false; record.snap = undefined; update();
                    element.style.setProperty('--win-left', (event.clientX - workspace.left - element.getBoundingClientRect().width * fraction) + 'px');
                    element.style.setProperty('--win-top', Math.max(62, event.clientY - workspace.top - 24) + 'px');
                }
                const rect = element.getBoundingClientRect();
                drag = { record, handle, pointer: event.pointerId, x: event.clientX, y: event.clientY, left: rect.left - workspace.left, top: rect.top - workspace.top, width: rect.width, height: rect.height, workspace, dx: 0, dy: 0 };
                element.setAttribute('data-window-dragging', '');
                handle.setPointerCapture(event.pointerId);
                event.preventDefault();
            });
            element.addEventListener('pointermove', event => {
                if (!drag || drag.record !== record || event.pointerId !== drag.pointer) return;
                const current = drag;
                const left = Math.max(8, Math.min(current.left + event.clientX - current.x, current.workspace.width - current.width - 8));
                const top = Math.max(62, Math.min(current.top + event.clientY - current.y, Math.max(62, innerHeight - current.workspace.top - 100 - current.height)));
                current.dx = left - current.left; current.dy = top - current.top;
                current.snap = event.clientY <= current.workspace.top + 76 ? 'full'
                    : event.clientX <= current.workspace.left + 28 ? 'left'
                    : event.clientX >= current.workspace.right - 28 ? 'right' : undefined;
                if (!current.frame) current.frame = requestAnimationFrame(() => {
                    if (drag !== current) return;
                    element.style.transform = `translate(${current.dx}px, ${current.dy}px)`;
                    showPreview(current.snap); current.frame = undefined;
                });
            });
            function end(event) {
                if (!drag || drag.record !== record || event.pointerId !== drag.pointer) return;
                finishDrag(event.type === 'pointercancel');
            }
            element.addEventListener('pointerup', end); element.addEventListener('pointercancel', end);
            element.addEventListener('lostpointercapture', event => {
                if (drag?.record === record) end({ pointerId: event.pointerId, type: 'pointercancel' });
            });
            const handle = element.querySelector('[data-window-handle]');
            handle.title = 'Geser untuk memindahkan. Alt + panah untuk snap; Alt + Enter untuk memperbesar.';
            handle.addEventListener('dblclick', event => {
                if (event.target.closest('button,a') || mobile.matches || medium.matches || modalOpen()) return;
                finishDrag(true); place(record, undefined, !record.maximized);
            });
            handle.addEventListener('keydown', event => {
                if (!event.altKey || event.target.closest('button,a,input') || mobile.matches || medium.matches || modalOpen()) return;
                if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter'].includes(event.key)) return;
                event.preventDefault(); finishDrag(true);
                const snap = event.key === 'ArrowLeft' ? 'left' : event.key === 'ArrowRight' ? 'right' : undefined;
                place(record, snap, event.key === 'ArrowUp' || (event.key === 'Enter' && !record.maximized));
                announcement(`${record.title}: tata letak diperbarui`);
            });
            element.querySelectorAll('[data-window-action]').forEach(button => button.addEventListener('click', () => {
                if (modalOpen()) return;
                const action = button.dataset.windowAction;
                if (action === 'close') hide(record, 'closed');
                if (action === 'minimize') hide(record, 'minimized');
                if (action === 'maximize') { finishDrag(true); place(record, undefined, !record.maximized); }
            }));
            element.querySelectorAll('form').forEach(form => {
                if (form.id !== 'contact-form') return;
                form.addEventListener('input', () => { form.dataset.dirty = 'true'; });
                form.addEventListener('reset', () => { delete form.dataset.dirty; });
            });
        });
        document.addEventListener('click', event => {
            if (!enabled) return;
            const link = event.target.closest('a[href]');
            if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download') || modalOpen()) return;
            const url = new URL(link.href);
            if (url.origin !== location.origin) return;
            if (url.pathname === '/' && !url.hash && !url.search) {
                event.preventDefault(); closedInitial = true; finishDrag(true);
                rememberScroll(records.get(stack.at(-1)));
                records.forEach(record => { stopMotion(record); if (record.status === 'open') record.status = 'minimized'; });
                update(); history.pushState({ desktop: 1, active: null }, '', '/');
                document.querySelector('.desktop-brand')?.focus({ preventScroll: true });
                if (mobile.matches) window.scrollTo({ top: 0, behavior: 'instant' });
                return;
            }
            const targetId = appId(url);
            if (targetId && !url.search) { event.preventDefault(); open(targetId, link); return; }
            // Forms, queried document links, account routes and downloads keep native navigation.
        });
        document.addEventListener('keydown', event => {
            if (!enabled || event.key !== 'Escape' || event.defaultPrevented || modalKeyEvents.has(event) || modalOpen() || event.target.closest('details[open],.user-dropdown.open')) return;
            if (drag) { event.preventDefault(); finishDrag(true); return; }
            const record = records.get(stack.at(-1));
            if (record) { event.preventDefault(); hide(record, 'closed'); }
        });
        document.addEventListener('keydown', event => {
            if (modalOpen() || event.target.closest('dialog')) modalKeyEvents.add(event);
        }, true);
        document.addEventListener('focusin', event => {
            if (!enabled || modalOpen()) return;
            const element = event.target.closest('[data-window-id]');
            if (element && records.get(element.dataset.windowId)?.status === 'open') focusFromInteraction(records.get(element.dataset.windowId));
        });
        document.querySelector('[data-close-all]')?.addEventListener('click', () => {
            if (modalOpen()) return;
            const living = [...records.values()].filter(record => record.status !== 'closed');
            if (!living.every(canClose)) return;
            living.forEach(record => {
                if (record.status === 'open') hide(record, 'closed', false, true);
                else {
                    stopMotion(record);
                    record.element.querySelectorAll('form[data-dirty="true"]').forEach(form => { form.reset(); delete form.dataset.dirty; });
                    record.status = 'closed';
                }
            });
            closedInitial = true; update();
            history.replaceState({ desktop: 1, active: null }, '', '/'); document.querySelector('.desktop-brand')?.focus();
        });
        window.addEventListener('beforeunload', event => {
            if ([...records.values()].some(dirty)) { event.preventDefault(); event.returnValue = ''; }
        });
        window.addEventListener('blur', () => finishDrag(true));
        document.addEventListener('visibilitychange', () => { if (document.hidden) finishDrag(true); });
        window.addEventListener('popstate', reconcile); window.addEventListener('hashchange', reconcile);
        // Initial fragment scrolling happens after document parsing; shell owns viewport position.
        window.addEventListener('load', () => { const record = records.get(stack.at(-1)); if (enabled && record) restoreScroll(record); }, { once: true });
        window.addEventListener('resize', () => {
            finishDrag(true);
            records.forEach(record => { if (record.finishMotion) record.finishMotion(); });
            if (mobile.matches && stack.length > 1) stack.slice(0, -1).forEach(id => { records.get(id).status = 'minimized'; });
            records.forEach(clamp); update();
        });
        mobile.addEventListener('change', () => {
            finishDrag(true);
            const record = records.get(stack.at(-1));
            if (!record) return;
            if (mobile.matches) record.mobileScroll = record.element.querySelector(':scope > .container')?.scrollTop || 0;
            else record.desktopScroll = scrollY;
            restoreScroll(record);
        });
        reducedMotion.addEventListener('change', () => {
            if (reducedMotion.matches) records.forEach(record => record.finishMotion?.());
        });
        enabled = true; document.body.setAttribute('data-desktop-ready', ''); reconcile(); return true;
    }
    function fallback() {
        finishDrag(true);
        enabled = false;
        document.body.removeAttribute('data-desktop-ready'); document.body.removeAttribute('data-mobile-window');
        records.forEach(record => { stopMotion(record); record.element.inert = false; record.element.hidden = false; record.element.style.transform = ''; });
        document.querySelectorAll('[data-dock-id]').forEach(link => {
            link.removeAttribute('aria-current'); link.removeAttribute('data-running');
            link.removeAttribute('data-window-state'); link.removeAttribute('aria-description');
        });
    }
    function setQuery(id, search) {
        const record = records.get(id);
        if (!record) return;
        record.url.search = search;
        if (stack.at(-1) === id) history.replaceState({ desktop: 1, active: id }, '', activeUrl(record));
    }
    window.PortfolioDesktop = { init, fallback, open, setQuery };
})();
