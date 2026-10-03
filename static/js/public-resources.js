(function () {
    const ui = window.PortfolioResources;
    if (!ui) return;
    const { node } = ui;
    let mathQueue = Promise.resolve();

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
        wrapper.dataset.aos = 'fade-up';
        wrapper.append(node('div', 'exp-timeline-dot'));
        const card = node('article', 'timeline-card');
        const header = node('div', 'card-header');
        const url = ui.httpUrl(data.thumbnail);
        const image = node(url ? 'img' : 'div', url ? 'experience-logo' : 'experience-logo-placeholder');
        if (url) { image.src = url; image.alt = `${data.company || data.title} Logo`; image.loading = 'lazy'; }
        header.append(image);
        const info = node('div', 'header-info');
        info.append(node('h2', 'experience-title', data.title));
        const period = `${date(data.started_at)} - ${data.is_ongoing ? 'Present' : date(data.ended_at)}`;
        info.append(node('p', 'experience-date', `${data.company ? data.company + ' • ' : ''}${period}`));
        header.append(info);
        card.append(header);
        const tags = node('div', 'card-tags');
        tags.append(node('span', 'badge category-badge', data.category_display.toUpperCase()),
            node('span', `badge ${data.is_ongoing ? 'status-ongoing' : 'status-completed'}`,
                data.is_ongoing ? 'Ongoing' : 'Completed'));
        card.append(tags);
        const details = node('details', 'experience-details');
        details.append(node('summary', 'experience-summary', 'View Details'),
            markdown(data.description_html, 'experience-desc'));
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

    function ide(snippet) {
        const latex = snippet.includes('\\begin');
        const cpp = snippet.includes('#include');
        const container = node('div', 'ide-window');
        const header = node('div', 'ide-header');
        const buttons = node('div', 'ide-buttons');
        ['btn-close', 'btn-minimize', 'btn-maximize'].forEach(name => buttons.append(node('span', name)));
        header.append(buttons, node('div', 'ide-title', latex ? '📄 main.tex — Overleaf'
            : cpp ? '⚙️ main.cpp — VS Code' : '🐍 main.py — VS Code'));
        const content = node('div', `ide-content ${latex ? 'overleaf-mode' : 'vscode-mode'}`);
        const pre = node('pre');
        pre.append(node('code', latex ? 'language-latex' : cpp ? 'language-cpp' : 'language-python', snippet));
        if (latex) {
            const editor = node('div', 'overleaf-editor');
            editor.append(pre);
            const pdf = node('div', 'overleaf-pdf');
            pdf.append(node('div', 'pdf-paper', `$$ ${snippet} $$`));
            content.append(editor, pdf);
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
            const button = node('button', 'tab-btn', item.fields.title);
            button.type = 'button'; button.dataset.pk = item.pk;
            button.id = `skill-tab-${item.pk}`;
            button.setAttribute('role', 'tab');
            button.setAttribute('aria-controls', `skill-panel-${item.pk}`);
            const panel = node('div', 'tab-panel');
            panel.id = `skill-panel-${item.pk}`;
            panel.setAttribute('role', 'tabpanel');
            panel.setAttribute('aria-labelledby', button.id);
            const details = node('div', 'skill-details');
            details.append(node('span', 'experience-category', item.fields.level),
                node('h3', '', item.fields.title), markdown(item.fields.description_html));
            if (item.fields.code_snippet) details.append(ide(item.fields.code_snippet));
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
        let startX, scrollLeft;
        header.addEventListener('mousedown', event => { startX = event.pageX; scrollLeft = header.scrollLeft; });
        header.addEventListener('mousemove', event => {
            if (startX === undefined) return;
            header.scrollLeft = scrollLeft - (event.pageX - startX);
        });
        ['mouseup', 'mouseleave'].forEach(name => header.addEventListener(name, () => { startX = undefined; }));
    }

    function education(root, item) {
        const wrapper = node('div', 'timeline-item');
        wrapper.dataset.aos = 'fade-up';
        const content = node('div', 'timeline-content');
        content.append(node('span', 'timeline-date', item.fields.period),
            node('h3', 'timeline-school', item.fields.school_name),
            node('p', 'timeline-detail', item.fields.detail), ui.actions(root, item));
        wrapper.append(node('div', 'timeline-dot'), content);
        return wrapper;
    }

    function techstack(root, item) {
        const wrapper = node('div', 'tech-item');
        wrapper.dataset.aos = 'fade-up';
        const button = node('button', 'tech-icon-wrapper');
        button.type = 'button'; button.setAttribute('aria-expanded', 'false');
        const url = ui.httpUrl(item.fields.icon_url);
        if (url) {
            const image = node('img', 'tech-icon');
            image.src = url; image.alt = ''; image.loading = 'lazy'; button.append(image);
        }
        button.append(node('span', '', item.fields.name));
        const snippet = node('div', 'tech-code-snippet mac-window');
        const header = node('div', 'mac-header');
        const dots = node('div', 'mac-dots');
        for (let i = 0; i < 3; i++) dots.append(node('span'));
        header.append(dots, node('div', 'mac-title', item.fields.filename));
        const pre = node('pre', 'mac-body');
        pre.append(node('code', '', item.fields.code_snippet));
        snippet.append(header, pre);
        snippet.id = `tech-code-${item.pk}`;
        button.setAttribute('aria-controls', snippet.id);
        button.addEventListener('click', () => {
            const expanded = wrapper.classList.contains('expanded');
            root.querySelectorAll('.tech-item').forEach(other => {
                other.classList.remove('expanded');
                other.querySelector('.tech-icon-wrapper').setAttribute('aria-expanded', 'false');
            });
            if (!expanded) { wrapper.classList.add('expanded'); button.setAttribute('aria-expanded', 'true'); }
        });
        wrapper.append(button, snippet, ui.actions(root, item));
        return wrapper;
    }

    document.querySelectorAll('[data-public-resource]').forEach(root => {
        ui.list(root, (items, content) => {
            if (root.dataset.resource === 'skills') { skills(root, items, content); return; }
            const render = { experience, education, techstack }[root.dataset.resource];
            content.replaceChildren(...items.map(item => render(root, item)));
        });
    });
})();
