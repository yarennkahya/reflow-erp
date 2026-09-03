/* ============================================================================
   Toplantı formu — canlı izin çakışması kontrolü.

   Endpoint URL'i şablondan data-* ile gelir; JS'te {% url %} olmaz.
   ========================================================================== */
(function (window, document) {
  'use strict';

  var form = document.querySelector('[data-o-conflict-url]');
  if (!form) return;

  var url = form.getAttribute('data-o-conflict-url');
  var warning = document.getElementById('o-conflict-warning');
  var dateInput = form.querySelector('[name="meeting_date"]');
  var startInput = form.querySelector('[name="start_time_only"]');
  var endInput = form.querySelector('[name="end_time_only"]');
  var organizer = form.querySelector('[name="organizer"]');
  var attendees = form.querySelector('[name="attendees"]');

  function hide() {
    if (!warning) return;
    warning.textContent = '';
    warning.hidden = true;
  }

  function check() {
    if (!warning) return;

    var ids = [];
    if (organizer && organizer.value) ids.push(organizer.value);
    if (attendees) {
      Array.prototype.forEach.call(attendees.selectedOptions, function (option) {
        if (ids.indexOf(option.value) === -1) ids.push(option.value);
      });
    }

    if (!dateInput || !dateInput.value || !startInput || !startInput.value ||
        !endInput || !endInput.value || !ids.length) {
      hide();
      return;
    }

    var params = new URLSearchParams({
      date: dateInput.value,
      start_time: startInput.value,
      end_time: endInput.value
    });
    ids.forEach(function (id) { params.append('employee_ids', id); });

    fetch(url + '?' + params.toString(), { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error('conflict'); return r.json(); })
      .then(function (data) {
        if (data.conflicts && data.conflicts.length) {
          warning.textContent = O.text('msgLeaveConflict',
            'Şu kişiler bu tarihte izinli görünüyor:') + ' ' + data.conflicts.join(', ');
          warning.hidden = false;
        } else {
          hide();
        }
      })
      .catch(hide);
  }

  [dateInput, startInput, endInput, organizer, attendees].forEach(function (el) {
    if (el) el.addEventListener('change', check);
  });
  check();
})(window, document);
