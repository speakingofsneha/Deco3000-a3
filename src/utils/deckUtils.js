// Deck utility functions - moved from deck-utils.js

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function escapeXml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function extractPdfName(sourcePdf) {
  if (!sourcePdf) return 'slides';
  const pathParts = sourcePdf.split('/');
  const filename = pathParts[pathParts.length - 1];
  return filename.replace(/\.pdf$/i, '');
}

function groupSlidesByTitle(slides) {
  const grouped = [];
  const titleMap = new Map();
  
  slides.forEach(slide => {
    if (slide.type === 'title') {
      grouped.push(slide);
      return;
    }
    
    const title = slide.title || '';
    
    if (titleMap.has(title)) {
      const existingIndex = titleMap.get(title);
      const existingSlide = grouped[existingIndex];
      
      const combinedContent = [...existingSlide.content, ...slide.content];
      const hasMedia = existingSlide.metadata?.has_media || slide.metadata?.has_media;
      const isMediaSlide = existingSlide.metadata?.is_media_slide || slide.metadata?.is_media_slide;
      
      grouped[existingIndex] = {
        ...existingSlide,
        content: combinedContent,
        metadata: {
          ...existingSlide.metadata,
          has_media: hasMedia,
          is_media_slide: isMediaSlide
        }
      };
    } else {
      grouped.push(slide);
      titleMap.set(title, grouped.length - 1);
    }
  });
  
  return grouped;
}

function renderSlideContent(contentItems, isMediaSlide, metadata = {}) {
  if (!contentItems || contentItems.length === 0) return '';
  
  // All layouts render as points
  return `<div class="points">${contentItems.map(b => `<p class="point body">${escapeHtml(b.text || '')}</p>`).join('')}</div>`;
}

