(function () {
    const form = document.getElementById('contact-form');
    const ajax = window.PortfolioAjax;
    if (!form || !ajax) return;
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('[type=submit]');
        if (button.disabled) return;
        const label = button.textContent;
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
                window.showToast('Gagal mengirim pesan', message, 'error');
            }
        } catch (_) { window.showToast('Gagal mengirim pesan', 'Periksa koneksi lalu coba lagi.', 'error'); }
        finally { button.disabled = false; button.textContent = label; }
    });
})();
