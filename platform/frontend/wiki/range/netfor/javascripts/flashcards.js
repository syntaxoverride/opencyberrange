/* Turn workbook study-card sections into click-to-flip cards.
 *
 * Progressive enhancement: the markdown source is unchanged, so with JS off
 * the learner still sees the cards as text. Handles the card conventions used
 * across the tracks:
 *
 *   1. "## Flashcards" / "### Flashcards"  -> <ul> of
 *        <li>Q: ... <strong>A: ...</strong></li>          (answer bold)
 *   2. "## Consolidated flashcards"        -> <ol>/<ul> of
 *        <li><strong>Q:</strong> ... <strong>A:</strong> ...</li>  (both bold)
 *   3. "## Spaced Repetition"              -> repeating
 *        <p><strong>Card N: ...</strong></p><p>Q: ...</p>
 *        <details><summary>Answer</summary>...code...</details>
 *
 * A page may hold several such sections (e.g. multiple "### Flashcards").
 * Idempotent, keyboard-accessible, and re-runs under Material's document$. */
(function () {
  "use strict";

  // ---- small helpers ---------------------------------------------------
  function stripLabel(html, label) {
    return html.replace(new RegExp("^\\s*" + label + "\\s*:?\\s*"), "").trim();
  }

  function nodeHTML(n) {
    if (n.nodeType === 1) return n.outerHTML;
    if (n.nodeType === 3) {
      var d = document.createElement("div");
      d.textContent = n.nodeValue;
      return d.innerHTML;
    }
    return "";
  }

  function htmlBetween(a, b) {
    var out = "", n = a.nextSibling;
    while (n && n !== b) { out += nodeHTML(n); n = n.nextSibling; }
    return out;
  }
  function htmlAfter(a) {
    var out = "", n = a.nextSibling;
    while (n) { out += nodeHTML(n); n = n.nextSibling; }
    return out;
  }

  // ---- parse one Q/A list item ----------------------------------------
  function parseListItem(li) {
    var strongs = Array.prototype.slice.call(li.querySelectorAll("strong"));
    // Consolidated: an explicit "Q:" label strong and an "A:" label strong.
    var qLabel = null, aLabel = null;
    strongs.forEach(function (s) {
      var t = s.textContent.trim();
      if (!qLabel && /^Q:?\s*$/.test(t)) qLabel = s;
      else if (!aLabel && /^A:?\s*$/.test(t)) aLabel = s;
    });
    if (qLabel && aLabel && qLabel.parentNode === li && aLabel.parentNode === li) {
      return { q: htmlBetween(qLabel, aLabel).trim(), a: htmlAfter(aLabel).trim() };
    }
    // Flashcards: whole answer lives inside a strong that starts "A:".
    var ansStrong = null;
    strongs.forEach(function (s) {
      if (!ansStrong && /^A:/.test(s.textContent.trim())) ansStrong = s;
    });
    if (ansStrong) {
      var a = stripLabel(ansStrong.innerHTML, "A");
      var clone = li.cloneNode(true);
      var cs = Array.prototype.slice.call(clone.querySelectorAll("strong"));
      for (var i = 0; i < cs.length; i++) {
        if (/^A:/.test(cs[i].textContent.trim())) { cs[i].parentNode.removeChild(cs[i]); break; }
      }
      var q = stripLabel(clone.innerHTML, "Q");
      if (q && a) return { q: q, a: a };
    }
    return null;
  }

  // ---- section builders -----------------------------------------------
  function nextList(heading) {
    var el = heading.nextElementSibling;
    while (el && !/^H[1-6]$/.test(el.tagName)) {
      if (el.tagName === "UL" || el.tagName === "OL") return el;
      el = el.nextElementSibling;
    }
    return null;
  }

  function buildBulletSection(heading) {
    var list = nextList(heading);
    if (!list || list.getAttribute("data-fc-done")) return false;
    var cards = [];
    list.querySelectorAll(":scope > li").forEach(function (li) {
      var c = parseListItem(li);
      if (c) cards.push({ q: c.q, a: c.a, eyebrow: null });
    });
    if (!cards.length) return false;
    list.setAttribute("data-fc-done", "1");
    list.style.display = "none";
    insertGrid(heading, cards, list);
    return true;
  }

  function headingLevel(h) {
    var m = /^H([1-6])$/.exec(h.tagName);
    return m ? parseInt(m[1], 10) : 6;
  }

  // A card starts at either "**Card N ...**" (a <p><strong>) or "### Card N" (a
  // heading), both used across the tracks.
  function isCardHeading(el) {
    if (!el) return false;
    if (/^H[3-6]$/.test(el.tagName)) return /^Card\b/i.test(el.textContent.trim());
    if (el.tagName === "P") {
      var s = el.querySelector("strong");
      return !!(s && /^Card\b/i.test(s.textContent.trim()));
    }
    return false;
  }
  function cardTitle(el) {
    var s = el.querySelector && el.querySelector("strong");
    return (s ? s.textContent : el.textContent).trim();
  }
  function findQuestion(el) {
    if (el.tagName === "P" && /^\s*Q\s*:/.test(el.textContent)) return el;
    if (el.querySelectorAll) {
      var ps = el.querySelectorAll("p");
      for (var k = 0; k < ps.length; k++) {
        if (/^\s*Q\s*:/.test(ps[k].textContent)) return ps[k];
      }
    }
    return null;
  }
  // Answer is a <details> (??? note) or an inline "**A:** ..." paragraph.
  function findAnswer(el) {
    var d = el.tagName === "DETAILS" ? el : (el.querySelector ? el.querySelector("details") : null);
    if (d) return { kind: "details", node: d };
    function aPara(p) {
      var s = p.querySelector("strong");
      return s && /^A:?/.test(s.textContent.trim());
    }
    if (el.tagName === "P" && aPara(el)) return { kind: "para", node: el };
    if (el.querySelectorAll) {
      var ps = el.querySelectorAll("p");
      for (var k = 0; k < ps.length; k++) if (aPara(ps[k])) return { kind: "para", node: ps[k] };
    }
    return null;
  }
  function answerHTML(ans) {
    var clone = ans.node.cloneNode(true);
    if (ans.kind === "details") {
      var sm = clone.querySelector("summary");
      if (sm) sm.parentNode.removeChild(sm);
      return clone.innerHTML.trim();
    }
    var as = clone.querySelector("strong");
    if (as && /^A:?/.test(as.textContent.trim())) as.parentNode.removeChild(as);
    return stripLabel(clone.innerHTML, "A");
  }
  function extractQuestion(pEl) {
    var clone = pEl.cloneNode(true);
    var qs = clone.querySelector("strong");
    if (qs && /^Q:?/.test(qs.textContent.trim())) qs.parentNode.removeChild(qs);
    return stripLabel(clone.innerHTML, "Q");
  }
  // Some cards put the whole Q and A in one element (a <p> with both a "Q:" and
  // an "A:" strong, like the mock-exam cards). Reuse the list-item parser on the
  // element and its descendants.
  function deepParseQA(el) {
    var r = parseListItem(el);
    if (r) return r;
    if (el.querySelectorAll) {
      var cs = el.querySelectorAll("p, li");
      for (var k = 0; k < cs.length; k++) {
        r = parseListItem(cs[k]);
        if (r) return r;
      }
    }
    return null;
  }

  function buildSpacedSection(heading) {
    if (heading.getAttribute("data-fc-done")) return false;
    var lvl = headingLevel(heading);
    // Collect the section's body elements (until the next same/higher heading).
    var body = [], el = heading.nextElementSibling;
    while (el) {
      var m = /^H([1-6])$/.exec(el.tagName);
      if (m && parseInt(m[1], 10) <= lvl) break;
      body.push(el);
      el = el.nextElementSibling;
    }
    // Walk body, grouping (Card title p) + question + answer. The question and
    // the answer <details> may sit directly after the title or be wrapped in a
    // <blockquote> (both authoring styles are used), so search each group deep.
    var cards = [], hidden = [];
    for (var i = 0; i < body.length; i++) {
      if (!isCardHeading(body[i])) continue;
      var title = cardTitle(body[i]);
      var group = [body[i]], j;
      for (j = i + 1; j < body.length && !isCardHeading(body[j]); j++) group.push(body[j]);
      i = j - 1;

      var q = null, a = null, g, k;
      // Combined Q+A in one element (mock-exam cards).
      for (k = 1; k < group.length; k++) {
        var qa = deepParseQA(group[k]);
        if (qa) { q = qa.q; a = qa.a; break; }
      }
      // Otherwise a separate question plus a details/A-paragraph answer.
      if (q === null) {
        var qNode = null, ans = null;
        for (k = 1; k < group.length; k++) {
          if (!qNode) qNode = findQuestion(group[k]);
          if (!ans) ans = findAnswer(group[k]);
        }
        if (qNode && ans) { q = extractQuestion(qNode); a = answerHTML(ans); }
      }
      if (q === null || a === null) continue;
      cards.push({ q: q, a: a, eyebrow: title });
      group.forEach(function (gg) { hidden.push(gg); });
    }
    if (!cards.length) return false;
    heading.setAttribute("data-fc-done", "1");
    hidden.forEach(function (g) { g.style.display = "none"; });
    insertGrid(heading, cards, hidden[hidden.length - 1] || heading);
    return true;
  }

  // ---- DOM construction -----------------------------------------------
  function buildFace(faceClass, tag, html, hint, eyebrow) {
    var face = document.createElement("span");
    face.className = "fc-face " + faceClass;

    var tagEl = document.createElement("span");
    tagEl.className = "fc-tag";
    tagEl.textContent = tag;
    face.appendChild(tagEl);

    if (eyebrow) {
      var eb = document.createElement("span");
      eb.className = "fc-eyebrow";
      eb.textContent = eyebrow;
      face.appendChild(eb);
    }

    var text = document.createElement("span");
    text.className = "fc-text";
    text.innerHTML = html; // authored workbook content, not user input
    face.appendChild(text);

    if (hint) {
      var h = document.createElement("span");
      h.className = "fc-hint";
      h.textContent = hint;
      face.appendChild(h);
    }
    return face;
  }

  function buildCard(card) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "fc-card";
    if (/<pre|<div class="highlight"/.test(card.a)) btn.className += " fc-card--code";
    btn.setAttribute("aria-pressed", "false");
    btn.setAttribute("aria-label", "Flashcard, click to reveal the answer");

    var inner = document.createElement("span");
    inner.className = "fc-inner";
    inner.appendChild(buildFace("fc-front", "Q", card.q, "Click to flip", card.eyebrow));
    inner.appendChild(buildFace("fc-back", "A", card.a, null, card.eyebrow));
    btn.appendChild(inner);

    btn.addEventListener("click", function () {
      var flipped = btn.classList.toggle("flipped");
      btn.setAttribute("aria-pressed", flipped ? "true" : "false");
    });
    return btn;
  }

  function insertGrid(heading, cards, hideAfter) {
    var help = document.createElement("p");
    help.className = "fc-help";
    help.textContent =
      "Test yourself: read the question, answer it in your head, then click the card to check.";

    var grid = document.createElement("div");
    grid.className = "fc-grid";
    cards.forEach(function (c) { grid.appendChild(buildCard(c)); });

    heading.insertAdjacentElement("afterend", grid);
    grid.insertAdjacentElement("beforebegin", help);
  }

  // ---- entry -----------------------------------------------------------
  function enhance() {
    var headings = document.querySelectorAll("h2, h3");
    headings.forEach(function (hd) {
      var t = hd.textContent.trim().toLowerCase();
      if (t === "flashcards" || t === "consolidated flashcards") buildBulletSection(hd);
      else if (t === "spaced repetition") buildSpacedSection(hd);
    });
  }

  if (typeof window.document$ !== "undefined" && window.document$.subscribe) {
    window.document$.subscribe(enhance);
  } else if (document.readyState !== "loading") {
    enhance();
  } else {
    document.addEventListener("DOMContentLoaded", enhance);
  }
})();
