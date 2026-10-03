(function () {
    const form = document.getElementById('contact-form');
    const ajax = window.PortfolioAjax;
    if (!form || !ajax) return;
    const feedback = form.querySelector('[data-contact-feedback]');
    form.querySelectorAll('.form-group [name]').forEach(field => {
        const error = field.closest('.form-group').querySelector('[data-contact-error]');
        if (!error) return;
        const ids = field.getAttribute('aria-describedby')?.split(/\s+/) || [];
        field.setAttribute('aria-describedby', [...new Set([...ids, error.id])].join(' '));
    });

    function clearField(field) {
        field.removeAttribute('aria-invalid');
        const error = field.closest('.form-group')?.querySelector('[data-contact-error]');
        if (error) { error.textContent = ''; error.hidden = true; }
    }

    function showErrors(errors, message) {
        let firstInvalid;
        const general = [];
        for (const [name, values] of Object.entries(errors || {})) {
            const field = [...form.elements].find(element => element.name === name);
            const error = field?.closest('.form-group')?.querySelector('[data-contact-error]');
            const text = ajax.validationMessages({ [name]: values }).join(' ');
            if (!field || !error) { general.push(text); continue; }
            error.textContent = text;
            error.hidden = false;
            field.setAttribute('aria-invalid', 'true');
            firstInvalid ||= field;
        }
        feedback.textContent = general.filter(Boolean).join(' ')
            || (firstInvalid ? 'Periksa kembali kolom yang ditandai.' : message);
        feedback.hidden = false;
        firstInvalid?.focus();
    }

    form.addEventListener('input', event => {
        clearField(event.target);
        if (!form.querySelector('[aria-invalid]')) feedback.hidden = true;
    });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('[type=submit]');
        if (button.disabled) return;
        const label = button.textContent;
        form.querySelectorAll('.form-group [name]').forEach(clearField);
        feedback.hidden = true;
        form.setAttribute('aria-busy', 'true');
        button.disabled = true; button.textContent = 'Mengirim...';
        try {
            const { response, data } = await ajax.fetchJson(form.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': ajax.getCsrfToken(form) },
                body: new FormData(form),
            });
            if (response.ok && data?.status === 'success') {
                window.showToast('Pesan terkirim', data.message, 'success'); form.reset();
            } else {
                const message = ajax.validationMessages(data?.errors).join(' ') || data?.message
                    || (response.status === 403 ? 'Permintaan ditolak. Muat ulang halaman lalu coba lagi.' : 'Terjadi kesalahan. Coba lagi.');
                showErrors(data?.errors, message);
                window.showToast('Gagal mengirim pesan', message, 'error');
            }
        } catch (_) {
            const message = 'Periksa koneksi lalu coba lagi.';
            showErrors(null, message);
            window.showToast('Gagal mengirim pesan', message, 'error');
        } finally {
            button.disabled = false; button.textContent = label;
            form.setAttribute('aria-busy', 'false');
            if (document.activeElement === document.body) button.focus();
        }
    });
})();
