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
        // Goes through the pywebview bridge (api/bridge.py -> crm/db.get_urgent_events).
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
        // bridge.log_crm_contact(org_id, status, summary, follow_up_date, method)
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
// Pulls recent emails for an organisation via the pywebview bridge, then offers
// to log a contact straight from one of them.
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
        // bridge.get_org_emails(org_id, limit) -> {status, emails:[...], message?}
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
        // bridge.add_crm_event(event_name, city, event_type, contact_month_start, contact_month_end, notes)
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

    for (let i = 0; i < firstDay; i++) {
        grid.innerHTML += `<div style="height:28px;"></div>`;
    }

    for (let d = 1; d <= daysInMonth; d++) {
        const isToday = d === today.getDate() && calMonth === today.getMonth() && calYear === today.getFullYear();
        const hasEvents = activeEvents.length > 0;
        const bgColor = isToday ? 'var(--accent)' : hasEvents ? 'rgba(34,197,94,0.12)' : 'transparent';
        grid.innerHTML += `
            <div onclick="calSelectDay(${d})"
                style="height:28px; display:flex; align-items:center; justify-content:center;
                       border-radius:6px; font-size:0.78rem; cursor:pointer;
                       background:${bgColor};
                       color:${isToday ? '#fff' : 'var(--text-primary)'};"
                onmouseover="this.style.background='rgba(255,255,255,0.08)'"
                onmouseout="this.style.background='${bgColor}'">
                ${d}
            </div>`;
    }
}

function calSelectDay(day) {
    const monthNum = calMonth + 1;
    const active = crmAllEvents.filter(e =>
        e.contact_month_start <= monthNum && monthNum <= e.contact_month_end
    );
    const el = document.getElementById('cal-day-events');
    if (active.length === 0) {
        el.innerHTML = `<span style="color:var(--text-muted);">Aucun événement à contacter en ${MONTHS_FR[calMonth]}.</span>`;
        return;
    }
    el.innerHTML = `<div style="font-weight:600; margin-bottom:6px; color:#fff;">${MONTHS_FR[calMonth]} — ${active.length} événement(s) actif(s)</div>` +
        active.map(e => `
            <div style="padding:6px 8px; margin-bottom:4px; border-radius:6px; background:rgba(34,197,94,0.1); border-left:2px solid #22c55e;">
                <div style="font-size:0.8rem; font-weight:500; color:#fff;">${e.event_name}</div>
                <div style="font-size:0.72rem; color:#888;">${e.city} · ${e.best_contact}</div>
            </div>`).join('');
}

function calPrev() {
    calMonth--;
    if (calMonth < 0) { calMonth = 11; calYear--; }
    calRender();
}

function calNext() {
    calMonth++;
    if (calMonth > 11) { calMonth = 0; calYear++; }
    calRender();
}
