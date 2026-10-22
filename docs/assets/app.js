(function () {
  var root = document.documentElement;
  var input = document.getElementById('provider-search');
  var status = document.getElementById('search-status');
  var dir = document.getElementById('directory-details');
  var items = Array.prototype.slice.call(document.querySelectorAll('#provider-list [data-provider]'));
  if (input) {
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      var shown = 0;
      items.forEach(function (el) {
        var hit = !q || el.getAttribute('data-provider').indexOf(q) !== -1;
        el.hidden = !hit;
        if (hit) { shown += 1; }
      });
      if (dir && q) { dir.open = true; }
      if (status) { status.textContent = shown + (shown === 1 ? ' provider' : ' providers') + ' shown'; }
    });
  }
  var btn = document.querySelector('[data-theme-toggle]');
  function current() {
    var t = root.getAttribute('data-theme');
    if (t) { return t; }
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function paint() {
    if (!btn) { return; }
    var dark = current() === 'dark';
    btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
    btn.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    btn.querySelector('.i-sun').hidden = !dark;
    btn.querySelector('.i-moon').hidden = dark;
  }
  if (btn) {
    paint();
    btn.addEventListener('click', function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      paint();
    });
  }
})();
