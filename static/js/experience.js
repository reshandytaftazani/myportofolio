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

    // Dialog & Form elements for CRUD
    const dialog = document.getElementById('experience-dialog') || app.querySelector('#experience-dialog');
    const form = document.getElementById('experience-modal-form') || dialog?.querySelector('form');
    const formTitle = dialog?.querySelector('[data-dialog-title]');
    const formSubtitle = dialog?.querySelector('[data-dialog-subtitle]');
    const formIcon = dialog?.querySelector('[data-dialog-icon]');
    const submitBtn = dialog?.querySelector('[data-submit-button]');
    const submitLabel = dialog?.querySelector('[data-submit-label]');
    const formError = dialog?.querySelector('[data-form-error]');

    const deleteDialog = document.getElementById('experience-delete-dialog') || app.querySelector('#experience-delete-dialog');
    const deleteLabel = deleteDialog?.querySelector('[data-delete-label]');
    const deleteConfirmBtn = deleteDialog?.querySelector('[data-confirm-delete]');
    const deleteSubmitLabel = deleteDialog?.querySelector('[data-delete-submit-label]');
    const deleteError = deleteDialog?.querySelector('[data-delete-error]');

    let activeCategory = config.initialCategory || 'all';
    let searchAbortController = null;
    let currentExperiences = [];
    let activated = false;
    let hasContent = Boolean(grid?.querySelector('.timeline-card, .exp-timeline-item'));
    const experienceIdPlaceholder = '00000000-0000-0000-0000-000000000000';

    function updateMetrics(items = currentExperiences) {
        const list = Array.isArray(items) ? items : [];
        const total = list.length;
        let ongoing = 0;
        let completed = 0;
        let stars = 0;

        for (const item of list) {
            if (item.is_ongoing) {
                ongoing += 1;
            } else {
                completed += 1;
            }
            stars += (Number(item.star_count) || 0);
        }

        const totalEl = document.getElementById('metric-total-roles');
        const ongoingEl = document.getElementById('metric-ongoing-roles');
        const completedEl = document.getElementById('metric-completed-roles');
        const starsEl = document.getElementById('metric-total-stars');

        if (totalEl) totalEl.textContent = String(total);
        if (ongoingEl) ongoingEl.textContent = String(ongoing);
        if (completedEl) completedEl.textContent = String(completed);
        if (starsEl) starsEl.textContent = String(stars);
    }

    let modalOpener = null;
    let deleteOpener = null;
    let pendingDeleteId = null;
    let isSaving = false;
    let isDeleting = false;

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

    function experienceEndpoint(pattern, id) {
        return pattern
            .replace(experienceIdPlaceholder, encodeURIComponent(id))
            .replace('__pk__', encodeURIComponent(id));
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
        const starUrl = experienceEndpoint(starUrlTemplate, exp.id);

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
        const canEdit = config.canEdit === 'true' || config.isEditor === 'true' || config.isSuperuser === 'true';
        const canDelete = config.canDelete === 'true' || config.isSuperuser === 'true';

        if (actionsDiv && (canEdit || canDelete)) {
            const mgmtGroup = document.createElement('div');
            mgmtGroup.className = 'resource-actions exp-card-mgmt-actions';
            mgmtGroup.setAttribute('role', 'group');
            mgmtGroup.setAttribute('aria-label', `Kelola ${exp.title}`);

            if (canEdit) {
                const editBtn = document.createElement('button');
                editBtn.type = 'button';
                editBtn.className = 'button resource-action resource-action--edit';
                editBtn.dataset.resourceAction = 'edit';
                editBtn.dataset.pk = exp.id;
                editBtn.dataset.label = exp.title;
                editBtn.setAttribute('aria-label', `Edit ${exp.title}`);
                editBtn.innerHTML = `
                    <svg class="resource-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L9 17l-4 1 1-4Z"/>
                    </svg>
                    <span class="resource-action__label">Edit</span>
                `;
                mgmtGroup.appendChild(editBtn);
            }

            if (canDelete) {
                const deleteBtn = document.createElement('button');
                deleteBtn.type = 'button';
                deleteBtn.className = 'button resource-action resource-action--delete';
                deleteBtn.dataset.resourceAction = 'delete';
                deleteBtn.dataset.pk = exp.id;
                deleteBtn.dataset.label = exp.title;
                deleteBtn.setAttribute('aria-label', `Hapus ${exp.title}`);
                deleteBtn.innerHTML = `
                    <svg class="resource-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6"/>
                    </svg>
                    <span class="resource-action__label">Hapus</span>
                `;
                mgmtGroup.appendChild(deleteBtn);
            }

            actionsDiv.appendChild(mgmtGroup);
        }

        wrapper.appendChild(article);
        return wrapper;
    }

    async function fetchExperiences(title = searchInput?.value.trim() || '', category = activeCategory) {
        if (searchAbortController) {
            searchAbortController.abort();
        }
        searchAbortController = new AbortController();
        const request = searchAbortController;

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

            if (request !== searchAbortController || request.signal.aborted) return;
            if (!response.ok) throw new Error(`Experience request failed (${response.status})`);

            const data = await response.json();
            if (request !== searchAbortController || request.signal.aborted) return;
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
                currentExperiences = [];
                updateMetrics(currentExperiences);

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

            currentExperiences = data.map(adaptExperience);
            data.forEach(item => {
                const card = buildExperienceCard(item);
                grid.appendChild(card);
            });
            updateMetrics(currentExperiences);
            displaySection({ grid: true });
        } catch (error) {
            if (error.name === 'AbortError' || request !== searchAbortController) return;
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
        if (searchAbortController) {
            searchAbortController.abort();
        }
        searchExperiences();
    });

    searchForm?.addEventListener('submit', event => {
        event.preventDefault();
        searchExperiences.cancel();
        if (searchAbortController) {
            searchAbortController.abort();
        }
        fetchExperiences();
    });

    app.querySelector('[data-experience-retry]')?.addEventListener('click', async () => {
        searchExperiences.cancel();
        if (searchAbortController) {
            searchAbortController.abort();
        }
        await fetchExperiences();
        if (errorState?.classList.contains('hide')) {
            const target = grid?.classList.contains('hide') ? emptyState : grid;
            target?.setAttribute('tabindex', '-1');
            target?.focus({ preventScroll: true });
        }
    });

    app.querySelector('[data-experience-reset]')?.addEventListener('click', event => {
        event.preventDefault();
        searchExperiences.cancel();
        if (searchAbortController) {
            searchAbortController.abort();
        }
        if (searchInput) searchInput.value = '';
        setActiveCategory('all');
        searchInput?.focus({ preventScroll: true });
    });

    function setActiveCategory(category) {
        searchExperiences.cancel();
        if (searchAbortController) {
            searchAbortController.abort();
        }
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

    // Star toggle handling (Optimistic UI Update with Auto-Rollback)
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
        if (!button || button.dataset.starBusy === 'true') return;

        // Find corresponding experience item in memory
        const expId = button.dataset.id || form.closest('.exp-timeline-item, .timeline-card')?.dataset.id;
        const expItem = currentExperiences.find(item => String(item.id) === String(expId));

        // 1. Snapshot previous UI & state for rollback
        const prevIsStarred = button.getAttribute('aria-pressed') === 'true';
        const prevCountText = count ? count.textContent : '0';
        const prevCount = parseInt(prevCountText, 10) || 0;
        const prevLabel = label ? label.textContent : (prevIsStarred ? 'Unstar' : 'Star');
        const prevTitle = button.title || '';
        const prevItemStarred = expItem ? expItem.is_starred : prevIsStarred;
        const prevItemCount = expItem ? expItem.star_count : prevCount;

        // 2. Compute optimistic target state (0ms instant response)
        const nextIsStarred = !prevIsStarred;
        const nextCount = Math.max(0, prevCount + (nextIsStarred ? 1 : -1));

        // Lock button interaction during in-flight request
        button.dataset.starBusy = 'true';

        // 3. Immediately apply Optimistic UI update
        button.setAttribute('aria-pressed', String(nextIsStarred));
        if (label) label.textContent = nextIsStarred ? 'Unstar' : 'Star';
        if (count) count.textContent = String(nextCount);
        button.title = nextIsStarred ? 'Anda membintangi pengalaman ini' : 'Beri star untuk pengalaman ini';

        // Update in-memory state and live summary metrics bar
        if (expItem) {
            expItem.is_starred = nextIsStarred;
            expItem.star_count = nextCount;
        }
        updateMetrics(currentExperiences);

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

            // 4. Server confirmed: synchronize with authoritative server values
            const serverIsStarred = Boolean(data.is_starred);
            const serverCount = data.star_count !== undefined ? data.star_count : (data.count || nextCount);

            button.setAttribute('aria-pressed', String(serverIsStarred));
            if (label) label.textContent = serverIsStarred ? 'Unstar' : 'Star';
            if (count) count.textContent = String(serverCount);
            button.title = data.starred_by_names
                ? `Dibintangi oleh ${data.starred_by_names}`
                : 'Jadilah yang pertama memberi star';

            if (expItem) {
                expItem.is_starred = serverIsStarred;
                expItem.star_count = serverCount;
                if (data.starred_by_names !== undefined) {
                    expItem.starred_by_names = data.starred_by_names;
                }
            }
            updateMetrics(currentExperiences);

            showToast(
                'Berhasil',
                serverIsStarred ? 'Star berhasil diberikan.' : 'Star berhasil dibatalkan.',
                'success'
            );
        } catch (error) {
            console.error('Error toggling star on experience (rolling back):', error);

            // 5. AUTO-ROLLBACK: Revert immediately to original snapshot values
            button.setAttribute('aria-pressed', String(prevIsStarred));
            if (label) label.textContent = prevLabel;
            if (count) count.textContent = String(prevCount);
            button.title = prevTitle;

            if (expItem) {
                expItem.is_starred = prevItemStarred;
                expItem.star_count = prevItemCount;
            }
            updateMetrics(currentExperiences);

            showToast('Gagal memperbarui star', 'Permintaan gagal. Perubahan dibatalkan.', 'error');
        } finally {
            button.dataset.starBusy = 'false';
        }
    });

    grid?.addEventListener('click', event => {
        const loginLink = event.target.closest('[data-action="star-login"]');
        if (loginLink && config.isAuthenticated !== 'true') {
            showToast('Perlu Login', 'Silakan login terlebih dahulu untuk memberi star.', 'warning');
        }
    });

    // -------------------------------------------------------------
    // MODAL FORM CRUD & TOAST ERROR HANDLING (TAHAP 4)
    // -------------------------------------------------------------

    function resetModalErrors() {
        if (formError) {
            formError.textContent = '';
            formError.hidden = true;
        }
        dialog?.querySelectorAll('[data-field-error]').forEach(el => {
            el.textContent = '';
            el.hidden = true;
        });
        form?.querySelectorAll('[aria-invalid]').forEach(el => {
            el.removeAttribute('aria-invalid');
            const describedBy = (el.getAttribute('aria-describedby') || '')
                .split(/\s+/)
                .filter(id => !id.endsWith('-error'))
                .join(' ');
            if (describedBy) {
                el.setAttribute('aria-describedby', describedBy);
            } else {
                el.removeAttribute('aria-describedby');
            }
        });
    }

    function handleValidationErrors(errorData) {
        let firstInvalidField = null;
        const generalErrors = [];

        for (const [key, val] of Object.entries(errorData || {})) {
            const messageText = Array.isArray(val) ? val.join(' ') : String(val);
            const field = form?.querySelector(`[name="${key}"]`);
            const inlineError = dialog?.querySelector(`[data-field-error="${key}"]`);

            if (field && inlineError) {
                inlineError.textContent = messageText;
                inlineError.hidden = false;
                field.setAttribute('aria-invalid', 'true');
                if (inlineError.id) {
                    const existing = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
                    if (!existing.includes(inlineError.id)) {
                        existing.push(inlineError.id);
                    }
                    field.setAttribute('aria-describedby', existing.join(' '));
                }
                if (!firstInvalidField) firstInvalidField = field;
            } else {
                generalErrors.push(`${key}: ${messageText}`);
            }
        }

        if (generalErrors.length && formError) {
            formError.textContent = generalErrors.join(' | ');
            formError.hidden = false;
        }

        if (firstInvalidField) {
            firstInvalidField.focus({ preventScroll: true });
        }
    }

    function showInlineError(fieldName, messageText) {
        const field = form?.querySelector(`[name="${fieldName}"]`);
        const inlineError = dialog?.querySelector(`[data-field-error="${fieldName}"]`);
        if (inlineError) {
            inlineError.textContent = messageText;
            inlineError.hidden = false;
        }
        if (field) {
            field.setAttribute('aria-invalid', 'true');
            if (inlineError && inlineError.id) {
                const existing = (field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
                if (!existing.includes(inlineError.id)) {
                    existing.push(inlineError.id);
                }
                field.setAttribute('aria-describedby', existing.join(' '));
            }
            field.focus({ preventScroll: true });
        }
    }

    function setSavingState(busy) {
        isSaving = busy;
        dialog?.querySelectorAll('button').forEach(btn => {
            btn.disabled = busy;
        });
        form?.setAttribute('aria-busy', String(busy));
        const spinner = submitBtn?.querySelector('.resource-spinner');
        if (spinner) spinner.style.display = busy ? 'inline-block' : 'none';

        const id = form?.querySelector('#experience-form-id')?.value;
        if (submitLabel) {
            submitLabel.textContent = busy
                ? 'Menyimpan...'
                : (id ? 'Perbarui Pengalaman' : 'Simpan Pengalaman');
        }
    }

    function setDeletingState(busy) {
        isDeleting = busy;
        deleteDialog?.querySelectorAll('button').forEach(btn => {
            btn.disabled = busy;
        });
        deleteDialog?.setAttribute('aria-busy', String(busy));
        const spinner = deleteConfirmBtn?.querySelector('.resource-spinner');
        if (spinner) spinner.style.display = busy ? 'inline-block' : 'none';

        if (deleteSubmitLabel) {
            deleteSubmitLabel.textContent = busy ? 'Menghapus...' : 'Ya, hapus data';
        }
    }

    function openCreateModal(opener) {
        if (!dialog || !form) return;
        if (config.isSuperuser !== 'true') {
            showToast('Aksi ditolak', 'Hanya Pemilik Portofolio yang dapat menambahkan pengalaman.', 'error');
            return;
        }

        modalOpener = opener;
        form.reset();
        const idField = form.querySelector('#experience-form-id');
        if (idField) idField.value = '';

        if (formTitle) formTitle.textContent = 'Tambah Pengalaman';
        if (formSubtitle) formSubtitle.textContent = 'Lengkapi informasi untuk ditampilkan di portofolio.';
        if (submitLabel) submitLabel.textContent = 'Simpan Pengalaman';

        if (formIcon) {
            formIcon.innerHTML = '<svg class="resource-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>';
        }

        resetModalErrors();
        dialog.showModal();
        form.querySelector('#exp-field-title')?.focus({ preventScroll: true });
    }

    async function openEditModal(pk, opener) {
        if (!dialog || !form) return;
        const canEdit = config.canEdit === 'true' || config.isEditor === 'true' || config.isSuperuser === 'true';
        if (!canEdit) {
            showToast('Aksi ditolak', 'Anda tidak memiliki izin untuk mengedit pengalaman.', 'error');
            return;
        }

        modalOpener = opener;
        if (opener) opener.disabled = true;

        const detailUrlTemplate = config.detailUrlTemplate || '/api/v1/experiences/__pk__/';
        const detailUrl = experienceEndpoint(detailUrlTemplate, pk);

        try {
            const response = await fetch(detailUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                },
            });

            if (response.status === 404) {
                showToast('Tidak ditemukan', 'Data pengalaman tidak ditemukan atau sudah dihapus.', 'error');
                return;
            }
            if (response.status === 403) {
                showToast('Aksi ditolak', 'Aksi ditolak: Anda tidak memiliki izin untuk melakukan tindakan ini.', 'error');
                return;
            }
            if (!response.ok) {
                throw new Error(`Detail request failed (${response.status})`);
            }

            const data = await response.json();
            form.reset();

            const idField = form.querySelector('#experience-form-id');
            if (idField) idField.value = data.id || pk;

            const titleField = form.querySelector('#exp-field-title');
            if (titleField) titleField.value = data.title || '';

            const companyField = form.querySelector('#exp-field-company');
            if (companyField) companyField.value = data.company || '';

            const categoryField = form.querySelector('#exp-field-category');
            if (categoryField) categoryField.value = data.category || 'full-time';

            const thumbField = form.querySelector('#exp-field-thumbnail');
            if (thumbField) thumbField.value = data.thumbnail || '';

            const startField = form.querySelector('#exp-field-started_at');
            if (startField) startField.value = data.started_at || '';

            const endField = form.querySelector('#exp-field-ended_at');
            if (endField) endField.value = data.ended_at || '';

            const descField = form.querySelector('#exp-field-description');
            if (descField) descField.value = data.description || '';

            if (formTitle) formTitle.textContent = 'Edit Pengalaman';
            if (formSubtitle) formSubtitle.textContent = 'Perbarui informasi agar portofolio tetap relevan.';
            if (submitLabel) submitLabel.textContent = 'Perbarui Pengalaman';

            if (formIcon) {
                formIcon.innerHTML = '<svg class="resource-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L9 17l-4 1 1-4Z"/></svg>';
            }

            resetModalErrors();
            dialog.showModal();
            titleField?.focus({ preventScroll: true });
        } catch (error) {
            console.error('Error opening edit modal for experience:', error);
            showToast('Gagal memuat formulir', 'Terjadi kesalahan saat memuat data pengalaman.', 'error');
        } finally {
            if (opener) opener.disabled = false;
        }
    }

    function openDeleteModal(pk, label, opener) {
        if (!deleteDialog) return;
        if (config.isSuperuser !== 'true') {
            showToast('Aksi ditolak', 'Hanya Pemilik Portofolio yang dapat menghapus pengalaman.', 'error');
            return;
        }

        deleteOpener = opener;
        pendingDeleteId = pk;

        if (deleteLabel) {
            deleteLabel.textContent = label || 'Pengalaman';
        }
        if (deleteError) {
            deleteError.textContent = '';
            deleteError.hidden = true;
        }

        deleteDialog.showModal();
    }

    // Live validation error clearing on input
    form?.addEventListener('input', event => {
        const field = event.target;
        if (!field.hasAttribute('aria-invalid')) return;
        field.removeAttribute('aria-invalid');
        const inlineError = dialog?.querySelector(`[data-field-error="${field.name}"]`);
        if (inlineError) {
            inlineError.textContent = '';
            inlineError.hidden = true;
        }
        const describedBy = (field.getAttribute('aria-describedby') || '')
            .split(/\s+/)
            .filter(id => !id.endsWith('-error'))
            .join(' ');
        if (describedBy) {
            field.setAttribute('aria-describedby', describedBy);
        } else {
            field.removeAttribute('aria-describedby');
        }
        if (!form.querySelector('[aria-invalid]')) {
            resetModalErrors();
        }
    });

    // Modal submit handler (POST create / PATCH update)
    form?.addEventListener('submit', async event => {
        event.preventDefault();
        if (isSaving) return;

        resetModalErrors();

        const idField = form.querySelector('#experience-form-id');
        const id = idField?.value.trim() || '';
        const isEdit = Boolean(id);

        const title = form.querySelector('#exp-field-title')?.value.trim() || '';
        const company = form.querySelector('#exp-field-company')?.value.trim() || null;
        const category = form.querySelector('#exp-field-category')?.value || 'full-time';
        const thumbnail = form.querySelector('#exp-field-thumbnail')?.value.trim() || null;
        const startedAt = form.querySelector('#exp-field-started_at')?.value || null;
        const endedAt = form.querySelector('#exp-field-ended_at')?.value || null;
        const description = form.querySelector('#exp-field-description')?.value.trim() || '';

        // Client-side quick check
        let hasClientError = false;
        if (!title) {
            showInlineError('title', 'Posisi / Peran tidak boleh kosong.');
            hasClientError = true;
        }
        if (!description) {
            showInlineError('description', 'Deskripsi tidak boleh kosong.');
            hasClientError = true;
        }
        if (startedAt && endedAt && endedAt < startedAt) {
            showInlineError('ended_at', 'Tanggal selesai tidak boleh lebih awal dari tanggal mulai.');
            hasClientError = true;
        }
        if (hasClientError) return;

        const payload = {
            title,
            company,
            category,
            thumbnail,
            started_at: startedAt,
            ended_at: endedAt,
            description,
        };

        const listUrl = config.listUrl || '/api/v1/experiences/';
        const detailUrlTemplate = config.detailUrlTemplate || '/api/v1/experiences/__pk__/';
        const url = isEdit ? experienceEndpoint(detailUrlTemplate, id) : listUrl;
        const method = isEdit ? 'PATCH' : 'POST';

        setSavingState(true);
        try {
            const csrfToken = ajax.getCsrfToken(form) || ajax.getCsrfToken();
            const response = await fetch(url, {
                method,
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(payload),
            });

            if (response.status === 201 || response.status === 200) {
                dialog.close();
                showToast(
                    'Berhasil',
                    isEdit ? 'Pengalaman berhasil diperbarui!' : 'Pengalaman baru berhasil ditambahkan!',
                    'success'
                );
                await fetchExperiences();
                return;
            }

            if (response.status === 400) {
                const errorData = await response.json().catch(() => ({}));
                handleValidationErrors(errorData);

                const messages = [];
                for (const [key, val] of Object.entries(errorData)) {
                    const msg = Array.isArray(val) ? val.join(' ') : String(val);
                    messages.push(`${key}: ${msg}`);
                }
                showToast('Gagal menyimpan', messages.join(' | ') || 'Mohon periksa kolom yang ditandai.', 'error');
                return;
            }

            if (response.status === 403) {
                const errorMsg = 'Aksi ditolak: Anda tidak memiliki izin untuk melakukan tindakan ini.';
                if (formError) {
                    formError.textContent = errorMsg;
                    formError.hidden = false;
                }
                showToast('Aksi ditolak', errorMsg, 'error');
                return;
            }

            throw new Error(`Server returned HTTP ${response.status}`);
        } catch (error) {
            console.error('Error saving experience:', error);
            if (formError) {
                formError.textContent = 'Tidak dapat terhubung ke server. Silakan coba lagi.';
                formError.hidden = false;
            }
            showToast('Kesalahan Server', 'Terjadi kesalahan pada server. Silakan coba lagi nanti.', 'error');
        } finally {
            setSavingState(false);
        }
    });

    // Delete confirmation handler (DELETE /api/v1/experiences/<id>/)
    deleteConfirmBtn?.addEventListener('click', async () => {
        if (!pendingDeleteId || isDeleting) return;
        const pk = pendingDeleteId;
        setDeletingState(true);

        const detailUrlTemplate = config.detailUrlTemplate || '/api/v1/experiences/__pk__/';
        const deleteUrl = experienceEndpoint(detailUrlTemplate, pk);

        try {
            const csrfToken = ajax.getCsrfToken() || ajax.getCsrfToken(form);
            const response = await fetch(deleteUrl, {
                method: 'DELETE',
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
            });

            if (response.status === 204 || response.status === 200) {
                pendingDeleteId = null;
                deleteDialog.close();
                showToast('Berhasil', 'Pengalaman berhasil dihapus!', 'success');
                await fetchExperiences();
                return;
            }

            if (response.status === 403) {
                const errorMsg = 'Aksi ditolak: Anda tidak memiliki izin untuk menghapus pengalaman ini.';
                if (deleteError) {
                    deleteError.textContent = errorMsg;
                    deleteError.hidden = false;
                }
                showToast('Aksi ditolak', errorMsg, 'error');
                return;
            }

            throw new Error(`Delete failed (HTTP ${response.status})`);
        } catch (error) {
            console.error('Error deleting experience:', error);
            if (deleteError) {
                deleteError.textContent = 'Gagal menghapus pengalaman. Silakan coba lagi.';
                deleteError.hidden = false;
            }
            showToast('Gagal Menghapus', 'Terjadi kesalahan saat menghapus data.', 'error');
        } finally {
            setDeletingState(false);
        }
    });

    // Modal dialog close & cancel handlers
    dialog?.querySelectorAll('[data-close-dialog]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!isSaving) dialog.close();
        });
    });
    dialog?.addEventListener('cancel', event => {
        if (isSaving) event.preventDefault();
    });
    dialog?.addEventListener('close', () => {
        if (modalOpener?.isConnected) {
            modalOpener.focus({ preventScroll: true });
        }
    });

    deleteDialog?.querySelectorAll('[data-close-delete]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!isDeleting) {
                pendingDeleteId = null;
                deleteDialog.close();
            }
        });
    });
    deleteDialog?.addEventListener('cancel', event => {
        if (isDeleting) event.preventDefault();
        else pendingDeleteId = null;
    });
    deleteDialog?.addEventListener('close', () => {
        if (deleteOpener?.isConnected) {
            deleteOpener.focus({ preventScroll: true });
        }
    });

    // Modal focus trap for Tab key
    [dialog, deleteDialog].forEach(modal => {
        modal?.addEventListener('keydown', event => {
            if (event.key !== 'Tab' || event.defaultPrevented) return;
            const focusables = [...modal.querySelectorAll('a[href], button, input, textarea, select, [tabindex]')]
                .filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length);
            const first = focusables[0];
            const last = focusables.at(-1);
            if (!first) {
                event.preventDefault();
                return;
            }
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        });
    });

    // Click event delegation for Create, Edit, and Delete triggers
    app.querySelector('[data-open-create]')?.addEventListener('click', event => {
        event.preventDefault();
        openCreateModal(event.currentTarget);
    });

    app.addEventListener('click', event => {
        const btn = event.target.closest('[data-resource-action]');
        if (!btn || btn.disabled) return;
        const action = btn.dataset.resourceAction;
        const pk = btn.dataset.pk;
        const label = btn.dataset.label;

        if (action === 'edit') {
            event.preventDefault();
            openEditModal(pk, btn);
        } else if (action === 'delete') {
            event.preventDefault();
            openDeleteModal(pk, label, btn);
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

    window.writeExperience = writeExperience;
    window.experienceEndpoint = experienceEndpoint;
    window.fetchExperiences = fetchExperiences;
    window.updateExperienceMetrics = updateMetrics;

    if (app.classList.contains('is-open') || !document.body.classList.contains('desktop-page')) {
        activated = true;
        fetchExperiences();
    }
    window.addEventListener('load', () => {
        if (!activated && (app.classList.contains('is-open') || !document.body.hasAttribute('data-desktop-ready'))) {
            activated = true;
            fetchExperiences();
        }
    });
})();
