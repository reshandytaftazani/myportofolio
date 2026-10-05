(function () {
    const ui = window.PortfolioResources;
    if (!ui) return;
    const { node } = ui;
    let mathQueue = Promise.resolve();

    // Keep the organization's initial visible until its remote logo has loaded.
    document.addEventListener('load', event => {
        const image = event.target;
        if (image instanceof HTMLImageElement && image.classList.contains('experience-logo')) {
            image.setAttribute('data-loaded', '');
        }
    }, true);
    document.querySelectorAll('#experience .experience-logo').forEach(image => {
        if (image.complete && image.naturalWidth) image.setAttribute('data-loaded', '');
    });

    function markdown(value, className = '') {
        const container = node('div', className);
        // description_html is sanitized with an explicit server allowlist.
        container.innerHTML = value || '';
        return container;
    }

    function date(value) {
        if (!value) return 'Unknown';
        const [year, month] = value.split('-').map(Number);
        return new Intl.DateTimeFormat('en', { month: 'short', year: 'numeric', timeZone: 'UTC' })
            .format(new Date(Date.UTC(year, month - 1, 1)));
    }

    function experience(root, item) {
        const data = item.fields;
        const wrapper = node('div', 'exp-timeline-item');
        wrapper.dataset.experienceCategory = data.category;
        const dot = node('span', 'exp-timeline-dot');
        dot.setAttribute('aria-hidden', 'true');
        wrapper.append(dot);
        const card = node('article', 'timeline-card');
        const header = node('div', 'card-header');
        const url = ui.httpUrl(data.thumbnail);
        const logo = node('div', 'experience-logo-frame');
        const initial = node('span', 'experience-logo-initial', (data.company || data.title).trim().slice(0, 1).toUpperCase());
        initial.setAttribute('aria-hidden', 'true');
        logo.append(initial);
        if (url) {
            const image = node('img', 'experience-logo');
            image.src = url; image.alt = ''; image.loading = 'lazy'; image.width = 52; image.height = 52;
            logo.append(image);
        }
        header.append(logo);
        const info = node('div', 'header-info');
        info.append(node('h3', 'experience-title', data.title));
        if (data.company) info.append(node('p', 'experience-company', data.company));
        const period = `${date(data.started_at)} — ${data.is_ongoing ? 'Present' : date(data.ended_at)}`;
        info.append(node('p', 'experience-date', period));
        header.append(info);
        card.append(header);
        const tags = node('div', 'card-tags');
        tags.append(node('span', 'badge category-badge', data.category_display),
            node('span', `badge ${data.is_ongoing ? 'status-ongoing' : 'status-completed'}`,
                data.is_ongoing ? 'Ongoing' : 'Completed'));
        card.append(tags);
        const details = node('details', 'experience-details');
        const summary = node('summary', 'experience-summary', 'View Details');
        const chevron = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        chevron.setAttribute('viewBox', '0 0 24 24');
        chevron.setAttribute('fill', 'none'); chevron.setAttribute('stroke', 'currentColor');
        chevron.setAttribute('stroke-width', '1.8'); chevron.setAttribute('aria-hidden', 'true');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'm6 9 6 6 6-6'); chevron.append(path); summary.append(chevron);
        details.append(summary, markdown(data.description_html, 'experience-desc'));
        card.append(details, ui.actions(root, item));
        wrapper.append(card);
        return wrapper;
    }

    function highlight(container) {
        container.querySelectorAll('pre code:not([data-highlighted])').forEach(code => {
            window.hljs?.highlightElement(code);
        });
    }

    function typeset(panel) {
        const run = () => {
            const math = window.MathJax;
            if (!math?.startup?.promise) return;
            mathQueue = mathQueue.then(() => math.startup.promise).then(() => {
                if (panel.isConnected && !panel.hidden) return math.typesetPromise([panel]);
            }).catch(error => console.warn('MathJax rendering failed:', error));
        };
        if (window.MathJax?.startup?.promise) run();
        else document.getElementById('MathJax-script')?.addEventListener('load', run, { once: true });
    }

    function ide(snippet, title) {
        const latex = snippet.includes('\\begin');
        const cpp = snippet.includes('#include');
        const container = node('div', 'ide-window');
        const header = node('div', 'ide-header');
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('viewBox', '0 0 24 24');
        icon.setAttribute('fill', 'none');
        icon.setAttribute('stroke', 'currentColor');
        icon.setAttribute('stroke-width', '1.6');
        icon.setAttribute('aria-hidden', 'true');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'm8 7-5 5 5 5m8-10 5 5-5 5m-3-12-2 14');
        icon.append(path);
        header.append(icon, node('div', 'ide-title', latex ? 'main.tex — Overleaf'
            : cpp ? 'main.cpp — VS Code' : 'main.py — VS Code'),
            node('span', 'ide-language', latex ? 'LaTeX' : cpp ? 'C++' : 'Python'));
        const content = node('div', `ide-content ${latex ? 'overleaf-mode' : 'vscode-mode'}`);
        const pre = node('pre');
        pre.tabIndex = 0;
        pre.setAttribute('role', 'region');
        pre.setAttribute('aria-label', `Code for ${title}`);
        pre.append(node('code', latex ? 'language-latex' : cpp ? 'language-cpp' : 'language-python', snippet));
        if (latex) {
            const editor = node('div', 'overleaf-editor');
            editor.append(node('p', 'source-label', 'Source'), pre);
            const pdf = node('div', 'overleaf-pdf');
            pdf.append(node('p', 'preview-label', 'Preview'));
            const paper = node('div', 'pdf-paper', `$$ ${snippet} $$`);
            paper.tabIndex = 0;
            paper.setAttribute('role', 'region');
            paper.setAttribute('aria-label', `Math preview for ${title}`);
            pdf.append(paper);
            content.append(pdf, editor);
        } else content.append(pre);
        container.append(header, content);
        return container;
    }

    function skills(root, items, content) {
        const activeId = content.querySelector('[aria-selected=true]')?.dataset.pk;
        window.MathJax?.typesetClear?.([content]);
        content.replaceChildren();
        const header = node('div', 'tabs-header');
        header.setAttribute('role', 'tablist'); header.setAttribute('aria-label', 'Skills');
        const panels = node('div', 'tabs-content');
        const tabs = [];
        const selected = items.some(item => item.pk === activeId) ? activeId : items[0]?.pk;
        function activate(index) {
            tabs.forEach(({ button, panel }, current) => {
                const active = current === index;
                button.classList.toggle('active', active);
                button.setAttribute('aria-selected', String(active));
                button.tabIndex = active ? 0 : -1;
                panel.classList.toggle('active', active);
                panel.hidden = !active;
            });
            if (tabs[index]) typeset(tabs[index].panel);
        }
        items.forEach((item, index) => {
            const button = node('button', 'tab-btn');
            const folder = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            folder.setAttribute('viewBox', '0 0 64 56');
            folder.setAttribute('aria-hidden', 'true');
            const name = item.fields.title.toLowerCase();
            const mark = /math|olympiad/.test(name) ? 'education'
                : /research|analysis/.test(name) ? 'experience'
                : /problem|debug/.test(name) ? 'projects' : 'skills';
            ['i-folder', `i-folder-mark-${mark}`].forEach(id => {
                const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
                use.setAttribute('href', `#${id}`);
                folder.append(use);
            });
            button.append(folder, node('span', 'skill-tab-label', item.fields.title));
            button.title = item.fields.title;
            button.type = 'button'; button.dataset.pk = item.pk;
            button.id = `skill-tab-${item.pk}`;
            button.setAttribute('role', 'tab');
            button.setAttribute('aria-controls', `skill-panel-${item.pk}`);
            const panel = node('div', 'tab-panel');
            panel.id = `skill-panel-${item.pk}`;
            panel.setAttribute('role', 'tabpanel');
            panel.setAttribute('aria-labelledby', button.id);
            const details = node('div', 'skill-details');
            const intro = node('div', 'skill-intro');
            const heading = node('div', 'skill-heading');
            heading.append(node('h3', '', item.fields.title),
                node('span', 'experience-category', item.fields.level));
            intro.append(heading, markdown(item.fields.description_html, 'markdown-content'));
            details.append(intro);
            if (item.fields.code_snippet) details.append(ide(item.fields.code_snippet, item.fields.title));
            details.append(ui.actions(root, item));
            panel.append(details); panels.append(panel); header.append(button);
            tabs.push({ button, panel });
            button.addEventListener('click', () => activate(index));
            button.addEventListener('keydown', event => {
                let next;
                if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
                if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
                if (event.key === 'Home') next = 0;
                if (event.key === 'End') next = tabs.length - 1;
                if (next === undefined) return;
                event.preventDefault(); tabs[next].button.focus(); activate(next);
            });
        });
        content.append(header, panels);
        highlight(content);
        document.getElementById('highlight-script')?.addEventListener('load', () => highlight(content), { once: true });
        if (items.length) activate(items.findIndex(item => item.pk === selected));
    }

    function education(root, item) {
        const wrapper = node('article', 'timeline-item');
        const dot = node('span', 'timeline-dot');
        dot.setAttribute('aria-hidden', 'true');
        const content = node('div', 'timeline-content');
        const header = node('div', 'education-card-header');
        const identity = node('div', 'education-identity');
        identity.append(node('h3', 'timeline-school', item.fields.school_name),
            node('span', 'timeline-date', item.fields.period));
        const monogram = node('span', 'education-logo-frame', Array.from(item.fields.school_name || '')[0]?.toUpperCase() || '');
        monogram.setAttribute('aria-hidden', 'true');
        header.append(identity, monogram);
        content.append(header,
            node('p', 'timeline-detail', item.fields.detail), ui.actions(root, item));
        wrapper.append(dot, content);
        return wrapper;
    }

    function techBrand(name) {
        const value = String(name || '').trim().toLowerCase();
        if (value === 'c++') return 'cpp';
        if (value === 'python') return 'python';
        if (value === 'java') return 'java';
        if (value === 'html5') return 'html';
        if (value === 'css3') return 'css';
        if (value === 'pandas') return 'pandas';
        if (value === 'latex') return 'latex';
        return 'other';
    }

    function techstack(root, item) {
        const data = item.fields;
        const name = data.name || '';
        const wrapper = node('details', 'tech-item');
        wrapper.dataset.techBrand = techBrand(name);
        const summary = node('summary', 'tech-icon-wrapper');
        const frame = node('span', 'tech-icon-frame');
        const url = ui.httpUrl(item.fields.icon_url);
        if (url) {
            const image = node('img', 'tech-icon');
            image.alt = ''; image.loading = 'lazy'; image.width = 64; image.height = 64;
            image.addEventListener('load', () => frame.setAttribute('data-loaded', ''));
            image.addEventListener('error', () => frame.setAttribute('data-failed', ''));
            image.src = url;
            frame.append(image);
            frame.append(node('span', 'tech-icon-fallback', name.slice(0, 2).toUpperCase()));
        } else {
            frame.append(node('span', 'tech-icon-fallback', name.slice(0, 2).toUpperCase()));
        }
        summary.setAttribute('aria-controls', `tech-code-${item.pk}`);
        summary.append(frame, node('span', 'tech-tab-label', name));
        const snippet = node('div', 'tech-code-snippet mac-window');
        snippet.id = `tech-code-${item.pk}`;
        const header = node('div', 'mac-header');
        const dots = node('div', 'mac-dots');
        for (let i = 0; i < 3; i++) dots.append(node('span'));
        dots.setAttribute('aria-hidden', 'true');
        header.append(dots, node('div', 'mac-title', data.filename || name));
        const pre = node('pre', 'mac-body');
        pre.tabIndex = 0;
        pre.setAttribute('role', 'region');
        pre.setAttribute('aria-label', `Code for ${data.filename || name}`);
        pre.append(node('code', '', data.code_snippet || ''));
        snippet.append(header, pre);
        wrapper.addEventListener('toggle', () => {
            wrapper.classList.toggle('expanded', wrapper.open);
            if (wrapper.open) {
                root.querySelectorAll('.tech-item[open]').forEach(other => {
                    if (other !== wrapper) { other.open = false; other.classList.remove('expanded'); }
                });
                requestAnimationFrame(() => wrapper.scrollIntoView({
                    block: 'start',
                    behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
                }));
            }
        });
        summary.addEventListener('pointermove', event => {
            if (event.pointerType !== 'mouse' || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
            const rect = summary.getBoundingClientRect();
            const x = (event.clientX - rect.left) / rect.width - .5;
            const y = (event.clientY - rect.top) / rect.height - .5;
            summary.style.setProperty('--tool-tilt-x', `${(-y * 5).toFixed(2)}deg`);
            summary.style.setProperty('--tool-tilt-y', `${(x * 5).toFixed(2)}deg`);
        });
        summary.addEventListener('pointerleave', () => {
            summary.style.removeProperty('--tool-tilt-x');
            summary.style.removeProperty('--tool-tilt-y');
        });
        wrapper.append(summary, snippet, ui.actions(root, item));
        return wrapper;
    }

    document.querySelectorAll('[data-public-resource]').forEach(root => {
        const controller = ui.list(root, (items, content) => {
            if (root.dataset.resource === 'skills') { skills(root, items, content); return; }
            const render = { experience, education, techstack }[root.dataset.resource];
            content.replaceChildren(...items.map((item, index) => render(root, item, index)));
        }, { autoLoad: !document.body.classList.contains('desktop-page') });
        window.addEventListener('load', () => {
            if (!document.body.hasAttribute('data-desktop-ready')) controller.activate();
        }, { once: true });
        root.addEventListener('desktop:open', () => {
            controller.activate();
            if (root.dataset.resource === 'techstack') requestAnimationFrame(() => {
                root.querySelector('.tech-item[open]')?.scrollIntoView({ block: 'start' });
            });
        });
    });
})();
