// OAW 消化系統 (catalog.py ui). No frameworks, no external resources.
// The main screen is the intake pipeline of docs/SKILL_INTAKE.md: the stage table, each food's
// stage and its current-stage actions all come from view.json (catalog_core.PIPELINE_STAGES), so
// the page, catalog.py menu and oaw_status.py show the same thing. Every food-derived string is
// set with textContent or a text node; this file never assigns markup. Display rules are kept in
// step with scripts/oaw_status.py.
'use strict';

(function () {
  // ------------------------------------------------------------------ display rules
  const LEVELS = { 'measured': '實測', 'static-measured': '靜態量測', 'not-measured': '未量測', 'historical-prior': '歷史證據' };
  const HEADLINES = {
    'nutritious': '營養', 'no-gain': '沒營養', 'untested': '未測', 'incomplete': '證據不完整', 'regressed': '變差',
    'diarrhea': '拉肚子', 'risky': '有疑慮', 'toxic': '有毒', 'inedible': '不能吃'
  };
  const FAMILY = {
    'nutritious': 'good', 'no-gain': 'gray', 'untested': 'gray', 'incomplete': 'gray', 'regressed': 'warn',
    'diarrhea': 'warn', 'risky': 'amber', 'toxic': 'bad', 'inedible': 'dark'
  };
  const DISPOSITIONS = { absorb: ['🟢', '吸收'], excrete: ['🔴', '排掉'], hold: ['🟡', '暫留'] };
  // Per-food stage states the engine writes; anything else is drawn as unknown, never guessed.
  const STAGE_STATES = ['done', 'partial', 'current', 'blocked', 'removed', 'todo', 'planned', 'skipped'];
  const METRICS = {
    'skills': 'skill 數', 'files': '檔案數', 'bytes': '大小（bytes）',
    'startup-loaded text bytes (codex)': '啟動載入文字 bytes（Codex）',
    'startup-loaded text bytes (claude)': '啟動載入文字 bytes（Claude）', 'hooks': 'hooks',
    'non-stdlib dependencies': '非標準函式庫相依', 'host settings writes': '寫入 host 設定', 'quality': '品質'
  };
  const BUILD_KINDS = { 'baseline': '基準版', 'restore-point': '還原點', 'absorb': '吸收', 'remove': '移除', 'restore': '還原', 'readd': '加回' };
  const HOSTS = { 'codex': 'Codex', 'claude': 'Claude' };
  const SEVERITY = { 'high': '高', 'medium': '中', 'low': '低', 'info': '資訊' };
  const TRIAGE = { 'benign': '已判良性', 'allergen': '已判過敏原', 'confirm-toxic': '你確認有毒' };
  const CHIPS = { 'free-checks-passed': '免費檢查通過', 'rules-updated-free-T0-pending': '規則已更新，待重跑免費檢查' };
  const INTEGRITY = { 'git-object-verified': 'git 物件驗證', 'unverified-against-commit': '未對 commit 驗證',
    'sha256-recorded': '已記 sha256（arXiv 沒有可驗證的 hash）' };
  // A paper's license rule (catalog_core.paper_license): what OAW may reuse from it.
  const REUSE = { 'quote-with-attribution': '可引用原文（要附出處）', 'ideas-only': '只取想法：重新實作，不複製原文' };
  const PLAN_STATUS = [
    ['waiting for standing policy', '等你設定常設預算'],
    ['within policy', '第 0/1 階段在常設預算內；第 2 階段和第二個 host 要先問你（v0 尚未開放付費實測）'],
    ['exceeds standing policy', '第 0/1 階段超過常設預算：需要你同意（v0 尚未開放付費實測）'],
    ['taste first', '先試吃：免費靜態檢查決定付費計畫'],
    ['no paid test: owner confirmed toxic', '不需實測：已確認有毒'],
    ['no paid test: oaw cannot digest', '不需實測：OAW 無法消化'],
    ['blocked', '被擋住：高嚴重度旗標要先分流'],
    ['no paid test needed', '不需付費實測：沒有可吸收的成分'],
    ['no components yet', '還沒有成分：論文要由 Elephant 拆成分（規劃中），或匯入已有的消化紀錄']
  ];
  const PLAN_STEPS = {
    'T0': '免費靜態檢查', 'T1': '離線整合', 'T2a': '人工分流旗標', 'G': 'Goldfish 盲審我們的吸收草稿', 'TX': '可拋棄環境試跑',
    'T3a-smoke': '行為 A/B 冒煙測試', 'T4': '和現有配方整合', 'P': '齊平底線（OAW＋食物 對 單吃食物）', 'T3a': '行為 A/B 完整測試'
  };
  // D13 (PRE-01): Stage 0/1 count against the per-food cap; Stage 2 always asks the owner first.
  const D13_STAGES = { 0: '第 0 階段（免費）', 1: '第 1 階段（篩選）', 2: '第 2 階段：先問你', overhead: '消化系統開銷' };
  const PLAN_STATES = {
    'done': '已完成', 'next': '下一步', 'planned': '已規劃', 'not available in v0': 'v0 尚未提供',
    'only if the smoke shows no deterministic negative': '冒煙沒有決定性負面才跑'
  };
  const KINDS = {
    'skill': 'skill', 'agent': 'agent', 'command': '指令', 'hook-set': 'hooks', 'mcp-server': 'MCP', 'plugin-manifest': 'plugin',
    'executable': '程式', 'dependency-manifest': '套件清單', 'instruction-file': '指示檔', 'binary': '二進位', 'docs': '文件',
    'other': '其他', 'method': '方法'
  };
  const DECISIONS = { 'absorbed': '已吸收', 'excreted': '已排掉', 'removed': '已移除', 'absorbed as backlog item': '已記成待辦（未改程式）' };
  const ORIGINS = { 'url': '你點名', 'scout': '每週偵查', 'import': '匯入' };
  const SANDBOX = {
    'isolated-venv': '隔離的 venv', 'project-copy': '專案副本', 'no-api-keys': '不帶 API key', 'no-network': '不連網',
    'disposable-vm': '可拋棄 VM'
  };
  const PLAN_ACTIONS = { 'retire': '停用', 'remove': '刪除', 'delete': '刪除', 'add': '新增', 'update': '更新', 'backup': '備份' };
  const ACTIONS = {
    'add': '加入', 'feed': '送去試吃', 'taste': '試吃', 'scout': '偵查', 'scout-pick': '你確認', 'import-report': '匯入報告',
    'plan': '實測計畫', 'absorb': '吸收', 'remove': '移除', 'builds': '版本', 'restore': '還原', 'effect': '評估',
    'policy-show': '常設預算', 'policy-set': '設定常設預算', 'triage': '分流', 'view': '更新視圖'
  };
  const RULES = [
    '沒有證據就沒有判定。星數和名氣只決定排序。',
    '食物不進專案，也不在你的電腦上執行，直到你按下吸收並安裝。',
    '「有毒」一定要經過人工確認。自動掃描只會舉旗，不會替作者貼上有毒的標籤。',
    '執行中只顯示進度和花費，不顯示即時分數。',
    '「加強」只在有實測證據時出現，否則一律顯示「未量測」。',
    'Elephant 和 Goldfish 的報告是匯入的歷史證據：只顯示，不計入判定。',
    '模型面向的 skill 文字要過行為 A/B 才能吸收（D17）；原型 v0 還沒有 A/B，所以食物的 skill 一律暫留。',
    '規劃中的站（Goldfish 零脈絡盲審、付費實測）畫出來但不能按，也不會被當成已經做過。',
    'Claude 和 Codex（這個網頁、catalog.py menu、oaw_status.py）讀的是同一份 view.json 和同一張站別表。'
  ];
  const UNSAFE = /[\u0000-\u001f\u007f-\u009f\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]/g;

  // ------------------------------------------------------------------ state
  const S = {
    token: '', meta: null, view: null, viewNote: null, sig: null, busy: false, lastAutoView: 0,
    selectedFood: null, live: null, selected: new Map(), open: new Map(), plans: new Map(), importPath: new Map(),
    scoutSel: new Set(), feedResult: null, policyOpen: false, policyDraft: null, policyPending: null, log: [], uid: 0
  };
  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  // An owner who asked the system for less motion gets every move instantly.
  const reducedMotion = () => !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  function txt(value, limit) {
    let text = value === null || value === undefined ? '' : String(value);
    text = text.replace(UNSAFE, ' ').replace(/\s+/g, ' ').trim();
    const most = limit || 200;
    return text.length > most ? text.slice(0, most - 1) + '…' : text;
  }

  // Long paths and keys keep their start and their end.
  function mid(value, limit) {
    const text = txt(value, 1000);
    const most = limit || 60;
    if (text.length <= most) return text;
    const head = Math.ceil((most - 1) / 2);
    return text.slice(0, head) + '…' + text.slice(text.length - (most - 1 - head));
  }

  // Same rule as oaw_status.part_state().
  function partState(part) {
    if (part.in_current_build) return part.decision === 'removed' ? '在目前版本中（移除後又還原回來：要重新測試）' : '在目前版本中';
    if (part.decision === 'absorbed') return '已吸收（不在目前版本）';
    return DECISIONS[part.decision] || (part.decision ? txt(part.decision, 40) : '');
  }

  // Builds elements from text only: `text` and string children become text nodes.
  function el(tag, props) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
      if (value === undefined || value === null || value === false) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = String(value);
      else if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2), value);
      else if (typeof value === 'boolean' && key in node) node[key] = value;
      else node.setAttribute(key, String(value));
    }
    for (let i = 2; i < arguments.length; i += 1) {
      for (const kid of [].concat(arguments[i])) {
        if (kid === null || kid === undefined || kid === false) continue;
        node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
      }
    }
    return node;
  }

  const chip = (text, kind) => el('span', { class: 'chip' + (kind ? ' ' + kind : ''), text: text });
  const levelChip = (level) => chip(LEVELS[level] || `未知等級（${txt(level, 30)}）`, 'lv-' + (LEVELS[level] ? level : 'unknown'));
  const fmt = (n) => (Number.isInteger(n) ? n.toLocaleString('zh-TW') : n === null || n === undefined ? '—' : txt(n, 40));
  const uid = (prefix) => `${prefix}-${(S.uid += 1)}`;

  function headlineLabel(verdict) {
    const code = verdict && verdict.headline;
    return HEADLINES[code] || `未知（${txt(code, 40)}，請更新 OAW）`;
  }

  function planStatusLabel(text) {
    const folded = String(text || '').toLowerCase();
    for (const [prefix, label] of PLAN_STATUS) if (folded.startsWith(prefix)) return label;
    return txt(text, 120) || '—';
  }

  function chipLabel(text) {
    const match = /^open-flags:(\d+)$/.exec(String(text));
    return match ? `${match[1]} 個旗標待分流` : CHIPS[text] || txt(text, 60);
  }

  // '加強' only next to measured evidence; otherwise 未量測.
  function qualityLabel(line) {
    if (!line || line.level !== 'measured') return '未量測';
    if (line.note === 'enhanced') return '加強（實測）';
    return `${txt(line.value, 40)}（實測，未宣稱改善）`;
  }

  function safetyLabel(food) {
    const flags = food.flags || {};
    if ((food.verdict || {}).headline === 'toxic') return '經人工確認有毒';
    if (!food.tasted) return '尚未檢查';
    if (flags.open) return `${flags.open} 個旗標未分流（高 ${flags.open_high || 0}）`;
    const pdf = txt((food.pinned || {}).pdf_sha12, 12);
    if (food.kind === 'paper') return `論文：只封存 PDF，不解析、不執行${pdf ? `（sha256 ${pdf}）` : ''}`;
    const tree = txt((food.pinned || {}).tree_sha12, 12);
    return tree ? `沒有觀察到有毒訊號（tree ${tree}）` : '沒有觀察到有毒訊號';
  }

  function tokensText(t) {
    if (!t || !Number.isFinite(t.min) || !Number.isFinite(t.max)) return '—';
    return `${(t.min / 1e6).toFixed(1)}–${(t.max / 1e6).toFixed(1)}M tokens` + (t.runs ? `（${t.runs} 次 run）` : '');
  }

  function when(iso) {
    const date = new Date(String(iso || ''));
    return Number.isNaN(date.getTime()) ? txt(iso, 25) : date.toLocaleString('zh-TW', { hour12: false });
  }

  // ------------------------------------------------------------------ network
  function readToken() {
    const match = /(?:^#|[#&])t=([A-Za-z0-9_-]{20,})/.exec(location.hash);
    let token = match ? match[1] : '';
    try {
      if (token) sessionStorage.setItem('oaw-ui-token', token);
      else token = sessionStorage.getItem('oaw-ui-token') || '';
    } catch (e) { /* storage blocked: the token lives only in this page */ }
    if (match) {
      try { history.replaceState(null, '', location.pathname); } catch (e) { /* keep the URL as is */ }
    }
    return token;
  }

  function banner(text) {
    const node = $('banner');
    node.textContent = text || '';
    node.hidden = !text;
  }

  async function api(path, body) {
    const init = { method: body === undefined ? 'GET' : 'POST', headers: { 'X-OAW-Token': S.token }, cache: 'no-store' };
    if (body !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(body);
    }
    let response;
    try {
      response = await fetch(path, init);
    } catch (e) {
      banner('連不上本機的網頁伺服器：它可能已經關掉了。在終端重新執行 python3 scripts/catalog.py ui。');
      throw new Error('連不上本機的網頁伺服器');
    }
    let data = null;
    try { data = await response.json(); } catch (e) { data = null; }
    if (response.status === 403) banner('通行碼無效或網址不對：請用終端顯示的完整網址重新開啟（含 #t=…）。');
    else if ($('banner').textContent.startsWith('連不上')) banner('');
    if (!response.ok && response.status !== 202) {
      const error = new Error((data && data.error) || `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function showBusy(label, job) {
    const progress = job && job.progress;
    const digest = job && job.digest;
    let text = (progress && progress.label) || label || '處理中…';
    if (digest && digest.stage_label) text += ` · ${txt(digest.stage_label, 20)}${digest.total ? ` ${digest.done}/${digest.total}` : ''}`;
    $('busy-text').textContent = `${text} · 只顯示進度，不顯示分數`;
    let ratio = null;
    if (progress && Number.isInteger(progress.done) && Number.isInteger(progress.total) && progress.total > 0) ratio = progress.done / progress.total;
    else if (digest && Number.isInteger(digest.done) && digest.total) ratio = digest.done / digest.total;
    const fill = $('busy-fill');
    fill.classList.toggle('indeterminate', ratio === null);
    fill.style.width = ratio === null ? '' : `${Math.max(6, Math.round(ratio * 100))}%`;
    $('busy').hidden = false;
    document.body.classList.add('is-busy');
  }

  function hideBusy() {
    $('busy').hidden = true;
    document.body.classList.remove('is-busy');
  }

  // While a taste runs, status.json says which stage it is in; the food's token stands there meanwhile.
  function liveStage(job) {
    const digest = job && job.state === 'running' ? job.digest : null;
    const map = (S.view && S.view.pipeline && S.view.pipeline.live_stages) || {};
    if (!digest || !digest.skill || !Object.prototype.hasOwnProperty.call(map, digest.stage)) return null;
    return { food: String(digest.skill), stage: String(map[digest.stage]) };
  }

  // The last live stage is kept until the job is over and the final view is loaded (run/trackBackground clear it),
  // so a status.json stage outside live_stages (for example done 3/3) never sends the token back to an older view.
  async function follow(job, label) {
    while (job && job.state === 'running') {
      showBusy(label, job);
      const live = liveStage(job);
      if (live && JSON.stringify(live) !== JSON.stringify(S.live)) {
        S.live = live;
        // A food fed a moment ago is already in view.json at 入口: fetch it, then move its token.
        await refresh(true);
      }
      await sleep(450);
      job = (await api('/api/job/' + encodeURIComponent(job.id))).job;
    }
    return job;
  }

  // Clears the live stage and loads the final view in one render.
  async function settle() {
    S.live = null;
    await refresh(true);
  }

  // Runs one engine action as a background job and returns its envelope (or null).
  async function run(action, params, label) {
    if (S.busy) {
      toast('還有一個動作在進行中，請稍等。', 'warn');
      return null;
    }
    S.busy = true;
    showBusy(label);
    let envelope = null;
    try {
      const data = await api('/api/action/' + action, params || {});
      const job = await follow(data.job, label);
      envelope = job ? job.result : null;
      logAction(label || ACTIONS[action] || action, envelope);
    } catch (e) {
      if (e.status === 409) toast('還有一個動作在進行中（例如自動評估），等它結束再按。', 'warn');
      else if (e.status !== 403) toast('沒有完成：' + txt(e.message, 200), 'bad');
    } finally {
      S.busy = false;
      hideBusy();
      await settle();
    }
    return envelope;
  }

  async function trackBackground(job) {
    if (S.busy) return;
    S.busy = true;
    const label = `自動${ACTIONS[job.action] || '動作'}`;
    try {
      const done = await follow(job, label);
      const envelope = done && done.result;
      logAction(label, envelope);
      if (envelope && !envelope.ok) toast(`${label}沒有完成：${txt(envelope.error, 200)}`, 'warn');
    } catch (e) { /* the banner explains connection problems */ } finally {
      S.busy = false;
      hideBusy();
      await settle();
    }
  }

  // A poll never re-renders under the owner's cursor; the next poll or action catches up.
  function editing() {
    const node = document.activeElement;
    return !!node && /^(INPUT|TEXTAREA|SELECT)$/.test(node.tagName) && !!node.closest('#my-oaw-body, #detail-body, #scout-body');
  }

  async function refresh(force) {
    let data;
    try { data = await api('/api/view'); } catch (e) { return; }
    const sig = data.view ? JSON.stringify([data.view.generated_at, data.view.generated_from]) : 'none:' + data.note;
    if (force || (sig !== S.sig && !editing())) {
      S.sig = sig;
      S.view = data.view;
      S.viewNote = data.note;
      render();
    }
    if (data.busy && !S.busy) trackBackground(data.busy);
    else if (data.stale && !S.busy && Date.now() - S.lastAutoView > 30000) {
      S.lastAutoView = Date.now();
      run('view', {}, '更新視圖（資料在別處改過）');
    }
  }

  // ------------------------------------------------------------------ feedback
  function toast(message, kind) {
    const node = el('div', { class: `toast ${kind || 'info'}`, role: kind === 'bad' ? 'alert' : 'status', text: message });
    $('toasts').append(node);
    requestAnimationFrame(() => node.classList.add('in'));
    setTimeout(() => {
      node.classList.remove('in');
      setTimeout(() => node.remove(), 400);
    }, kind === 'bad' ? 7000 : 4200);
  }

  // The engine sends error_zh for known errors; the English original stays in 動作紀錄.
  function errorText(envelope) {
    if (!envelope) return '';
    if (envelope.error_zh) return txt(envelope.error_zh, 300);
    return `${txt(envelope.error, 240)}（英文原文；細節見動作紀錄）`;
  }

  function report(envelope, okMessage) {
    if (!envelope) return;
    if (envelope.ok) toast(okMessage || '完成', 'good');
    else if (envelope.code === 3) toast('等你輸入終端上的確認碼。', 'info');
    else toast('沒有完成：' + errorText(envelope), 'bad');
  }

  function logAction(label, envelope) {
    S.log.unshift({ at: new Date(), label: label, envelope: envelope });
    S.log.length = Math.min(S.log.length, 10);
    const box = $('log');
    box.replaceChildren(...S.log.map((entry) => {
      const env = entry.envelope || {};
      const mark = env.ok ? '✔' : env.code === 3 ? '⏸' : '✖';
      return el('details', { class: 'log-entry' },
        el('summary', { text: `${mark} ${entry.at.toLocaleTimeString('zh-TW', { hour12: false })} ${txt(entry.label, 80)}` }),
        el('pre', { class: 'log-lines', text: (env.lines || [env.error || '']).map((line) => txt(line, 400)).join('\n') }));
    }));
  }

  function ask(options) {
    const dialog = $('dialog');
    const lines = options.lines || [];
    const list = el('ul', { class: 'dlg-lines' }, lines.slice(0, 120).map((line) => el('li', { text: txt(line, 300) })));
    if (lines.length > 120) list.append(el('li', { class: 'muted', text: `…還有 ${lines.length - 120} 行` }));
    const reason = options.reason ? el('input', { type: 'text', class: 'reason', maxlength: '300', id: 'dialog-reason',
      placeholder: options.reasonRequired ? '原因（必填，會記進決定紀錄）' : '原因（可空白，會記進決定紀錄）' }) : null;
    $('dialog-title').textContent = options.title;
    $('dialog-body').replaceChildren(list, reason ? el('label', { for: 'dialog-reason', class: 'small', text: '原因' }) : '', reason || '');
    const ok = $('dialog-ok');
    ok.textContent = options.ok || '確認';
    ok.disabled = !!options.disabled || (!!options.reasonRequired && !!reason);
    if (reason && options.reasonRequired && !options.disabled) {
      reason.addEventListener('input', () => { ok.disabled = !reason.value.trim(); });
    }
    ok.classList.toggle('danger', !!options.danger);
    if (typeof dialog.showModal !== 'function') {
      if (options.reasonRequired || options.disabled) return Promise.resolve(null);
      return Promise.resolve(window.confirm(`${options.title}\n\n${lines.slice(0, 20).join('\n')}`) ? { reason: '' } : null);
    }
    return openDialog(() => ({ reason: reason ? reason.value.trim() : '' }));
  }

  function openDialog(collect) {
    const dialog = $('dialog');
    const ok = $('dialog-ok');
    return new Promise((resolve) => {
      const finish = (value) => {
        ok.onclick = null;
        $('dialog-cancel').onclick = null;
        dialog.onclose = null;
        if (dialog.open) dialog.close();
        resolve(value);
      };
      ok.onclick = () => finish(collect());
      $('dialog-cancel').onclick = () => finish(null);
      dialog.onclose = () => finish(null);
      dialog.showModal();
    });
  }

  // 核准 on the pipeline: pick the parts to absorb; the preview and the confirmation follow.
  function askChoose(options) {
    const dialog = $('dialog');
    const ok = $('dialog-ok');
    const chosen = new Set();
    const list = el('ul', { class: 'dlg-choices' }, options.items.map((item) => {
      const id = uid('pick');
      return el('li', {},
        el('input', { type: 'checkbox', id: id, onchange: (e) => {
          if (e.target.checked) chosen.add(item.id); else chosen.delete(item.id);
          ok.disabled = !chosen.size;
        } }),
        el('label', { for: id }, el('span', { class: 'part-name', text: item.label }), el('span', { class: 'muted small', text: item.sub })));
    }));
    $('dialog-title').textContent = options.title;
    $('dialog-body').replaceChildren(el('p', { class: 'small muted', text: options.note || '' }), list);
    ok.textContent = options.ok || '下一步';
    ok.disabled = true;
    ok.classList.remove('danger');
    if (typeof dialog.showModal !== 'function') return Promise.resolve(null);
    return openDialog(() => Array.from(chosen));
  }

  // ------------------------------------------------------------------ render: top and my OAW
  function render() {
    renderTop();
    renderPipeline();
    renderScout();
    renderDetail();
    renderMy();
    renderFeedResult();
  }

  // ------------------------------------------------------------------ render: the intake pipeline
  function pipeTable() {
    const table = S.view && S.view.pipeline;
    return table && Array.isArray(table.stages) && table.stages.length ? table : null;
  }

  const stageIsPlanned = (stage) => stage.automation === 'planned';
  const stateName = (table, state) => txt((table.states_zh || {})[state], 10) || `未知狀態（${txt(state, 20)}）`;

  function automationChip(table, kind) {
    const known = ['automated', 'owner', 'mixed', 'planned'].includes(kind);
    return chip(txt((table.automation_zh || {})[kind], 10) || txt(kind, 20), 'auto auto-' + (known ? kind : 'unknown'));
  }

  function renderLegend(table) {
    const order = (table.legend || []).filter((k) => STAGE_STATES.includes(k));
    $('legend').replaceChildren(...order.map((state) => el('span', { class: 'leg' },
      el('span', { class: `dot st-${state}`, 'aria-hidden': 'true' }), el('span', { text: stateName(table, state) }))));
  }

  function stageButtons(stage) {
    if (stage.id === 'plan') {
      return el('button', { type: 'button', class: 'btn tiny', text: '匯入紀錄', title: '匯入 Elephant／Goldfish 消化紀錄（歷史證據）', onclick: openImport });
    }
    if (stage.id === 'build') {
      return el('button', { type: 'button', class: 'btn tiny', text: '版本與 skill', title: '目前版本、skill、和預設比、版本時間線、常設預算', onclick: () => jump('my-oaw') });
    }
    return '';
  }

  // Where each food's token stands now: the live stage while a taste runs, else the engine's stage.
  function hereOf(table, food) {
    const live = S.live && S.live.food === food.id && table.order.includes(S.live.stage) ? S.live.stage : null;
    return live || (food.pipeline || {}).stage;
  }

  function headRow(table) {
    const counts = {};
    for (const food of (S.view && Array.isArray(S.view.foods) ? S.view.foods : []).filter(Boolean)) {
      const at = hereOf(table, food);
      counts[at] = (counts[at] || 0) + 1;
    }
    const row = el('div', { class: 'trow thead', role: 'row' }, el('div', { class: 'tcell tlabel', role: 'columnheader', text: '食物' }));
    table.stages.forEach((stage, index) => {
      const planned = stageIsPlanned(stage);
      const count = Number.isInteger(counts[stage.id]) ? counts[stage.id] : 0;
      // A planned stage has nothing to press: its header is text only.
      row.append(el('div', { class: `tcell stage-head${planned ? ' planned' : ''}${index === 0 ? ' inlet-target' : ''}`, role: 'columnheader',
        'data-stage': stage.id, title: txt(stage.summary_zh, 300) },
        el('div', { class: 'sh-top' }, el('span', { class: 'sh-num', text: String(index + 1) }), el('span', { class: 'sh-name', text: txt(stage.label_zh, 8) })),
        automationChip(table, stage.automation),
        count ? el('span', { class: 'sh-count', text: `${count} 樣在這裡` }) : '',
        planned ? '' : stageButtons(stage)));
    });
    return row;
  }

  function pips(food) {
    const parts = (Array.isArray(food.components) ? food.components : []).filter(Boolean);
    if (!parts.length) return '';
    const box = el('span', { class: 'pips', 'aria-hidden': 'true' });
    for (const part of parts.slice(0, 12)) {
      const key = DISPOSITIONS[part.disposition] ? part.disposition : 'unknown';
      box.append(el('span', { class: `pip d-${key}${part.in_current_build ? ' built' : ''}` }));
    }
    if (parts.length > 12) box.append(el('span', { class: 'pip-more', text: `+${parts.length - 12}` }));
    return box;
  }

  function token(table, food, stage, state, working) {
    const verdict = food.verdict || {};
    const family = FAMILY[verdict.headline] || 'unknown';
    const counts = food.counts || {};
    const parts = Array.isArray(food.components) ? food.components.length : 0;
    const abHolds = Number.isInteger((food.pipeline || {}).ab_holds) ? food.pipeline.ab_holds : 0;
    const label = `${txt(food.display, 60)}：在「${txt(stage.label_zh, 8)}」（${working ? '試吃中' : stateName(table, state)}）`
      + `；判定 ${headlineLabel(verdict)}` + (parts ? `；成分 吸收 ${counts.absorb || 0}、排掉 ${counts.excrete || 0}、暫留 ${counts.hold || 0}` : '')
      + (abHolds ? `（其中 ${abHolds} 個 skill 文字缺行為 A/B，D17）` : '');
    return el('button', { type: 'button', class: `token fam-${family} st-${state}${working ? ' working' : ''}`, 'data-food': food.id,
      'data-stage': stage.id, 'data-engine': txt((food.pipeline || {}).stage, 20), 'aria-label': label, title: '打開食物卡',
      onclick: () => openFood(food.id) },
      el('span', { class: 'tok-sym', 'aria-hidden': 'true', text: txt(verdict.symbol, 3) || '?' }), pips(food));
  }

  function stageActionButtons(food, stage) {
    const box = el('div', { class: 'cell-actions' });
    const actions = ((food.pipeline || {}).actions || []).filter((action) => action && action.stage === stage.id);
    actions.forEach((action, index) => {
      if (action.where === 'terminal') {
        // Owner codes stay on the terminal: the page shows the full command and where to go in the menu.
        box.append(terminalHint(action));
        return;
      }
      const danger = action.id === 'forget' || action.id === 'remove-food';
      box.append(el('button', { type: 'button', class: `btn tiny act${index === 0 && !danger ? ' primary' : ''}${danger ? ' danger' : ''}`,
        text: txt(action.label_zh, 40), onclick: () => stageAction(food, action) }));
    });
    return box;
  }

  function terminalHint(action) {
    const command = txt((S.meta && S.meta.menu_command) || 'python scripts/catalog.py menu --target <專案>', 600);
    const code = el('code', { class: 'term-cmd', text: command });
    const copy = el('button', { type: 'button', class: 'btn tiny', text: '複製指令', onclick: async () => {
      try {
        await navigator.clipboard.writeText(command);
        toast('已複製：貼到你自己開的 PowerShell 或 cmd（Git Bash 請用 winpty）。', 'info');
      } catch (e) {
        const more = code.closest('details');
        if (more) more.open = true;
        const range = document.createRange();
        range.selectNodeContents(code);
        const chosen = window.getSelection();
        chosen.removeAllRanges();
        chosen.addRange(range);
        toast('瀏覽器不讓網頁複製：指令已選取，按 Ctrl+C。', 'warn');
      }
    } });
    // Compact in a stage column: the copy button carries the full command; the command itself folds out.
    return el('div', { class: 'term-hint' },
      el('span', { text: `${txt(action.label_zh, 40)}：確認碼只在終端。` }), copy,
      el('details', { class: 'term-more' }, el('summary', { text: '看指令' }),
        el('span', { class: 'small', text: '在你自己開的終端（PowerShell、cmd）執行：' }), code,
        el('span', { class: 'small', text: '然後按這一站的字母（例如 a），或選「12 靜態：分流旗標」。' })));
  }

  function laneCell(table, food, stage, state, here, working) {
    const known = STAGE_STATES.includes(state) ? state : 'unknown';
    const planned = stageIsPlanned(stage);
    const cell = el('div', { class: `tcell cell st-${known}${here ? ' here' : ''}`, role: 'cell', 'data-stage': stage.id },
      el('span', { class: 'cell-head' }, el('span', { class: 'cell-stage', text: txt(stage.label_zh, 8) }),
        el('span', { class: 'cell-state', text: here && working ? '試吃中' : stateName(table, known === 'unknown' ? state : known) }),
        automationChip(table, stage.automation)));
    if (here) {
      cell.append(token(table, food, stage, known, working),
        el('p', { class: 'cell-note', text: working ? '試吃中…（只顯示進度，不顯示分數）' : txt((food.pipeline || {}).note_zh, 160) }));
    } else {
      cell.append(el('span', { class: `dot mark st-${known}`, title: `${txt(stage.label_zh, 8)}：${stateName(table, known === 'unknown' ? state : known)}` }));
    }
    // Planned stages are drawn but never offer an action.
    if (planned) return cell;
    if (here && !working) cell.append(stageActionButtons(food, stage));
    for (const detail of ((food.pipeline || {}).details || [])) {
      if (detail && detail.stage === stage.id && detail.id === 'plan') {
        cell.append(el('button', { type: 'button', class: 'btn tiny link', text: txt(detail.label_zh, 20), onclick: () => planFlow(food, true) }));
      }
    }
    return cell;
  }

  function lane(table, food) {
    const pipeline = food.pipeline || {};
    const states = pipeline.stages || {};
    const live = S.live && S.live.food === food.id && table.order.includes(S.live.stage) ? S.live.stage : null;
    const here = hereOf(table, food);
    const verdict = food.verdict || {};
    const family = FAMILY[verdict.headline] || 'unknown';
    const row = el('div', { class: `trow lane fam-${family}${S.selectedFood === food.id ? ' selected' : ''}`, role: 'row', 'data-food': food.id },
      el('div', { class: 'tcell tlabel', role: 'rowheader' },
        el('button', { type: 'button', class: 'food-name', text: txt(food.display, 60), title: '打開食物卡', onclick: () => openFood(food.id) }),
        el('span', { class: 'lane-chips' }, el('span', { class: `vchip fam-${family}`, text: `${txt(verdict.symbol, 3)} ${headlineLabel(verdict)}` }),
          levelChip(verdict.level), food.kind === 'paper' ? chip('論文') : '')));
    const at = table.order.indexOf(here);
    table.stages.forEach((stage, index) => {
      let state = states[stage.id];
      if (live) {
        // While tasting, only the stages before the live one are done; nothing is claimed beyond it.
        state = stage.id === live ? 'current' : stageIsPlanned(stage) ? 'planned' : index < at ? 'done' : 'todo';
      }
      row.append(laneCell(table, food, stage, state, stage.id === here, !!live && stage.id === live));
    });
    return row;
  }

  function capturePositions() {
    const seen = new Map();
    for (const node of document.querySelectorAll('#track .token[data-food]')) {
      seen.set(node.dataset.food, { rect: node.getBoundingClientRect(), stage: node.dataset.stage, engine: node.dataset.engine });
    }
    return seen;
  }

  // A token whose stage changed glides from where it stood to its new stage (a CSS transition);
  // with reduced motion it simply appears there.
  function animateMoves(before) {
    if (!before.size || reducedMotion()) return;
    const order = (pipeTable() || {}).order || [];
    for (const node of document.querySelectorAll('#track .token[data-food]')) {
      const prev = before.get(node.dataset.food);
      if (!prev || prev.stage === node.dataset.stage) continue;
      // A glide backwards is drawn only when the engine moved the food back, never for a stale view.
      const back = order.indexOf(node.dataset.stage) < order.indexOf(prev.stage);
      if (back && prev.engine === node.dataset.engine) continue;
      const now = node.getBoundingClientRect();
      const dx = prev.rect.left - now.left;
      const dy = prev.rect.top - now.top;
      if (!dx && !dy) continue;
      node.style.transform = `translate(${dx}px, ${dy}px)`;
      node.getBoundingClientRect();
      node.classList.add('travel');
      node.style.transform = '';
      const cell = node.closest('.cell');
      node.addEventListener('transitionend', () => {
        node.classList.remove('travel');
        if (cell) cell.classList.add('arrived');
      }, { once: true });
    }
  }

  // No food yet: the stage list as one lane without a token. Narrow screens show it (their header row is hidden).
  function stageList(table) {
    const row = el('div', { class: 'trow lane stage-list', role: 'row', 'aria-label': '流程的九站（還沒有食物）' },
      el('div', { class: 'tcell tlabel', role: 'rowheader' }, el('span', { class: 'muted small', text: '流程的九站' })));
    table.stages.forEach((stage, index) => {
      const planned = stageIsPlanned(stage);
      const state = planned ? 'planned' : 'todo';
      row.append(el('div', { class: `tcell cell st-${state}`, role: 'cell', 'data-stage': stage.id },
        el('span', { class: 'cell-head' }, el('span', { class: 'cell-stage', text: `${index + 1} ${txt(stage.label_zh, 8)}` }),
          automationChip(table, stage.automation)),
        el('span', { class: `dot mark st-${state}`, title: `${txt(stage.label_zh, 8)}：${txt((table.automation_zh || {})[stage.automation], 10)}` })));
    });
    return row;
  }

  // The header buttons (匯入紀錄, 版本與 skill) for narrow screens, where the header row is hidden.
  function renderTools(table) {
    const box = $('pipe-tools');
    if (!box) return;
    box.replaceChildren(...table.stages.filter((stage) => !stageIsPlanned(stage)).map(stageButtons).filter(Boolean));
  }

  function renderGuide(table) {
    const inlets = (table.inlets || []).map((inlet) => el('li', { class: 'guide-inlet' },
      el('strong', { text: `入口：${txt(inlet.label_zh, 60)}` }),
      el('ul', {}, (inlet.steps || []).map((step) => el('li', {}, txt(step.label_zh, 160), ' ', automationChip(table, step.automation))))));
    const stages = table.stages.map((stage, index) => el('li', { class: stageIsPlanned(stage) ? 'planned' : '' },
      el('div', { class: 'guide-head' }, el('strong', { text: `${index + 1} ${txt(stage.label_zh, 8)}` }), automationChip(table, stage.automation),
        el('span', { class: 'muted small', text: (stage.decisions || []).map((d) => txt(d, 6)).join('、') })),
      el('p', { class: 'small', text: txt(stage.summary_zh, 300) }),
      el('ul', {}, (stage.steps || []).map((step) => el('li', { class: 'small' }, txt(step.label_zh, 160), ' ', automationChip(table, step.automation))))));
    $('stage-guide').replaceChildren(...inlets, ...stages);
  }

  function renderPipeline() {
    const before = capturePositions();
    const table = pipeTable();
    const track = $('track');
    const empty = $('pipe-empty');
    const foods = S.view && Array.isArray(S.view.foods) ? S.view.foods.filter(Boolean) : [];
    if (!table) {
      track.replaceChildren();
      $('legend').replaceChildren();
      empty.hidden = false;
      empty.textContent = S.view ? 'view.json 沒有站別表：在終端執行 python3 scripts/catalog.py view。' : (S.viewNote === 'invalid' ? 'view.json 無效：在終端執行 catalog.py view。' : '讀取中…');
      return;
    }
    renderLegend(table);
    track.style.setProperty('--stages', String(table.stages.length));
    track.replaceChildren(headRow(table), ...(foods.length ? foods.map((food) => lane(table, food)) : [stageList(table)]));
    renderTools(table);
    // Real data only: no food means the empty pipeline, the two inlets and one sentence.
    empty.hidden = foods.length > 0;
    empty.textContent = foods.length ? '' : txt(table.empty_zh, 200);
    renderGuide(table);
    animateMoves(before);
  }

  function jump(id) {
    const node = $(id);
    if (node) node.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start' });
  }

  function openFood(foodId) {
    S.selectedFood = foodId;
    renderPipeline();
    renderDetail();
    jump('detail');
  }

  function openImport() {
    $('import-any').open = true;
    jump('detail');
    $('import-dir').focus();
  }

  function renderDetail() {
    const body = $('detail-body');
    const foods = S.view && Array.isArray(S.view.foods) ? S.view.foods.filter(Boolean) : [];
    const food = foods.find((item) => item.id === S.selectedFood);
    if (!food) {
      $('detail-title').textContent = '🍱 食物卡';
      body.replaceChildren(el('p', { class: 'muted', text: foods.length
        ? '點流程上的食物名稱或圖示，看它的食物卡：成分、旗標、判定依據、計畫、Elephant／Goldfish 紀錄。'
        : '還沒有食物：先從上面任一個入口加入。' }));
      return;
    }
    $('detail-title').textContent = `🍱 食物卡：${txt(food.display, 60)}`;
    body.replaceChildren(card(food), el('div', { class: 'row' },
      el('button', { type: 'button', class: 'btn tiny', text: '收起食物卡', onclick: () => { S.selectedFood = null; renderPipeline(); renderDetail(); } })));
  }

  function renderTop() {
    const meta = S.meta || {};
    const name = $('project-name');
    name.textContent = meta.project ? `${txt(meta.project_name, 60)} · ${mid(meta.project, 64)}` : '';
    name.title = meta.project ? txt(meta.project, 400) : '';
    const funnel = (S.view && S.view.funnel) || {};
    $('top-stats').replaceChildren(
      chip(`食物 ${funnel.submitted || 0}`), chip(`已試吃 ${funnel.tasted || 0}`),
      chip(`實測 ${funnel.measured || 0}`), chip(`已吸收成分 ${funnel.absorbed_parts || 0}（在目前版本）`),
      funnel.backlog_items ? chip(`待辦 ${funnel.backlog_items}（未改程式）`) : '');
  }

  // Same rule as oaw_status.installed_skills(): a fresh effect first, else the current build's skills.
  function skillRows(view) {
    const my = view.my_oaw || {};
    const effect = my.effect || {};
    const skills = effect.skills || null;
    const current = (Array.isArray(my.timeline) ? my.timeline : []).find((build) => build && build.current);
    let present;
    let base = null;
    if (skills) base = (skills.same || []).concat(skills.removed || []);
    if (skills && !effect.stale) present = (skills.same || []).concat(skills.added || []);
    else if (current && my.current_matches_build !== false) present = current.skills || [];
    else if (skills) present = (skills.same || []).concat(skills.added || []);
    else return null;
    const now = new Set(present);
    const rows = Array.from(now).map((name) => ({ name: txt(name, 64), tag: base === null || base.includes(name) ? '' : '新增' }));
    if (base !== null) for (const name of new Set(base)) if (!now.has(name)) rows.push({ name: txt(name, 64), tag: '比預設少' });
    return rows.sort((a, b) => a.name.localeCompare(b.name));
  }

  function block(title, action, ...body) {
    return el('div', { class: 'block' }, el('div', { class: 'block-head' }, el('h3', { text: title }), action || ''), ...body);
  }

  function skillsBlock(view) {
    const rows = skillRows(view);
    if (!rows) return block('skill', null, el('p', { class: 'muted', text: '還沒評估：按「重新評估」取得目前的 skill 清單。' }));
    const egm = new Set((S.meta && S.meta.egm_skills) || []);
    const present = rows.filter((row) => row.tag !== '比預設少');
    const missing = rows.filter((row) => row.tag === '比預設少');
    const egmPresent = present.filter((row) => egm.has(row.name));
    const list = el('ul', { class: 'skills' });
    const effect = (view.my_oaw || {}).effect || {};
    const onlyOn = (!effect.stale && effect.skills && effect.skills.only_on) || {};
    const hostChip = (name) => {
      const hosts = onlyOn[name];
      if (!Array.isArray(hosts)) return '';
      return chip(hosts.length ? `只在 ${hosts.map((h) => HOSTS[h] || txt(h, 20)).join('、')}` : '沒有裝到任何 host', 'warn');
    };
    for (const row of present.filter((r) => !egm.has(r.name))) {
      list.append(el('li', { class: 'skill' },
        el('span', { class: 'skill-name mono', text: row.name }), row.tag ? chip(row.tag) : '', hostChip(row.name),
        el('button', { type: 'button', class: 'btn tiny act', text: '移除', title: `移除 ${row.name}（先預覽）`, onclick: () => removeFlow(row.name) })));
    }
    if (egmPresent.length) {
      list.append(el('li', { class: 'skill egm' },
        el('details', {}, el('summary', { text: `EGM（內建，${egmPresent.length} 個 skill）` }),
          el('p', { class: 'mono small', text: egmPresent.map((row) => row.name).join('、') })),
        el('button', { type: 'button', class: 'btn tiny act', text: '移除 EGM', title: '移除整組 EGM skill（先預覽）', onclick: () => removeFlow('egm') })));
    }
    const out = block(`skill（${present.length}）`, null, list);
    if (missing.length) {
      const egmMissing = missing.filter((row) => egm.has(row.name));
      const back = el('ul', { class: 'skills' });
      if (egmMissing.length) {
        back.append(el('li', { class: 'skill' }, el('span', { class: 'skill-name', text: `EGM（${egmMissing.length} 個 skill 比預設少）` }),
          el('button', { type: 'button', class: 'btn tiny act', text: '加回 EGM', title: '經 oaw.py migrate 加回整組 EGM（先預覽）', onclick: () => readdFlow('egm') })));
      }
      for (const row of missing.filter((r) => !egm.has(r.name))) {
        back.append(el('li', { class: 'skill' }, el('span', { class: 'skill-name mono', text: row.name }), chip('比預設少'),
          el('button', { type: 'button', class: 'btn tiny act', text: '加回', title: `經 oaw.py migrate 加回 ${row.name}（先預覽）`, onclick: () => readdFlow(row.name) })));
      }
      out.append(el('p', { class: 'muted small', text: '比預設少（加回會保留之後的其他變更；加回的 skill 要重新測試）：' }), back);
    }
    return out;
  }

  function effectBlock(effect, release) {
    const again = el('button', {
      type: 'button', class: 'btn tiny act', text: '重新評估',
      onclick: async () => report(await run('effect', {}, '評估和預設的差異'), '評估完成：每一行都是靜態量測，品質未量測')
    });
    if (!effect || !Array.isArray(effect.lines)) return block(`和預設 ${txt(release, 20)} 比`, again, el('p', { class: 'muted', text: '尚未評估。' }));
    const body = el('tbody');
    // Each line carries its evidence level under the metric name; a difference is a fact, not a judgement,
    // so deltas are not coloured better or worse.
    const metricCell = (line, name) => el('td', { class: 'metric', title: txt(line.note, 200) },
      el('div', { class: 'metric-wrap' }, el('span', { class: 'metric-name', text: name }), levelChip(line.level)));
    for (const line of effect.lines) {
      if (!line) continue;
      if (line.metric === 'quality') {
        body.append(el('tr', { class: 'quality' }, metricCell(line, '品質'), el('td', { colspan: '3', class: 'quality-value', text: qualityLabel(line) })));
        continue;
      }
      const delta = Number.isInteger(line.delta) ? (line.delta > 0 ? `+${line.delta}` : String(line.delta)) : '';
      body.append(el('tr', {},
        metricCell(line, METRICS[line.metric] || txt(line.metric, 60)),
        el('td', { class: 'num', text: fmt(line.current) }), el('td', { class: 'num', text: fmt(line.default) }),
        el('td', { class: 'num delta', text: delta })));
    }
    const table = el('table', { class: 'effect' },
      el('thead', {}, el('tr', {}, ['項目／證據等級', '目前', '預設', '差'].map((h) => el('th', { text: h })))), body);
    return block(`和預設 ${txt(effect.release || release, 20)} 比`, again,
      effect.stale ? el('p', { class: 'notice warn', text: '這份評估已過期（安裝層改過）：按「重新評估」。' }) : '',
      el('div', { class: 'table-wrap' }, table),
      el('p', { class: 'muted small', text: '「加強」只會在有實測證據時出現，沒有就寫「未量測」。bytes ÷ 4 只是 token 估計。' }));
  }

  // One effect line as text plus its evidence-level chip (compact form of the effect table).
  function effectItem(line) {
    if (line.metric === 'quality') return el('li', {}, el('span', { text: `品質：${qualityLabel(line)}` }), levelChip(line.level));
    const delta = Number.isInteger(line.delta) ? `（${line.delta > 0 ? '+' : ''}${line.delta}）` : '';
    return el('li', {}, el('span', { text: `${METRICS[line.metric] || txt(line.metric, 60)}：${fmt(line.current)} 對 ${fmt(line.default)}${delta}` }), levelChip(line.level));
  }

  // D12: every build shows its skills, its absorbed components and its effect versus the default.
  function buildDetails(build) {
    const skills = (build.skills || []).map((s) => txt(s, 64));
    const parts = (build.components || []).map((c) => txt(c, 120));
    const effect = build.effect && Array.isArray(build.effect.lines) ? build.effect : null;
    return el('details', { class: 'tl-details' },
      el('summary', { text: `內容：${skills.length} 個 skill · ${parts.length} 個吸收的成分 · 和預設比` }),
      el('p', { class: 'small', text: 'skill：' + (skills.join('、') || '（沒有）') }),
      el('p', { class: 'small', text: '吸收的成分：' + (parts.join('、') || '（沒有）') }),
      effect ? el('ul', { class: 'tl-effect' }, effect.lines.filter(Boolean).map(effectItem))
        : el('p', { class: 'muted small', text: '這一版沒有評估紀錄。' }));
  }

  function timelineBlock(timeline) {
    if (!timeline.length) return block('版本時間線', null, el('p', { class: 'muted', text: '還沒有版本：第一次吸收或移除時，會先存一個基準版。' }));
    const list = el('ol', { class: 'timeline' });
    for (const build of timeline.slice().reverse()) {
      list.append(el('li', { class: 'tl-item' + (build.current ? ' current' : '') },
        el('span', { class: 'tl-dot', 'aria-hidden': 'true' }),
        el('div', { class: 'tl-main' },
          el('div', { class: 'tl-top' }, el('span', { class: 'mono tl-name', text: txt(build.name, 60) }),
            chip(BUILD_KINDS[build.kind] || txt(build.kind, 20)), build.current ? chip('目前') : ''),
          el('div', { class: 'tl-label', text: txt(build.label_zh || build.label, 160) }),
          el('div', { class: 'muted small', text: `${when(build.created_at)} · ${(build.skills || []).length} 個 skill` + (build.doctor ? ` · doctor ${txt(build.doctor, 20)}` : '') }),
          buildDetails(build)),
        build.current ? '' : el('button', { type: 'button', class: 'btn tiny act', text: '還原到這版', onclick: () => restoreFlow(build) })));
    }
    return block('版本時間線', null, list);
  }

  function policyBlock(policy) {
    const out = block('常設預算', null);
    if (policy.set) {
      out.append(el('p', { text: `每樣食物 ${fmt(policy.per_food_token_cap)} tokens · 每週 ${fmt(policy.weekly_token_cap)} tokens` }),
        el('p', { class: 'small', text: '試跑條件：' + (policy.sandbox || []).map((c) => SANDBOX[c] || txt(c, 30)).join('、') }));
    } else {
      out.append(el('p', { class: 'muted', text: '還沒設定。設定一次後，系統在預算內自己決定怎麼測，超過才問你。' }));
    }
    out.append(el('p', { class: 'muted small', text: '原型 v0 只顯示計畫和預估花費，不會真的執行付費實測。' }));
    if (S.policyPending) {
      const code = el('input', { type: 'text', inputmode: 'numeric', maxlength: '6', class: 'code', id: 'policy-code', placeholder: '6 位數', autocomplete: 'off' });
      out.append(el('p', { class: 'notice', text: '確認碼已印在啟動 catalog.py ui 的終端機上（不會出現在網頁）。' }),
        el('div', { class: 'row' }, el('label', { for: 'policy-code', class: 'small', text: '確認碼' }), code,
          el('button', { type: 'button', class: 'btn primary act', text: '確認', onclick: () => confirmPolicy(code.value.trim()) }),
          el('button', { type: 'button', class: 'btn act', text: '取消', onclick: () => { S.policyPending = null; renderMy(); } })));
      return out;
    }
    if (!S.policyOpen) {
      out.append(el('button', { type: 'button', class: 'btn act', text: policy.set ? '修改常設預算' : '設定常設預算', onclick: () => { S.policyOpen = true; renderMy(); } }));
      return out;
    }
    const draft = S.policyDraft || { food: policy.per_food_token_cap || '', week: policy.weekly_token_cap || '', sandbox: policy.sandbox || ['isolated-venv', 'project-copy', 'no-api-keys'] };
    S.policyDraft = draft;
    const food = el('input', { type: 'number', min: '0', step: '1000000', id: 'policy-food', value: draft.food, oninput: (e) => { draft.food = e.target.value; } });
    const week = el('input', { type: 'number', min: '0', step: '1000000', id: 'policy-week', value: draft.week, oninput: (e) => { draft.week = e.target.value; } });
    const boxes = ((S.meta && S.meta.sandbox_conditions) || Object.keys(SANDBOX)).map((condition) => {
      const id = uid('sb');
      return el('label', { class: 'check', for: id },
        el('input', { type: 'checkbox', id: id, checked: draft.sandbox.includes(condition), onchange: (e) => {
          draft.sandbox = e.target.checked ? draft.sandbox.concat([condition]) : draft.sandbox.filter((c) => c !== condition);
        } }), SANDBOX[condition] || condition);
    });
    out.append(
      el('div', { class: 'field' }, el('label', { for: 'policy-food', text: '每樣食物的付費上限（tokens）' }), food),
      el('div', { class: 'field' }, el('label', { for: 'policy-week', text: '每週的付費上限（tokens）' }), week),
      el('p', { class: 'small muted', text: txt((S.meta && (S.meta.token_label_zh || S.meta.token_label)) || '', 160) }),
      el('fieldset', { class: 'checks' }, el('legend', { text: '試跑的隔離條件' }), boxes),
      el('div', { class: 'row' },
        el('button', { type: 'button', class: 'btn primary act', text: '送出（終端會顯示確認碼）', onclick: submitPolicy }),
        el('button', { type: 'button', class: 'btn act', text: '取消', onclick: () => { S.policyOpen = false; S.policyDraft = null; renderMy(); } })));
    return out;
  }

  async function submitPolicy() {
    const draft = S.policyDraft || {};
    const perFood = Number(draft.food);
    const weekly = Number(draft.week);
    if (!Number.isInteger(perFood) || !Number.isInteger(weekly) || perFood < 0 || weekly < 0) {
      toast('請填 0 以上的整數 token 上限。', 'warn');
      return;
    }
    if (!draft.sandbox || !draft.sandbox.length) {
      toast('至少勾一個試跑條件。', 'warn');
      return;
    }
    const params = { per_food_tokens: perFood, weekly_tokens: weekly, sandbox: draft.sandbox.slice() };
    const envelope = await run('policy-set', params, '設定常設預算');
    if (!envelope) return;
    if (envelope.code === 3) {
      S.policyPending = params;
      renderMy();
      toast('確認碼已印在啟動 ui 的終端機上。', 'info');
    } else report(envelope, '常設預算已設定');
  }

  async function confirmPolicy(code) {
    if (!/^\d{6}$/.test(code)) {
      toast('確認碼是 6 位數字。', 'warn');
      return;
    }
    const params = Object.assign({}, S.policyPending, { confirm: code });
    S.policyPending = null;
    const envelope = await run('policy-set', params, '確認常設預算');
    if (envelope && envelope.ok) {
      S.policyOpen = false;
      S.policyDraft = null;
      renderMy();
      toast('常設預算已設定：在預算內由系統決定怎麼測（v0 仍不執行付費實測）。', 'good');
    } else if (envelope) toast(envelope.error_zh ? txt(envelope.error_zh, 200) : '確認碼不對或過期（每個碼只能試一次）：請重新送出取得新的碼。', 'bad');
  }

  function renderMy() {
    const body = $('my-oaw-body');
    const meta = S.meta || {};
    const view = S.view;
    const kids = [];
    if (S.meta && !meta.installed) kids.push(el('p', { class: 'notice warn', text: '這個資料夾還沒有安裝 OAW：先執行 python3 scripts/oaw.py init --target 這個專案。' }));
    if (!view) {
      kids.push(el('p', { class: 'muted', text: S.viewNote === 'invalid' ? 'view.json 無效：在終端執行 catalog.py view。' : '還沒有資料。' }));
      body.replaceChildren(...kids);
      return;
    }
    const my = view.my_oaw || {};
    const timeline = Array.isArray(my.timeline) ? my.timeline : [];
    const current = timeline.find((build) => build && build.current);
    kids.push(el('div', { class: 'build-card' },
      el('div', { class: 'build-kicker', text: my.current_build ? '目前版本' : '目前版本（預設）' }),
      el('div', { class: 'build-name mono', text: txt(my.current_build || view.release, 60) }),
      el('div', { class: 'build-label', text: current ? txt(current.label_zh || current.label, 160) : '還沒有建立版本：第一次吸收或移除時，會先存一個基準版。' }),
      my.current_build && my.current_matches_build === false ? el('p', { class: 'notice warn', text: '⚠ 目前的安裝和記錄的版本不同（在 catalog 之外被改過）。' }) : ''));
    kids.push(skillsBlock(view), effectBlock(my.effect, view.release || '2.0.0'), timelineBlock(timeline), policyBlock(view.policy || {}));
    body.replaceChildren(...kids);
  }

  // ------------------------------------------------------------------ render: feeding
  function renderFeedResult() {
    const box = $('feed-result');
    const envelope = S.feedResult;
    if (!envelope) {
      box.replaceChildren();
      return;
    }
    if (!envelope.ok) {
      box.replaceChildren(el('p', { class: 'notice bad', text: '沒有完成：' + errorText(envelope) }));
      return;
    }
    const r = envelope.result || {};
    const items = [];
    if ((r.added || []).length) items.push(el('li', { text: '新加入：' + r.added.map((id) => txt(id, 64)).join('、') }));
    for (const merge of r.merges || []) {
      const inputs = (merge.inputs || []).map((i) => txt(i, 300));
      const ignored = (merge.ignored || []).map((x) => `${x.field === 'ref' ? 'ref' : '子目錄'} ${txt(x.value, 80)}`);
      items.push(el('li', { class: 'feed-merge', title: inputs.join('\n') },
        `合併：${inputs.length} 個寫法是同一個 repo → `, el('span', { class: 'mono', text: mid(merge.key, 90) }),
        '（只試吃一次）' + (ignored.length ? `；用第一個寫法，已忽略 ${ignored.join('、')}` : '')));
    }
    for (const entry of r.existing || []) items.push(el('li', { text: `已經在食物卡裡：${txt(entry.id, 64)}` }));
    for (const error of r.errors || []) items.push(el('li', { class: 'bad', text: `不能用：${txt(error.input, 120)}（${txt(error.error_zh || error.error, 160)}）` }));
    for (const taste of r.tasted || []) {
      const counts = taste.components || {};
      const family = FAMILY[taste.verdict] || 'unknown';
      items.push(el('li', { class: `fam-line fam-${family}`, text: `試吃完成：${txt(taste.food, 64)} · ${headlineLabel({ headline: taste.verdict })} · 🟢${counts.absorb || 0} 🔴${counts.excrete || 0} 🟡${counts.hold || 0}` }));
    }
    for (const fail of r.failed || []) items.push(el('li', { class: 'bad', text: `✖ 試吃失敗：${txt(fail.food, 64)}（${txt(fail.error_zh || fail.error, 200)}）` }));
    if ((r.already_tasted || []).length) items.push(el('li', { text: '已經試吃過：' + r.already_tasted.map((id) => txt(id, 64)).join('、') }));
    box.replaceChildren(el('ul', { class: 'feed-lines' }, items),
      el('button', { type: 'button', class: 'btn tiny', text: '收起', onclick: () => { S.feedResult = null; renderFeedResult(); } }));
  }

  function feedToast(envelope) {
    if (!envelope) return;
    if (!envelope.ok) {
      report(envelope);
      return;
    }
    const r = envelope.result || {};
    const parts = [`試吃完成 ${(r.tasted || []).length} 樣`];
    if ((r.merges || []).length) parts.push(`合併 ${r.merges.length} 組重複`);
    if ((r.failed || []).length) parts.push(`失敗 ${r.failed.length}`);
    toast(parts.join(' · '), feedTone(r));
  }

  // Green only when every tasted food is measured nutritious; otherwise the worst family wins.
  function feedTone(r) {
    const families = (r.tasted || []).map((t) => FAMILY[t.verdict] || 'unknown');
    if (families.includes('bad')) return 'bad';
    if ((r.failed || []).length || (r.errors || []).length || families.some((f) => ['amber', 'warn', 'dark', 'unknown'].includes(f))) return 'warn';
    if (families.length && families.every((f) => f === 'good')) return 'good';
    return 'neutral';
  }

  async function feed() {
    const area = $('feed-urls');
    const urls = area.value.split(/[\s,]+/).filter(Boolean);
    if (!urls.length) {
      toast('先貼上至少一個 GitHub repo 或 arXiv 論文網址。', 'warn');
      area.focus();
      return;
    }
    if (urls.length > 50) {
      toast('一次最多 50 個網址。', 'warn');
      return;
    }
    const envelope = await run('feed', { urls: urls }, `送去試吃（${urls.length} 個網址）`);
    if (!envelope) return;
    S.feedResult = envelope;
    renderFeedResult();
    if (envelope.ok) area.value = '';
    feedToast(envelope);
  }

  async function scoutFeed() {
    const keys = Array.from(S.scoutSel);
    if (!keys.length) return;
    const envelope = await run('feed', { scout_keys: keys }, `把 ${keys.length} 個候選送去試吃`);
    if (!envelope) return;
    S.scoutSel.clear();
    S.feedResult = envelope;
    render();
    feedToast(envelope);
  }

  function renderScout() {
    const box = $('scout-body');
    const scout = (S.view && S.view.feeding && S.view.feeding.scout) || {};
    const candidates = Array.isArray(scout.candidates) ? scout.candidates : [];
    const last = scout.last_run;
    const head = el('p', { class: 'muted small', text: (last ? `上次偵查：${txt(last.week, 12)} · 看到 ${last.seen} · 留下 ${last.kept}` : '還沒偵查過')
      + ` · 已自動濾掉 ${scout.dropped_without_review || 0} 個無關的 repo（不經審查）` });
    if (!candidates.length) {
      box.replaceChildren(head, el('p', { class: 'muted', text: '還沒有候選：按「立即偵查」（會連網搜尋 GitHub；只記錄候選，不下載）。' }));
      return;
    }
    const list = el('ul', { class: 'scout-list' });
    for (const item of candidates) {
      const picked = item.status === 'picked';
      const id = uid('sc');
      list.append(el('li', { class: 'scout-item' + (picked ? ' picked' : '') },
        el('input', { type: 'checkbox', id: id, disabled: picked, checked: !picked && S.scoutSel.has(item.key), onchange: (e) => {
          if (e.target.checked) S.scoutSel.add(item.key); else S.scoutSel.delete(item.key);
          const go = $('scout-feed');
          if (go) {
            go.disabled = !S.scoutSel.size;
            go.textContent = S.scoutSel.size ? `把勾選的送去試吃（${S.scoutSel.size}）` : '把勾選的送去試吃';
          }
        } }),
        el('label', { for: id },
          el('span', { class: 'scout-name', text: txt(item.display, 80) }),
          item.description ? el('span', { class: 'scout-desc', text: txt(item.description, 160) }) : '',
          el('span', { class: 'scout-meta', text: `★${fmt(item.stars || 0)}（排隊依據，非品質） · ${txt(item.relevance, 80)}` + (picked ? ' · 已送去' : '') }))));
    }
    const go = el('button', { type: 'button', id: 'scout-feed', class: 'btn primary act', disabled: !S.scoutSel.size,
      text: S.scoutSel.size ? `把勾選的送去試吃（${S.scoutSel.size}）` : '把勾選的送去試吃', onclick: scoutFeed });
    box.replaceChildren(head, list, el('div', { class: 'row' }, go));
  }

  // ------------------------------------------------------------------ render: food cards
  function selection(foodId) {
    if (!S.selected.has(foodId)) S.selected.set(foodId, new Set());
    return S.selected.get(foodId);
  }

  function openState(foodId) {
    if (!S.open.has(foodId)) S.open.set(foodId, { elephant: false, goldfish: false, plan: false });
    return S.open.get(foodId);
  }

  function partRow(food, part, key) {
    const selected = selection(food.id);
    const historical = part.level === 'historical-prior';
    const selectable = historical ? part.disposition === 'absorb' && !part.decision : part.can_absorb === true;
    const id = uid('part');
    const status = partState(part);
    const mark = selectable
      ? el('input', { type: 'checkbox', id: id, checked: selected.has(part.id), onchange: (e) => {
        if (e.target.checked) selected.add(part.id); else selected.delete(part.id);
        updateAbsorbButton(food.id);
      } })
      : el('span', { class: 'part-mark', 'aria-hidden': 'true', text: key === 'absorb' ? '•' : key === 'excrete' ? '×' : '…' });
    const tags = el('span', { class: 'part-tags' }, chip(KINDS[part.kind] || txt(part.kind, 20)), part.exec_class ? chip(txt(part.exec_class, 10)) : '',
      part.missing_code === 'ab' ? chip('缺行為 A/B（靜態檢查通過）', 'amber') : '', status ? chip(status, part.in_current_build && part.decision === 'removed' ? 'warn' : '') : '',
      part.history ? chip(txt(part.history, 40)) : '', levelChip(part.level));
    if (historical) {
      // Report text is data written by someone else: fenced and collapsed, never styled like an OAW-derived reason.
      const text = [part.name ? `名稱：${part.name}` : '', part.reason ? `理由：${part.reason}` : '', part.oaw_target ? `OAW 目標：${part.oaw_target}` : '',
        part.missing_test ? `缺的測試：${part.missing_test}` : ''].filter(Boolean).join('\n');
      return el('div', { class: 'part' }, mark,
        el('label', { for: selectable ? id : undefined, class: 'part-body' },
          el('span', { class: 'part-name' }, el('span', { class: 'part-id mono', text: txt(part.id, 80) })), tags,
          text ? untrusted('報告原文', text) : ''));
    }
    return el('div', { class: 'part' }, mark,
      el('label', { for: selectable ? id : undefined, class: 'part-body' },
        el('span', { class: 'part-name' }, txt(part.name || part.id, 80), el('span', { class: 'part-id mono', text: txt(part.id, 80) })), tags,
        part.reason ? el('span', { class: 'part-reason', text: txt(part.reason_zh || part.reason, 300) }) : '',
        part.missing_test ? el('span', { class: 'part-missing', text: '缺：' + txt(part.missing_zh || part.missing_test, 200) } ) : ''));
  }

  // `compact` (imported reports) opens only short groups, so a 30-part ledger stays scannable.
  function groups(food, parts, emptyText, compact) {
    const wrap = el('div', { class: 'parts' });
    for (const key of ['absorb', 'excrete', 'hold']) {
      const items = parts.filter((part) => part && part.disposition === key);
      const [icon, label] = DISPOSITIONS[key];
      const open = compact ? items.length <= 3 : key !== 'hold' || items.length <= 3;
      const group = el('details', { class: `group g-${key}${compact ? ' hist' : ''}`, open: open },
        el('summary', {}, el('span', { text: compact ? `${label}（歷史提案）` : `${icon} ${label}` }), el('span', { class: 'count', text: String(items.length) })));
      if (!items.length) group.append(el('p', { class: 'muted small', text: key === 'absorb' ? emptyText : '沒有。' }));
      for (const part of items) group.append(partRow(food, part, key));
      wrap.append(group);
    }
    return wrap;
  }

  function untrusted(title, text) {
    return el('details', { class: 'untrusted' }, el('summary', { text: `${title}（未受信任的文字，點開看）` }), el('pre', { text: txt(text, 600) }));
  }

  const kv = (key, value) => el('p', { class: 'kv' }, el('span', { class: 'k', text: key }), el('span', { text: value }));

  function importForm(food) {
    const input = el('input', { type: 'text', class: 'path', id: uid('imp'), placeholder: '報告資料夾路徑', value: S.importPath.get(food.id) || '',
      oninput: (e) => S.importPath.set(food.id, e.target.value) });
    const go = el('button', { type: 'button', class: 'btn act', text: '匯入', onclick: async () => {
      const directory = input.value.trim();
      if (!directory) {
        toast('先填資料夾路徑。', 'warn');
        return;
      }
      report(await run('import-report', { food: food.id, directory: directory }, `匯入 ${food.id} 的報告`), '已匯入：標成歷史證據，不計入判定');
    } });
    return el('div', { class: 'import' },
      el('label', { for: input.id, class: 'small', text: '放 digest.json、verify.json、goldfish-*.json、components.json、integration.json、proposals.md 的資料夾（論文的紀錄：components.json、goldfish-*.json、skeptic.json、digest.md…）' }),
      el('div', { class: 'row' }, input, go));
  }

  function elephantPanel(food) {
    const reports = food.historical || [];
    const panel = el('div', { class: 'inner elephant' }, el('h4', { text: '🐘 Elephant 報告（和 OAW 合不合）' }), chip('歷史證據 · 不計入判定', 'lv-historical-prior'));
    if (!reports.length) {
      panel.append(el('p', { class: 'muted', text: '還沒有匯入 Elephant 報告。' }), importForm(food));
      return panel;
    }
    for (const r of reports) {
      const e = r.elephant;
      panel.append(el('p', { class: 'mono small muted', text: txt(r.evidence_id, 100) }));
      if (e) {
        panel.append(kv('整合方式', txt(e.integration_mode, 60) || '—'),
          kv('養分／拉肚子風險／提議的 A/B', `${fmt(e.nutrients)} / ${fmt(e.diarrhea_risks)} / ${fmt(e.proposed_ab_tests)}`));
        if ((e.gates || []).length) panel.append(el('ul', { class: 'gates' }, e.gates.map((g) => el('li', {}, el('span', { text: txt(g.gate, 60) }), chip(txt(g.verdict, 20))))));
        if (e.what_it_does) panel.append(untrusted('Elephant 的描述', e.what_it_does));
      }
      if (r.verify) {
        const statuses = Object.entries(r.verify.by_status || {}).map(([k, n]) => `${txt(k, 20)} ${n}`).join('、');
        panel.append(kv('查證', `${fmt(r.verify.checks)} 項${statuses ? '（' + statuses + '）' : ''} · 漏掉 ${fmt(r.verify.missed_issues)}`));
      }
      if (r.integration) {
        panel.append(untrusted('整合紀錄摘要', Object.entries(r.integration).map(([k, v]) => `${txt(k, 40)}：${txt(v, 160)}`).join('\n')));
      }
      if (r.proposals && (r.proposals.headings || []).length) {
        panel.append(untrusted(`吸收提案的章節（${r.proposals.headings.length}）`, r.proposals.headings.map((h) => txt(h, 120)).join('\n')));
      }
      if (r.paper) {
        panel.append(kv('論文（紀錄裡寫的）', `${txt(r.paper.title, 160) || '—'} · ${txt(r.paper.version, 8) || '沒有版本'} · ${txt(r.paper.license, 40) || '授權不明'}`));
      }
      for (const review of r.reviews || []) {
        const severity = Object.entries(review.by_severity || {}).map(([k, n]) => `${txt(k, 20)} ${n}`).join('、');
        panel.append(kv(`其他審查（${txt(review.reviewer, 40)}）`, `${fmt(review.findings)} 項發現${severity ? '（' + severity + '）' : ''}`));
      }
      if ((r.documents || []).length) {
        panel.append(untrusted(`紀錄文件（${r.documents.length}）`, r.documents.map((d) => `${txt(d.name, 60)}（${fmt(d.bytes)} bytes）：`
          + (d.headings || []).map((h) => txt(h, 120)).join('；')).join('\n')));
      }
      if ((r.components || []).length) {
        panel.append(el('h5', { text: `Elephant 提的成分分流（${r.components.length}）` }),
          groups(food, r.components, '沒有提議吸收的成分。', true),
          el('p', { class: 'muted small', text: '勾選歷史提案再按「吸收選中的成分」，只會記成待辦項目，不改程式。' }));
      }
    }
    panel.append(el('details', { class: 'small' }, el('summary', { text: '再匯入一份報告' }), importForm(food)));
    return panel;
  }

  // D15: what a goldfish record must state about its launch; anything missing is shown as 未記錄, never assumed.
  const LAUNCH_FIELDS = [['method', '啟動方式'], ['host_version', 'host 版本'], ['inherited_context', '繼承的脈絡'], ['init_event_check', 'init event 檢查']];

  function launchValue(launch, key) {
    const value = launch && launch[key];
    return value === null || value === undefined || value === '' ? el('span', { class: 'muted', text: '未記錄' }) : el('span', { text: txt(value, 160) });
  }

  function goldfishPanel(food) {
    const reports = food.historical || [];
    const panel = el('div', { class: 'inner goldfish' }, el('h4', { text: '🐟 Goldfish 報告（匯入；零脈絡未驗證）' }), chip('歷史證據 · 不計入判定', 'lv-historical-prior'));
    const fishes = reports.flatMap((r) => r.goldfish || []);
    if (!fishes.length) {
      panel.append(el('p', { class: 'muted', text: reports.length ? '這份紀錄沒有 Goldfish 審查。' : '還沒有匯入 Goldfish 報告。' }));
      if (!reports.length) panel.append(importForm(food));
      return panel;
    }
    for (const fish of fishes) {
      panel.append(el('div', { class: 'fish' },
        el('div', { class: 'fish-head' }, el('span', { class: 'mono', text: txt(fish.reviewer, 40) }), chip(`${fmt(fish.findings)} 項發現`),
          Object.entries(fish.by_severity || {}).map(([k, n]) => chip(`${txt(k, 20)} ${n}`))),
        el('ul', { class: 'fish-launch small' }, LAUNCH_FIELDS.map(([key, name]) => el('li', {},
          `${name}：`, launchValue(fish.launch, key)))),
        fish.summary ? untrusted('Goldfish 的結論', fish.summary) : ''));
    }
    panel.append(el('p', { class: 'muted small', text: 'Goldfish 審的是我們的吸收草稿才算數；只審食物本身不能取代（D10）。零脈絡要驗證過（D15）：盲審這一站還是規劃中。' }));
    return panel;
  }

  function planPanel(food) {
    const plan = S.plans.get(food.id);
    const panel = el('div', { class: 'inner plan' }, el('h4', { text: '計畫：系統依證據決定的測試（實測還是規劃中）' }));
    if (!plan) {
      panel.append(el('p', { class: 'muted', text: '載入中…' }));
      return panel;
    }
    panel.append(kv('狀態', planStatusLabel(plan.status)),
      el('p', { class: 'muted small', text: '由系統決定要測什麼（D11），最便宜、最能分辨的先做；你只設定一次常設預算。' }));
    const list = el('ol', { class: 'psteps' });
    for (const step of plan.steps || []) {
      list.append(el('li', { class: 'pstep' + (step.state === 'done' ? ' done' : '') },
        el('div', { class: 'pstep-head' }, el('span', { class: 'mono', text: txt(step.id, 12) }), el('strong', { text: PLAN_STEPS[step.id] || txt(step.name, 100) }),
          chip(PLAN_STATES[step.state] || txt(step.state, 60)), chip(step.tokens ? tokensText(step.tokens) : txt(step.cost_zh || step.cost, 30)),
          D13_STAGES[step.d13_stage] ? chip(D13_STAGES[step.d13_stage], step.d13_stage === 2 ? 'warn' : '') : '',
          step.sandbox_level ? chip(`沙箱 level ${txt(step.sandbox_level, 2)}`) : '',
          step.conditional ? chip('條件式') : ''),
        el('div', { class: 'small muted', text: txt(step.name_zh || step.name, 160) }),
        el('div', { class: 'small', text: '能證明：' + (step.can_prove_zh || step.can_prove || []).map((x) => txt(x, 120)).join('；') }),
        el('div', { class: 'small', text: '不能證明：' + (step.cannot_prove_zh || step.cannot_prove || []).map((x) => txt(x, 120)).join('；') })));
    }
    const policySet = !!(S.view && S.view.policy && S.view.policy.set);
    const estimate = plan.estimate || {};
    const fixed = Number.isFinite(estimate.unconditional_max) ? { min: estimate.min, max: estimate.unconditional_max } : estimate;
    const extra = Number.isFinite(estimate.conditional_max) && estimate.conditional_max > 0
      ? `；另加最多 ${(estimate.conditional_max / 1e6).toFixed(1)}M tokens（條件式，只在冒煙測試沒有決定性負面時才跑）` : '';
    const screening = Number.isFinite(estimate.screening_max) ? `第 0/1 階段最多 ${(estimate.screening_max / 1e6).toFixed(1)}M tokens（和常設預算比）` : '';
    panel.append(list, kv('付費預估合計', tokensText(fixed) + extra), screening ? kv('常設預算比的是', screening) : '',
      plan.second_host_zh ? el('p', { class: 'muted small', text: txt(plan.second_host_zh, 160) }) : '',
      el('p', { class: 'muted small', text: txt(estimate.label_zh || estimate.label, 160) }),
      el('div', { class: 'row' }, el('button', { type: 'button', class: 'btn', disabled: true, text: '實測（依常設政策）：規劃中' }),
        el('span', { class: 'hint', text: '實測這一站還沒自動化：原型 v0 只顯示系統規劃的測試和預估花費。' + (policySet ? '' : '也還沒設定常設預算（在「版本：我的 OAW」）。') })));
    return panel;
  }

  function updateAbsorbButton(foodId) {
    const size = selection(foodId).size;
    for (const button of document.querySelectorAll('.absorb-btn')) {
      if (button.dataset.food !== foodId) continue;
      button.disabled = !size;
      button.textContent = size ? `吸收選中的成分（${size}）` : '吸收選中的成分';
    }
  }

  function card(food) {
    const verdict = food.verdict || {};
    const family = FAMILY[verdict.headline] || 'unknown';
    const tasted = !!food.tasted;
    const open = openState(food.id);
    const parts = Array.isArray(food.components) ? food.components : [];
    const installed = parts.some((part) => part.in_current_build);
    const pipeline = food.pipeline || {};
    const pinned = food.pinned || {};
    // A repository is pinned to a commit; a paper to an arXiv version plus the sha256 of its sealed PDF.
    const pin = food.kind === 'paper'
      ? (pinned.pdf_sha12 ? `${pinned.version ? 'arXiv ' + txt(pinned.version, 8) : '本機 PDF'} · sha256 ${txt(pinned.pdf_sha12, 12)}` : '未固定版本')
      : pinned.commit7 ? '@' + txt(pinned.commit7, 12) : '未固定版本';
    const meta = [txt(food.id, 64), food.kind === 'paper' ? '論文' : '', ORIGINS[food.origin] || '', pin, INTEGRITY[pinned.integrity] || '',
      food.license ? txt(food.license, 40) : '', food.exec_class ? '執行等級 ' + txt(food.exec_class, 10) : ''].filter(Boolean).join(' · ');
    const node = el('article', { class: `card fam-${family}`, 'data-food': food.id },
      el('header', { class: 'card-head' },
        el('div', { class: `badge fam-${family}` },
          el('span', { class: 'badge-sym', 'aria-hidden': 'true', text: txt(verdict.symbol, 3) || '?' }),
          el('span', { class: 'badge-text', text: headlineLabel(verdict) })),
        el('div', { class: 'card-title' }, el('h3', { text: txt(food.display, 80) }), el('p', { class: 'meta mono', text: meta }))),
      (verdict.reasons || []).length ? el('p', { class: 'verdict-reasons', text: '判定依據：' + (verdict.reasons_zh || verdict.reasons).map((r) => txt(r, 160)).join('；') }) : '',
      el('p', { class: 'stage-now' }, el('span', { class: 'k', text: '這一站' }),
        `${txt(pipeline.stage_label_zh, 8) || '?'}（${txt(pipeline.state_zh, 8) || '?'}）· ${txt(pipeline.note_zh, 160) || '—'}`),
      pipeline.parity ? el('p', { class: 'small muted', text: txt(pipeline.parity.label_zh, 60) }) : '',
      food.paper ? paperBlock(food.paper) : '');
    const chips = [levelChip(verdict.level)];
    for (const c of verdict.chips || []) chips.push(chip(chipLabel(c)));
    if (verdict.stale) chips.push(chip('⟲ 需重測', 'warn'));
    if ((verdict.badges || []).includes('evolved') && verdict.level === 'measured') chips.push(chip('進化（實測）', 'good'));
    for (const allergen of food.allergens || []) chips.push(chip('過敏原 ' + txt(allergen, 40), 'amber'));
    node.append(el('p', { class: 'safety', title: txt(food.safety_text, 200) }, el('span', { class: 'k', text: '安全' }), safetyLabel(food)),
      el('div', { class: 'chips' }, chips));
    if (food.last_error) node.append(el('p', { class: 'notice bad', text: `上次試吃失敗（${when(food.last_error.at)}）：` + txt(food.last_error.error_zh || food.last_error.error, 300) }));
    if (verdict.headline === 'toxic') node.append(el('p', { class: 'notice bad', text: '經人工確認有毒：不會進專案。' }));
    else if ((food.flags || {}).open) {
      node.append(el('p', { class: 'notice warn', text: `${food.flags.open} 個旗標待分流（高 ${food.flags.open_high || 0}）：在終端執行 catalog.py menu → 12「分流旗標」（良性、過敏原要終端確認碼）。靜態規則只會舉旗，不會判有毒。` }));
    }
    if (verdict.headline === 'inedible') node.append(el('p', { class: 'notice', text: 'OAW 沒辦法照原樣消化它（這不是說它有害）。' }));
    const flagList = (food.flag_list || []).filter(Boolean);
    if (flagList.length) {
      node.append(el('details', { class: 'flags', open: flagList.some((f) => f.severity === 'high' && !f.triage) },
        el('summary', { text: `旗標（${flagList.length}）` }),
        el('ul', { class: 'flag-list' }, flagList.map((f) => el('li', {},
          chip(SEVERITY[f.severity] || txt(f.severity, 8), 'sev-' + (SEVERITY[f.severity] ? f.severity : 'low')),
          el('span', { class: 'mono', text: `${txt(f.rule, 16)} ${mid(f.path, 60)}${f.line ? ':' + f.line : ''}` }),
          el('span', { text: txt(f.meaning_zh || f.meaning, 120) }), f.triage ? chip(TRIAGE[f.triage] || txt(f.triage, 20)) : '')))));
    }
    if (parts.length) node.append(groups(food, parts, '沒有可以直接吸收的成分。'));
    else if (food.kind === 'paper') node.append(el('p', { class: 'muted small', text: txt(food.components_note_zh, 200) || '論文的成分要由 Elephant 拆（規劃中），或匯入已有的消化紀錄；v0 不會自己拆，也不會編造成分。' }));
    else node.append(el('p', { class: 'muted small', text: tasted ? '沒有拆出成分。' : '試吃後會把食物拆成成分，分成吸收／排掉／暫留。' }));
    if (open.elephant) node.append(elephantPanel(food));
    if (open.goldfish) node.append(goldfishPanel(food));
    if (open.plan) node.append(planPanel(food));
    const selected = selection(food.id);
    const historyCount = (food.historical || []).length;
    node.append(el('div', { class: 'actions' },
      tasted ? '' : el('button', { type: 'button', class: 'btn primary act', text: '送去試吃', onclick: () => tasteFlow(food) }),
      el('button', { type: 'button', class: 'btn act toggle' + (open.elephant ? ' on' : ''), 'aria-pressed': String(open.elephant),
        text: '🐘 Elephant 報告' + (historyCount ? '' : '（未匯入）'), onclick: () => togglePanel(food.id, 'elephant') }),
      el('button', { type: 'button', class: 'btn act toggle' + (open.goldfish ? ' on' : ''), 'aria-pressed': String(open.goldfish),
        text: '🐟 Goldfish 報告' + (historyCount ? '' : '（未匯入）'), onclick: () => togglePanel(food.id, 'goldfish') }),
      el('button', { type: 'button', class: 'btn act toggle' + (open.plan ? ' on' : ''), 'aria-pressed': String(open.plan), text: '看計畫', onclick: () => planFlow(food) }),
      el('button', { type: 'button', class: 'btn primary act absorb-btn', 'data-food': food.id, disabled: !selected.size,
        text: selected.size ? `吸收選中的成分（${selected.size}）` : '吸收選中的成分', onclick: () => absorbFlow(food) }),
      el('button', { type: 'button', class: 'btn danger act', disabled: !installed, text: '移除已安裝的部分',
        title: installed ? '移除這樣食物已安裝的 skill（先預覽）' : '還沒有吸收任何會安裝的成分', onclick: () => removeFlow(food.id, food) }),
      installed ? '' : el('button', { type: 'button', class: 'btn act', text: '忘掉這樣食物', title: '從食物卡拿掉（先預覽）；決定紀錄會保留', onclick: () => forgetFlow(food) })));
    return node;
  }

  // A paper's title, authors, version and license (from the sealed taste, or as an imported record states them).
  function paperBlock(paper) {
    const authors = (paper.authors || []).map((a) => txt(a, 80));
    const total = Number.isInteger(paper.authors_total) ? paper.authors_total : authors.length;
    const more = total > authors.length ? `（共 ${total} 位）` : '';
    const version = paper.version ? txt(paper.version, 8) + (paper.version_date ? `（${txt(paper.version_date, 20)}）` : '') : '沒有版本（本機 PDF）';
    return el('div', { class: 'paper' },
      el('p', { class: 'paper-title', text: txt(paper.title, 300) || '（沒有標題：本機 PDF 只記檔案本身）' }),
      kv('作者', authors.length ? authors.join('、') + more : '未記錄'),
      kv('版本', version + (paper.arxiv_id ? ` · arXiv:${txt(paper.arxiv_id, 40)}` : '')),
      kv('授權', `${txt(paper.license, 60) || '不明'}` + (REUSE[paper.reuse] ? ` · ${REUSE[paper.reuse]}` : '')),
      Number.isInteger(paper.abstract_chars) ? kv('摘要', `${fmt(paper.abstract_chars)} 字元（摘要原文留在 LAB_HOME，不進專案）`) : '',
      paper.from === 'imported' ? el('p', { class: 'muted small', text: '這是匯入的紀錄自己寫的（歷史證據）；試吃後改用封存的中繼資料。' }) : '');
  }

  function togglePanel(foodId, name) {
    const open = openState(foodId);
    open[name] = !open[name];
    renderDetail();
  }

  // ------------------------------------------------------------------ flows
  async function stageAction(food, action) {
    const params = action.params || {};
    if (action.id === 'taste') return tasteFlow(food);
    if (action.id === 'forget') return forgetFlow(food);
    if (action.id === 'absorb') return absorbChoose(food);
    if (action.id === 'remove-food') return removeFlow(food.id, food);
    if (action.id === 'restore' && typeof params.build === 'string') return restoreFlow({ name: params.build });
    toast('這個動作只在終端：執行 python3 scripts/catalog.py menu。', 'info');
    return null;
  }

  // 核准: choose the parts on the pipeline, then the usual preview and confirmation.
  async function absorbChoose(food) {
    const parts = (Array.isArray(food.components) ? food.components : [])
      .filter((part) => part && part.can_absorb === true)
      .map((part) => ({ id: part.id, label: txt(part.name || part.id, 80), sub: `${txt(part.id, 80)} · ${LEVELS[part.level] || txt(part.level, 20)} · ${txt(part.reason_zh || part.reason, 160)}` }));
    const history = (food.historical || []).flatMap((report) => report.components || [])
      .filter((part) => part && part.disposition === 'absorb' && !part.decision)
      .map((part) => ({ id: part.id, label: txt(part.id, 80), sub: '歷史提案：只記成待辦，不改程式，也不產生新版本' }));
    const items = parts.concat(history);
    if (!items.length) {
      toast('這樣食物目前沒有可以吸收的成分。', 'info');
      return;
    }
    const ids = await askChoose({ title: `核准：吸收 ${txt(food.display, 60)} 的哪些成分？`, items: items, ok: '下一步：預覽',
      note: '先預覽要寫哪些檔案，你確認後才吸收：先存還原點，再產生新版本，並評估和預設比的差異（每一行標證據等級）。' });
    if (ids && ids.length) await absorbFlow(food, ids);
  }

  async function tasteFlow(food) {
    report(await run('taste', { food: food.id }, `試吃 ${food.id}`), `${food.id} 試吃完成`);
  }

  // `show` (from the 計畫 stage on the pipeline) always opens the card on the plan.
  async function planFlow(food, show) {
    const open = openState(food.id);
    if (open.plan && !show) {
      open.plan = false;
      renderDetail();
      return;
    }
    const envelope = await run('plan', { food: food.id }, `${food.id} 的測試計畫`);
    if (envelope && envelope.ok) {
      S.plans.set(food.id, envelope.result.plan);
      open.plan = true;
      if (show) openFood(food.id);
      else renderDetail();
    } else report(envelope);
  }

  async function absorbFlow(food, chosen) {
    const ids = chosen || Array.from(selection(food.id));
    if (!ids.length) return;
    const preview = await run('absorb', { food: food.id, components: ids, apply: false }, '預覽吸收');
    if (!preview) return;
    if (!preview.ok) {
      report(preview);
      return;
    }
    const r = preview.result || {};
    const lines = r.creates_build
      ? ['先存一個還原點，再產生新版本，並立刻評估和預設 2.0.0 比的差異（每一行標證據等級）。',
        'skill 文字照原樣複製（還沒重新實作成 OAW 部件），附上食物的授權檔和出處說明 OAW-UPSTREAM.md。']
      : ['只把歷史提案記成待辦（寫進決定紀錄）：不改任何安裝檔，也不產生新版本。'];
    for (const s of r.selections || []) lines.push(`${s.id}：${s.outcome === 'installed' ? '安裝 skill ' + s.name : '記成待辦項目（不改程式）'}`);
    if ((r.writes || []).length) lines.push('會新增的檔案：', ...r.writes, '另外會寫入吸收收據：.oaw/catalog/absorbed/' + txt(food.id, 64) + '.json');
    const answer = await ask({ title: r.creates_build ? `吸收 ${txt(food.display, 60)} 的 ${ids.length} 個成分？` : `把 ${ids.length} 個歷史提案記成待辦？`,
      lines: lines, ok: r.creates_build ? '確認吸收' : '記成待辦', reason: true });
    if (!answer) return;
    const done = await run('absorb', { food: food.id, components: ids, apply: true, reason: answer.reason || '由網頁吸收' }, r.creates_build ? '吸收中' : '記成待辦');
    if (done && done.ok) {
      S.selected.delete(food.id);
      renderDetail();
      const res = done.result || {};
      if (res.build) {
        const doctor = (res.doctor || {}).status;
        toast(`已吸收：新版本 ${txt(res.build, 60)} · doctor：${txt(doctor, 20)}`, doctor === 'healthy' ? 'info' : 'warn');
      } else toast(`已記成待辦 ${(res.backlog || []).length} 項（未改程式，沒有新版本）`, 'info');
    } else report(done);
  }

  async function removeFlow(name, food) {
    const label = food ? `${txt(food.display, 60)} 已安裝的部分` : name === 'egm' ? '整組 EGM' : name;
    const target = { name: name, food: !!food };
    const preview = await run('remove', Object.assign({ apply: false }, target), `預覽移除 ${label}`);
    if (!preview) return;
    if (!preview.ok) {
      report(preview);
      return;
    }
    const r = preview.result || {};
    const lines = ['先備份並存一個還原點，再移除；之後可以用「還原到這版」一鍵加回來，但加回來的 skill 會標「要重新測試」（D6）。'];
    for (const a of r.actions || []) lines.push(`${PLAN_ACTIONS[a.action] || txt(a.action, 20)}  ${txt(a.path, 200)}`);
    for (const path of r.deletes || []) lines.push(`刪除  ${txt(path, 200)}`);
    const conflicts = r.conflicts || [];
    if (conflicts.length) lines.push(`⚠ 你改過的檔案擋住了移除：${conflicts.join('、')}（先用 oaw.py migrate 處理）`);
    const answer = await ask({ title: `移除 ${label}？`, lines: lines, ok: '確認移除', reason: true, reasonRequired: true, danger: true, disabled: conflicts.length > 0 });
    if (!answer || !answer.reason) return;
    const done = await run('remove', Object.assign({ apply: true, reason: answer.reason }, target), `移除 ${label}`);
    if (done && done.ok) toast(`已移除 ${label}：新版本 ${txt(done.result.build, 60)} · doctor：${txt((done.result.doctor || {}).status, 20)}`, 'good');
    else report(done);
  }

  async function readdFlow(name) {
    const label = name === 'egm' ? '整組 EGM' : name;
    const preview = await run('readd', { name: name, apply: false }, `預覽加回 ${label}`);
    if (!preview) return;
    if (!preview.ok) {
      report(preview);
      return;
    }
    const r = preview.result || {};
    const lines = ['經 oaw.py migrate 加回：先備份並存一個還原點；之後的其他變更都保留。加回的 skill 算「未測」，要重新測試（D6）。'];
    for (const a of r.actions || []) lines.push(`${PLAN_ACTIONS[a.action] || txt(a.action, 20)}  ${txt(a.path, 200)}`);
    const conflicts = r.conflicts || [];
    if (conflicts.length) lines.push(`⚠ 你改過的檔案擋住了加回：${conflicts.join('、')}（先用 oaw.py migrate 處理）`);
    const answer = await ask({ title: `加回 ${label}？`, lines: lines, ok: '確認加回', reason: true, reasonRequired: true, disabled: conflicts.length > 0 });
    if (!answer || !answer.reason) return;
    const done = await run('readd', { name: name, apply: true, reason: answer.reason }, `加回 ${label}`);
    if (done && done.ok) toast(`已加回 ${label}：新版本 ${txt(done.result.build, 60)} · doctor：${txt((done.result.doctor || {}).status, 20)}（要重新測試）`, 'good');
    else report(done);
  }

  async function forgetFlow(food) {
    const preview = await run('forget', { food: food.id, apply: false }, `預覽忘掉 ${food.id}`);
    if (!preview) return;
    if (!preview.ok) {
      report(preview);
      return;
    }
    const lines = ['從食物卡拿掉這樣食物：刪掉它的登記和證據摘要；決定紀錄保留（重新送來時從頭開始），LAB_HOME 的封存保留。'];
    for (const path of preview.result.evidence || []) lines.push('刪除  ' + txt(path, 200));
    const answer = await ask({ title: `忘掉 ${txt(food.display, 60)}？`, lines: lines, ok: '確認忘掉', reason: true, danger: true });
    if (!answer) return;
    report(await run('forget', { food: food.id, apply: true, reason: answer.reason || '由網頁忘掉' }, `忘掉 ${food.id}`), `已忘掉 ${txt(food.id, 64)}`);
  }

  async function restoreFlow(build) {
    const preview = await run('restore', { build: build.name, apply: false }, `預覽還原到 ${build.name}`);
    if (!preview) return;
    if (!preview.ok) {
      report(preview);
      return;
    }
    const writes = preview.result.writes || [];
    const deletes = preview.result.deletes || [];
    const kept = preview.result.kept || [];
    const blocked = preview.result.conflicts || [];
    const lines = ['只動 OAW 安裝層，不動你的專案資料；先把目前的安裝存成還原點，還原後跑 doctor。',
      writes.length || deletes.length ? `寫入 ${writes.length} 個檔、刪除 ${deletes.length} 個檔：` : '檔案已經和這一版一樣，只會改「目前版本」的紀錄。']
      .concat(writes.map((w) => '寫入  ' + txt(w.path, 200)), deletes.map((d) => '刪除  ' + txt(d.path, 200)),
        kept.map((p) => '保留  ' + txt(p, 200) + '（你的自訂檔，不會被蓋掉）'),
        blocked.length ? ['⚠ 這些檔案不屬於目前的安裝層，還原會蓋掉它們，所以不能還原：先移開或改名：'] : [],
        blocked.map((p) => '擋住  ' + txt(p, 200)));
    const answer = await ask({ title: `還原到 ${txt(build.name, 60)}？`, lines: lines, ok: '確認還原', disabled: blocked.length > 0 });
    if (!answer) return;
    const done = await run('restore', { build: build.name, apply: true }, `還原到 ${build.name}`);
    if (done && done.ok) {
      toast(`已還原到 ${txt(done.result.build, 60)} · doctor：${txt((done.result.doctor || {}).status, 20)} · 原本的安裝存成 ${txt(done.result.restore_point, 60)}`, 'good');
    } else report(done);
  }

  async function importAny() {
    const directory = $('import-dir').value.trim();
    const food = $('import-food').value.trim();
    if (!directory) {
      toast('先填報告資料夾路徑。', 'warn');
      $('import-dir').focus();
      return;
    }
    const envelope = await run('import-report', { food: food, directory: directory }, '匯入消化紀錄');
    if (envelope && envelope.ok) {
      $('import-dir').value = '';
      $('import-food').value = '';
      const id = txt(envelope.result.food, 64);
      openState(envelope.result.food).elephant = true;
      openFood(envelope.result.food);
      toast(`已匯入 ${id} 的紀錄：標成歷史證據，不計入判定`, 'good');
    } else report(envelope);
  }

  async function scoutRun() {
    const envelope = await run('scout', {}, '偵查中（連網搜尋 GitHub，只記錄候選）');
    if (envelope && envelope.ok) {
      toast(`偵查完成：留下 ${fmt(envelope.result.kept)} 個候選，自動濾掉 ${fmt((envelope.result.dropped || []).length)} 個無關 repo。`, 'good');
    } else report(envelope);
  }

  // ------------------------------------------------------------------ start
  async function init() {
    $('rules').replaceChildren(...RULES.map((rule) => el('li', { text: rule })));
    $('feed-go').addEventListener('click', feed);
    $('scout-run').addEventListener('click', scoutRun);
    $('import-go').addEventListener('click', importAny);
    $('feed-urls').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) feed();
    });
    renderPipeline();
    renderDetail();
    S.token = readToken();
    if (!S.token) {
      banner('網址裡沒有通行碼：請用終端顯示的完整網址開啟（含 #t=…）。');
      return;
    }
    try {
      S.meta = await api('/api/meta');
    } catch (e) {
      return;
    }
    await refresh(true);
    setInterval(() => {
      if (!S.busy && !document.hidden) refresh(false);
    }, 5000);
  }

  init();
})();