function renderSlideDeck(slideDeck) {
  const deckEl = document.getElementById('deck');
  if (!deckEl) {
    console.error('Deck element not found');
    return;
  }
  
  deckEl.innerHTML = '';

  const groupedSlides = groupSlidesByTitle(slideDeck.slides || []);
  const totalSlides = groupedSlides.length;
  updateSlideMeta(1, totalSlides);

  groupedSlides.forEach((slide, idx) => {
    const section = document.createElement('section');
    const isTitle = slide.type === 'title' && idx === 0;
    const savedTheme = localStorage.getItem('slide-theme') || 'light';
    section.className = 'slide slide--' + savedTheme + (isTitle ? ' slide--title' : '');

    if (isTitle) {
      const subtitle = (slide.content && slide.content[0] && slide.content[0].text) ? slide.content[0].text : '';
      section.innerHTML = `
        <div class="slide__canvas slide__canvas--${savedTheme}">
          <div class="title__wrap">
            <h1 class="title__heading">${escapeHtml(slide.title || '')}</h1>
            ${subtitle ? `<p class="title__subtitle">${escapeHtml(subtitle)}</p>` : ''}
          </div>
        </div>
      `;
    } else {
      const hasMedia = slide.metadata && slide.metadata.has_media === true;
      const isMediaSlide = slide.metadata && slide.metadata.is_media_slide === true;
      const layout = slide.metadata && slide.metadata.layout ? slide.metadata.layout : 'default';
      const inlineMedia = Boolean(slide.metadata && slide.metadata.inline_media);
      
      // Determine layout class based on metadata
      const layoutClassMap = {
        // Image + Text layouts
        'media-description-below': ' layout--media-description-below',
        'media-description-above': ' layout--media-description-above',
        'two-media-description': ' layout--two-media-description',
        'heading-two-media-description-below': ' layout--heading-two-media-description-below',
        'heading-two-media-description': ' layout--heading-two-media-description',
        'heading-four-points-media-left': ' layout--heading-four-points-media-left',
        'heading-description-media-right': ' layout--heading-description-media-right',
        // Text only layouts
        'key-statement': ' layout--key-statement',
        'two-col-description': ' layout--two-col-description',
        'three-points': ' layout--three-points',
        'three-points-list': ' layout--three-points-list',
        'four-points': ' layout--four-points',
        'four-points-grid': ' layout--four-points-grid',
        'four-points-grid-below': ' layout--four-points-grid-below',
        'six-points': ' layout--six-points',
        // Special layouts
        'problem-statement': ' layout--problem-statement'
      };
      
      let layoutClass = '';
      if (layoutClassMap[layout]) {
        layoutClass = layoutClassMap[layout];
      }
      
      section.className += layoutClass;
      
      // Render media based on layout
      let mediaHtml = '';
      if (hasMedia) {
        const slots = Math.max(1, slide.metadata?.media_slots || 1);
        
        // For two-media layouts, wrap in container
        if (layout === 'two-media-description' || layout === 'heading-two-media-description-below' || layout === 'heading-two-media-description') {
          const mediaPlaceholders = Array.from({ length: slots })
            .map(() => '<div class="media-placeholder" aria-hidden="true"></div>')
            .join('');
          mediaHtml = `<div class="media-container">${mediaPlaceholders}</div>`;
        } else {
          // Single media placeholder
          mediaHtml = Array.from({ length: slots })
            .map(() => '<div class="media-placeholder" aria-hidden="true"></div>')
            .join('');
        }
      }
      
      // For side-by-side layouts, render media and content in correct order
      let contentOrder = '';
      if (layout === 'heading-four-points-media-left' || layout === 'heading-description-media-right') {
        // Media is rendered separately, content goes first
        contentOrder = 'content-first';
      }
      
      // All layouts render as points (not media-description)
      const renderAsMediaSlide = false;
      
      // For grid-below and six-points layouts, extract intro text from first 1-2 bullets
      let introTextHtml = '';
      let contentToRender = slide.content || [];
      
      if (layout === 'four-points-grid-below' || layout === 'six-points') {
        // Use first 1-2 bullets as intro text, rest as grid items
        const introBullets = contentToRender.slice(0, Math.min(2, contentToRender.length));
        const gridBullets = contentToRender.slice(introBullets.length);
        
        if (introBullets.length > 0) {
          introTextHtml = `<div class="intro-text">${introBullets.map(b => `<p>${escapeHtml(b.text || '')}</p>`).join('')}</div>`;
        }
        contentToRender = gridBullets;
      }
      
      // For side-by-side layouts, order content and media differently
      let contentHtml = renderSlideContent(contentToRender, renderAsMediaSlide, slide.metadata || {});
      
      if (layout === 'heading-four-points-media-left' || layout === 'heading-description-media-right') {
        // Content (heading + points) on left, media on right
      section.innerHTML = `
        <div class="slide__canvas slide__canvas--${savedTheme}">
          <div class="slide__content">
            <div class="overline">${idx + 1} / ${totalSlides}</div>
            <h1 class="heading">${escapeHtml(slide.title || '')}</h1>
              ${contentHtml}
            ${mediaHtml}
            </div>
          </div>
        `;
      } else {
        // Standard order: heading, intro text, media, content
        section.innerHTML = `
          <div class="slide__canvas slide__canvas--${savedTheme}">
            <div class="slide__content">
              <div class="overline">${idx + 1} / ${totalSlides}</div>
              <h1 class="heading">${escapeHtml(slide.title || '')}</h1>
              ${introTextHtml}
              ${mediaHtml}
              ${contentHtml}
          </div>
        </div>
      `;
      }
    }
    deckEl.appendChild(section);
  });

  setTimeout(() => {
    setupSlideObserver();
    const savedTheme = localStorage.getItem('slide-theme') || 'light';
    applyThemeToSlides(savedTheme);
    setupDropdown();
    setupBackgroundToolbar();
  }, 300);
}

function updateSlideMeta(currentSlide, totalSlides) {
  const metaEl = document.getElementById('deck-meta');
  if (metaEl) {
    metaEl.textContent = `Section ${currentSlide} of ${totalSlides}`;
  }
}

function setupSlideObserver() {
  const slides = document.querySelectorAll('.slide');
  if (slides.length === 0) return;

  function updateActiveSlide() {
    const viewportCenter = window.innerHeight / 2;
    let activeSlide = null;
    let minDistance = Infinity;

    slides.forEach((slide) => {
      const rect = slide.getBoundingClientRect();
      const slideCenter = rect.top + (rect.height / 2);
      const distance = Math.abs(slideCenter - viewportCenter);

      if (rect.top < window.innerHeight && rect.bottom > 0) {
        if (distance < minDistance) {
          minDistance = distance;
          activeSlide = slide;
        }
      }
    });

    if (!activeSlide) {
      slides.forEach((slide) => {
        const rect = slide.getBoundingClientRect();
        if (rect.top >= 0 && rect.top < window.innerHeight) {
          if (!activeSlide) {
            activeSlide = slide;
          }
        }
      });
    }

    slides.forEach(slide => {
      slide.classList.remove('slide--active');
    });

    if (activeSlide) {
      activeSlide.classList.add('slide--active');
      const slideIndex = Array.from(slides).indexOf(activeSlide) + 1;
      updateSlideMeta(slideIndex, slides.length);
    } else if (slides.length > 0) {
      slides[0].classList.add('slide--active');
      updateSlideMeta(1, slides.length);
    }
  }

  let scrollTimeout;
  const handleScroll = () => {
    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(updateActiveSlide, 10);
  };
  
  window.addEventListener('scroll', handleScroll, { passive: true });
  window.addEventListener('resize', handleScroll, { passive: true });

  if (slides.length > 0) {
    slides[0].classList.add('slide--active');
    updateSlideMeta(1, slides.length);
  }
  
  setTimeout(() => {
    updateActiveSlide();
  }, 100);
  
  setTimeout(() => {
    updateActiveSlide();
  }, 500);
}

