(function () {
  var input = document.getElementById('provider-search');
  if (!input) { return; }
  var items = Array.prototype.slice.call(document.querySelectorAll('#provider-list [data-provider]'));
  var status = document.getElementById('search-status');
  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    var shown = 0;
    items.forEach(function (el) {
      var hit = !q || el.getAttribute('data-provider').indexOf(q) !== -1;
      el.hidden = !hit;
      if (hit) { shown += 1; }
    });
    if (status) { status.textContent = shown + (shown === 1 ? ' provider' : ' providers') + ' shown'; }
  });
})();
