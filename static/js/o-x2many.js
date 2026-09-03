/* ============================================================================
   Dinamik satır widget'ı (Odoo "one2many" alanı).

   Projede birbirinden bağımsız ÜÇ uygulama vardı:
     - purchasing/order_create_form  (klonlama + tedarikçi→ürün filtreleme)
     - sales/order_form              (klonlama)
     - production/recipe_create      (JS template literal + %100 doğrulayıcı)

   Hepsi bu tek widget'a indi. KRİTİK: input name'leri JS'te DEĞİL, sunucunun
   bastığı satır markup'ında yaşar — bu yüzden view'lardaki
   request.POST.getlist('product') gibi çağrılar aynen çalışmaya devam eder.

   Sözleşme:
     [data-o-x2many]              kapsayıcı, data-o-min="1"
     [data-o-x2many-rows]         satırların konteyneri
     <template data-o-x2many-template>  yeni satır şablonu (yoksa ilk satır klonlanır)
     [data-o-x2many-add]          ekle butonu
     [data-o-x2many-del]          satır içi sil butonu
     [data-o-filter-source="#id"] + [data-o-filter-attr="supplier"]
                                  option'ları başka bir alana göre filtreler
     [data-o-x2many-sum]          data-o-sum-field / -target / -label
   ========================================================================== */
(function (window, document) {
  'use strict';

  function rowsOf(root) {
    var box = root.querySelector('[data-o-x2many-rows]');
    return box ? O.$$(':scope > .o-x2many-row', box) : [];
  }

  function minOf(root) {
    return parseInt(root.getAttribute('data-o-min') || '1', 10);
  }

  /**
   * Filtre kaynağını çözer.
   *   "#supplier"  -> belgedeki tekil alan (tüm satırlar için ortak)
   *   "^product"   -> AYNI SATIRDAKİ [name=product] alanı
   */
  function filterSource(select) {
    var ref = select.getAttribute('data-o-filter-source') || '';
    if (!ref) return null;
    if (ref.charAt(0) === '^') {
      var row = select.closest('.o-x2many-row');
      return row ? row.querySelector('[name="' + ref.slice(1) + '"]') : null;
    }
    try { return document.querySelector(ref); } catch (e) { return null; }
  }

  /* ── option filtreleme (ör. tedarikçi -> ürün, ürün -> lot) ───────────── */
  function applyFilters(root) {
    O.$$('select[data-o-filter-source]', root).forEach(function (select) {
      var source = filterSource(select);
      if (!source) return;
      var attr = select.getAttribute('data-o-filter-attr') || 'filter';
      var wanted = source.value;

      O.$$('option[data-' + attr + ']', select).forEach(function (option) {
        var match = option.getAttribute('data-' + attr) === wanted;
        option.hidden = !match;
        option.disabled = !match;
      });

      // Seçili option artık geçerli değilse temizle.
      var current = select.selectedOptions[0];
      if (current && current.value && current.getAttribute('data-' + attr) !== wanted) {
        select.value = '';
      }
    });
  }

  /* ── canlı toplam (ör. reçete oranları %100 olmalı) ───────────────────── */
  function updateSum(root) {
    var box = root.querySelector('[data-o-x2many-sum]');
    if (!box) return;

    var field = box.getAttribute('data-o-sum-field');
    var target = parseFloat(box.getAttribute('data-o-sum-target') || 'NaN');
    var label = box.getAttribute('data-o-sum-label') || O.text('msgTotal', 'Toplam');
    var suffix = box.getAttribute('data-o-sum-suffix') || '';

    var total = 0;
    O.$$('[name="' + field + '"]', root).forEach(function (input) {
      var value = parseFloat(input.value);
      if (!isNaN(value)) total += value;
    });

    var rounded = Math.round(total * 100) / 100;
    box.textContent = label + ': ' + rounded + suffix;
    box.classList.remove('o-sum-ok', 'o-sum-bad');
    if (!isNaN(target)) {
      box.classList.add(Math.abs(total - target) < 0.01 ? 'o-sum-ok' : 'o-sum-bad');
    }
  }

  function refresh(root) {
    var rows = rowsOf(root);
    var min = minOf(root);
    rows.forEach(function (row) {
      var del = row.querySelector('[data-o-x2many-del]');
      if (del) del.disabled = rows.length <= min;
    });
    applyFilters(root);
    updateSum(root);
  }

  function newRow(root) {
    var tpl = root.querySelector('template[data-o-x2many-template]');
    var node;
    if (tpl && tpl.content && tpl.content.firstElementChild) {
      node = tpl.content.firstElementChild.cloneNode(true);
    } else {
      var first = rowsOf(root)[0];
      if (!first) return null;
      node = first.cloneNode(true);
    }
    O.$$('input, select, textarea', node).forEach(function (field) {
      if (field.type === 'checkbox' || field.type === 'radio') field.checked = false;
      else field.value = '';
    });
    return node;
  }

  function init(root) {
    if (root.dataset.oX2manyReady === '1') return;
    root.dataset.oX2manyReady = '1';

    var box = root.querySelector('[data-o-x2many-rows]');
    if (!box) return;

    root.addEventListener('click', function (event) {
      var add = event.target.closest('[data-o-x2many-add]');
      if (add) {
        event.preventDefault();
        var node = newRow(root);
        if (node) {
          box.appendChild(node);
          refresh(root);
          var focusable = node.querySelector('select, input');
          if (focusable) focusable.focus();
        }
        return;
      }

      var del = event.target.closest('[data-o-x2many-del]');
      if (del && rowsOf(root).length > minOf(root)) {
        event.preventDefault();
        var row = del.closest('.o-x2many-row');
        if (row) row.remove();
        refresh(root);
      }
    });

    root.addEventListener('input', function (event) {
      var box2 = root.querySelector('[data-o-x2many-sum]');
      if (box2 && event.target.name === box2.getAttribute('data-o-sum-field')) updateSum(root);
    });

    // Filtre kaynağı kapsayıcının DIŞINDA olabilir (ör. tedarikçi seçimi).
    // Satır içi kaynaklar (^name) için delege change handler yeterli.
    O.$$('select[data-o-filter-source]', root).forEach(function (select) {
      var ref = select.getAttribute('data-o-filter-source') || '';
      if (ref.charAt(0) === '^') return;
      var source = filterSource(select);
      if (source && source.dataset.oFilterBound !== '1') {
        source.dataset.oFilterBound = '1';
        source.addEventListener('change', function () { applyFilters(root); });
      }
    });

    root.addEventListener('change', function () { applyFilters(root); });

    refresh(root);
  }

  function initAll(scope) {
    O.$$('[data-o-x2many]', scope || document).forEach(init);
  }

  document.addEventListener('DOMContentLoaded', function () { initAll(); });
  // AJAX bölgesi değişince içindeki widget'lar yeniden kurulmalı.
  O.on('o:region-replaced', function (event) { initAll(event.detail.region); });

  O.initX2many = initAll;
})(window, document);