function setupDropdown() {
  // Remove existing listeners to avoid duplicates
  const existingHandler = window._exportDropdownHandler;
  if (existingHandler) {
    document.removeEventListener('click', existingHandler);
  }

  const handler = (e) => {
    const dropdown = document.querySelector('.export-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
      closeDropdown();
    }
  };
  window._exportDropdownHandler = handler;
  document.addEventListener('click', handler);

  const exportBtn = document.getElementById('export-btn');
  if (exportBtn) {
    // Remove old listeners by cloning
    const newBtn = exportBtn.cloneNode(true);
    exportBtn.parentNode.replaceChild(newBtn, exportBtn);
    
    newBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleDropdown();
    });
  }

  // Setup dropdown items with fresh event listeners
  setTimeout(() => {
    document.querySelectorAll('.dropdown-item').forEach(item => {
      // Remove old listeners
      const newItem = item.cloneNode(true);
      item.parentNode.replaceChild(newItem, item);
      
      newItem.addEventListener('click', (e) => {
        e.stopPropagation();
        const format = newItem.getAttribute('data-format');
        if (window.deckUtils && window.deckUtils.exportSlides) {
          window.deckUtils.exportSlides(format);
        } else {
          exportSlides(format);
        }
      });
    });
  }, 100);
}

function toggleDropdown() {
  const menu = document.getElementById('export-menu');
  if (menu) menu.classList.toggle('show');
}

function closeDropdown() {
  const menu = document.getElementById('export-menu');
  if (menu) menu.classList.remove('show');
}

function applyThemeToSlides(theme) {
  const slides = document.querySelectorAll('.slide');
  const slideCanvases = document.querySelectorAll('.slide__canvas');
  
  slides.forEach(slide => {
    if (theme === 'dark') {
      slide.classList.add('slide--dark');
      slide.classList.remove('slide--light');
    } else {
      slide.classList.remove('slide--dark');
      slide.classList.add('slide--light');
    }
  });

  slideCanvases.forEach(canvas => {
    if (theme === 'dark') {
      canvas.classList.add('slide__canvas--dark');
      canvas.classList.remove('slide__canvas--light');
    } else {
      canvas.classList.remove('slide__canvas--dark');
      canvas.classList.add('slide__canvas--light');
    }
  });
}

function setupBackgroundToolbar() {
  const backgroundBtn = document.getElementById('background-btn');
  const backgroundMenu = document.getElementById('background-menu');
  if (!backgroundBtn || !backgroundMenu) return;
  
  let currentTheme = localStorage.getItem('slide-theme') || 'light';

  applyThemeToSlides(currentTheme);
  updateDropdownStates(currentTheme);

  function toggleBackgroundMenu() {
    backgroundMenu.classList.toggle('show');
  }

  function closeBackgroundMenu() {
    backgroundMenu.classList.remove('show');
  }

  function updateDropdownStates(theme) {
    document.querySelectorAll('.toolbar-dropdown-item').forEach(item => {
      if (item.getAttribute('data-theme') === theme) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  }

  function applyTheme(theme) {
    applyThemeToSlides(theme);
    updateDropdownStates(theme);
    localStorage.setItem('slide-theme', theme);
    currentTheme = theme;
  }

  // Remove old listeners
  const newBtn = backgroundBtn.cloneNode(true);
  backgroundBtn.parentNode.replaceChild(newBtn, backgroundBtn);

  newBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleBackgroundMenu();
  });

  document.querySelectorAll('.toolbar-dropdown-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      const theme = item.getAttribute('data-theme');
      applyTheme(theme);
      closeBackgroundMenu();
    });
  });

  const existingBgHandler = window._backgroundDropdownHandler;
  if (existingBgHandler) {
    document.removeEventListener('click', existingBgHandler);
  }

  const bgHandler = (e) => {
    const dropdown = document.querySelector('.background-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
      closeBackgroundMenu();
    }
  };
  window._backgroundDropdownHandler = bgHandler;
  document.addEventListener('click', bgHandler);
}

