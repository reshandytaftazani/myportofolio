(() => {
    document.addEventListener('error', event => {
        const image = event.target;
        if (!(image instanceof HTMLImageElement)) return;
        image.hidden = true;
        if (!image.alt || image.nextElementSibling?.classList.contains('image-fallback')) return;
        const fallback = document.createElement('span');
        fallback.className = 'image-fallback'; fallback.textContent = image.alt;
        image.after(fallback);
    }, true);
})();
