(() => {
    if (!document.body.classList.contains('desktop-page')) return;
    try {
        if (!window.PortfolioDesktop?.init()) return;
    } catch (error) {
        console.error('Desktop initialization failed', error);
        window.PortfolioDesktop?.fallback();
        return;
    }
    // Optional enhancements cannot prevent navigation or server content.
    try { window.initDesktopIcons?.(); } catch (error) { console.error('Icon enhancement failed', error); }
    try { window.initDesktopClock?.(); } catch (error) { console.error('Clock enhancement failed', error); }
})();
