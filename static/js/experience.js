(function () {
    const app = document.querySelector('[data-experience-app]');
    if (!app || !window.PortfolioAjax) return;

    const ajax = window.PortfolioAjax;
    const resources = window.PortfolioResources;
    const config = app.dataset;

    const loadingState = document.getElementById('experience-loading') || app.querySelector('#experience-loading');
    const errorState = document.getElementById('experience-error') || app.querySelector('#experience-error');
    const emptyState = document.getElementById('experience-empty') || app.querySelector('#experience-empty');
    const grid = app.querySelector('[data-list]') || app.querySelector('.timeline-container');
    const searchForm = document.getElementById('experience-search-form') || app.querySelector('#experience-search-form');
    const searchInput = document.getElementById('experience-search-input') || app.querySelector('#experience-search-input');
    const filters = app.querySelector('.experience-filters') || app.querySelector('.project-filters');

    let activeCategory = config.initialCategory || 'all';
    let activeRequest = null;
    let activated = false;
    let hasContent = Boolean(grid?.querySelector('.timeline-card, .exp-timeline-item'));
    const experienceIdPlaceholder = '00000000-0000-0000-0000-000000000000';

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

    function formatDate(value) {
        if (!value) return '';
        try {
            const parts = String(value).split('-').map(Number);
            if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                const [year, month] = parts;
                return new Intl.DateTimeFormat('en', { month: 'short', year: 'numeric', timeZone: 'UTC' })
                    .format(new Date(Date.UTC(year, month - 1, 1)));
            }
        } catch (_e) {}
        return String(value);
    }

    function formatPeriod(startedAt, endedAt, isOngoing) {
        const startStr = formatDate(startedAt);
        if (isOngoing) {
            return startStr ? `${startStr} — Present` : 'Present';
        }
        const endStr = formatDate(endedAt);
        if (startStr && endStr) return `${startStr} — ${endStr}`;
        return startStr || endStr || 'Unknown';
    }

    function formatDescription(text) {
        if (!text) return '<p>Tidak ada rincian deskripsi.</p>';
        return escapeHtml(text)
            .split(/\n{2,}/)
            .map(paragraph => `<p>${paragraph.replace(/\n/g, '<br>')}</p>`)
            .join('');
    }

    function csrfInput() {
        return `<input type="hidden" name="csrfmiddlewaretoken" value="${escapeHtml(ajax.getCsrfToken())}">`;
    }

    function adaptExperience(raw) {
        const fields = raw.fields || raw;
        const id = raw.id || raw.pk || fields.id;
        return {
            id: String(id),
            title: fields.title || '',
            company: fields.company || '',
            description: fields.description || '',
            category: fields.category || 'full-time',
            category_display: fields.category_display || fields.category || '',
            thumbnail: fields.thumbnail || '',
            started_at: fields.started_at || null,
            ended_at: fields.ended_at || null,
            is_ongoing: Boolean(fields.is_ongoing),
            star_count: Number(fields.star_count) || 0,
            is_starred: Boolean(fields.is_starred),
            starred_by_names: fields.starred_by_names || '',
        };
    }

    function buildExperienceCard(rawItem) {
        const exp = adaptExperience(rawItem);
        const wrapper = document.createElement('div');
        wrapper.className = 'exp-timeline-item';
        wrapper.dataset.experienceCategory = exp.category;
        wrapper.dataset.id = exp.id;

        const dot = document.createElement('span');
        dot.className = 'exp-timeline-dot';
        dot.setAttribute('aria-hidden', 'true');
        wrapper.appendChild(dot);

        const article = document.createElement('article');
        article.className = 'timeline-card';
        article.dataset.id = exp.id;

        const initial = (exp.company || exp.title || '?').trim().slice(0, 1).toUpperCase();
        const thumbUrl = safeHttpUrl(exp.thumbnail);
        const logoFrame = document.createElement('div');
        logoFrame.className = 'experience-logo-frame';

        const initialSpan = document.createElement('span');
        initialSpan.className = 'experience-logo-initial';
        initialSpan.setAttribute('aria-hidden', 'true');
        initialSpan.textContent = initial;
        logoFrame.appendChild(initialSpan);

        if (thumbUrl) {
            const img = document.createElement('img');
            img.className = 'experience-logo';
            img.src = thumbUrl;
            img.alt = `Logo ${escapeHtml(exp.company || exp.title)}`;
            img.loading = 'lazy';
            img.width = 52;
            img.height = 52;
            img.addEventListener('load', () => img.setAttribute('data-loaded', ''));
            img.addEventListener('error', () => img.remove());
            logoFrame.appendChild(img);
        }

        const starUrlTemplate = config.starUrlTemplate || '/api/v1/experiences/__pk__/star/';
        const starUrl = starUrlTemplate
            .replace(experienceIdPlaceholder, encodeURIComponent(exp.id))
            .replace('__pk__', encodeURIComponent(exp.id));

        const starIcon = '<svg class="resource-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 3 2.8 5.7 6.3.9-4.5 4.4 1.1 6.2-5.7-3-5.7 3 1.1-6.2-4.5-4.4 6.3-.9Z"/></svg>';
        const starCount = `<span class="star-count resource-star-count" aria-live="polite">${exp.star_count}</span>`;
        const starTitle = exp.starred_by_names
            ? `Dibintangi oleh ${escapeHtml(exp.starred_by_names)}`
            : 'Jadilah yang pertama memberi star';
        const isStarred = Boolean(exp.is_starred);

        const loginUrl = config.loginUrl || `/login/?next=${encodeURIComponent(location.pathname + location.search)}&notice=star`;
        const starHtml = config.isAuthenticated === 'true'
            ? `<form method="post" action="${escapeHtml(starUrl)}" class="star-form" data-experience-star-form>
                ${csrfInput()}
                <button type="submit" class="button resource-action resource-star" aria-pressed="${isStarred}" title="${escapeHtml(starTitle)}" data-action="star" data-id="${escapeHtml(exp.id)}">
                    ${starIcon}<span class="star-label">${isStarred ? 'Unstar' : 'Star'}</span>${starCount}
                </button>
              </form>`
            : `<a href="${escapeHtml(loginUrl)}" class="button resource-action resource-star" data-action="star-login">
                ${starIcon}<span>Login untuk star</span>${starCount}
              </a>`;

        const period = formatPeriod(exp.started_at, exp.ended_at, exp.is_ongoing);
        const categoryBadge = `<span class="badge category-badge">${escapeHtml(exp.category_display || exp.category)}</span>`;
        const statusBadge = `<span class="badge ${exp.is_ongoing ? 'status-ongoing' : 'status-completed'}">${exp.is_ongoing ? 'Ongoing' : 'Completed'}</span>`;
        const companyHtml = exp.company ? `<p class="experience-company">${escapeHtml(exp.company)}</p>` : '';

        article.innerHTML = `
            <div class="card-header">
                ${logoFrame.outerHTML}
                <div class="header-info">
                    <h3 class="experience-title">${escapeHtml(exp.title)}</h3>
                    ${companyHtml}
                    <p class="experience-date">${escapeHtml(period)}</p>
                </div>
            </div>
            <div class="card-tags">
                ${categoryBadge}
                ${statusBadge}
            </div>
            <details class="experience-details">
                <summary class="experience-summary">
                    <span>View Details</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                        <path d="m6 9 6 6 6-6"></path>
                    </svg>
                </summary>
                <div class="experience-desc">
                    ${formatDescription(exp.description)}
                </div>
            </details>
            <div class="resource-actions experience-actions">
                ${starHtml}
            </div>
        `;

        const actionsDiv = article.querySelector('.resource-actions');
        if (actionsDiv && resources?.actions) {
            const itemObj = { pk: exp.id, fields: exp };
            const mgmt = resources.actions(app, itemObj);
            if (mgmt && mgmt.children.length) {
                while (mgmt.firstChild) {
                    actionsDiv.appendChild(mgmt.firstChild);
                }
            }
        }

        wrapper.appendChild(article);
        return wrapper;
    }

    async function fetchExperiences(title = searchInput?.value.trim() || '', category = activeCategory) {
        activeRequest?.abort();
        activeRequest = new AbortController();
        const request = activeRequest;

        displaySection({ loading: true });

        const baseUrl = config.listUrl || '/api/v1/experiences/';
        const url = new URL(baseUrl, window.location.origin);
        if (title) url.searchParams.set('title', title);
        if (category && category.toLowerCase() !== 'all') {
            url.searchParams.set('category', category);
        }

        try {
            const response = await fetch(url.href, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
                signal: request.signal,
            });

            if (request !== activeRequest || request.signal.aborted) return;
            if (!response.ok) throw new Error(`Experience request failed (${response.status})`);

            const data = await response.json();
            if (request !== activeRequest || request.signal.aborted) return;
            if (!Array.isArray(data)) throw new Error('Data format invalid, expected an array.');

            const canonical = new URL('/experience/', window.location.origin);
            if (title) canonical.searchParams.set('title', title);
            if (category && category.toLowerCase() !== 'all') canonical.searchParams.set('category', category);
            if (window.PortfolioDesktop?.setQuery) {
                window.PortfolioDesktop.setQuery('experience', canonical.search);
            } else if (window.location.pathname.includes('/experience/')) {
                history.replaceState(history.state, '', canonical.pathname + canonical.search);
            }

            grid.replaceChildren();
            hasContent = data.length > 0;

            if (!data.length) {
                const filtered = Boolean(title || (category && category.toLowerCase() !== 'all'));
                const heading = emptyState?.querySelector('[data-empty-title]');
                const description = emptyState?.querySelector('[data-empty-description]');
                if (heading) {
                    heading.textContent = filtered ? 'Tidak ada pengalaman yang cocok' : 'Belum ada pengalaman';
                }
                if (description) {
                    description.textContent = filtered
                        ? 'Coba kata kunci lain atau tampilkan semua kategori.'
                        : 'Pengalaman akan tampil di sini setelah ditambahkan.';
                }
                const reset = emptyState?.querySelector('[data-experience-reset]');
                if (reset) reset.hidden = !filtered;
                displaySection({ empty: true });
                return;
            }

            data.forEach(item => {
                const card = buildExperienceCard(item);
                grid.appendChild(card);
            });
            displaySection({ grid: true });
        } catch (error) {
            if (error.name === 'AbortError' || request !== activeRequest) return;
            console.error('Error loading experiences:', error);
            displaySection({ error: true });
        }
    }

    const debounce = resources?.debounce || function (func, wait) {
        let timeout;
        const executedFunction = function (...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
        executedFunction.cancel = function () {
            clearTimeout(timeout);
        };
        return executedFunction;
    };

    const searchExperiences = debounce(() => fetchExperiences(), 300);

    searchInput?.addEventListener('input', () => {
        activeRequest?.abort();
        searchExperiences();
    });

    searchForm?.addEventListener('submit', event => {
        event.preventDefault();
        searchExperiences.cancel();
        fetchExperiences();
    });

    app.querySelector('[data-experience-retry]')?.addEventListener('click', async () => {
        searchExperiences.cancel();
        await fetchExperiences();
        if (errorState?.classList.contains('hide')) {
            searchInput?.focus({ preventScroll: true });
        }
    });

    app.querySelector('[data-experience-reset]')?.addEventListener('click', event => {
        event.preventDefault();
        if (searchInput) searchInput.value = '';
        setActiveCategory('all');
        searchInput?.focus({ preventScroll: true });
    });

    function setActiveCategory(category) {
        searchExperiences.cancel();
        activeCategory = category || 'all';
        const field = searchForm?.querySelector('[name="category"]');
        if (field) field.value = activeCategory;
        filters?.querySelectorAll('[data-filter]').forEach(button => {
            const isActive = button.dataset.filter.toLowerCase() === activeCategory.toLowerCase();
            button.classList.toggle('active', isActive);
            button.classList.toggle('project-filter-btn--inactive', !isActive);
            button.setAttribute('aria-pressed', String(isActive));
        });
        fetchExperiences();
    }

    filters?.addEventListener('click', event => {
        const button = event.target.closest('[data-filter]');
        if (button) {
            event.preventDefault();
            setActiveCategory(button.dataset.filter);
        }
    });

    // Star toggle handling (both form submit and button click delegation)
    grid?.addEventListener('submit', async event => {
        const form = event.target.closest('[data-experience-star-form], .star-form');
        if (!form) return;
        event.preventDefault();

        if (config.isAuthenticated !== 'true') {
            showToast('Perlu Login', 'Silakan login terlebih dahulu untuk memberi star.', 'warning');
            if (config.loginUrl) {
                window.location.assign(config.loginUrl);
            }
            return;
        }

        const button = form.querySelector('button[type="submit"], [data-action="star"]');
        const label = button?.querySelector('.star-label');
        const count = button?.querySelector('.star-count');
        if (!button || button.disabled) return;
        button.disabled = true;

        try {
            const csrfToken = ajax.getCsrfToken(form) || ajax.getCsrfToken();
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                },
            });

            if (response.redirected) {
                window.location.assign(response.url);
                return;
            }

            const data = await response.json().catch(() => null);
            if (!response.ok || !data) {
                throw new Error(`Star request failed (${response.status})`);
            }

            const isStarred = Boolean(data.is_starred);
            button.setAttribute('aria-pressed', String(isStarred));
            if (label) label.textContent = isStarred ? 'Unstar' : 'Star';
            if (count) count.textContent = data.star_count !== undefined ? data.star_count : (data.count || 0);
            button.title = data.starred_by_names
                ? `Dibintangi oleh ${data.starred_by_names}`
                : 'Jadilah yang pertama memberi star';

            showToast(
                'Berhasil',
                isStarred ? 'Star berhasil diberikan.' : 'Star berhasil dibatalkan.',
                'success'
            );
        } catch (error) {
            console.error('Error toggling star on experience:', error);
            showToast('Gagal memperbarui star', 'Permintaan gagal. Silakan coba lagi.', 'error');
        } finally {
            button.disabled = false;
        }
    });

    grid?.addEventListener('click', event => {
        const loginLink = event.target.closest('[data-action="star-login"]');
        if (loginLink && config.isAuthenticated !== 'true') {
            showToast('Perlu Login', 'Silakan login terlebih dahulu untuk memberi star.', 'warning');
        }
    });

    app.addEventListener('desktop:open', () => {
        if (!activated) {
            activated = true;
            fetchExperiences();
        }
    });

    app.addEventListener('desktop:query', event => {
        const query = new URLSearchParams(event.detail);
        if (searchInput) searchInput.value = query.get('title') || '';
        setActiveCategory(query.get('category') || 'all');
        activated = true;
    });

    async function writeExperience(url, method = 'POST', payload) {
        const response = await fetch(url, {
            method,
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': ajax.getCsrfToken(),
            },
            body: payload === undefined ? undefined : JSON.stringify(payload),
        });
        if (response.status === 204) return null;
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            const messages = Object.values(data).flat().filter(value => typeof value === 'string');
            throw new Error(messages.join(' ') || `Request failed (HTTP ${response.status}).`);
        }
        return data;
    }

    function experienceEndpoint(pattern, id) {
        return pattern
            .replace(experienceIdPlaceholder, id)
            .replace('__pk__', id);
    }

    window.writeExperience = writeExperience;
    window.experienceEndpoint = experienceEndpoint;
    window.fetchExperiences = fetchExperiences;

    if (app.classList.contains('is-open') || !document.body.classList.contains('desktop-page')) {
        activated = true;
        fetchExperiences();
    }
    window.addEventListener('load', () => {
        if (app.classList.contains('is-open') && !activated) {
            activated = true;
            fetchExperiences();
        }
    });
})();
