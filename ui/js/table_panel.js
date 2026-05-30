// ─── Table Panel ──────────────────────────────────────────────────────────────

let tableColumns = ['Column 1', 'Column 2'];
let tableRows    = [['', '']];

// Pending CSV parsed data — set during preview, cleared on confirm/dismiss
let _pendingCSV  = null; // { columns: string[], rows: string[][] }

// ─────────────────────────────────────────────────────────────────────────────
// Render
// ─────────────────────────────────────────────────────────────────────────────

function tableRender() {
  const table     = document.getElementById('custom-table');
  const headersEl = document.getElementById('table-headers');
  if (!table || !headersEl) return;

  headersEl.innerHTML = tableColumns.map((col, ci) => `
    <div style="display:flex;align-items:center;gap:3px;background:rgba(255,255,255,0.06);
                border-radius:6px;padding:2px 6px;border:1px solid rgba(255,255,255,0.1);">
      <input value="${col.replace(/"/g,'&quot;')}"
             oninput="tableColumns[${ci}]=this.value;tableRenderHead();"
             style="background:transparent;border:none;color:var(--text-primary);font-size:0.75rem;
                    width:${Math.max(60,col.length*8)}px;outline:none;">
      <button onclick="tableRemoveColumn(${ci})"
              style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:0.8rem;padding:0 2px;">×</button>
    </div>`).join('');

  tableRenderHead();

  let tbody = document.getElementById('custom-table-body');
  if (!tbody) {
    tbody = document.createElement('tbody');
    tbody.id = 'custom-table-body';
    table.appendChild(tbody);
  }
  tbody.innerHTML = tableRows.map((row, ri) => `
    <tr>
      <td style="padding:4px 6px;color:var(--text-muted);font-size:0.7rem;user-select:none;">${ri+1}</td>
      ${tableColumns.map((_,ci) => `
        <td style="padding:2px;">
          <input value="${(row[ci]||'').replace(/"/g,'&quot;')}"
                 oninput="tableRows[${ri}][${ci}]=this.value"
                 style="width:100%;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
                        border-radius:4px;padding:4px 6px;color:var(--text-primary);font-size:0.75rem;
                        outline:none;box-sizing:border-box;"
                 onkeydown="if(event.key==='Tab'&&!event.shiftKey&&${ci}===${tableColumns.length-1}&&${ri}===tableRows.length-1){event.preventDefault();tableAddRow();}">
        </td>`).join('')}
      <td><button onclick="tableRemoveRow(${ri})"
                  style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:0.75rem;padding:2px 4px;">🗑</button></td>
    </tr>`).join('');
}

