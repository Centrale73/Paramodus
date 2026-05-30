// ─── CRM Panel ────────────────────────────────────────────────────────────────

let crmAllEvents = [];
let crmCurrentFilter = 'all';

// Helper: the pywebview bridge (window.pywebview.api). Returns null before ready.
function _crmApi() {
    return (window.pywebview && window.pywebview.api) || null;
}

async function crmRefresh() {
    const tbody = document.getElementById('crm-table-body');
    tbody.innerHTML = '<tr><td colspan="5" style="padding:20px; text-align:center; color:var(--text-muted);">Loading…</td></tr>';
    const api = _crmApi();
    if (!api) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding:20px; text-align:center; color:var(--text-muted);">En attente du backend…</td></tr>';
        return;
    }
    try {
        const data = await api.get_urgent_events();
        if (data && data.error) {
            tbody.innerHTML = `<tr><td colspan="5" style="padding:20px; text-align:center; color:#ef4444;">Erreur CRM : ${data.error}</td></tr>`;
            crmAllEvents = [];
            return;
        }
        crmAllEvents = (data && data.events) || [];
        crmRender();
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding:20px; text-align:center; color:#ef4444;">Failed to load CRM data.</td></tr>';
    }
}

function crmSetFilter(filter, btn) {
    crmCurrentFilter = filter;
    document.querySelectorAll('.crm-filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    crmRender();
}

function crmRender() {
    const tbody = document.getElementById('crm-table-body');
    const urgencyDot = { green: '🟢', yellow: '🟡', red: '🔴', grey: '⚪' };

    let filtered = crmAllEvents;
    if (crmCurrentFilter !== 'all') {
        filtered = crmAllEvents.filter(e => e.urgency === crmCurrentFilter);
    }

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding:20px; text-align:center; color:var(--text-muted);">Aucun événement.</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(e => `
        <tr class="crm-row crm-row-${e.urgency}" data-id="${e.id}">
            <td style="padding:6px 4px;">${urgencyDot[e.urgency] || '⚪'}</td>
            <td style="padding:6px 4px; font-weight:500;">${e.city || '—'}</td>
            <td style="padding:6px 4px; max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${e.event_name}">${e.event_name}</td>
            <td style="padding:6px 4px; font-size:0.72rem; color:var(--text-muted);">${e.best_contact || '—'}</td>
            <td style="padding:6px 4px; white-space:nowrap;">
                <button onclick="crmLogContact(${e.org_id}, '${(e.event_name || '').replace(/'/g, "\\'")}')"
                    style="font-size:0.7rem; padding:2px 6px; border-radius:4px; border:1px solid rgba(255,255,255,0.12); background:transparent; color:var(--text-muted); cursor:pointer;" title="Journaliser un contact">✉</button>
                <button onclick="crmShowEmails(${e.org_id}, '${(e.event_name || '').replace(/'/g, "\\'")}')"
                    style="font-size:0.7rem; padding:2px 6px; border-radius:4px; border:1px solid rgba(255,255,255,0.12); background:transparent; color:var(--text-muted); cursor:pointer;" title="Voir les courriels récents (Gmail)">📧</button>
                <button onclick="crmDeleteEvent(event, ${e.id})"
                    style="font-size:0.7rem; padding:2px 6px; border-radius:4px;
                           border:1px solid rgba(239,68,68,0.3); background:transparent;
                           color:#ef4444; cursor:pointer; margin-left:2px;" title="Delete event">🗑</button>
            </td>
        </tr>
    `).join('');
}

async function crmLogContact(orgId, eventName) {
    if (!orgId) { alert('Aucun organisme lié à cet événement.'); return; }
    const api = _crmApi();
    if (!api) { alert('Backend non prêt.'); return; }

    const summary = prompt(`Journaliser un contact pour : ${eventName}\nRésumé :`);
    if (!summary) return;
    const status = prompt('Statut ? (Contacté / Intéressé / À relancer / Rencontre prévue / Refus / Bon potentiel futur)', 'Contacté');
    if (!status) return;
    const followUp = prompt('Date de relance ? (AAAA-MM-JJ ou laisser vide)', '');

    try {
        const res = await api.log_crm_contact(orgId, status, summary, followUp || '', 'UI');
        if (res && res.status === 'success') {
            alert('✅ Contact journalisé !');
            crmRefresh();
        } else {
            alert('❌ Échec : ' + ((res && res.message) || 'erreur inconnue'));
        }
    } catch (e) {
        alert('❌ Échec : ' + e);
    }
}

// ─── Gmail: suivi des courriels (read-only) ────────────────────────────────────
async function crmShowEmails(orgId, eventName) {
    if (!orgId) { alert('Aucun organisme lié à cet événement.'); return; }
    const api = _crmApi();
    if (!api) { alert('Backend non prêt.'); return; }

    const panel = document.getElementById('crm-email-panel');
    const body = document.getElementById('crm-email-body');
    const titleEl = document.getElementById('crm-email-title');
    if (panel) panel.style.display = 'block';
    if (titleEl) titleEl.textContent = `Courriels — ${eventName}`;
    if (body) body.innerHTML = '<div style="color:var(--text-muted); padding:8px;">Chargement des courriels…</div>';

    let res;
    try {
        res = await api.get_org_emails(orgId, 5);
    } catch (e) {
        if (body) body.innerHTML = `<div style="color:#ef4444; padding:8px;">Erreur : ${e}</div>`;
        return;
    }

    if (!res || res.status !== 'success') {
        const msg = (res && res.message) || 'Gmail non activé ou identifiants manquants.';
        if (body) body.innerHTML = `<div style="color:var(--text-muted); padding:8px;">${msg}</div>`;
        return;
    }

    const emails = res.emails || [];
    if (emails.length === 0) {
        if (body) body.innerHTML = `<div style="color:var(--text-muted); padding:8px;">Aucun courriel récent trouvé${res.email ? ' pour ' + res.email : ''}.</div>`;
        return;
    }

    if (body) {
        body.innerHTML = emails.map(m => `
            <div style="padding:8px; margin-bottom:6px; border-radius:6px; background:rgba(255,255,255,0.04); border-left:2px solid var(--accent, #22c55e);">
                <div style="font-size:0.8rem; font-weight:500; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${(m.subject || '(sans objet)').replace(/</g, '&lt;')}</div>
                <div style="font-size:0.72rem; color:#888; margin:2px 0;">${(m.from || '').replace(/</g, '&lt;')} · ${(m.date || '')}</div>
                <div style="font-size:0.72rem; color:var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${(m.snippet || '').replace(/</g, '&lt;')}</div>
                <button onclick="crmLogContact(${orgId}, '${eventName.replace(/'/g, "\\'")}')"
                    style="margin-top:6px; font-size:0.7rem; padding:2px 8px; border-radius:4px; border:1px solid rgba(255,255,255,0.12); background:transparent; color:var(--text-muted); cursor:pointer;">Journaliser depuis ce courriel</button>
            </div>`).join('');
    }
}

function crmHideEmails() {
    const panel = document.getElementById('crm-email-panel');
    if (panel) panel.style.display = 'none';
}

function crmShowAddEvent() {
    const form = document.getElementById('crm-add-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function crmSubmitAddEvent() {
    const payload = {
        city: document.getElementById('crm-add-city').value,
        event_name: document.getElementById('crm-add-name').value,
        event_type: document.getElementById('crm-add-type').value,
        contact_month_start: parseInt(document.getElementById('crm-add-ms').value) || null,
        contact_month_end: parseInt(document.getElementById('crm-add-me').value) || null,
        notes: document.getElementById('crm-add-notes').value,
    };
    if (!payload.event_name) { alert('Le nom de l\'événement est requis.'); return; }
    const api = _crmApi();
    if (!api) { alert('Backend non prêt.'); return; }
    try {
        const res = await api.add_crm_event(
            payload.event_name,
            payload.city,
            payload.event_type,
            payload.contact_month_start,
            payload.contact_month_end,
            payload.notes
        );
        if (res && res.status === 'error') {
            alert('❌ Échec : ' + res.message);
            return;
        }
    } catch (e) {
        alert('❌ Échec : ' + e);
        return;
    }
    document.getElementById('crm-add-form').style.display = 'none';
    crmRefresh();
}


// ─── Calendar Panel ────────────────────────────────────────────────────────────

const MONTHS_FR = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];
let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth();
let calSelectedDay = null; // currently selected day number

// Pad a number to two digits
function _pad2(n) { return String(n).padStart(2, '0'); }

// Build a YYYY-MM-DD string from year, month (0-indexed), day
function _isoDate(y, m, d) {
    return `${y}-${_pad2(m + 1)}-${_pad2(d)}`;
}

function calRender() {
    document.getElementById('cal-month-label').textContent = `${MONTHS_FR[calMonth]} ${calYear}`;
    const grid = document.getElementById('cal-grid');
    grid.innerHTML = '';

    const firstDay = new Date(calYear, calMonth, 1).getDay();
    const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    const today = new Date();
    const monthNum = calMonth + 1;

    const activeEvents = crmAllEvents.filter(e =>
        e.contact_month_start <= monthNum && monthNum <= e.contact_month_end
    );

    // Empty cells before the first weekday
    for (let i = 0; i < firstDay; i++) {
        grid.innerHTML += `<div style="height:28px;"></div>`;
    }

    for (let d = 1; d <= daysInMonth; d++) {
        const isToday   = d === today.getDate() && calMonth === today.getMonth() && calYear === today.getFullYear();
        const isSelected = d === calSelectedDay;
        const hasEvents = activeEvents.length > 0;

        let bgColor;
        if (isSelected)     bgColor = 'rgba(108,92,231,0.55)';
        else if (isToday)   bgColor = 'var(--accent)';
        else if (hasEvents) bgColor = 'rgba(34,197,94,0.12)';
        else                bgColor = 'transparent';

        const textColor = (isToday && !isSelected) ? '#fff' : 'var(--text-primary)';
        const fontWeight = isSelected ? '700' : '400';

        grid.innerHTML += `
            <div onclick="calSelectDay(${d})"
                data-day="${d}"
                style="height:28px; display:flex; align-items:center; justify-content:center;
                       border-radius:6px; font-size:0.78rem; cursor:pointer;
                       background:${bgColor};
                       color:${textColor};
                       font-weight:${fontWeight};
                       transition:background 0.15s;"
                onmouseover="if(this.dataset.day != '${calSelectedDay}') this.style.background='rgba(255,255,255,0.08)'"
                onmouseout="if(this.dataset.day != '${calSelectedDay}') this.style.background='${bgColor}'">
                ${d}
            </div>`;
    }
}

/**
 * Called when a user clicks a calendar day.
 * - Marks the day as selected and re-renders the grid
 * - Populates the inline event form with the clicked date as start date
 * - If end date is before the new start, resets it to the same day
 */
function calSelectDay(day) {
    calSelectedDay = day;
    calRender(); // re-render to highlight selected day

    const startDateISO = _isoDate(calYear, calMonth, day);
    const dayLabel = `${day} ${MONTHS_FR[calMonth]} ${calYear}`;

    // Show active CRM events for this month in the day-events area
    const monthNum = calMonth + 1;
    const active = crmAllEvents.filter(e =>
        e.contact_month_start <= monthNum && monthNum <= e.contact_month_end
    );

    const eventsEl = document.getElementById('cal-day-events');
    if (active.length === 0) {
        eventsEl.innerHTML = `<span style="color:var(--text-muted);">Aucun événement actif en ${MONTHS_FR[calMonth]}.</span>`;
    } else {
        eventsEl.innerHTML =
            `<div style="font-weight:600; margin-bottom:6px; color:#fff;">${MONTHS_FR[calMonth]} — ${active.length} event(s)</div>` +
            active.map(e => `
                <div style="padding:6px 8px; margin-bottom:4px; border-radius:6px;
                            background:rgba(34,197,94,0.1); border-left:2px solid #22c55e;
                            display:flex; align-items:center; justify-content:space-between;">
                    <div>
                        <div style="font-size:0.8rem; font-weight:500; color:#fff;">${e.event_name}</div>
                        <div style="font-size:0.72rem; color:#888;">${e.city} · ${e.best_contact}</div>
                    </div>
                    <button onclick="crmDeleteEvent(event, ${e.id})"
                        style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:0.85rem;padding:2px 4px;"
                        title="Delete">🗑</button>
                </div>`).join('');
    }

    // Populate and reveal the inline event-creation form
    const form = document.getElementById('cal-event-form');
    if (!form) return;

    // Set start date display label
    const startLabelEl = document.getElementById('cal-form-start-label');
    if (startLabelEl) startLabelEl.textContent = dayLabel;

    // Set hidden start-date value
    const startDateInput = document.getElementById('cal-form-start-date');
    if (startDateInput) startDateInput.value = startDateISO;

    // Default end-date to same day if not yet set or if it's before new start
    const endDateInput = document.getElementById('cal-form-end-date');
    if (endDateInput) {
        if (!endDateInput.value || endDateInput.value < startDateISO) {
            endDateInput.value = startDateISO;
            endDateInput.min = startDateISO;
        } else {
            endDateInput.min = startDateISO;
        }
    }

    // Default start time to 09:00 if empty
    const startTimeInput = document.getElementById('cal-form-start-time');
    if (startTimeInput && !startTimeInput.value) startTimeInput.value = '09:00';

    // Default end time to 10:00 if empty
    const endTimeInput = document.getElementById('cal-form-end-time');
    if (endTimeInput && !endTimeInput.value) endTimeInput.value = '10:00';

    // Show the form
    form.style.display = 'block';

    // Scroll the form into view smoothly
    form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Validates and saves the new calendar event.
 * Calls api.add_calendar_event(title, start_datetime, end_datetime, notes) via the bridge.
 */
async function calSaveEvent() {
    const title     = (document.getElementById('cal-form-title')?.value || '').trim();
    const startDate = document.getElementById('cal-form-start-date')?.value;
    const startTime = document.getElementById('cal-form-start-time')?.value || '09:00';
    const endDate   = document.getElementById('cal-form-end-date')?.value;
    const endTime   = document.getElementById('cal-form-end-time')?.value || '10:00';
    const notes     = (document.getElementById('cal-form-notes')?.value || '').trim();

    if (!title) {
        _calFormError('Le titre de l\'événement est requis.');
        return;
    }
    if (!startDate) {
        _calFormError('Sélectionnez d\'abord un jour de début.');
        return;
    }
    if (!endDate) {
        _calFormError('La date de fin est requise.');
        return;
    }

    const startISO = `${startDate}T${startTime}:00`;
    const endISO   = `${endDate}T${endTime}:00`;

    if (endISO <= startISO) {
        _calFormError('La date/heure de fin doit être après le début.');
        return;
    }

    _calFormError(''); // clear any previous error

    const saveBtn = document.getElementById('cal-form-save-btn');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Enregistrement…'; }

    const api = _crmApi();
    if (!api) {
        // No bridge (dev mode): just log and show confirmation
        console.log('[CalSaveEvent] No bridge. Would save:', { title, startISO, endISO, notes });
        _calFormSuccess(`✅ Événement enregistré (mode dev) : ${title}`);
        calCancelEvent();
        return;
    }

    try {
        // Bridge call: api.add_calendar_event(title, start_datetime, end_datetime, notes)
        const res = await api.add_calendar_event(title, startISO, endISO, notes);
        if (res && res.status === 'error') {
            _calFormError('❌ Échec : ' + (res.message || 'erreur inconnue'));
        } else {
            _calFormSuccess(`✅ Événement "${title}" enregistré.`);
            calCancelEvent();
            crmRefresh();
        }
    } catch (e) {
        _calFormError('❌ Échec : ' + e);
    } finally {
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Enregistrer'; }
    }
}

/** Show an inline error message inside the form */
function _calFormError(msg) {
    const el = document.getElementById('cal-form-error');
    if (!el) return;
    el.textContent = msg;
    el.style.display = msg ? 'block' : 'none';
    el.style.color = '#ef4444';
}

/** Show a temporary success message below the form */
function _calFormSuccess(msg) {
    const el = document.getElementById('cal-form-error');
    if (!el) return;
    el.textContent = msg;
    el.style.display = 'block';
    el.style.color = '#22c55e';
    setTimeout(() => { el.style.display = 'none'; }, 3000);
}

/** Hide the event form and reset its fields */
function calCancelEvent() {
    const form = document.getElementById('cal-event-form');
    if (form) form.style.display = 'none';
    // Reset fields
    const ids = ['cal-form-title','cal-form-start-time','cal-form-end-date','cal-form-end-time','cal-form-notes'];
    ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    _calFormError('');
    calSelectedDay = null;
    calRender();
}

async function crmDeleteEvent(evt, eventId) {
  evt.stopPropagation();
  const confirmed = await showConfirmModal();
  if (!confirmed) return;
  const api = _crmApi();
  if (!api) { alert('Backend not ready.'); return; }
  try {
    const res = await api.delete_crm_event(eventId);
    if (res && res.status === 'success') {
      crmRefresh();
    } else {
      showAlertModal((res && res.message) || 'Delete failed.', 'Error', '❌');
    }
  } catch (e) {
    showAlertModal(String(e), 'Error', '❌');
  }
}

async function calDeleteEvent(evt, eventId) {
  evt.stopPropagation();
  const confirmed = await showConfirmModal();
  if (!confirmed) return;
  const api = _crmApi();
  if (!api) { alert('Backend not ready.'); return; }
  try {
    const res = await api.delete_calendar_event(eventId);
    if (res && res.status === 'success') {
      crmRefresh();
      calRender();
    } else {
      showAlertModal((res && res.message) || 'Delete failed.', 'Error', '❌');
    }
  } catch (e) {
    showAlertModal(String(e), 'Error', '❌');
  }
}

function calPrev() {
    calMonth--;
    if (calMonth < 0) { calMonth = 11; calYear--; }
    // Reset selection when navigating away
    calSelectedDay = null;
    const form = document.getElementById('cal-event-form');
    if (form) form.style.display = 'none';
    calRender();
}

function calNext() {
    calMonth++;
    if (calMonth > 11) { calMonth = 0; calYear++; }
    calSelectedDay = null;
    const form = document.getElementById('cal-event-form');
    if (form) form.style.display = 'none';
    calRender();
}
