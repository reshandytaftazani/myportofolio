(function (window) {
    function getCsrfToken(form) {
        const formToken = form?.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
        if (formToken) return formToken;

        const cookie = document.cookie
            .split(';')
            .map(part => part.trim())
            .find(part => part.startsWith('csrftoken='));
        return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
    }

    async function fetchJson(url, options = {}) {
        const headers = new Headers(options.headers || {});
        if (!headers.has('Accept')) headers.set('Accept', 'application/json');

        const response = await fetch(url, { ...options, headers });
        let data = null;
        try {
            data = await response.json();
        } catch (error) {
            if (error.name === 'AbortError') throw error;
            // CSRF middleware and login redirects may return HTML instead of JSON.
        }
        return { response, data };
    }

    function validationMessages(errors) {
        return Object.values(errors || {})
            .flatMap(value => Array.isArray(value) ? value : [value])
            .map(error => typeof error === 'string' ? error : error?.message)
            .filter(Boolean);
    }

    window.PortfolioAjax = Object.freeze({
        fetchJson,
        getCsrfToken,
        validationMessages,
    });
})(window);
