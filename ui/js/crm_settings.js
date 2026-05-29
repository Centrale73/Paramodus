// ui/js/crm_settings.js
// CRM connector settings panel — injected into the Settings sidebar view.

(function () {
  'use strict';

  // ── Inject HTML into the Settings view ──────────────────────────────────
  function injectPanel() {
    const anchor = document.querySelector('#view-settings .config-section');
    if (!anchor || document.getElementById('crm-connector-section')) return;

    const panel = document.createElement('div');
    panel.id = 'crm-connector-section';
    panel.className = 'config-section';
    panel.style.cssText = 'margin-top:20px;';
    panel.innerHTML = `
      <label class="config-label">CRM Backend</label>

      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <button id="crm-btn-local"
          onclick="CRMSettings.selectType('local')"
          style="flex:1; padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.15);
                 background:rgba(255,255,255,0.08); color:#fff; cursor:pointer;
                 font-size:0.82rem; font-weight:600; transition:background 0.2s, border-color 0.2s;">
          Local (built-in)
        </button>
        <button id="crm-btn-relaticle"
          onclick="CRMSettings.selectType('relaticle')"
          style="flex:1; padding:8px; border-radius:8px; border:1px solid rgba(255,255,255,0.08);
                 background:transparent; color:#888; cursor:pointer;
                 font-size:0.82rem; font-weight:600; transition:background 0.2s, border-color 0.2s;">
          Relaticle
        </button>
      </div>

      <div id="crm-relaticle-fields" style="display:none; flex-direction:column; gap:10px;">
        <div>
          <label style="display:block; margin-bottom:4px; font-size:0.78rem; color:#888;">API URL</label>
          <input id="crm-url-input" type="url" placeholder="https://your-relaticle.app"
            style="width:100%; padding:9px 10px; border-radius:8px; font-size:0.85rem;
                   background:rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.1);
                   color:#fff; outline:none; box-sizing:border-box;" />
        </div>
        <div>
          <label style="display:block; margin-bottom:4px; font-size:0.78rem; color:#888;">API Token</label>
          <div style="position:relative;">
            <input id="crm-token-input" type="password"
              placeholder="Leave blank to keep saved token"
              style="width:100%; padding:9px 36px 9px 10px; border-radius:8px; font-size:0.85rem;
                     background:rgba(0,0,0,0.25); border:1px solid rgba(255,255,255,0.1);
                     color:#fff; outline:none; box-sizing:border-box;" />
            <button onclick="CRMSettings.toggleTokenVisibility()" title="Show/hide token"
              style="position:absolute; right:8px; top:50%; transform:translateY(-50%);
                     background:none; border:none; color:#888; cursor:pointer; font-size:1rem; padding:2px;">
              👁
            </button>
          </div>
          <div id="crm-token-hint" style="font-size:0.72rem; color:#666; margin-top:3px; display:none;">
            A token is already saved. Leave blank to keep it.
          </div>
        </div>
      </div>

      <div id="crm-status-bar"
        style="margin-top:10px; padding:8px 10px; border-radius:8px; font-size:0.8rem;
               display:none; align-items:center; gap:8px; border:1px solid transparent;">
        <span id="crm-status-dot" style="width:8px; height:8px; border-radius:50%; flex-shrink:0;"></span>
        <span id="crm-status-msg"></span>
      </div>

      <div style="display:flex; gap:8px; margin-top:12px;">
        <button id="crm-save-btn"
          onclick="CRMSettings.save()"
          style="flex:1; padding:9px; border-radius:8px; border:none;
                 background:var(--accent, #22c55e); color:#fff; cursor:pointer;
                 font-size:0.85rem; font-weight:600; transition:opacity 0.2s;">
          Save
        </button>
        <button id="crm-test-btn"
          onclick="CRMSettings.test()"
          style="flex:1; padding:9px; border-radius:8px;
                 border:1px solid rgba(255,255,255,0.12); background:transparent;
                 color:#ccc; cursor:pointer; font-size:0.85rem; transition:background 0.2s;">
          Test
        </button>
      </div>
    `;
    anchor.after(panel);
  }

  // ── State ────────────────────────────────────────────────────────────────
  let _currentType = 'local';

  function _api() { return window.pywebview && window.pywebview.api; }

  function _setButtonLoading(btnId, loading, label) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    btn.style.opacity = loading ? '0.6' : '1';
    btn.textContent = loading ? '…' : label;
  }

  function _showStatus(ok, msg) {
    const bar = document.getElementById('crm-status-bar');
    const dot = document.getElementById('crm-status-dot');
    const txt = document.getElementById('crm-status-msg');
    if (!bar) return;
    bar.style.display = 'flex';
    bar.style.background   = ok ? 'rgba(34,197,94,0.1)'  : 'rgba(239,68,68,0.1)';
    bar.style.borderColor  = ok ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.25)';
    dot.style.background   = ok ? '#22c55e' : '#ef4444';
    txt.textContent = msg;
  }

  function _hideStatus() {
    const bar = document.getElementById('crm-status-bar');
    if (bar) bar.style.display = 'none';
  }

  function _applyTypeButtons(type) {
    const local  = document.getElementById('crm-btn-local');
    const rel    = document.getElementById('crm-btn-relaticle');
    const fields = document.getElementById('crm-relaticle-fields');
    if (!local || !rel) return;
    if (type === 'local') {
      local.style.background  = 'rgba(255,255,255,0.08)';
      local.style.borderColor = 'rgba(255,255,255,0.15)';
      local.style.color       = '#fff';
      rel.style.background    = 'transparent';
      rel.style.borderColor   = 'rgba(255,255,255,0.08)';
      rel.style.color         = '#888';
      if (fields) fields.style.display = 'none';
    } else {
      rel.style.background    = 'rgba(255,255,255,0.08)';
      rel.style.borderColor   = 'rgba(255,255,255,0.15)';
      rel.style.color         = '#fff';
      local.style.background  = 'transparent';
      local.style.borderColor = 'rgba(255,255,255,0.08)';
      local.style.color       = '#888';
      if (fields) fields.style.display = 'flex';
    }
  }

  // ── Public ───────────────────────────────────────────────────────────────
  const CRMSettings = {

    selectType(type) {
      _currentType = type;
      _applyTypeButtons(type);
      _hideStatus();
    },

    toggleTokenVisibility() {
      const inp = document.getElementById('crm-token-input');
      if (!inp) return;
      inp.type = inp.type === 'password' ? 'text' : 'password';
    },

    async load() {
      const api = _api();
      if (!api) return;
      try {
        const cfg = await api.get_crm_config();
        _currentType = cfg.type || 'local';
        _applyTypeButtons(_currentType);
        const urlInp = document.getElementById('crm-url-input');
        const hint   = document.getElementById('crm-token-hint');
        if (urlInp && cfg.relaticle_url) urlInp.value = cfg.relaticle_url;
        if (hint) hint.style.display = cfg.token_set ? 'block' : 'none';
      } catch (e) {
        console.warn('[CRM] Failed to load config:', e);
      }
    },

    async save() {
      _setButtonLoading('crm-save-btn', true, 'Save');
      _hideStatus();
      const api = _api();
      if (!api) {
        _showStatus(false, 'pywebview not ready.');
        _setButtonLoading('crm-save-btn', false, 'Save');
        return;
      }
      const url   = (document.getElementById('crm-url-input')   || {}).value || '';
      const token = (document.getElementById('crm-token-input') || {}).value || '';
      try {
        const result = await api.save_crm_config(_currentType, url, token);
        _showStatus(result.ok, result.message);
        if (result.ok && _currentType === 'relaticle' && token) {
          const inp  = document.getElementById('crm-token-input');
          const hint = document.getElementById('crm-token-hint');
          if (inp)  inp.value = '';
          if (hint) hint.style.display = 'block';
        }
      } catch (e) {
        _showStatus(false, String(e));
      } finally {
        _setButtonLoading('crm-save-btn', false, 'Save');
      }
    },

    async test() {
      _setButtonLoading('crm-test-btn', true, 'Test');
      _hideStatus();
      const api = _api();
      if (!api) {
        _showStatus(false, 'pywebview not ready.');
        _setButtonLoading('crm-test-btn', false, 'Test');
        return;
      }
      try {
        const result = await api.test_crm_connection();
        _showStatus(result.ok, result.message);
      } catch (e) {
        _showStatus(false, String(e));
      } finally {
        _setButtonLoading('crm-test-btn', false, 'Test');
      }
    },
  };

  window.CRMSettings = CRMSettings;

  // ── Boot ─────────────────────────────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectPanel);
  } else {
    injectPanel();
  }

  // Load config whenever Settings tab opens
  const _origToggle = window.toggleSidebar;
  window.toggleSidebar = function (view) {
    if (typeof _origToggle === 'function') _origToggle(view);
    if (view === 'settings') setTimeout(() => CRMSettings.load(), 100);
  };

  // Also fire on pywebviewready in case Settings is already open
  window.addEventListener('pywebviewready', () => {
    const v = document.getElementById('view-settings');
    if (v && v.style.display !== 'none') CRMSettings.load();
  });

})();
