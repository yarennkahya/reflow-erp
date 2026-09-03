/* ============================================================================
   Grafik görünümü — Chart.js köprüsü.

   Renkler CSS token'larından okunur, bu yüzden tema değişince grafik de
   yeniden çizilir (o:theme olayı). Şablon tarafı yalnızca bir <canvas> ve
   bir <script type="application/json"> veri adacığı basar.
   ========================================================================== */
(function (window, document) {
  'use strict';

  var charts = {};

  function token(name, fallback) {
    var value = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (value || '').trim() || fallback;
  }

  function palette() {
    return [
      token('--o-primary', '#6B4632'),
      token('--o-accent', '#C87941'),
      token('--o-info', '#3E6B8A'),
      token('--o-success', '#2E7D52'),
      token('--o-warning', '#B8791C'),
      token('--o-danger', '#C0392B'),
    ];
  }

  function withAlpha(color, alpha) {
    // #rrggbb -> rgba(); zaten rgb()/hsl() ise olduğu gibi bırak.
    if (color.charAt(0) !== '#' || color.length !== 7) return color;
    var r = parseInt(color.slice(1, 3), 16);
    var g = parseInt(color.slice(3, 5), 16);
    var b = parseInt(color.slice(5, 7), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
  }

  function build(canvas) {
    var payloadEl = document.getElementById(canvas.getAttribute('data-o-chart-data'));
    if (!payloadEl) return;

    var data;
    try { data = JSON.parse(payloadEl.textContent); } catch (e) { return; }
    if (!data || !data.labels) return;

    var type = canvas.getAttribute('data-o-chart') || 'bar';
    var colors = palette();
    var text = token('--o-text-muted', '#6B6058');
    var grid = token('--o-border', '#E3DDD6');
    var surface = token('--o-surface', '#FFFFFF');

    var multiAxis = (data.datasets || []).some(function (d) { return d.axis === 'value'; }) &&
                    (data.datasets || []).some(function (d) { return d.axis === 'count'; });

    var datasets = (data.datasets || []).map(function (set, index) {
      var color = colors[index % colors.length];
      var base = {
        label: set.label,
        data: set.data,
        borderColor: color,
        borderWidth: type === 'line' ? 2 : 1,
        backgroundColor: type === 'line' ? withAlpha(color, 0.14)
                       : type === 'doughnut' ? colors
                       : withAlpha(color, 0.82),
        borderRadius: type === 'bar' ? 2 : undefined,
        tension: type === 'line' ? 0.3 : undefined,
        fill: type === 'line',
      };
      if (multiAxis) base.yAxisID = set.axis === 'value' ? 'y1' : 'y';
      if (set.stack) base.stack = set.stack;
      return base;
    });

    var scales = {};
    if (type !== 'doughnut' && type !== 'pie') {
      scales.x = { grid: { display: false }, ticks: { color: text } };
      scales.y = {
        beginAtZero: true,
        grid: { color: grid },
        ticks: { color: text },
        border: { display: false },
      };
      if (multiAxis) {
        scales.y1 = {
          beginAtZero: true, position: 'right',
          grid: { drawOnChartArea: false },
          ticks: { color: text },
          border: { display: false },
        };
      }
    }

    if (charts[canvas.id]) charts[canvas.id].destroy();
    charts[canvas.id] = new window.Chart(canvas, {
      type: type,
      data: { labels: data.labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 260 },
        plugins: {
          legend: {
            display: datasets.length > 1 || type === 'doughnut',
            position: type === 'doughnut' ? 'right' : 'top',
            labels: { color: text, boxWidth: 10, boxHeight: 10, usePointStyle: true },
          },
          tooltip: {
            backgroundColor: token('--o-text', '#2B211B'),
            titleColor: surface,
            bodyColor: surface,
            borderColor: grid,
            borderWidth: 1,
            padding: 8,
            displayColors: true,
          },
        },
        scales: scales,
      },
    });
  }

  function initAll(scope) {
    if (!window.Chart) return;
    O.$$('canvas[data-o-chart]', scope || document).forEach(build);
  }

  document.addEventListener('DOMContentLoaded', function () { initAll(); });
  O.on('o:region-replaced', function (event) { initAll(event.detail.region); });
  // Tema değişince renkler token'lardan yeniden okunmalı.
  O.on('o:theme', function () { initAll(); });

  O.initCharts = initAll;
})(window, document);
