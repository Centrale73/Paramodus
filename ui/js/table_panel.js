// ─── Table Panel ──────────────────────────────────────────────────────────────

let tableColumns = ['Column 1', 'Column 2'];
let tableRows    = [['', '']];

function tableRender() {
  const table    = document.getElementById('custom-table');
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
  if (!thead) { thead=document.createElement('thead'); thead.id='custom-table-head'; table.prepend(thead); }
  thead.innerHTML = `<tr>
    <th style="width:32px;padding:4px 6px;font-size:0.68rem;color:var(--text-muted);font-weight:500;text-align:left;">#</th>
    ${tableColumns.map(col=>`
      <th style="padding:4px 6px;font-size:0.72rem;color:var(--text-primary);font-weight:600;
                 text-align:left;border-bottom:1px solid rgba(255,255,255,0.1);">
        ${col.replace(/</g,'&lt;')}</th>`).join('')}
    <th style="width:28px;"></th>
  </tr>`;
}

function tableAddColumn() {
  tableColumns.push(`Column ${tableColumns.length+1}`);
  tableRows.forEach(r=>r.push(''));
  tableRender();
}

function tableRemoveColumn(ci) {
  if (tableColumns.length <= 1) return;
  tableColumns.splice(ci,1);
  tableRows.forEach(r=>r.splice(ci,1));
  tableRender();
}

function tableAddRow() {
  tableRows.push(new Array(tableColumns.length).fill(''));
  tableRender();
  setTimeout(()=>{
    const inputs=document.querySelectorAll('#custom-table-body tr:last-child td input');
    if(inputs[0]) inputs[0].focus();
  },30);
}

function tableRemoveRow(ri) {
  if (tableRows.length<=1) { tableRows[0]=new Array(tableColumns.length).fill(''); tableRender(); return; }
  tableRows.splice(ri,1);
  tableRender();
}

async function tableSendToAgent() {
  const api = (window.pywebview && window.pywebview.api) || null;
  const fb  = document.getElementById('table-agent-feedback');
  const header = `| # | ${tableColumns.join(' | ')} |`;
  const sep    = `|---|${tableColumns.map(()=>'---').join('|')}|`;
  const body   = tableRows.map((r,i)=>`| ${i+1} | ${tableColumns.map((_,ci)=>r[ci]||'').join(' | ')} |`).join('\n');
  const markdown = `${header}\n${sep}\n${body}`;

  if (!api) {
    if (typeof appendMessage==='function') appendMessage('user',`Table data:\n\n${markdown}`);
    return;
  }
  if (fb) { fb.style.display='block'; fb.textContent='Sending to agent…'; fb.style.color='var(--text-muted)'; }
  try {
    const res = await api.table_delegate_query(markdown);
    if (res && res.status==='error') {
      if (fb) { fb.textContent='❌ '+res.message; fb.style.color='#ef4444'; }
    } else {
      if (fb) { fb.textContent='✅ Table forwarded to agent.'; fb.style.color='#22c55e';
                setTimeout(()=>{ fb.style.display='none'; },3000); }
    }
  } catch(e) { if(fb){fb.textContent='❌ '+e;fb.style.color='#ef4444';} }
}

document.addEventListener('DOMContentLoaded', ()=>tableRender());
