/* =========================================================================
   NEUTURA - SCRIPT PARTILHADO POR TODAS AS PÁGINAS
   Menu mobile, cabeçalho compacto, carrosséis,
   aviso de links externos, filtros de receitas e formulários.
   ========================================================================= */
document.addEventListener("DOMContentLoaded", () => {
    const html = document.documentElement;
    const body = document.body;

    /* --- 1. IDIOMA ---
       Cada língua tem o seu URL (PT na raiz, EN em /en/); o seletor PT | EN
       são links normais. Aqui só se escolhe a língua dos textos gerados por JS. */
    const isEn = html.lang === 'en';
    const t = (pt, en) => (isEn ? en : pt);

    /* --- 2. MENU MOBILE (HAMBÚRGUER) --- */
    const toggle = document.querySelector('.nav-toggle');
    const panel = document.getElementById('nav-panel');
    const backdrop = document.querySelector('.nav-backdrop');

    function setMenu(open) {
        if (!toggle || !panel) return;
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        panel.classList.toggle('is-open', open);
        if (backdrop) backdrop.classList.toggle('is-open', open);
        body.classList.toggle('nav-open', open);
        if (open) {
            const first = panel.querySelector('a, button');
            if (first) first.focus();
        }
    }

    if (toggle && panel) {
        toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
        if (backdrop) backdrop.addEventListener('click', () => setMenu(false));
        panel.querySelectorAll('a').forEach(a => a.addEventListener('click', () => setMenu(false)));
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && panel.classList.contains('is-open')) {
                setMenu(false);
                toggle.focus();
            }
        });
        window.matchMedia('(min-width: 901px)').addEventListener('change', e => { if (e.matches) setMenu(false); });
    }

    /* --- 3. CABEÇALHO COMPACTO AO FAZER SCROLL --- */
    const header = document.querySelector('.site-header');
    if (header) {
        const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 40);
        onScroll();
        window.addEventListener('scroll', onScroll, { passive: true });
    }

    /* --- 4. CARROSSÉIS COM SETAS E INDICADORES --- */
    document.querySelectorAll('.horizontal-scroll-wrapper').forEach((wrapper, idx) => {
        const track = wrapper.querySelector('.horizontal-scroll');
        if (!track) return;
        const items = Array.from(track.children);
        if (items.length < 2) return;

        if (!track.id) track.id = 'carousel-' + (idx + 1);
        track.setAttribute('tabindex', '0');

        const controls = document.createElement('div');
        controls.className = 'carousel-controls';
        controls.innerHTML =
            '<button type="button" class="carousel-btn carousel-prev" aria-controls="' + track.id + '">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="15 18 9 12 15 6"></polyline></svg>' +
            '<span class="sr-only">' + t('Produtos anteriores', 'Previous products') + '</span></button>' +
            '<div class="carousel-dots"></div>' +
            '<button type="button" class="carousel-btn carousel-next" aria-controls="' + track.id + '">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="9 18 15 12 9 6"></polyline></svg>' +
            '<span class="sr-only">' + t('Produtos seguintes', 'Next products') + '</span></button>';
        wrapper.appendChild(controls);

        const prev = controls.querySelector('.carousel-prev');
        const next = controls.querySelector('.carousel-next');
        const dotsWrap = controls.querySelector('.carousel-dots');

        const step = () => items[0].getBoundingClientRect().width + parseFloat(getComputedStyle(track).columnGap || 0);
        const visibleCount = () => Math.max(1, Math.round(track.clientWidth / step()));
        const pageCount = () => Math.max(1, Math.ceil(items.length / visibleCount()));

        function buildDots() {
            dotsWrap.innerHTML = '';
            const pages = pageCount();
            for (let i = 0; i < pages; i++) {
                const dot = document.createElement('button');
                dot.type = 'button';
                dot.className = 'carousel-dot';
                dot.innerHTML = '<span class="sr-only">' +
                    t('Ir para o grupo ' + (i + 1) + ' de ' + pages, 'Go to group ' + (i + 1) + ' of ' + pages) + '</span>';
                dot.addEventListener('click', () => {
                    track.scrollTo({ left: i * visibleCount() * step() });
                });
                dotsWrap.appendChild(dot);
            }
            controls.hidden = pages < 2;
            update();
        }

        function update() {
            const maxScroll = track.scrollWidth - track.clientWidth - 2;
            prev.disabled = track.scrollLeft <= 2;
            next.disabled = track.scrollLeft >= maxScroll;
            const current = Math.min(pageCount() - 1, Math.round(track.scrollLeft / (visibleCount() * step())));
            const atEnd = track.scrollLeft >= maxScroll;
            dotsWrap.querySelectorAll('.carousel-dot').forEach((d, i, all) => {
                const active = atEnd ? i === all.length - 1 : i === current;
                d.setAttribute('aria-current', active ? 'true' : 'false');
            });
        }

        prev.addEventListener('click', () => track.scrollBy({ left: -visibleCount() * step() }));
        next.addEventListener('click', () => track.scrollBy({ left: visibleCount() * step() }));
        track.addEventListener('scroll', () => window.requestAnimationFrame(update), { passive: true });
        track.addEventListener('keydown', e => {
            if (e.key === 'ArrowRight') { e.preventDefault(); next.click(); }
            if (e.key === 'ArrowLeft') { e.preventDefault(); prev.click(); }
        });
        window.addEventListener('resize', buildDots);
        buildDots();
    });

    /* --- 5. AVISO DE LINKS QUE ABREM NOUTRO SEPARADOR --- */
    document.querySelectorAll('a[target="_blank"]').forEach(a => {
        if (a.querySelector('.new-tab-note')) return;
        const isPdf = /\.pdf($|\?)/i.test(a.getAttribute('href') || '');
        const note = document.createElement('span');
        note.className = 'sr-only new-tab-note';
        note.textContent = isPdf
            ? t(' (PDF, abre num novo separador)', ' (PDF, opens in a new tab)')
            : t(' (abre num novo separador)', ' (opens in a new tab)');
        a.appendChild(note);
    });

    /* --- 6. FILTROS DE RECEITAS --- */
    const filterBtns = document.querySelectorAll('.filter-btn[data-filter]');
    if (filterBtns.length) {
        const cards = document.querySelectorAll('.recipe-card[data-category]');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const filter = btn.dataset.filter;
                filterBtns.forEach(b => {
                    b.classList.toggle('active', b === btn);
                    b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
                });
                cards.forEach(card => {
                    card.hidden = !(filter === 'all' || card.dataset.category === filter);
                });
            });
        });
    }

    /* --- 7. FORMULÁRIOS SEM BACKEND ---
       Enquanto não houver endpoint de envio (action="#"), o formulário não
       finge que enviou: mostra o email alternativo. Quando o backend estiver
       pronto basta colocar o URL no atributo action do <form>. */
    document.querySelectorAll('form[data-pending-backend]').forEach(form => {
        form.addEventListener('submit', e => {
            const action = form.getAttribute('action') || '#';
            if (action !== '#') return;
            e.preventDefault();
            const status = form.querySelector('.form-status');
            if (status) {
                status.hidden = false;
                status.focus();
            }
        });
    });

    /* --- 8. VÍDEO SÓ CARREGA QUANDO FICA VISÍVEL --- */
    const lazyVideos = document.querySelectorAll('video[data-lazy]');
    if (lazyVideos.length && 'IntersectionObserver' in window) {
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const io = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const video = entry.target;
                video.querySelectorAll('source[data-src]').forEach(s => { s.src = s.dataset.src; });
                video.muted = true; // necessário para autoplay
                video.load();
                if (!reduceMotion) video.play().catch(() => {});
                io.unobserve(video);
            });
        }, { rootMargin: '200px' });
        lazyVideos.forEach(v => io.observe(v));
    }
});
