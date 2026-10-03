(function (window) {
    const ajax = window.PortfolioAjax;
    if (!ajax) return;
    const createdTags = new Map();

    function node(tag, className = '', text) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text ?? '';
        return element;
    }

    function httpUrl(value) {
        if (!value) return '';
        try {
            const url = new URL(value);
            return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
        } catch (_) { return ''; }
    }

    function debounce(callback, delay = 300) {
        let timer;
        const run = (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => callback(...args), delay);
        };
        run.cancel = () => clearTimeout(timer);
        return run;
    }

    function message(data, fallback) {
        return ajax.validationMessages(data?.errors).join(' ') || data?.message || fallback;
    }

    function notify(title, text, type = 'error') {
        window.showToast?.(title, text, type);
    }

    function icon(name) {
        const paths = {
            plus: 'M12 5v14M5 12h14',
            edit: 'M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L9 17l-4 1 1-4Z',
            delete: 'M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6',
            check: 'm20 6-11 12-5-5',
        };
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'resource-icon');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('stroke-width', '1.8');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('focusable', 'false');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', paths[name]);
        svg.append(path);
        return svg;
    }

    function actions(root, item) {
        const group = node('div', 'resource-actions');
        const label = item.fields.title || item.fields.school_name || item.fields.name;
        group.setAttribute('role', 'group');
        group.setAttribute('aria-label', `Kelola ${label}`);
        for (const [action, text, allowed] of [
            ['edit', 'Edit', root.dataset.canEdit === 'true'],
            ['delete', 'Hapus', root.dataset.canDelete === 'true'],
        ]) {
            if (!allowed) continue;
            const button = node('button', `button resource-action resource-action--${action}`);
            button.append(icon(action), node('span', 'resource-action__label', text));
            button.type = 'button';
            button.setAttribute('aria-label', `${text} ${label}`);
            button.dataset.resourceAction = action;
            button.dataset.pk = item.pk;
            button.dataset.label = label;
            group.append(button);
        }
        group.hidden = !group.childElementCount;
        return group;
    }

    function bindManagement(root, refresh) {
        const config = root.dataset;
        const dialog = document.getElementById(`${config.resource}-dialog`);
        const form = dialog?.querySelector('[data-resource-form]');
        const fields = form?.querySelector('[data-form-fields]');
        const initialFields = fields?.innerHTML;
        const title = dialog?.querySelector('[data-dialog-title]');
        const subtitle = dialog?.querySelector('[data-dialog-subtitle]');
        const dialogIcon = dialog?.querySelector('[data-dialog-icon]');
        const feedback = form?.querySelector('[data-form-error]');
        const saveButton = form?.querySelector('[type=submit]');
        const saveLabel = saveButton?.querySelector('[data-submit-label]');
        const label = config.resourceLabel || config.resource;
        const deleteDialog = document.getElementById(`${config.resource}-delete-dialog`);
        const deleteFeedback = deleteDialog?.querySelector('[data-delete-error]');
        const deleteLabel = deleteDialog?.querySelector('[data-delete-submit-label]');
        let saving = false;
        let deleting = false;
        let pendingDeletion;
        let submitLabel = 'Tambah data';
        let editingSequence = 0;
        let editRequest;
        let tagRequest;
        let tagSequence = 0;
        const endpoint = (pattern, pk) => pattern.replace('__pk__', encodeURIComponent(pk));

        function resetError() {
            if (feedback) { feedback.textContent = ''; feedback.hidden = true; }
            fields?.querySelectorAll('[data-field-error]').forEach(error => {
                error.textContent = ''; error.hidden = true;
            });
            fields?.querySelectorAll('[aria-invalid]').forEach(field => field.removeAttribute('aria-invalid'));
        }

        function prepareFields() {
            fields?.querySelectorAll('input, textarea, select').forEach(field => {
                const group = field.closest('.form-group');
                if (!group) return;
                const ids = [...group.querySelectorAll('.resource-field-help, [data-field-error]')]
                    .map(element => element.id).filter(Boolean);
                const existing = field.getAttribute('aria-describedby')?.split(/\s+/) || [];
                field.setAttribute('aria-describedby', [...new Set([...existing, ...ids])].join(' '));
            });
            setupTagPicker();
        }

        function setupTagPicker() {
            const picker = fields?.querySelector('[data-tag-picker]');
            const select = picker?.querySelector('select[name=tags]');
            const choices = picker?.querySelector('[data-tag-choices]');
            if (!select || !choices) return;
            const status = picker.querySelector('[data-tag-status]');
            const toggle = picker.querySelector('[data-open-tag]');
            const creator = picker.querySelector('[data-tag-creator]');
            const nameInput = picker.querySelector('[data-tag-name]');
            const colorInput = picker.querySelector('[data-tag-color]');
            const tagError = picker.querySelector('[data-tag-error]');
            const createButton = picker.querySelector('[data-save-tag]');
            let tagSaving = false;
            let catalog = new Map([...select.options].map(option => [option.value, {
                pk: option.value, fields: { name: option.textContent, color: '#3b82f6' },
            }]));

            function updateChoices(items) {
                const selected = new Set([...select.selectedOptions].map(option => option.value));
                const focused = choices.contains(document.activeElement) ? document.activeElement.dataset.tagPk : null;
                catalog = new Map(items.map(item => [String(item.pk), item]));
                for (const [pk, item] of createdTags) catalog.set(pk, item);
                const sorted = [...catalog.values()].sort((left, right) =>
                    left.fields.name.localeCompare(right.fields.name));
                select.replaceChildren(...sorted.map(item => new Option(item.fields.name, String(item.pk),
                    false, selected.has(String(item.pk)))));
                choices.replaceChildren();
                for (const item of sorted) {
                    const pk = String(item.pk);
                    const button = node('button', 'resource-tag-chip');
                    button.type = 'button';
                    button.dataset.tagPk = pk;
                    button.setAttribute('aria-pressed', String(selected.has(pk)));
                    const color = /^#[0-9a-f]{6}$/i.test(item.fields.color) ? item.fields.color : '#3b82f6';
                    button.style.setProperty('--tag-color', color);
                    const dot = node('span', 'resource-tag-chip__dot');
                    dot.setAttribute('aria-hidden', 'true');
                    const check = icon('check');
                    check.classList.add('resource-tag-chip__check');
                    button.append(dot, node('span', '', item.fields.name), check);
                    button.disabled = saving;
                    button.addEventListener('click', () => {
                        const option = [...select.options].find(option => option.value === pk);
                        option.selected = !option.selected;
                        button.setAttribute('aria-pressed', String(option.selected));
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                    });
                    choices.append(button);
                    if (pk === focused) button.focus({ preventScroll: true });
                }
                status.textContent = sorted.length ? '' : 'Belum ada tag tersedia.';
                status.hidden = Boolean(sorted.length);
            }

            function resetTagError() {
                if (!tagError) return;
                tagError.textContent = '';
                tagError.hidden = true;
                nameInput.removeAttribute('aria-invalid');
            }

            function closeCreator() {
                if (!creator || tagSaving) return;
                creator.hidden = true;
                toggle.setAttribute('aria-expanded', 'false');
                nameInput.value = '';
                colorInput.value = '#3b82f6';
                resetTagError();
            }

            select.hidden = true;
            choices.hidden = false;
            updateChoices([...catalog.values()]);
            if (toggle) {
                toggle.hidden = false;
                toggle.addEventListener('click', () => {
                    if (!creator.hidden) { closeCreator(); return; }
                    creator.hidden = false;
                    toggle.setAttribute('aria-expanded', 'true');
                    resetTagError();
                    nameInput.focus();
                });
                picker.querySelector('[data-cancel-tag]').addEventListener('click', () => {
                    closeCreator(); toggle.focus();
                });
                nameInput.addEventListener('input', resetTagError);
            }

            async function createTag() {
                if (saving || tagSaving) return;
                resetTagError();
                const name = nameInput.value.trim();
                if (!name) {
                    tagError.textContent = 'Masukkan nama tag terlebih dahulu.';
                    tagError.hidden = false;
                    nameInput.setAttribute('aria-invalid', 'true');
                    nameInput.focus();
                    return;
                }
                tagSaving = true;
                setBusy(true, 'Menyimpan tag...');
                creator.setAttribute('aria-busy', 'true');
                nameInput.disabled = true;
                colorInput.disabled = true;
                createButton.textContent = 'Membuat tag...';
                const payload = new FormData();
                payload.set('name', name);
                payload.set('color', colorInput.value);
                try {
                    const { response, data } = await ajax.fetchJson(picker.dataset.tagCreateUrl, {
                        method: 'POST', headers: { 'X-CSRFToken': ajax.getCsrfToken(form) }, body: payload,
                    });
                    if (!response.ok || !data?.item?.fields) {
                        throw new Error(message(data, 'Tag tidak dapat dibuat. Silakan coba lagi.'));
                    }
                    const item = data.item;
                    const pk = String(item.pk);
                    createdTags.set(pk, item);
                    updateChoices([...catalog.values()]);
                    const option = [...select.options].find(option => option.value === pk);
                    option.selected = true;
                    select.dispatchEvent(new Event('input', { bubbles: true }));
                    updateChoices([...catalog.values()]);
                    tagSaving = false;
                    closeCreator();
                    status.textContent = `Tag "${item.fields.name}" dipilih. Simpan proyek untuk menerapkannya.`;
                    status.hidden = false;
                    notify('Tag siap digunakan', data.message, 'success');
                } catch (error) {
                    tagError.textContent = error.message;
                    tagError.hidden = false;
                } finally {
                    tagSaving = false;
                    nameInput.disabled = false;
                    colorInput.disabled = false;
                    creator.setAttribute('aria-busy', 'false');
                    createButton.textContent = 'Buat & pilih tag';
                    setBusy(false);
                }
                if (creator.hidden) toggle.focus();
                else nameInput.focus();
            }

            createButton?.addEventListener('click', createTag);
            nameInput?.addEventListener('keydown', event => {
                if (event.key === 'Enter') { event.preventDefault(); createTag(); }
            });

            tagRequest?.abort();
            const current = ++tagSequence;
            const request = new AbortController();
            tagRequest = request;
            ajax.fetchJson(picker.dataset.tagListUrl, { signal: request.signal }).then(({ response, data }) => {
                if (current !== tagSequence || !picker.isConnected) return;
                if (!response.ok || !Array.isArray(data)) throw new Error('Invalid tag list');
                updateChoices(data);
            }).catch(error => {
                if (error.name === 'AbortError' || current !== tagSequence || !picker.isConnected) return;
                status.textContent = 'Daftar tag belum dapat diperbarui. Pilihan yang sudah dimuat tetap bisa digunakan.';
                status.hidden = false;
            });
        }

        function validationError(data, fallback) {
            let firstInvalid;
            const general = [];
            for (const [name, errors] of Object.entries(data?.errors || {})) {
                const field = [...fields.querySelectorAll('[name]')].find(element => element.name === name);
                const inline = field?.closest('.form-group')?.querySelector('[data-field-error]');
                const text = ajax.validationMessages({ [name]: errors }).join(' ');
                if (!field || !inline) { general.push(text); continue; }
                inline.textContent = text;
                inline.hidden = false;
                field.setAttribute('aria-invalid', 'true');
                firstInvalid ||= field;
            }
            feedback.textContent = general.filter(Boolean).join(' ') || (firstInvalid
                ? 'Periksa kembali kolom yang ditandai.' : fallback);
            feedback.hidden = false;
            if (firstInvalid?.hidden) firstInvalid.closest('[data-tag-picker]')?.querySelector('button')?.focus();
            else firstInvalid?.focus();
        }

        function openForm(editing) {
            submitLabel = editing ? 'Simpan perubahan' : 'Tambah data';
            title.textContent = `${editing ? 'Edit' : 'Tambah'} ${label}`;
            subtitle.textContent = editing ? 'Perbarui informasi agar portofolio tetap relevan.'
                : 'Lengkapi informasi untuk ditampilkan di portofolio.';
            dialogIcon.replaceChildren(icon(editing ? 'edit' : 'plus'));
            saveLabel.textContent = submitLabel;
            prepareFields();
            resetError();
            dialog.showModal();
            fields.querySelector('input:not([type=hidden]), textarea, select')?.focus({ preventScroll: true });
        }

        function setBusy(busy, busyLabel = 'Menyimpan...') {
            saving = busy;
            dialog?.querySelectorAll('button').forEach(button => { button.disabled = busy; });
            form?.setAttribute('aria-busy', String(busy));
            if (saveLabel) saveLabel.textContent = busy ? busyLabel : submitLabel;
        }

        function cancelEdit() {
            editingSequence++;
            editRequest?.abort();
            tagSequence++;
            tagRequest?.abort();
        }

        root.querySelector('[data-open-create]')?.addEventListener('click', () => {
            if (!dialog || !form || saving || deleting) return;
            cancelEdit();
            fields.innerHTML = initialFields;
            form.reset();
            form.action = config.createUrl;
            openForm(false);
        });

        dialog?.querySelectorAll('[data-close-dialog]').forEach(button => {
            button.addEventListener('click', () => { if (!saving) dialog.close(); });
        });
        dialog?.addEventListener('cancel', event => { if (saving) event.preventDefault(); });
        dialog?.addEventListener('close', cancelEdit);
        form?.addEventListener('input', event => {
            const field = event.target;
            if (!field.hasAttribute('aria-invalid')) return;
            field.removeAttribute('aria-invalid');
            const inline = field.closest('.form-group')?.querySelector('[data-field-error]');
            if (inline) { inline.textContent = ''; inline.hidden = true; }
            if (!fields.querySelector('[aria-invalid]')) resetError();
        });

        deleteDialog?.querySelectorAll('[data-close-delete]').forEach(button => {
            button.addEventListener('click', () => { if (!deleting) deleteDialog.close(); });
        });
        deleteDialog?.addEventListener('cancel', event => { if (deleting) event.preventDefault(); });
        deleteDialog?.addEventListener('close', () => { pendingDeletion = undefined; });
        deleteDialog?.querySelector('[data-confirm-delete]')?.addEventListener('click', async () => {
            if (!pendingDeletion || deleting) return;
            const { button, pk } = pendingDeletion;
            deleting = true;
            deleteDialog.setAttribute('aria-busy', 'true');
            deleteDialog.querySelectorAll('button').forEach(control => { control.disabled = true; });
            deleteLabel.textContent = 'Menghapus...';
            deleteFeedback.hidden = true;
            button.disabled = true;
            try {
                const { response, data } = await ajax.fetchJson(endpoint(config.deleteUrl, pk), {
                    method: 'POST', headers: { 'X-CSRFToken': ajax.getCsrfToken() },
                });
                if (!response.ok || !data?.pk) throw new Error(message(data, 'Gagal menghapus data.'));
                deleteDialog.close();
                notify('Berhasil', data.message, 'success');
                refresh();
            } catch (error) {
                deleteFeedback.textContent = error.message;
                deleteFeedback.hidden = false;
                notify('Gagal menghapus', error.message);
            } finally {
                deleting = false;
                button.disabled = false;
                deleteDialog.setAttribute('aria-busy', 'false');
                deleteDialog.querySelectorAll('button').forEach(control => { control.disabled = false; });
                deleteLabel.textContent = 'Ya, hapus data';
            }
        });

        form?.addEventListener('submit', async event => {
            event.preventDefault();
            if (saving) return;
            const creator = fields.querySelector('[data-tag-creator]');
            const draftTag = creator?.querySelector('[data-tag-name]');
            if (creator && !creator.hidden && draftTag.value.trim()) {
                const error = creator.querySelector('[data-tag-error]');
                error.textContent = 'Buat tag ini atau batalkan sebelum menyimpan proyek.';
                error.hidden = false;
                draftTag.focus();
                return;
            }
            resetError();
            setBusy(true);
            try {
                const { response, data } = await ajax.fetchJson(form.action, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': ajax.getCsrfToken(form) },
                    body: new FormData(form),
                });
                if (!response.ok || !data?.item) {
                    const text = message(data, `Gagal menyimpan data (status ${response.status}).`);
                    validationError(data, text);
                    notify('Gagal menyimpan', text);
                    return;
                }
                setBusy(false);
                dialog.close();
                notify('Berhasil', data.message, 'success');
                refresh(data.item);
            } catch (_) {
                feedback.textContent = 'Tidak dapat terhubung ke server. Silakan coba lagi.';
                feedback.hidden = false;
                notify('Gagal menyimpan', feedback.textContent);
            } finally { setBusy(false); }
        });

        root.addEventListener('click', async event => {
            const button = event.target.closest('[data-resource-action]');
            if (!button || button.disabled || saving || deleting) return;
            const pk = button.dataset.pk;
            if (button.dataset.resourceAction === 'delete') {
                if (!deleteDialog) return;
                pendingDeletion = { button, pk };
                deleteDialog.querySelector('[data-delete-label]').textContent = button.dataset.label;
                deleteFeedback.textContent = '';
                deleteFeedback.hidden = true;
                deleteDialog.showModal();
            } else if (dialog && form) {
                cancelEdit();
                const current = editingSequence;
                const controller = new AbortController();
                editRequest = controller;
                button.disabled = true;
                try {
                    const { response, data } = await ajax.fetchJson(endpoint(config.detailUrl, pk), {
                        signal: controller.signal,
                    });
                    if (current !== editingSequence) return;
                    if (!response.ok || typeof data?.form_html !== 'string') {
                        throw new Error(message(data, 'Gagal memuat formulir.'));
                    }
                    // HTML comes only from the role protected Django form renderer.
                    fields.innerHTML = data.form_html;
                    form.action = endpoint(config.editUrl, pk);
                    openForm(true);
                } catch (error) {
                    if (error.name !== 'AbortError') notify('Gagal membuka formulir', error.message);
                } finally { button.disabled = false; }
            }
        });
    }

    function list(root, render, { autoLoad = true } = {}) {
        const loading = root.querySelector('[data-loading]');
        const empty = root.querySelector('[data-empty]');
        const errorState = root.querySelector('[data-error]');
        const content = root.querySelector('[data-list]');
        const search = root.querySelector('[data-search-input]');
        let controller;
        let sequence = 0;
        let loaded = false;

        function state(value) {
            if (loading) loading.hidden = value !== 'loading';
            if (empty) empty.hidden = value !== 'empty';
            if (errorState) errorState.hidden = value !== 'error';
            content.hidden = value !== 'list';
            root.setAttribute('aria-busy', String(value === 'loading'));
        }

        function invalidate() { sequence++; controller?.abort(); }
        async function load() {
            delayed.cancel();
            invalidate();
            const current = sequence;
            const request = new AbortController();
            controller = request;
            state('loading');
            const url = new URL(root.dataset.listUrl, window.location.origin);
            if (search?.value.trim()) url.searchParams.set('q', search.value.trim());
            try {
                const { response, data } = await ajax.fetchJson(url, { signal: request.signal });
                if (current !== sequence) return;
                if (!response.ok || !Array.isArray(data)) throw new Error('Invalid list response');
                render(data, content);
                loaded = true;
                state(data.length ? 'list' : 'empty');
                window.AOS?.refreshHard();
            } catch (error) {
                if (error.name !== 'AbortError' && current === sequence) state('error');
            }
        }
        const delayed = debounce(load);
        search?.addEventListener('input', () => { invalidate(); state('loading'); delayed(); });
        root.querySelector('[data-search-form]')?.addEventListener('submit', event => {
            event.preventDefault(); load();
        });
        root.querySelector('[data-retry]')?.addEventListener('click', load);
        bindManagement(root, load);
        if (autoLoad) load();
        return { load, activate() { if (!loaded) load(); } };
    }

    window.PortfolioResources = Object.freeze({ node, httpUrl, debounce, actions, bindManagement, list });
})(window);