function tableRenderHead() {
  const table = document.getElementById('custom-table');
  let thead = document.getElementById('custom-table-head');
  if (!thead) {
    thead = document.createElement('thead');
    thead.id = 'custom-table-head';
    table.prepend(thead);
  }
  thead.innerHTML = `<tr>
    <th style="width:32px;padding:4px 6px;font-size:0.68rem;color:var(--text-muted);font-weight:500;text-align:left;">#</th>
    ${tableColumns.map(col => `
      <th style="padding:4px 6px;font-size:0.72rem;color:var(--text-primary);font-weight:600;
                 text-align:left;border-bottom:1px solid rgba(255,255,255,0.1);">
        ${col.replace(/</g,'&lt;')}</th>`).join('')}
    <th style="width:28px;"></th>
  </tr>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Row / Column mutations
// ─────────────────────────────────────────────────────────────────────────────

function tableAddColumn() {
  tableColumns.push(`Column ${tableColumns.length + 1}`);
  tableRows.forEach(r => r.push(''));
  tableRender();
}

function tableRemoveColumn(ci) {
  if (tableColumns.length <= 1) return;
  tableColumns.splice(ci, 1);
  tableRows.forEach(r => r.splice(ci, 1));
  tableRender();
}

function tableAddRow() {
  tableRows.push(new Array(tableColumns.length).fill(''));
  tableRender();
  setTimeout(() => {
    const inputs = document.querySelectorAll('#custom-table-body tr:last-child td input');
    if (inputs[0]) inputs[0].focus();
  }, 30);
}

function tableRemoveRow(ri) {
  if (tableRows.length <= 1) {
    tableRows[0] = new Array(tableColumns.length).fill('');
    tableRender();
    return;
  }
  tableRows.splice(ri, 1);
  tableRender();
}

// ─────────────────────────────────────────────────────────────────────────────
// CSV Import
// ─────────────────────────────────────────────────────────────────────────────

/** Minimal CSV parser — handles quoted fields and CRLF/LF line endings. */
function _parseCSV(text) {
  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');

  function parseLine(line) {
    const fields = [];
    let cur = '', inQuote = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (inQuote) {
        if (ch === '"' && line[i+1] === '"') { cur += '"'; i++; }
        else if (ch === '"') { inQuote = false; }
        else { cur += ch; }
      } else {
        if (ch === '"') { inQuote = true; }
        else if (ch === ',') { fields.push(cur.trim()); cur = ''; }
        else { cur += ch; }
      }
    }
    fields.push(cur.trim());
    return fields;
  }

  const nonEmpty = lines.filter(l => l.trim() !== '');
  if (nonEmpty.length === 0) return null;

  const headers = parseLine(nonEmpty[0]);
  const rows    = nonEmpty.slice(1).map(l => {
    const f = parseLine(l);
    // Pad / truncate to match header count
    while (f.length < headers.length) f.push('');
    return f.slice(0, headers.length);
  });

  return { columns: headers, rows };
}

/** Called when user drags a file onto the drop zone. */
function tableHandleCSVDrop(evt) {
  const file = evt.dataTransfer && evt.dataTransfer.files && evt.dataTransfer.files[0];
  if (file) tableHandleCSVFile(file);
}

/** Reads the File object, parses it, shows the preview banner. */
function tableHandleCSVFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.csv') && file.type !== 'text/csv') {
    _tableSetDZLabel('Only .csv files are supported.');
    return;
  }
  _tableSetDZLabel(`Reading ${file.name}…`);

  const reader = new FileReader();
  reader.onload = e => {
    const parsed = _parseCSV(e.target.result);
    if (!parsed || parsed.columns.length === 0) {
      _tableSetDZLabel('Could not parse CSV — check the file format.');
      return;
    }
    _pendingCSV = parsed;
    _showCSVPreview(file.name, parsed);
  };
  reader.onerror = () => { _tableSetDZLabel('Error reading file.'); };
  reader.readAsText(file);

  // Reset the file input so the same file can be re-selected
  const inp = document.getElementById('table-csv-input');
  if (inp) inp.value = '';
}

function _showCSVPreview(filename, parsed) {
  const preview  = document.getElementById('table-csv-preview');
  const infoEl   = document.getElementById('table-csv-preview-info');
  const dzLabel  = document.getElementById('table-dz-label');

  if (dzLabel) dzLabel.textContent = `📄 ${filename}`;

  if (infoEl) {
    const colList = parsed.columns.slice(0, 5).join(', ')
                  + (parsed.columns.length > 5 ? ` … +${parsed.columns.length-5} more` : '');
    infoEl.innerHTML =
      `<b>${parsed.columns.length}</b> column${parsed.columns.length !== 1 ? 's' : ''} · `
    + `<b>${parsed.rows.length}</b> row${parsed.rows.length !== 1 ? 's' : ''}<br>`
    + `<span style="font-size:0.68rem;opacity:0.7;">${colList}</span>`;
  }

  if (preview) preview.style.display = 'block';
}

/** User clicked "Load into Table" — replace current table state with parsed CSV. */
function tableConfirmCSV() {
  if (!_pendingCSV) return;

  tableColumns = _pendingCSV.columns.slice();
  tableRows    = _pendingCSV.rows.map(r => r.slice());

  _pendingCSV = null;
  _dismissCSVPreview();
  tableRender();

  // Auto-send to agent with a confirmation message in the chat
  _tableSetFeedback('CSV loaded. Use ▶ Send to Agent when ready.', 'var(--accent)', 4000);
}

/** User clicked "Dismiss" — discard the pending CSV. */
function tableDismissCSV() {
  _pendingCSV = null;
  _dismissCSVPreview();
  _tableSetDZLabel('Drop a CSV here \u00a0or\u00a0 click to import');
}

function _dismissCSVPreview() {
  const preview = document.getElementById('table-csv-preview');
  if (preview) preview.style.display = 'none';
}

function _tableSetDZLabel(text) {
  const el = document.getElementById('table-dz-label');
  if (el) el.textContent = text;
}

function _tableSetFeedback(msg, color, timeout) {
  const fb = document.getElementById('table-agent-feedback');
  if (!fb) return;
  fb.style.display  = 'block';
  fb.textContent    = msg;
  fb.style.color    = color || 'var(--text-muted)';
  if (timeout) setTimeout(() => { fb.style.display = 'none'; }, timeout);
}

// ─────────────────────────────────────────────────────────────────────────────
// Send to Agent
// ─────────────────────────────────────────────────────────────────────────────

async function tableSendToAgent() {
  const api = (window.pywebview && window.pywebview.api) || null;
  const header   = `| # | ${tableColumns.join(' | ')} |`;
  const sep      = `|---|${tableColumns.map(() => '---').join('|')}|`;
  const body     = tableRows.map((r, i) =>
    `| ${i+1} | ${tableColumns.map((_, ci) => r[ci] || '').join(' | ')} |`
  ).join('\n');
  const markdown = `${header}\n${sep}\n${body}`;

  if (!api) {
    if (typeof appendMessage === 'function') appendMessage('user', `Table data:\n\n${markdown}`);
    return;
  }

  _tableSetFeedback('Sending to agent…', 'var(--text-muted)', 0);

  try {
    const res = await api.table_delegate_query(markdown);
    if (res && res.status === 'error') {
      _tableSetFeedback('❌ ' + res.message, '#ef4444', 0);
    } else {
      _tableSetFeedback('✅ Table forwarded to agent.', '#22c55e', 3000);
    }
  } catch (e) {
    _tableSetFeedback('❌ ' + e, '#ef4444', 0);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Drop-zone hover style (injected once)
// ─────────────────────────────────────────────────────────────────────────────

(function _injectDZStyle() {
  const style = document.createElement('style');
  style.textContent = `
    #table-csv-dropzone:hover,
    #table-csv-dropzone.table-dz-hover {
      border-color: var(--accent) !important;
      background: rgba(108,92,231,0.07);
    }
  `;
  document.head.appendChild(style);
})();

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => tableRender());
