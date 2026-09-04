/* ============================================================================
 * OCR SOC guided tour -- self-contained, no dependencies, no build step.
 *
 * Drop-in coach-marks walkthrough for the SOC hunt/triage views. It anchors to
 * the existing CSS classes already in the shipped frontend (.im-htoggle--brief,
 * .im-htoggle--wb, the SIEM .im-htoggle, .im-qrow alert rows, .im-map case
 * file), so it needs NO source edits and NO rebuild -- inject the file and it
 * finds its own anchors.
 *
 * Behaviors:
 *   - First-open only: auto-starts once per learner (localStorage), then never
 *     again until they click "Show me around" (a small pill, bottom-right).
 *   - Briefing / an alert row: highlighted, and the tour advances when the
 *     learner actually clicks it (learn by doing; the real action happens).
 *   - Workbook: highlighted, but the click is INTERCEPTED -- the tooltip fires
 *     and the new tab does NOT open, exactly as specified.
 *   - SIEM access / case file: highlighted with an explanation.
 *   - Steps whose anchor is absent on the current view are skipped gracefully,
 *     so the same file works on both hunt and triage.
 *
 * Tune STEPS below to change copy or order. Bump TOUR_VERSION to re-show a
 * revised tour to learners who already finished the old one.
 * ==========================================================================*/
