/**
 * Apple Analysis Dashboard - Interactive Scripts
 * Google Playground Style
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all animations and interactions
    initScrollAnimations();
    initConfidenceAnimations();
    initHoverEffects();
    initSmoothScrolling();
});

/**
 * Scroll-triggered animations
 */
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-on-scroll');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Add staggered delay for multiple elements
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, index * 100);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    animatedElements.forEach(el => observer.observe(el));

    // Also animate cards and sections that aren't marked
    const cards = document.querySelectorAll('.question-card, .visual-card, .insight-card, .step-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = `all 0.6s ease ${index * 0.1}s`;

        const cardObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });

        cardObserver.observe(card);
    });
}

/**
 * Animate confidence bars and rings
 */
function initConfidenceAnimations() {
    // Animate bar charts
    const barFills = document.querySelectorAll('.bar-fill, .confidence-bar');

    const barObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const targetWidth = entry.target.style.width;
                entry.target.style.width = '0%';
                setTimeout(() => {
                    entry.target.style.transition = 'width 1s ease-out';
                    entry.target.style.width = targetWidth;
                }, 100);
            }
        });
    }, { threshold: 0.5 });

    barFills.forEach(bar => barObserver.observe(bar));

    // Animate hop fills with scale animation
    const hopFills = document.querySelectorAll('.hop-fill');
    hopFills.forEach((hop, index) => {
        // Use transform scale instead of height for smoother animation
        hop.style.transform = 'scaleY(0)';
        hop.style.transformOrigin = 'bottom';

        const hopObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        hop.style.transition = 'transform 0.8s ease-out';
                        hop.style.transform = 'scaleY(1)';
                    }, index * 150);
                    hopObserver.unobserve(hop);
                }
            });
        }, { threshold: 0.1 });

        hopObserver.observe(hop);
    });

    // Animate progress rings
    const progressRings = document.querySelectorAll('.progress-ring');
    progressRings.forEach(ring => {
        const parent = ring.closest('.confidence-ring');
        if (parent) {
            const value = parent.dataset.value || 50;
            ring.style.strokeDasharray = `${value} 100`;
        }
    });
}

/**
 * Add hover effects and interactions
 */
function initHoverEffects() {
    // Card tilt effect
    const cards = document.querySelectorAll('.question-card, .stat-bubble');

    cards.forEach(card => {
        card.addEventListener('mouseenter', (e) => {
            card.style.transform = 'translateY(-8px) scale(1.02)';
        });

        card.addEventListener('mouseleave', (e) => {
            card.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Button ripple effect
    const buttons = document.querySelectorAll('.cta-button, .nav-link');

    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();

            ripple.style.cssText = `
                position: absolute;
                background: rgba(255,255,255,0.3);
                border-radius: 50%;
                pointer-events: none;
                width: 100px;
                height: 100px;
                transform: translate(-50%, -50%) scale(0);
                animation: ripple 0.6s ease-out;
            `;

            ripple.style.left = (e.clientX - rect.left) + 'px';
            ripple.style.top = (e.clientY - rect.top) + 'px';

            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    });

    // Add ripple animation style
    if (!document.querySelector('#ripple-style')) {
        const style = document.createElement('style');
        style.id = 'ripple-style';
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: translate(-50%, -50%) scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

/**
 * Smooth scrolling for anchor links
 */
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Counter animation for numbers
 */
function animateCounter(element, target, duration = 1500) {
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = Math.floor(start + (target - start) * easeOutQuart);

        element.textContent = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = target;
        }
    }

    requestAnimationFrame(update);
}

/**
 * Animate counters when in view
 */
const counters = document.querySelectorAll('[data-count]');
counters.forEach(counter => {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = parseInt(counter.dataset.count);
                animateCounter(counter, target);
                observer.unobserve(counter);
            }
        });
    });
    observer.observe(counter);
});

/**
 * Add floating particles effect to hero section
 */
function createParticles() {
    const hero = document.querySelector('.hero');
    if (!hero) return;

    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.cssText = `
            position: absolute;
            width: ${Math.random() * 10 + 5}px;
            height: ${Math.random() * 10 + 5}px;
            background: ${['#4285F4', '#EA4335', '#FBBC04', '#34A853'][Math.floor(Math.random() * 4)]};
            border-radius: 50%;
            opacity: 0.1;
            pointer-events: none;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            animation: floatParticle ${Math.random() * 10 + 10}s ease-in-out infinite;
            animation-delay: ${Math.random() * 5}s;
        `;
        hero.appendChild(particle);
    }

    // Add particle animation if not exists
    if (!document.querySelector('#particle-style')) {
        const style = document.createElement('style');
        style.id = 'particle-style';
        style.textContent = `
            @keyframes floatParticle {
                0%, 100% { transform: translate(0, 0) rotate(0deg); }
                25% { transform: translate(20px, -30px) rotate(90deg); }
                50% { transform: translate(-10px, -50px) rotate(180deg); }
                75% { transform: translate(-30px, -20px) rotate(270deg); }
            }
        `;
        document.head.appendChild(style);
    }
}

// Create particles on load
createParticles();

/**
 * Mobile menu toggle (if needed)
 */
function initMobileMenu() {
    const nav = document.querySelector('.nav');
    const navLinks = document.querySelector('.nav-links');

    // Create mobile menu button
    const menuBtn = document.createElement('button');
    menuBtn.className = 'mobile-menu-btn';
    menuBtn.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
        </svg>
    `;
    menuBtn.style.cssText = `
        display: none;
        background: none;
        border: none;
        cursor: pointer;
        padding: 8px;
        color: var(--gray-700);
    `;

    // Add styles for mobile
    const style = document.createElement('style');
    style.textContent = `
        @media (max-width: 768px) {
            .mobile-menu-btn { display: block !important; }
            .nav-links {
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: white;
                flex-direction: column;
                padding: 16px;
                box-shadow: var(--shadow-lg);
                display: none;
            }
            .nav-links.open { display: flex !important; }
        }
    `;
    document.head.appendChild(style);

    nav.appendChild(menuBtn);

    menuBtn.addEventListener('click', () => {
        navLinks.classList.toggle('open');
    });
}

initMobileMenu();

console.log('🍎 Apple Analysis Dashboard loaded successfully!');
console.log('📊 Powered by OpMech-GraphRAG');
