// ============================
// FuReelina — interactions
// ============================

// Mobile nav toggle
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');
const navOverlay = document.getElementById('navOverlay');

function closeNav() {
  hamburger.classList.remove('active');
  navLinks.classList.remove('active');
  navOverlay.classList.remove('active');
  document.body.style.overflow = '';
}

function toggleNav() {
  const isOpen = navLinks.classList.toggle('active');
  hamburger.classList.toggle('active');
  navOverlay.classList.toggle('active');
  document.body.style.overflow = isOpen ? 'hidden' : '';
}

hamburger.addEventListener('click', toggleNav);
navOverlay.addEventListener('click', closeNav);

// Close on link tap (mobile)
document.querySelectorAll('.nav-links a').forEach(link => {
  link.addEventListener('click', () => {
    if (window.innerWidth <= 768) closeNav();
  });
});

// ============================
// Parallax character — follows cursor
// ============================
const character = document.getElementById('heroCharacter');
const charImg = character?.querySelector('.char-img');
const charGlow = character?.querySelector('.char-glow');

let targetX = 0, targetY = 0;
let currentX = 0, currentY = 0;

document.addEventListener('mousemove', (e) => {
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2;
  // Normalize to range roughly -1..1
  targetX = (e.clientX - cx) / cx;
  targetY = (e.clientY - cy) / cy;
});

// Smooth animation loop for parallax
function animateParallax() {
  currentX += (targetX - currentX) * 0.06;
  currentY += (targetY - currentY) * 0.06;

  if (character) {
    const moveX = currentX * 18;
    const moveY = currentY * 14;
    character.style.transform = `translate(${moveX}px, ${moveY}px)`;
  }
  if (charImg) {
    const tiltX = currentY * -6;
    const tiltY = currentX * 6;
    charImg.style.transform = `perspective(1200px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
  }
  if (charGlow) {
    charGlow.style.transform = `translate(${currentX * 30}px, ${currentY * 25}px) scale(1)`;
  }

  requestAnimationFrame(animateParallax);
}
animateParallax();

// ============================
// Scroll reveal for sections
// ============================
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.feature-card, .quote-card, .section-title, .section-text, .cta-title, .cta-sub').forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(30px)';
  el.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
  revealObserver.observe(el);
});

// Subtle navbar bg intensity on scroll
const navbar = document.querySelector('.navbar');
window.addEventListener('scroll', () => {
  if (window.scrollY > 40) {
    navbar.style.background = 'rgba(5, 8, 20, 0.9)';
  } else {
    navbar.style.background = 'rgba(10, 16, 40, 0.75)';
  }
});
