/* Departman seçilince bağlı pozisyon dropdown'ını filtreler.
   Veri kaynağı: <script type="application/json" id="o-dept-positions"> */
(function () {
  'use strict';

  function init(root) {
    var dataEl = (root || document).querySelector('#o-dept-positions');
    if (!dataEl) return;

    var byDept  = JSON.parse(dataEl.textContent);
    var deptSel = (root || document).querySelector('[name="department"]');
    var posSel  = (root || document).querySelector('[name="position"]');
    if (!deptSel || !posSel) return;

    var saved = posSel.value;

    function rebuild(restoreSaved) {
      var deptId = deptSel.value;
      var opts   = byDept[deptId] || [];

      /* Kilitli görünüm: sınıf `.o-field` wrapper'a uygulanır */
      var wrap = posSel.closest('.o-field');
      if (wrap) wrap.classList.toggle('o-field--locked', !deptId);

      posSel.innerHTML = '<option value="">---------</option>';
      opts.forEach(function (p) {
        var o = document.createElement('option');
        o.value = String(p.id);
        o.textContent = p.title;
        posSel.appendChild(o);
      });

      if (restoreSaved && saved) {
        posSel.value = saved;
      }
    }

    deptSel.addEventListener('change', function () {
      saved = '';
      rebuild(false);
    });

    rebuild(true);
  }

  document.addEventListener('DOMContentLoaded', function () { init(document); });
  document.addEventListener('o:region-replaced', function (e) { init(e.target); });
})();
