// ─── Table Panel ──────────────────────────────────────────────────────────────

let tableColumns = ['Column 1', 'Column 2'];
let tableRows    = [['', '']];

// Pending CSV parsed data — set during preview, cleared on confirm/dismiss
let _pendingCSV  = null; // { columns, rows, delim }

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
                  style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:0.75rem;padding:2px 4px;">\uD83D\uDDD1</button></td>
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
  tableColumns.push('Column ' + (tableColumns.length + 1));
  tableRows.forEach(function(r) { r.push(''); });
  tableRender();
}

function tableRemoveColumn(ci) {
  if (tableColumns.length <= 1) return;
  tableColumns.splice(ci, 1);
  tableRows.forEach(function(r) { r.splice(ci, 1); });
  tableRender();
}

function tableAddRow() {
  tableRows.push(new Array(tableColumns.length).fill(''));
  tableRender();
  setTimeout(function() {
    var inputs = document.querySelectorAll('#custom-table-body tr:last-child td input');
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
// CSV Parser
// ─────────────────────────────────────────────────────────────────────────────
//
// Handles:
//   - Comma, semicolon, or tab delimiters (auto-detected)
//   - Excel "sep=X" first-line hint (common in European exports)
//   - RFC-4180 quoted fields with escaped double-quotes ("")
//   - CRLF, LF, CR line endings
//   - UTF-8 BOM stripping
//
function _parseCSV(text) {
  // Strip UTF-8 BOM
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);

  // Strip residual null bytes (present after UTF-16 LE decode)
  text = text.replace(/\x00/g, '');

  var lines    = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  // Filter blank lines AND lines that were only null bytes (reduced to empty after strip)
  var nonEmpty = lines.filter(function(l) { return l.trim() !== ''; });
  if (nonEmpty.length === 0) return null;

  // ── Delimiter detection ────────────────────────────────────────────────────
  var startLine = 0;
  var delim     = ',';

  var sepHint = nonEmpty[0].match(/^sep=(.)/i);
  if (sepHint) {
    delim     = sepHint[1];
    startLine = 1;
  } else {
    var header = nonEmpty[0];
    var semis  = (header.match(/;/g)  || []).length;
    var commas = (header.match(/,/g)  || []).length;
    var tabs   = (header.match(/\t/g) || []).length;
    if      (semis  > commas && semis  >= tabs)  delim = ';';
    else if (tabs   > commas && tabs   >= semis)  delim = '\t';
    // else stays ','
  }

  // ── RFC-4180 field parser ──────────────────────────────────────────────────
  function parseLine(line) {
    var fields = [], cur = '', inQuote = false;
    for (var i = 0; i < line.length; i++) {
      var ch = line[i];
      if (inQuote) {
        if (ch === '"' && line[i+1] === '"') { cur += '"'; i++; }
        else if (ch === '"')                  { inQuote = false; }
        else                                  { cur += ch; }
      } else {
        if      (ch === '"')  { inQuote = true; }
        else if (ch === delim){ fields.push(cur.trim()); cur = ''; }
        else                  { cur += ch; }
      }
    }
    fields.push(cur.trim());
    return fields;
  }

  var dataLines = nonEmpty.slice(startLine);
  if (dataLines.length === 0) return null;

  var headers = parseLine(dataLines[0]);
  var rows    = dataLines.slice(1).map(function(l) {
    var f = parseLine(l);
    while (f.length < headers.length) f.push('');
    return f.slice(0, headers.length);
  });

  return { columns: headers, rows: rows, delim: delim };
}

// ─────────────────────────────────────────────────────────────────────────────
// CSV File Handling
// ─────────────────────────────────────────────────────────────────────────────

// Called when user drags a file onto the drop zone.
function tableHandleCSVDrop(evt) {
  var file = evt.dataTransfer && evt.dataTransfer.files && evt.dataTransfer.files[0];
  if (file) tableHandleCSVFile(file);
}

// Reads the File, tries UTF-8 first then falls back to ISO-8859-1 (Latin-1).
// Latin-1 covers the vast majority of legacy / European CSV exports
// (Excel on Windows often saves in the system code page, not UTF-8).
function tableHandleCSVFile(file) {
  if (!file) return;
  var name = file.name.toLowerCase();
  if (!name.endsWith('.csv') && file.type !== 'text/csv') {
    _tableSetDZLabel('Only .csv files are supported.');
    return;
  }
  _tableSetDZLabel('Reading ' + file.name + '\u2026');

  function tryParse(text) {
    var p = _parseCSV(text);
    return (p && p.columns.length > 0) ? p : null;
  }

  function readWith(encoding, cb) {
    var r = new FileReader();
    r.onload  = function(e) { cb(e.target.result); };
    r.onerror = function()  { _tableSetDZLabel('Error reading file.'); };
    r.readAsText(file, encoding);
  }

  // Encoding detection chain:
  //   1. Read as UTF-8
  //   2. If >10% null bytes  → UTF-16 LE (no BOM)
  //   3. Else if U+FFFD found → ISO-8859-1 / Latin-1
  //   4. Otherwise           → UTF-8 is fine
  readWith('UTF-8', function(utf8Text) {
    var nullCount = (utf8Text.match(/\x00/g) || []).length;
    if (nullCount > utf8Text.length * 0.1) {
      // UTF-16 LE: re-read with correct encoding
      readWith('UTF-16LE', function(utf16Text) {
        var parsed = tryParse(utf16Text);
        if (!parsed) { _tableSetDZLabel('Could not parse CSV \u2014 check the file format.'); return; }
        _pendingCSV = parsed;
        _showCSVPreview(file.name, parsed, 'UTF-16 LE');
      });
    } else if (utf8Text.indexOf('\uFFFD') !== -1) {
      // Legacy code-page encoding: retry as Latin-1
      readWith('ISO-8859-1', function(latin1Text) {
        var parsed = tryParse(latin1Text);
        if (!parsed) { _tableSetDZLabel('Could not parse CSV \u2014 check the file format.'); return; }
        _pendingCSV = parsed;
        _showCSVPreview(file.name, parsed, 'ISO-8859-1');
      });
    } else {
      var parsed = tryParse(utf8Text);
      if (!parsed) { _tableSetDZLabel('Could not parse CSV \u2014 check the file format.'); return; }
      _pendingCSV = parsed;
      _showCSVPreview(file.name, parsed, 'UTF-8');
    }
  });

  // Reset input so same file can be re-selected
  var inp = document.getElementById('table-csv-input');
  if (inp) inp.value = '';
}

function _showCSVPreview(filename, parsed, encoding) {
  var preview = document.getElementById('table-csv-preview');
  var infoEl  = document.getElementById('table-csv-preview-info');
  var dzLabel = document.getElementById('table-dz-label');

  if (dzLabel) dzLabel.textContent = '\uD83D\uDCC4 ' + filename;

  if (infoEl) {
    var colList     = parsed.columns.slice(0, 6).join(', ')
                    + (parsed.columns.length > 6 ? ' \u2026 +' + (parsed.columns.length - 6) + ' more' : '');
    var delimLabels = { ',': 'comma', ';': 'semicolon', '\t': 'tab' };
    var delimLabel  = delimLabels[parsed.delim] || parsed.delim;
    var encBadge    = encoding
      ? '<span style="margin-left:5px;padding:1px 5px;border-radius:3px;' +
        'background:rgba(255,255,255,0.07);font-size:0.65rem;">' + encoding + '</span>'
      : '';
    infoEl.innerHTML =
      '<b>' + parsed.columns.length + '</b> col' + (parsed.columns.length !== 1 ? 's' : '') +
      ' &middot; <b>' + parsed.rows.length + '</b> row' + (parsed.rows.length !== 1 ? 's' : '') +
      ' &middot; ' + delimLabel + '-delimited' + encBadge + '<br>' +
      '<span style="font-size:0.68rem;opacity:0.7;">' + colList + '</span>';
  }

  if (preview) preview.style.display = 'block';
}

// User confirmed — load CSV data into the table
function tableConfirmCSV() {
  if (!_pendingCSV) return;
  tableColumns = _pendingCSV.columns.slice();
  tableRows    = _pendingCSV.rows.map(function(r) { return r.slice(); });
  _pendingCSV  = null;
  _dismissCSVPreview();
  tableRender();
  _tableSetFeedback('CSV loaded. Use \u25B6 Send to Agent when ready.', 'var(--accent)', 5000);
}

// User dismissed — discard pending data
function tableDismissCSV() {
  _pendingCSV = null;
  _dismissCSVPreview();
  _tableSetDZLabel('Drop a CSV here \u00a0or\u00a0 click to import');
}

function _dismissCSVPreview() {
  var preview = document.getElementById('table-csv-preview');
  if (preview) preview.style.display = 'none';
}

function _tableSetDZLabel(text) {
  var el = document.getElementById('table-dz-label');
  if (el) el.textContent = text;
}

function _tableSetFeedback(msg, color, timeout) {
  var fb = document.getElementById('table-agent-feedback');
  if (!fb) return;
  fb.style.display = 'block';
  fb.textContent   = msg;
  fb.style.color   = color || 'var(--text-muted)';
  if (timeout) setTimeout(function() { fb.style.display = 'none'; }, timeout);
}

// ─────────────────────────────────────────────────────────────────────────────
// Send to Agent
// ─────────────────────────────────────────────────────────────────────────────

async function tableSendToAgent() {
  var api      = (window.pywebview && window.pywebview.api) || null;
  var header   = '| # | ' + tableColumns.join(' | ') + ' |';
  var sep      = '|---|' + tableColumns.map(function() { return '---'; }).join('|') + '|';
  var body     = tableRows.map(function(r, i) {
    return '| ' + (i+1) + ' | ' + tableColumns.map(function(_, ci) { return r[ci] || ''; }).join(' | ') + ' |';
  }).join('\n');
  var markdown = header + '\n' + sep + '\n' + body;

  if (!api) {
    if (typeof appendMessage === 'function') appendMessage('user', 'Table data:\n\n' + markdown);
    return;
  }

  _tableSetFeedback('Sending to agent\u2026', 'var(--text-muted)', 0);

  try {
    var res = await api.table_delegate_query(markdown);
    if (res && res.status === 'error') {
      _tableSetFeedback('\u274C ' + res.message, '#ef4444', 0);
    } else {
      _tableSetFeedback('\u2705 Table forwarded to agent.', '#22c55e', 3000);
    }
  } catch(e) {
    _tableSetFeedback('\u274C ' + e, '#ef4444', 0);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Drop-zone hover styles (injected once at load)
// ─────────────────────────────────────────────────────────────────────────────

(function _injectDZStyle() {
  var style = document.createElement('style');
  style.textContent = [
    '#table-csv-dropzone:hover,',
    '#table-csv-dropzone.table-dz-hover {',
    '  border-color: var(--accent) !important;',
    '  background: rgba(108,92,231,0.07);',
    '}'
  ].join('\n');
  document.head.appendChild(style);
})();

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function() { tableRender(); });