function slideToSvg(slideElement) {
  const rect = slideElement.getBoundingClientRect();
  const width = Math.round(rect.width);
  const height = Math.round(rect.height);
  
  const styles = window.getComputedStyle(slideElement);
  const bgColor = styles.backgroundColor || '#ffffff';
  
  const svgTextElements = [];
  const walker = document.createTreeWalker(
    slideElement,
    NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
    null
  );
  
  let node;
  const processedTextNodes = new Set();
  
  while (node = walker.nextNode()) {
    if (node.nodeType === Node.TEXT_NODE && !processedTextNodes.has(node)) {
      processedTextNodes.add(node);
      const text = node.textContent.trim();
      if (text) {
        const parentElement = node.parentElement;
        if (parentElement) {
          const elementRect = parentElement.getBoundingClientRect();
          const slideRect = slideElement.getBoundingClientRect();
          
          if (elementRect.width > 0 && elementRect.height > 0) {
            const computedStyles = window.getComputedStyle(parentElement);
            const fontSize = parseFloat(computedStyles.fontSize) || 16;
            const fontFamily = computedStyles.fontFamily.split(',')[0].replace(/['"]/g, '').trim() || 'sans-serif';
            const fontWeight = computedStyles.fontWeight || 'normal';
            let fontStyle = computedStyles.fontStyle || 'normal';
            
            const tagName = parentElement.tagName?.toLowerCase();
            const className = parentElement.className || '';
            const isHeading = (tagName && ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) ||
                             className.includes('heading') || className.includes('title__heading');
            
            if (isHeading) {
              fontStyle = 'normal';
            }
            
            const color = computedStyles.color || '#000000';
            const textAlign = computedStyles.textAlign || 'left';
            const lineHeight = parseFloat(computedStyles.lineHeight) || fontSize * 1.5;
            
            const x = elementRect.left - slideRect.left;
            const y = elementRect.top - slideRect.top + fontSize;
            
            let textX = x;
            let anchor = 'start';
            if (textAlign === 'center') {
              textX = x + (elementRect.width / 2);
              anchor = 'middle';
            } else if (textAlign === 'right') {
              textX = x + elementRect.width;
              anchor = 'end';
            }
            
            const lines = text.split('\n').filter(line => line.trim());
            lines.forEach((line, index) => {
              if (line.trim()) {
                svgTextElements.push(
                  `<text x="${textX}" y="${y + (index * lineHeight)}" 
                    font-family="${fontFamily}" 
                    font-size="${fontSize}" 
                    font-weight="${fontWeight}" 
                    font-style="${fontStyle}"
                    fill="${color}"
                    text-anchor="${anchor}">${escapeXml(line.trim())}</text>`
                );
              }
            });
          }
        }
      }
    }
  }
  
  const svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
<rect width="100%" height="100%" fill="${bgColor}"/>
${svgTextElements.join('\n')}
</svg>`;
  
  return svgContent;
}

async function exportSlides(format) {
  const slides = document.querySelectorAll('.slide');
  if (slides.length === 0) {
    alert('No slides to export');
    return;
  }

  const button = document.getElementById('export-btn');
  if (!button) return;
  
  const originalText = button.textContent;
  button.textContent = 'Exporting...';
  button.disabled = true;
  closeDropdown();

  try {
    const zip = new JSZip();
    const promises = [];

    if (format === 'png') {
      for (let i = 0; i < slides.length; i++) {
        const slide = slides[i];
        const canvasPromise = html2canvas(slide, {
          backgroundColor: '#ffffff',
          scale: 2,
          useCORS: true,
          logging: false
        }).then(canvas => {
          return new Promise((resolve) => {
            canvas.toBlob((blob) => {
              zip.file(`slide ${i + 1}.png`, blob);
              resolve();
            }, 'image/png');
          });
        });
        promises.push(canvasPromise);
      }
    } else if (format === 'svg') {
      for (let i = 0; i < slides.length; i++) {
        const slide = slides[i];
        const svgContent = slideToSvg(slide);
        const blob = new Blob([svgContent], { type: 'image/svg+xml' });
        zip.file(`slide ${i + 1}.svg`, blob);
      }
    }

    await Promise.all(promises);

    const zipBlob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(zipBlob);
    const a = document.createElement('a');
    a.href = url;
    const pdfName = document.getElementById('deck-title')?.textContent || 'slides';
    a.download = `${pdfName}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    button.textContent = 'Exported!';
    setTimeout(() => {
      button.textContent = originalText;
      button.disabled = false;
    }, 2000);
  } catch (error) {
    console.error('Export failed:', error);
    alert('Export failed: ' + error.message);
    button.textContent = originalText;
    button.disabled = false;
  }
}

// Export functions for use in React
if (typeof window !== 'undefined') {
  window.deckUtils = {
    renderSlideDeck,
    extractPdfName,
    exportSlides,
    setupDropdown,
    setupBackgroundToolbar
  };
}

