(() => {
    window.initDesktopClock = () => {
        const format = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Jakarta', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
        const date = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Jakarta', weekday: 'short', day: 'numeric', month: 'short' });
        const calendarDate = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Jakarta', year: 'numeric', month: 'numeric', day: 'numeric', weekday: 'long' });
        const calendarMonth = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Jakarta', month: 'long', year: 'numeric' });
        let renderedDate;
        function tick() {
            const now = new Date();
            const label = format.format(now);
            document.querySelectorAll('[data-desktop-clock]').forEach(node => { node.textContent = `${date.format(now)} · ${label} WIB`; node.dateTime = now.toISOString(); });
            document.querySelectorAll('[data-widget-clock]').forEach(node => { node.textContent = label; node.dateTime = now.toISOString(); });
            const parts = Object.fromEntries(format.formatToParts(now).filter(part => part.type !== 'literal').map(part => [part.type, Number(part.value)]));
            document.querySelector('[data-clock-hour]')?.setAttribute('transform', `rotate(${(parts.hour % 12 + parts.minute / 60) * 30} 50 50)`);
            document.querySelector('[data-clock-minute]')?.setAttribute('transform', `rotate(${parts.minute * 6} 50 50)`);
            const calendarParts = Object.fromEntries(calendarDate.formatToParts(now).filter(part => part.type !== 'literal').map(part => [part.type, part.value]));
            const dayKey = `${calendarParts.year}-${calendarParts.month}-${calendarParts.day}`;
            if (dayKey !== renderedDate) {
                renderedDate = dayKey;
                const weekday = document.querySelector('[data-calendar-weekday]');
                const day = document.querySelector('[data-calendar-date]');
                const month = document.querySelector('[data-calendar-month]');
                if (weekday) weekday.textContent = calendarParts.weekday;
                if (day) { day.textContent = calendarParts.day; day.dateTime = `${calendarParts.year}-${calendarParts.month.padStart(2, '0')}-${calendarParts.day.padStart(2, '0')}`; }
                if (month) month.textContent = calendarMonth.format(now);
                const days = document.querySelector('[data-calendar-days]');
                if (days) {
                    const year = Number(calendarParts.year), monthIndex = Number(calendarParts.month) - 1;
                    const offset = (new Date(Date.UTC(year, monthIndex, 1)).getUTCDay() + 6) % 7;
                    const count = new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
                    const fragment = document.createDocumentFragment();
                    for (let number = 1; number <= count; number++) {
                        const cell = document.createElement('span');
                        cell.textContent = String(number);
                        if (number === 1) cell.style.gridColumnStart = String(offset + 1);
                        if (number === Number(calendarParts.day)) cell.className = 'calendar-today';
                        fragment.append(cell);
                    }
                    days.replaceChildren(fragment);
                }
            }
        }
        let timer;
        function start() { clearInterval(timer); tick(); timer = setInterval(tick, 30000); }
        start();
        window.addEventListener('pagehide', () => clearInterval(timer));
        window.addEventListener('pageshow', event => { if (event.persisted) start(); });
    };
})();
