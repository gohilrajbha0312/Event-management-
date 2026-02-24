// ─── Mobile Navigation Toggle ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.querySelector('.nav-menu-toggle');
    const links = document.querySelector('.navbar-links');
    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('open');
        });
    }

    // ─── FAQ Accordion ──────────────────────────────────────────────
    document.querySelectorAll('.faq-question').forEach(btn => {
        btn.addEventListener('click', () => {
            const item = btn.closest('.faq-item');
            const isActive = item.classList.contains('active');
            // Close all
            document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('active'));
            if (!isActive) item.classList.add('active');
        });
    });

    // ─── Dashboard Tabs ─────────────────────────────────────────────
    document.querySelectorAll('.dash-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;
            // Tabs
            tab.closest('.dash-tabs').querySelectorAll('.dash-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            // Content
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            const el = document.getElementById(target);
            if (el) el.classList.add('active');
        });
    });

    // ─── Auto-dismiss flash messages ────────────────────────────────
    document.querySelectorAll('.flash').forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-10px)';
            setTimeout(() => flash.remove(), 300);
        }, 5000);
    });

    // ─── Fade-in on scroll ──────────────────────────────────────────
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.feature-card, .event-card, .stat-item, .testimonial-card').forEach(el => {
        observer.observe(el);
    });
});
