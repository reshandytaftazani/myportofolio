(function () {
    const app = document.querySelector('[data-dashboard-app]');
    const ui = window.PortfolioResources;
    if (!app || !ui) return;
    const controllers = new Map();
    app.querySelectorAll('[data-dashboard-resource]').forEach(root => {
        const columns = [...root.querySelectorAll('[data-column]')].map(th => th.dataset.column);
        controllers.set(root.dataset.resource, ui.list(root, (items, content) => {
            const tbody = content.querySelector('tbody');
            tbody.replaceChildren();
            for (const item of items) {
                const row = ui.node('tr');
                for (const field of columns) {
                    const value = item.fields[field];
                    row.append(ui.node('td', '', typeof value === 'boolean' ? (value ? 'Ya' : 'Tidak') : value));
                }
                const actions = ui.node('td');
                actions.append(ui.actions(root, item));
                row.append(actions);
                tbody.append(row);
            }
        }, { autoLoad: false }));
    });
    const tabs = [...app.querySelectorAll('[data-dashboard-tab]')];
    function activate(tab) {
        tabs.forEach(button => {
            const active = button === tab;
            button.setAttribute('aria-selected', String(active));
            button.tabIndex = active ? 0 : -1;
            document.getElementById(button.getAttribute('aria-controls')).hidden = !active;
        });
        controllers.get(tab.dataset.dashboardTab)?.activate();
    }
    tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => activate(tab));
        tab.addEventListener('keydown', event => {
            let next;
            if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
            if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
            if (event.key === 'Home') next = 0;
            if (event.key === 'End') next = tabs.length - 1;
            if (next === undefined) return;
            event.preventDefault();
            tabs[next].focus(); activate(tabs[next]);
        });
    });
    if (tabs.length) activate(tabs[0]);
})();
