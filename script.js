/* ============================================
   Slide Navigation Controller
   Direction: Horizontal (left/right)
   Scroll: Vertical within slide
   ============================================ */

(function () {
  const slides = document.querySelectorAll('.slide');
  const totalSlides = slides.length;
  const progressFill = document.getElementById('progressFill');
  const pageIndicator = document.getElementById('pageIndicator');
  const navDotsContainer = document.getElementById('navDots');
  const keyboardHint = document.getElementById('keyboardHint');

  let currentSlide = 0;
  let isAnimating = false;
  const ANIMATION_DURATION = 500;

  const slideTitles = [
    '封面',
    '岗位匹配',
    '履历总览',
    '纵向·VLM',
    '纵向·NLU',
    '纵向·代驾',
    '纵向·论文',
    '横向·Agent',
    '横向·文档',
    '横向·Hackathon',
    '横向·孵化',
    '历史·Innovus',
    '历史·毕设',
    '历史·校企',
    '历史·Legacy',
    '总结',
  ];

  // --- Initialize Navigation Dots ---
  function initNavDots() {
    slideTitles.forEach((title, i) => {
      const dot = document.createElement('button');
      dot.className = 'nav-dot' + (i === 0 ? ' active' : '');
      dot.setAttribute('aria-label', title);

      const tooltip = document.createElement('span');
      tooltip.className = 'dot-tooltip';
      tooltip.textContent = title;
      dot.appendChild(tooltip);

      dot.addEventListener('click', () => goToSlide(i));
      navDotsContainer.appendChild(dot);
    });
  }

  // --- Update UI State ---
  function updateUI() {
    const progress = (currentSlide / (totalSlides - 1)) * 100;
    progressFill.style.width = progress + '%';
    pageIndicator.textContent = (currentSlide + 1) + ' / ' + totalSlides;

    const dots = navDotsContainer.querySelectorAll('.nav-dot');
    dots.forEach((dot, i) => {
      dot.classList.toggle('active', i === currentSlide);
    });

    if (currentSlide > 0) {
      keyboardHint.style.opacity = '0';
    }
  }

  // --- Go to Slide (horizontal) ---
  function goToSlide(index) {
    if (index === currentSlide || isAnimating || index < 0 || index >= totalSlides) return;

    isAnimating = true;
    const direction = index > currentSlide ? 1 : -1;

    // Hide current slide — slide out to opposite side
    slides[currentSlide].classList.remove('active');
    slides[currentSlide].style.transform = `translateX(${-60 * direction}px)`;

    // Prepare target slide — start from the incoming side
    currentSlide = index;
    slides[currentSlide].style.transform = `translateX(${60 * direction}px)`;

    // Force reflow
    void slides[currentSlide].offsetHeight;

    slides[currentSlide].classList.add('active');
    slides[currentSlide].style.transform = 'translateX(0)';

    // Scroll to top
    slides[currentSlide].scrollTop = 0;

    updateUI();

    setTimeout(() => {
      isAnimating = false;
    }, ANIMATION_DURATION);
  }

  function nextSlide() {
    goToSlide(currentSlide + 1);
  }

  function prevSlide() {
    goToSlide(currentSlide - 1);
  }

  // --- Keyboard Navigation ---
  // Left/Right for slide switching; Up/Down for in-slide scrolling
  document.addEventListener('keydown', (e) => {
    switch (e.key) {
      case 'ArrowRight':
      case 'PageDown':
        e.preventDefault();
        nextSlide();
        break;
      case 'ArrowLeft':
      case 'PageUp':
        e.preventDefault();
        prevSlide();
        break;
      case ' ':
        // Space: next slide only if not scrollable, else let it scroll
        {
          const slide = slides[currentSlide];
          const hasScroll = slide.scrollHeight > slide.clientHeight;
          const atBottom = slide.scrollTop + slide.clientHeight >= slide.scrollHeight - 2;
          if (!hasScroll || atBottom) {
            e.preventDefault();
            nextSlide();
          }
        }
        break;
      case 'Home':
        e.preventDefault();
        goToSlide(0);
        break;
      case 'End':
        e.preventDefault();
        goToSlide(totalSlides - 1);
        break;
    }
  });

  // --- Touch Navigation (horizontal swipe) ---
  let touchStartY = 0;
  let touchStartX = 0;

  document.addEventListener('touchstart', (e) => {
    touchStartY = e.touches[0].clientY;
    touchStartX = e.touches[0].clientX;
  }, { passive: true });

  document.addEventListener('touchend', (e) => {
    const touchEndY = e.changedTouches[0].clientY;
    const touchEndX = e.changedTouches[0].clientX;
    const diffY = touchStartY - touchEndY;
    const diffX = touchStartX - touchEndX;

    // Only trigger on horizontal swipe
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
      if (diffX > 0) {
        nextSlide();
      } else {
        prevSlide();
      }
    }
  }, { passive: true });

  // --- Initialize ---
  initNavDots();
  updateUI();

  // 履历总览等处的「点击跳转指定页」（供 data-slide 使用）
  window.__presentationGoToSlide = function (index) {
    const n = parseInt(String(index), 10);
    if (Number.isFinite(n)) goToSlide(n);
  };

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-slide]');
    if (!btn) return;
    const raw = btn.getAttribute('data-slide');
    if (raw == null || raw === '') return;
    const idx = parseInt(raw, 10);
    if (!Number.isFinite(idx)) return;
    e.preventDefault();
    goToSlide(idx);
  });

  // Animate elements on slide change
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.target.classList.contains('active')) {
        animateSlideContent(mutation.target);
      }
    });
  });

  slides.forEach((slide) => {
    observer.observe(slide, { attributes: true, attributeFilter: ['class'] });
  });

  function animateSlideContent(slide) {
    const elements = slide.querySelectorAll(
      '.timeline-card, .result-card, .summary-card, .feature-list li, .flow-step, .tech-tag, .jd-matrix td, .jd-matrix th, .t-project-card, .figure-block'
    );
    elements.forEach((el, i) => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(20px)';
      el.style.transition = 'none';

      setTimeout(() => {
        el.style.transition = `opacity 0.4s ease ${i * 0.05}s, transform 0.4s ease ${i * 0.05}s`;
        el.style.opacity = '1';
        el.style.transform = 'translateX(0)';
      }, 50);
    });
  }

  // Trigger initial animation for cover
  animateSlideContent(slides[0]);
})();