(function () {
  if (window.__ocrSocTour) return;              // single init guard
  window.__ocrSocTour = true;

  var TOUR_VERSION = 'v1';
  var DONE_KEY = 'ocr_soc_tour_done_' + TOUR_VERSION;

  // --- step definitions --------------------------------------------------
  // sel: CSS anchor (first match used). advanceOnClick: real click advances.
  // blockClick: swallow the click (show tooltip, do not navigate).
  var STEPS = [
    {
      sel: '.im-htoggle--brief',
      title: 'Start with the Briefing',
      body: 'Your mission briefing: the scenario, the network map, and how to work tonight’s queue. Click it to open.',
      advanceOnClick: true
    },
    {
      sel: '.im-htoggle--wb',
      title: 'The Workbook',
      body: 'The full step-by-step chapter for this exercise. It opens in a new tab — we’ll leave it closed for the tour. Open it any time you get stuck.',
      blockClick: true
    },
    {
      sel: '.im-htoggle:not(.im-htoggle--brief):not(.im-htoggle--wb)',
      title: 'SIEM Access',
      body: 'Your live evidence lives in the SIEM. Open this to get the console URL and the read-only analyst login. A self-signed certificate warning is normal.'
    },
    {
      sel: '.im-qrow',
      title: 'The Alert Queue',
      body: 'Each row here is a lead to investigate. Click one to open it, read the detail, and pivot into the SIEM to settle it.',
      advanceOnClick: true
    },
    {
      sel: '.im-map',
      title: 'Your Case File',
      body: 'Record each finding and answer here as you work. Nothing is graded until you submit it in this rail — this is your scoreboard for the exercise.'
    }
  ];

  // --- styles ------------------------------------------------------------
  var CSS = ''
    + '.soc-tour-spot{position:fixed;z-index:2147483000;border-radius:8px;'
    + 'box-shadow:0 0 0 4px rgba(59,130,246,.9),0 0 0 9999px rgba(8,12,24,.66);'
    + 'transition:all .22s cubic-bezier(.4,0,.2,1);pointer-events:none}'
    + '.soc-tour-tip{position:fixed;z-index:2147483001;max-width:320px;'
    + 'background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:10px;'
    + 'padding:14px 16px;box-shadow:0 12px 32px rgba(0,0,0,.5);'
    + 'font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14px;line-height:1.5}'
    + '.soc-tour-tip h4{margin:0 0 6px;font-size:15px;color:#fff;font-weight:700}'
    + '.soc-tour-tip p{margin:0 0 12px;color:#cbd5e1}'
    + '.soc-tour-row{display:flex;align-items:center;justify-content:space-between;gap:10px}'
    + '.soc-tour-count{font-size:12px;color:#94a3b8}'
    + '.soc-tour-btns{display:flex;gap:8px}'
    + '.soc-tour-btn{border:none;border-radius:6px;padding:6px 12px;font-size:13px;font-weight:600;cursor:pointer}'
    + '.soc-tour-btn--next{background:#3b82f6;color:#fff}'
    + '.soc-tour-btn--next:hover{background:#2563eb}'
    + '.soc-tour-btn--back{background:#0f172a;color:#e2e8f0;border:1px solid #334155}'
    + '.soc-tour-skip{background:none;border:none;color:#94a3b8;font-size:12px;cursor:pointer;text-decoration:underline}'
    + '.soc-tour-tip--pulse{animation:soc-tour-pulse .4s ease}'
    + '@keyframes soc-tour-pulse{0%{transform:scale(1)}40%{transform:scale(1.04)}100%{transform:scale(1)}}'
    + '.soc-tour-pill{position:fixed;right:16px;bottom:16px;z-index:2147482000;'
    + 'background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:999px;'
    + 'padding:8px 14px;font-size:13px;font-weight:600;cursor:pointer;'
    + 'box-shadow:0 4px 14px rgba(0,0,0,.4);font-family:system-ui,sans-serif}'
    + '.soc-tour-pill:hover{border-color:#3b82f6}';

  function injectCss() {
    if (document.getElementById('soc-tour-css')) return;
    var s = document.createElement('style');
    s.id = 'soc-tour-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // --- state -------------------------------------------------------------
  var idx = 0, active = false, spot = null, tip = null, seq = [];

  function firstEl(sel) { try { return document.querySelector(sel); } catch (e) { return null; } }

  // Build the runnable sequence from STEPS whose anchor exists right now.
  function buildSeq() {
    seq = [];
    for (var i = 0; i < STEPS.length; i++) {
      if (firstEl(STEPS[i].sel)) seq.push(STEPS[i]);
    }
    return seq.length > 0;
  }

  function ensureEls() {
    if (!spot) { spot = document.createElement('div'); spot.className = 'soc-tour-spot'; document.body.appendChild(spot); }
    if (!tip) { tip = document.createElement('div'); tip.className = 'soc-tour-tip'; document.body.appendChild(tip); }
  }

  function place() {
    var step = seq[idx];
    var el = step && firstEl(step.sel);
    if (!el) { next(); return; }
    try { el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' }); } catch (e) {}
    var r = el.getBoundingClientRect();
    var pad = 6;
    spot.style.left = (r.left - pad) + 'px';
    spot.style.top = (r.top - pad) + 'px';
    spot.style.width = (r.width + pad * 2) + 'px';
    spot.style.height = (r.height + pad * 2) + 'px';

    // tooltip: below the target if room, else above
    var tipTop = r.bottom + 12, below = true;
    tip.innerHTML = ''
      + '<h4></h4><p></p>'
      + '<div class="soc-tour-row"><span class="soc-tour-count"></span>'
      + '<div class="soc-tour-btns">'
      + (idx > 0 ? '<button class="soc-tour-btn soc-tour-btn--back">Back</button>' : '')
      + '<button class="soc-tour-btn soc-tour-btn--next"></button>'
      + '</div></div>'
      + '<div style="margin-top:8px"><button class="soc-tour-skip">Skip tour</button></div>';
    tip.querySelector('h4').textContent = step.title;
    tip.querySelector('p').textContent = step.body;
    tip.querySelector('.soc-tour-count').textContent = 'Step ' + (idx + 1) + ' of ' + seq.length;
    var nextBtn = tip.querySelector('.soc-tour-btn--next');
    nextBtn.textContent = (idx === seq.length - 1) ? 'Done' : 'Next';
    nextBtn.onclick = next;
    var backBtn = tip.querySelector('.soc-tour-btn--back');
    if (backBtn) backBtn.onclick = prev;
    tip.querySelector('.soc-tour-skip').onclick = finish;

    // measure after content set
    var tw = tip.offsetWidth || 320, th = tip.offsetHeight || 120;
    if (tipTop + th > window.innerHeight - 8) { tipTop = r.top - th - 12; below = false; }
    if (tipTop < 8) tipTop = 8;
    var tipLeft = Math.min(Math.max(8, r.left), window.innerWidth - tw - 8);
    tip.style.left = tipLeft + 'px';
    tip.style.top = tipTop + 'px';
    tip.style.display = 'block';
    spot.style.display = 'block';

    // advance-on-click: let the real click through, then move on
    if (step.advanceOnClick && el) {
      el.addEventListener('click', onAdvanceClick, { once: true });
    }
  }

  function onAdvanceClick() { if (active) setTimeout(next, 260); }

  function clearAdvance() {
    var step = seq[idx]; if (!step) return;
    var el = firstEl(step.sel);
    if (el) el.removeEventListener('click', onAdvanceClick);
  }

  function goto(i) {
    clearAdvance();
    if (i < 0 || i >= seq.length) { finish(); return; }
    idx = i; place();
  }
  function next() { goto(idx + 1); }
  function prev() { goto(idx - 1); }

  // Workbook (and any blockClick step): swallow the click so the tab never opens
  function onCaptureClick(e) {
    if (!active) return;
    var step = seq[idx];
    if (!step || !step.blockClick) return;
    var el = firstEl(step.sel);
    if (el && (e.target === el || el.contains(e.target))) {
      e.preventDefault();
      e.stopPropagation();
      if (tip) { tip.classList.remove('soc-tour-tip--pulse'); void tip.offsetWidth; tip.classList.add('soc-tour-tip--pulse'); }
    }
  }

  function onKey(e) { if (e.key === 'Escape' && active) finish(); }
  function onReflow() { if (active) place(); }

  function start() {
    injectCss();
    if (!buildSeq()) return false;
    ensureEls();
    active = true; idx = 0;
    document.addEventListener('click', onCaptureClick, true);
    document.addEventListener('keydown', onKey);
    window.addEventListener('resize', onReflow);
    window.addEventListener('scroll', onReflow, true);
    place();
    showPill();
    return true;
  }

  function finish() {
    active = false;
    clearAdvance();
    document.removeEventListener('click', onCaptureClick, true);
    document.removeEventListener('keydown', onKey);
    window.removeEventListener('resize', onReflow);
    window.removeEventListener('scroll', onReflow, true);
    if (spot) spot.style.display = 'none';
    if (tip) tip.style.display = 'none';
    try { localStorage.setItem(DONE_KEY, '1'); } catch (e) {}
  }

  // --- replay pill -------------------------------------------------------
  var pill = null;
  function showPill() {
    if (pill) return;
    pill = document.createElement('button');
    pill.className = 'soc-tour-pill';
    pill.textContent = '❓ Show me around';
    pill.onclick = function () { if (!active) start(); };
    document.body.appendChild(pill);
  }

  // --- SOC-view detection + first-open autostart -------------------------
  function onSocView() {
    // heuristic: the SOC header toggles are present and we're on a /soc/ route
    var p = location.pathname || '';
    return firstEl('.im-htoggle--brief') && (/\/soc\//.test(p) || firstEl('.im-qrow'));
  }

  var armed = false;
  function poll() {
    injectCss();
    if (onSocView()) {
      if (!pill) showPill();                 // replay always available on SOC views
      if (!armed) {
        armed = true;
        var done = false;
        try { done = localStorage.getItem(DONE_KEY) === '1'; } catch (e) {}
        if (!done && !active) setTimeout(function () { if (onSocView()) start(); }, 700);
      }
    } else {
      armed = false;                          // re-arm when they navigate away and back
      if (pill && !active) { pill.remove(); pill = null; }
    }
  }
  setInterval(poll, 800);
  poll();

  // public API for manual control / testing
  window.socTour = { start: start, finish: finish, reset: function () { try { localStorage.removeItem(DONE_KEY); } catch (e) {} } };
})();
