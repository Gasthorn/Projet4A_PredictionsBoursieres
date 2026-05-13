(function () {
  'use strict';

  var card = null;
  var hideTimer = null;
  var currentUrl = null;

  /* ── Build the floating card once ── */
  function buildCard() {
    if (card) return;
    card = document.createElement('div');
    card.id = 'apc-card';
    card.innerHTML =
      '<div class="apc-img-wrap"><img id="apc-img" src="" alt=""/><div class="apc-img-placeholder"><i class="fas fa-newspaper"></i></div></div>' +
      '<div class="apc-body">' +
        '<div id="apc-site" class="apc-site"></div>' +
        '<div id="apc-title" class="apc-title">Chargement…</div>' +
        '<div id="apc-desc" class="apc-desc"></div>' +
        '<div class="apc-footer"><span class="apc-hint">Cliquez pour lire l\'article complet</span>' +
        '<i class="fas fa-external-link-alt apc-ext-icon"></i></div>' +
      '</div>';
    document.body.appendChild(card);
  }

  /* ── Position card near cursor, avoiding viewport edges ── */
  function place(e) {
    if (!card) return;
    var W = 360, H = 300;
    var x = e.clientX + 24;
    var y = e.clientY - 60;
    if (x + W > window.innerWidth - 16)  x = e.clientX - W - 24;
    if (y + H > window.innerHeight - 16) y = window.innerHeight - H - 16;
    if (y < 8) y = 8;
    card.style.left = x + 'px';
    card.style.top  = y + 'px';
  }

  /* ── Fetch OG data and populate card ── */
  async function loadPreview(url, sourceFallback, titleFallback) {
    try {
      var resp = await fetch('/api/preview?url=' + encodeURIComponent(url));
      var data = await resp.json();
      if (currentUrl !== url) return; // stale

      var imgEl    = document.getElementById('apc-img');
      var titleEl  = document.getElementById('apc-title');
      var descEl   = document.getElementById('apc-desc');
      var siteEl   = document.getElementById('apc-site');
      var placeholder = card.querySelector('.apc-img-placeholder');

      siteEl.textContent  = data.site_name || sourceFallback || '';
      titleEl.textContent = data.title || titleFallback || 'Article';
      descEl.textContent  = data.description || '';

      if (data.image) {
        imgEl.onload  = function () { imgEl.style.display = 'block'; placeholder.style.display = 'none'; };
        imgEl.onerror = function () { imgEl.style.display = 'none';  placeholder.style.display = 'flex'; };
        imgEl.src = data.image;
      } else {
        imgEl.style.display = 'none';
        placeholder.style.display = 'flex';
      }

      card.classList.remove('apc-loading');
      card.classList.add('apc-visible');
    } catch (err) {
      if (currentUrl !== url) return;
      document.getElementById('apc-title').textContent = titleFallback || 'Aperçu indisponible';
      card.classList.remove('apc-loading');
      card.classList.add('apc-visible');
    }
  }

  /* ── Show card on hover ── */
  function onEnter(e) {
    var el  = this;
    var url = el.dataset.previewUrl || el.getAttribute('href') || '';
    if (!url || url === '#') return;

    buildCard();
    clearTimeout(hideTimer);

    var titleFb  = el.dataset.title  || '';
    var sourceFb = el.dataset.source || '';

    if (currentUrl === url) {
      place(e);
      card.style.display = 'flex';
      card.classList.add('apc-visible');
      return;
    }

    currentUrl = url;
    card.classList.remove('apc-visible');
    card.classList.add('apc-loading');
    card.style.display = 'flex';
    place(e);

    /* reset content */
    document.getElementById('apc-title').textContent = 'Chargement…';
    document.getElementById('apc-desc').textContent  = '';
    document.getElementById('apc-site').textContent  = sourceFb;
    var imgEl = document.getElementById('apc-img');
    imgEl.src = '';
    imgEl.style.display = 'none';
    card.querySelector('.apc-img-placeholder').style.display = 'flex';

    loadPreview(url, sourceFb, titleFb);
  }

  function onMove(e)  { place(e); }

  function onLeave()  {
    hideTimer = setTimeout(function () {
      if (card) card.classList.remove('apc-visible');
    }, 180);
  }

  /* ── Attach listeners to all unbound news links ── */
  function attach(root) {
    var links = (root || document).querySelectorAll('.analyse-news-link:not([data-apc-bound])');
    links.forEach(function (el) {
      el.setAttribute('data-apc-bound', '1');
      el.addEventListener('mouseenter', onEnter);
      el.addEventListener('mousemove',  onMove);
      el.addEventListener('mouseleave', onLeave);
    });
  }

  /* ── Bootstrap ── */
  document.addEventListener('DOMContentLoaded', function () { attach(); });

  /* Re-attach when Dash re-renders the news feed */
  var observer = new MutationObserver(function (mutations) {
    var needAttach = false;
    mutations.forEach(function (m) { if (m.addedNodes.length) needAttach = true; });
    if (needAttach) attach();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
