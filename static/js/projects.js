(function () {
    const app = document.querySelector('[data-projects-app]');
    if (!app || !window.PortfolioAjax) return;

    const ajax = window.PortfolioAjax;
    const config = app.dataset;
    const loadingState = document.getElementById('loading');
    const errorState = document.getElementById('error');
    const emptyState = document.getElementById('empty');
    const grid = document.getElementById('grid');
    const searchForm = document.getElementById('project-search-form');
    const searchInput = document.getElementById('search-input');
    const filters = app.querySelector('.project-filters');
    const projectForm = document.getElementById('project-form');
    let activeCategory = config.initialCategory || 'all';
    let activeRequest;
    const projectIdPlaceholder = '00000000-0000-0000-0000-000000000000';

    function showToast(title, message, type = 'normal', duration = 3000) {
        if (typeof window.showToast === 'function') {
            window.showToast(title, message, type, duration);
        }
    }

    function displaySection({ loading = false, error = false, empty = false, grid: showGrid = false }) {
        loadingState?.classList.toggle('hide', !loading);
        errorState?.classList.toggle('hide', !error);
        emptyState?.classList.toggle('hide', !empty);
        grid?.classList.toggle('hide', !showGrid);
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
        article.className = 'experience-card';

        const imageUrl = safeHttpUrl(project.project_image_url);
        const projectUrl = safeHttpUrl(project.project_url);
        const starUrl = config.starUrlTemplate.replace(projectIdPlaceholder, encodeURIComponent(projectId));
        const isStarred = Boolean(project.is_starred);
        const starTitle = project.starred_by_names
            ? `Dibintangi oleh ${project.starred_by_names}`
            : 'Jadilah yang pertama memberi star';
        const imageHtml = imageUrl
            ? `<img src="${escapeHtml(imageUrl)}" alt="Gambar ${escapeHtml(project.title)}" class="project-image">`
            : '';
        const projectLinkHtml = projectUrl
            ? `<a href="${escapeHtml(projectUrl)}" class="button" target="_blank" rel="noopener noreferrer">Lihat Project</a>`
            : '';
        const deleteHtml = config.isSuperuser === 'true'
            ? `<form method="post" action="${escapeHtml(config.deleteUrlTemplate.replace(projectIdPlaceholder, encodeURIComponent(projectId)))}" class="project-delete-form" style="display:inline;">
                    ${csrfInput()}
                    <button type="submit" class="button button-danger" data-confirm="Yakin ingin menghapus project ini?">Hapus</button>
                </form>`
            : '';

        article.innerHTML = `
            ${imageHtml}
            <h2>${escapeHtml(project.title)}</h2>
            <span class="experience-category">${escapeHtml(project.tech_stack)}</span>
            <p class="experience-description">${escapeHtml(project.description)}</p>
            <div class="project-card-actions">
                <div class="project-actions">
                    ${projectLinkHtml}
                    <form method="post" action="${escapeHtml(starUrl)}" class="star-form">
                        ${csrfInput()}
                        <button type="submit" class="button button-star${isStarred ? ' is-starred' : ''}" title="${escapeHtml(starTitle)}">
                            <span class="star-icon" aria-hidden="true">★</span>
                            <span class="star-label">${isStarred ? 'Unstar' : 'Star'}</span>
                            <span class="star-count">${Number(project.star_count) || 0}</span>
                        </button>
                    </form>
                    ${deleteHtml}
                </div>
            </div>`;
        return article;
    }

    async function fetchProjects(title = searchInput?.value.trim() || '', category = activeCategory) {
        activeRequest?.abort();
        activeRequest = new AbortController();
        displaySection({ loading: true });

        const url = new URL(config.projectsUrl, window.location.origin);
        if (title) url.searchParams.set('title', title);
        if (category && category !== 'all') url.searchParams.set('category', category);

        try {
            const { response, data } = await ajax.fetchJson(url, { signal: activeRequest.signal });
            if (!response.ok || !Array.isArray(data)) throw new Error(`Projects request failed (${response.status})`);

            grid.replaceChildren();
            if (!data.length) {
                displaySection({ empty: true });
                return;
            }
            data.forEach(item => grid.appendChild(buildProjectCard(item)));
            displaySection({ grid: true });
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Error loading projects:', error);
            displaySection({ error: true });
        }
    }

    function debounce(callback, delay) {
        let timer;
        const debounced = (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => callback(...args), delay);
        };
        debounced.cancel = () => clearTimeout(timer);
        return debounced;
    }

    const searchProjects = debounce(() => fetchProjects(), 300);
    searchInput?.addEventListener('input', searchProjects);
    searchForm?.addEventListener('submit', event => {
        event.preventDefault();
        searchProjects.cancel();
        fetchProjects();
    });

    function setActiveCategory(category) {
        searchProjects.cancel();
        activeCategory = category;
        filters?.querySelectorAll('[data-filter]').forEach(button => {
            const isActive = button.dataset.filter === category;
            button.classList.toggle('active', isActive);
            button.classList.toggle('project-filter-btn--inactive', !isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
        fetchProjects();
    }

    filters?.addEventListener('click', event => {
        const button = event.target.closest('[data-filter]');
        if (button) setActiveCategory(button.dataset.filter);
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
        button.style.cssText = 'white-space: nowrap; transition: all 0.3s ease;';
        button.textContent = category;
        filters.appendChild(button);
    }

    async function submitProject(event) {
        event.preventDefault();
        const submitButton = projectForm?.querySelector('button[type="submit"]');
        if (!projectForm || !submitButton) return;
        submitButton.disabled = true;

        try {
            const { response, data } = await ajax.fetchJson(config.createUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': ajax.getCsrfToken(projectForm) },
                body: new FormData(projectForm),
            });
            if (response.ok) {
                projectForm.reset();
                document.getElementById('add-project-modal')?.hidePopover();
                addCategoryFilter(data?.category);
                showToast('Berhasil', data?.message || 'Proyek berhasil ditambahkan.', 'success');
                fetchProjects();
                return;
            }

            const messages = ajax.validationMessages(data?.errors);
            showToast(
                'Gagal menambahkan proyek',
                messages.join(' ') || data?.message || `Terjadi kesalahan (status ${response.status}).`,
                'error',
            );
        } catch (error) {
            console.error('Error adding project:', error);
            showToast('Gagal menambahkan proyek', 'Tidak dapat terhubung ke server. Silakan coba lagi.', 'error');
        } finally {
            submitButton.disabled = false;
        }
    }

    projectForm?.addEventListener('submit', submitProject);

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

            button.classList.toggle('is-starred', Boolean(data.is_starred));
            label.textContent = data.is_starred ? 'Unstar' : 'Star';
            count.textContent = data.count;
            button.title = data.starred_by_names
                ? `Dibintangi oleh ${data.starred_by_names}`
                : 'Jadilah yang pertama memberi star';
        } catch (error) {
            console.error('Error toggling star:', error);
            showToast('Gagal memperbarui star', 'Permintaan gagal. Silakan coba lagi.', 'error');
        } finally {
            button.disabled = false;
        }
    });

    grid?.addEventListener('click', event => {
        const button = event.target.closest('[data-confirm]');
        if (button && !window.confirm(button.dataset.confirm)) event.preventDefault();
    });

    fetchProjects();
})();
