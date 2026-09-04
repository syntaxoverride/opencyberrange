/* Show a learner the week they are working in, and nothing else.
 *
 * A student arrives from a specific exercise, so the chapter they are in is in
 * the URL. Listing the other weeks beside it is noise at best, and at worst
 * advertises pages the server will refuse (auth.py::_require_workbook_released).
 * So the nav is reduced to the chapter being read.
 *
 * The hiding itself is done in CSS (extra.css, .ocr-nav-gating) with the class
 * set inline in <head> (overrides/main.html), because this file runs at the end
 * of <body> and anything it hid would already have been painted. This script
 * only marks what to reveal.
 *
 * On the workbook index there is no chapter in the URL, so it falls back to the
 * released list from the API, which keeps the landing page navigable instead of
 * stranding someone with an empty sidebar.
 *
 * Fail-open throughout: any error, a slow lookup, or a page this cannot parse
 * ends with the full nav restored. Nothing here is a security control. The
 * server gate is the only thing that actually withholds a page.
 */
(function () {
  var m = window.location.pathname.match(/^\/wiki\/course\/([^\/]+)\/(.*)$/);
  if (!m) return;
  var slug = m[1];
  var rest = m[2] || '';
  var root = document.documentElement;

  // The head block sets this. If it did not run, scripting is not the thing to
  // rely on, so leave the nav exactly as built.
  if (!root.classList.contains('ocr-nav-gating')) return;

  function ungate() { root.classList.remove('ocr-nav-gating'); }

  function chapterOf(href) {
    var tail = (href || '').split('/wiki/course/' + slug + '/')[1];
    if (!tail) return null;
    var seg = tail.split('/')[0];
    // Assets and files are not chapters.
    return (!seg || seg.indexOf('.') !== -1) ? null : seg;
  }

  // Reveal the chapters named in `open`; keep the gate so the rest stay hidden.
  function reveal(open) {
    var items = document.querySelectorAll(
      '.md-nav--primary > .md-nav__list > .md-nav__item--nested'
    );
    var shown = 0;
    Array.prototype.forEach.call(items, function (item) {
      var link = item.querySelector('a.md-nav__link[href]');
      var chapter = link ? chapterOf(link.href) : null;
      // A section we cannot resolve stays visible rather than vanishing.
      if (!chapter || open[chapter]) { item.classList.add('ocr-nav-open'); shown++; }
    });
    // Never leave someone with an empty sidebar; if nothing matched, show all.
    if (!shown) ungate();
  }

  var current = chapterOf(window.location.href);
  if (current) {
    var only = {};
    only[current] = true;
    reveal(only);
    return;                     // no request needed: the URL already told us
  }

  // Workbook index: no chapter in the URL. Ask which weeks have been released
  // so the landing page still lists somewhere to go.
  var settled = false;
  var failOpen = setTimeout(function () { if (!settled) ungate(); }, 2000);
  fetch('/api/auth/wiki-released?slug=' + encodeURIComponent(slug), {
    credentials: 'same-origin'
  })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      settled = true;
      clearTimeout(failOpen);
      if (!data || data.all || !Array.isArray(data.chapters) || !data.chapters.length) {
        ungate();
        return;
      }
      var open = {};
      data.chapters.forEach(function (c) { open[c] = true; });
      reveal(open);
    })
    .catch(function () { settled = true; clearTimeout(failOpen); ungate(); });
})();
