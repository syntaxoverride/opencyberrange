/*
 * Mermaid colour fix for Material dark mode (slate).
 *
 * Two-part fix:
 *
 * 1. CSS-variable overrides on <body> (belt-and-suspenders backup for
 *    extra.css).  Forces light node backgrounds + dark default label
 *    text in slate mode.
 *
 * 2. Shadow-DOM injection via attachShadow interception.  Material
 *    renders mermaid SVGs inside a *closed* Shadow DOM.  Its themeCSS
 *    sets  .nodeLabel { color: var(--md-mermaid-label-fg-color); }
 *    which overrides per-node color directives (e.g. color:#fff on a
 *    red node).  We inject a corrective <style> into each shadow root
 *    that makes .nodeLabel inherit colour from its parent .node group,
 *    so per-node directives are honoured while unstyled nodes still
 *    get the dark default.
 */
(function () {
  'use strict';

  /* ── Part 1: Shadow-DOM injection ─────────────────────────────── */
  var _origAttach = Element.prototype.attachShadow;
  Element.prototype.attachShadow = function (init) {
    var shadow = _origAttach.call(this, init);
    if (this.classList && this.classList.contains('mermaid')) {
      var obs = new MutationObserver(function () {
        obs.disconnect();
        var s = document.createElement('style');
        s.textContent =
          '.node{color:var(--md-mermaid-label-fg-color)}' +
          '.nodeLabel,.nodeLabel p{color:inherit!important}';
        shadow.appendChild(s);
      });
      obs.observe(shadow, { childList: true });
    }
    return shadow;
  };

  /* ── Part 2: CSS-variable overrides on <body> ─────────────────── */
  var SLATE_OVERRIDES = {
    '--md-mermaid-label-fg-color': '#1a1a1a',
    '--md-mermaid-node-bg-color':  '#90caf9',
    '--md-mermaid-node-fg-color':  '#1565c0',
    '--md-mermaid-edge-color':     '#546e7a',
    '--md-mermaid-label-bg-color': '#e3f2fd'
  };

  function applyMermaidFix() {
    var scheme = document.body.getAttribute('data-md-color-scheme');
    var keys = Object.keys(SLATE_OVERRIDES);
    if (scheme === 'slate') {
      keys.forEach(function (k) {
        document.body.style.setProperty(k, SLATE_OVERRIDES[k], 'important');
      });
    } else {
      /* In light mode the defaults are fine: remove our overrides */
      keys.forEach(function (k) {
        document.body.style.removeProperty(k);
      });
    }
  }

  /* Apply immediately once the body is available */
  if (document.body) {
    applyMermaidFix();
  } else {
    document.addEventListener('DOMContentLoaded', applyMermaidFix);
  }

  /* Re-apply whenever the user toggles light/dark mode.
     Material changes the data-md-color-scheme attribute on <body>. */
  var observer = new MutationObserver(function (mutations) {
    mutations.forEach(function (m) {
      if (m.attributeName === 'data-md-color-scheme') {
        applyMermaidFix();
      }
    });
  });

  function observe() {
    observer.observe(document.body, { attributes: true, attributeFilter: ['data-md-color-scheme'] });
  }

  if (document.body) {
    observe();
  } else {
    document.addEventListener('DOMContentLoaded', observe);
  }
})();
