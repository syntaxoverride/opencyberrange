/*
 * PDF Export: adds a "Save as PDF" button to every wiki page.
 *
 * Uses html2pdf.js to render the page content directly to a downloadable
 * PDF file without opening the browser print dialog.
 */
(function () {
  'use strict';

  function insertButton() {
    var heading = document.querySelector('.md-content h1');
    if (!heading) return;

    /* Avoid duplicate buttons on instant navigation */
    if (heading.parentNode.querySelector('.pdf-export-btn')) return;

    var btn = document.createElement('button');
    btn.className = 'pdf-export-btn';
    btn.title = 'Save this page as PDF';
    btn.setAttribute('aria-label', 'Save as PDF');

    /* Download icon (SVG) + label */
    btn.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">' +
        '<path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13zm-3 4h4v1.5h-4V13zm6 4H8v-1.5h8V17zm0-3H8v-1.5h8V14z"/>' +
      '</svg>' +
      ' <span>Save as PDF</span>';

    btn.addEventListener('click', function () {
      if (typeof html2pdf === 'undefined') {
        alert('PDF library is still loading. Please try again in a moment.');
        return;
      }

      var content = document.querySelector('.md-content__inner');
      if (!content) {
        alert('Could not find page content.');
        return;
      }

      /* Grab the page title for the filename */
      var title = (heading.textContent || 'document').trim().replace(/[^\w\s-]/g, '').replace(/\s+/g, '_');

      /* Show generating state */
      var origHTML = btn.innerHTML;
      btn.innerHTML =
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="currentColor" class="pdf-spin">' +
          '<path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>' +
        '</svg>' +
        ' <span>Generating...</span>';
      btn.disabled = true;

      /* Clone the content so we can modify it for PDF without affecting the page */
      var clone = content.cloneNode(true);

      /* Remove the PDF button itself from the clone */
      var cloneBtn = clone.querySelector('.pdf-export-btn');
      if (cloneBtn) cloneBtn.remove();

      /* Remove any tabbed content wrappers that hide tabs: show all tabs */
      clone.querySelectorAll('[hidden]').forEach(function (el) {
        el.removeAttribute('hidden');
      });

      /* Force light theme colors on the clone */
      clone.style.color = '#1a1a1a';
      clone.style.background = '#fff';

      /* Ensure code blocks have visible text */
      clone.querySelectorAll('pre, code').forEach(function (el) {
        el.style.color = '#1a1a1a';
        el.style.background = '#f5f5f5';
        el.style.whiteSpace = 'pre-wrap';
        el.style.wordBreak = 'break-word';
      });

      /* Add copyright footer */
      var footer = document.createElement('div');
      footer.style.cssText = 'margin-top:2em;padding-top:0.5em;border-top:1px solid #ddd;text-align:center;font-size:9pt;color:#666;';
      footer.textContent = '\u00A9 2026 Open Cyber Range';
      clone.appendChild(footer);

      var opt = {
        margin:       [10, 10, 15, 10],
        filename:     title + '.pdf',
        image:        { type: 'jpeg', quality: 0.95 },
        html2canvas:  { scale: 2, useCORS: true, logging: false, scrollY: 0 },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
      };

      html2pdf().set(opt).from(clone).save().then(function () {
        btn.innerHTML = origHTML;
        btn.disabled = false;
      }).catch(function () {
        btn.innerHTML = origHTML;
        btn.disabled = false;
        alert('PDF generation failed. Please try again.');
      });
    });

    /* Insert right after the h1 */
    heading.insertAdjacentElement('afterend', btn);
  }

  /* Run on initial load */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', insertButton);
  } else {
    insertButton();
  }

  /* Re-run after MkDocs Material instant navigation */
  if (typeof document$ !== 'undefined') {
    document$.subscribe(function () { insertButton(); });
  } else {
    /* Fallback: listen for location changes via the instant-loading event */
    document.addEventListener('DOMContentSwitch', insertButton);
    /* Material fires a custom event on the body after navigation */
    var bodyObs = new MutationObserver(function () { insertButton(); });
    if (document.body) {
      bodyObs.observe(document.body, { childList: true, subtree: false });
    } else {
      document.addEventListener('DOMContentLoaded', function () {
        bodyObs.observe(document.body, { childList: true, subtree: false });
      });
    }
  }
})();
