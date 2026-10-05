(function () {
    const app = document.querySelector('[data-projects-app]');
    if (!app || !window.PortfolioAjax) return;

    const ajax = window.PortfolioAjax;
    const resources = window.PortfolioResources;
    const config = app.dataset;
    const loadingState = document.getElementById('loading');
    const errorState = document.getElementById('error');
    const emptyState = document.getElementById('empty');
    const grid = document.getElementById('grid');
    const searchForm = document.getElementById('project-search-form');
    const searchInput = document.getElementById('search-input');
    const filters = app.querySelector('.project-filters');
    let activeCategory = config.initialCategory || 'all';
    let activeRequest;
    let activated = false;
    let hasContent = Boolean(grid?.querySelector('article'));
    const projectIdPlaceholder = '00000000-0000-0000-0000-000000000000';
    app.setAttribute('data-resource-ready', '');

    function showToast(title, message, type = 'normal', duration = 3000) {
        if (typeof window.showToast === 'function') {
            window.showToast(title, message, type, duration);
        }
    }

    function displaySection({ loading = false, error = false, empty = false, grid: showGrid = false }) {
        loadingState?.classList.toggle('hide', !loading);
        loadingState?.classList.toggle('sr-only', loading && hasContent);
        errorState?.classList.toggle('hide', !error);
        emptyState?.classList.toggle('hide', !empty);
        grid?.classList.toggle('hide', !(showGrid || ((loading || error) && hasContent)));
        grid?.setAttribute('aria-busy', String(loading));
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function safeHttpUrl(value) {
        if (!value) return '';
        try {
            const url = new URL(value, window.location.origin);
            return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
        } catch (_error) {
            return '';
        }
    }

    function csrfInput() {
        return `<input type="hidden" name="csrfmiddlewaretoken" value="${escapeHtml(ajax.getCsrfToken())}">`;
    }

    function buildProjectCard(item) {
        const project = item.fields;
        const projectId = item.pk;
        const article = document.createElement('article');
        article.className = 'experience-card project-card';

        const imageUrl = safeHttpUrl(project.project_image_url);
        const projectUrl = safeHttpUrl(project.project_url);
        const starUrl = config.starUrlTemplate.replace(projectIdPlaceholder, encodeURIComponent(projectId));
        const isStarred = Boolean(project.is_starred);
        const starTitle = project.starred_by_names
            ? `Dibintangi oleh ${project.starred_by_names}`
            : 'Jadilah yang pertama memberi star';
        const imageHtml = `<div class="project-media">${imageUrl
            ? `<img src="${escapeHtml(imageUrl)}" alt="Gambar ${escapeHtml(project.title)}" class="project-image" loading="lazy" decoding="async" width="800" height="500">`
            : `<div class="project-media-placeholder"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 6-6 4 4 3-3 5 5"/></svg><span>Pratinjau belum tersedia</span></div>`}</div>`;
        const projectLinkHtml = projectUrl
            ? `<a href="${escapeHtml(projectUrl)}" class="button project-link" target="_blank" rel="noopener noreferrer">Lihat Project <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M7 17 17 7M7 7h10v10"/></svg></a>`
            : '';
        const starIcon = '<svg class="resource-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 3 2.8 5.7 6.3.9-4.5 4.4 1.1 6.2-5.7-3-5.7 3 1.1-6.2-4.5-4.4 6.3-.9Z"/></svg>';
        const starCount = `<span class="star-count resource-star-count" aria-live="polite">${Number(project.star_count) || 0}</span>`;
        const starHtml = config.isAuthenticated === 'true'
            ? `<form method="post" action="${escapeHtml(starUrl)}" class="star-form">
                ${csrfInput()}
                <button type="submit" class="button resource-action resource-star" aria-pressed="${isStarred}" title="${escapeHtml(starTitle)}">
                    ${starIcon}<span class="star-label">${isStarred ? 'Unstar' : 'Star'}</span>${starCount}
                </button>
              </form>`
            : `<a href="${escapeHtml(config.loginUrl)}" class="button resource-action resource-star">${starIcon}<span>Login untuk star</span>${starCount}</a>`;
        const technologiesHtml = project.tech_stack && project.tech_stack !== project.category
            ? `<p class="project-technologies">${escapeHtml(project.tech_stack)}</p>` : '';

        article.innerHTML = `
            ${imageHtml}
            <div class="project-card-body">
            <div class="project-card-heading">
                <h2 class="project-card-title">${escapeHtml(project.title)}</h2>
                <span class="experience-category project-category">${escapeHtml(project.category)}</span>
            </div>
            ${technologiesHtml}
            <p class="experience-description">${escapeHtml(project.description)}</p>
            <div class="project-card-actions">
                <div class="project-actions">
                    ${projectLinkHtml}
                    ${starHtml}
                </div>
            </div>
            </div>`;
        article.append(resources.actions(app, item));
        return article;
    }

    async function fetchProjects(title = searchInput?.value.trim() || '', category = activeCategory) {
        activeRequest?.abort();
        activeRequest = new AbortController();
        const request = activeRequest;
        displaySection({ loading: true });

        const url = new URL(config.projectsUrl, window.location.origin);
        if (title) url.searchParams.set('title', title);
        if (category && category !== 'all') url.searchParams.set('category', category);

        try {
            const { response, data } = await ajax.fetchJson(url, { signal: request.signal });
            if (request !== activeRequest || request.signal.aborted) return;
            if (!response.ok || !Array.isArray(data)) throw new Error(`Projects request failed (${response.status})`);
            const canonical = new URL('/projects/', location.origin);
            if (title) canonical.searchParams.set('title', title);
            if (category && category !== 'all') canonical.searchParams.set('category', category);
            if (window.PortfolioDesktop?.setQuery) window.PortfolioDesktop.setQuery('projects', canonical.search);
            else history.replaceState(history.state, '', canonical.pathname + canonical.search);

            grid.replaceChildren();
            hasContent = data.length > 0;
            if (!data.length) {
                const filtered = Boolean(title || (category && category !== 'all'));
                const heading = emptyState.querySelector('[data-empty-title]');
                const description = emptyState.querySelector('[data-empty-description]');
                if (heading) heading.textContent = filtered ? 'Tidak ada proyek yang cocok' : 'Belum ada proyek';
                if (description) description.textContent = filtered ? 'Coba judul lain atau tampilkan semua kategori.' : 'Karya akan tampil di sini setelah ditambahkan.';
                const reset = emptyState.querySelector('[data-projects-reset]');
                if (reset) reset.hidden = !filtered;
                displaySection({ empty: true });
                return;
            }
            data.forEach(item => grid.appendChild(buildProjectCard(item)));
            displaySection({ grid: true });
        } catch (error) {
            if (error.name === 'AbortError' || request !== activeRequest) return;
            console.error('Error loading projects:', error);
            displaySection({ error: true });
        }
    }

    const searchProjects = resources.debounce(() => fetchProjects(), 300);
    app.querySelector('[data-projects-retry]')?.addEventListener('click', async () => {
        searchProjects.cancel();
        await fetchProjects();
        if (errorState?.classList.contains('hide')) searchInput?.focus({ preventScroll: true });
    });
    searchInput?.addEventListener('input', () => { activeRequest?.abort(); searchProjects(); });
    searchForm?.addEventListener('submit', event => {
        event.preventDefault();
        searchProjects.cancel();
        fetchProjects();
    });

    function setActiveCategory(category) {
        searchProjects.cancel();
        activeCategory = category;
        const field = searchForm?.querySelector('[name="category"]');
        if (field) field.value = category;
        filters?.querySelectorAll('[data-filter]').forEach(button => {
            const isActive = button.dataset.filter === category;
            button.classList.toggle('active', isActive);
            button.classList.toggle('project-filter-btn--inactive', !isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
        fetchProjects();
    }
    app.querySelector('[data-projects-reset]')?.addEventListener('click', event => {
        event.preventDefault();
        if (searchInput) searchInput.value = '';
        setActiveCategory('all'); searchInput?.focus({ preventScroll: true });
    });

    filters?.addEventListener('click', event => {
        const button = event.target.closest('[data-filter]');
        if (button) { event.preventDefault(); setActiveCategory(button.dataset.filter); }
    });

    function addCategoryFilter(category) {
        if (!category || !filters) return;
        const existing = [...filters.querySelectorAll('[data-filter]')]
            .find(button => button.dataset.filter === category);
        if (existing) return;

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'button project-filter-btn project-filter-btn--inactive';
        button.dataset.filter = category;
        button.setAttribute('aria-pressed', 'false');
        button.textContent = category;
        filters.appendChild(button);
    }

    grid?.addEventListener('submit', async event => {
        const form = event.target.closest('.star-form');
        if (!form) return;
        event.preventDefault();

        if (config.isAuthenticated !== 'true') {
            window.location.assign(config.loginUrl);
            return;
        }

        const button = form.querySelector('button[type="submit"]');
        const label = button?.querySelector('.star-label');
        const count = button?.querySelector('.star-count');
        if (!button || !label || !count || button.disabled) return;
        button.disabled = true;

        try {
            const { response, data } = await ajax.fetchJson(form.action, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': ajax.getCsrfToken(form),
                },
                body: new FormData(form),
            });
            if (response.redirected) {
                window.location.assign(response.url);
                return;
            }
            if (!response.ok || !data) throw new Error(`Star request failed (${response.status})`);

            button.setAttribute('aria-pressed', String(Boolean(data.is_starred)));
            label.textContent = data.is_starred ? 'Unstar' : 'Star';
            count.textContent = data.count;
            button.title = data.starred_by_names
                ? `Dibintangi oleh ${data.starred_by_names}`
                : 'Jadilah yang pertama memberi star';
            showToast('Berhasil', data.is_starred
                ? 'Star berhasil diberikan.' : 'Star berhasil dibatalkan.', 'success');
        } catch (error) {
            console.error('Error toggling star:', error);
            showToast('Gagal memperbarui star', 'Permintaan gagal. Silakan coba lagi.', 'error');
        } finally {
            button.disabled = false;
        }
    });

    resources.bindManagement(app, item => {
        searchProjects.cancel();
        addCategoryFilter(item?.fields.category);
        fetchProjects();
    });

    app.addEventListener('desktop:open', () => {
        if (!activated) { activated = true; fetchProjects(); }
    });
    app.addEventListener('desktop:query', event => {
        const query = new URLSearchParams(event.detail);
        if (searchInput) searchInput.value = query.get('title') || '';
        setActiveCategory(query.get('category') || 'all');
        activated = true;
    });
    if (!document.body.classList.contains('desktop-page')) fetchProjects();
})();
