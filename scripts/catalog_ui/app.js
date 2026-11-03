// OAW 消化系統 (catalog.py ui). No frameworks, no external resources.
// Every food-derived string is set with textContent or a text node; this file never
// assigns markup. Display rules are kept in step with scripts/oaw_status.py.
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
  const STEP_MARKS = ['①', '②', '③', '④'];
  const STEP_NAMES = ['找到', '試吃', '實測', '結果'];
  const METRICS = {
    'skills': 'skill 數', 'files': '檔案數', 'bytes': '大小（bytes）',
    'startup-loaded text bytes (codex)': '啟動載入文字 bytes（Codex）',
    'startup-loaded text bytes (claude)': '啟動載入文字 bytes（Claude）', 'hooks': 'hooks',
    'non-stdlib dependencies': '非標準函式庫相依', 'host settings writes': '寫入 host 設定', 'quality': '品質'
  };
  const BUILD_KINDS = { 'baseline': '基準版', 'restore-point': '還原點', 'absorb': '吸收', 'remove': '移除', 'restore': '還原', 'readd': '加回' };
  const HOSTS = { 'codex': 'Codex', 'claude': 'Claude' };
  const SEVERITY = { 'high': '高', 'medium': '中', 'low': '低' };
  const TRIAGE = { 'benign': '已判良性', 'allergen': '已判過敏原', 'confirm-toxic': '你確認有毒' };
  const OWNER_CONFIRMS = '建議（尚未經你確認）';
  const CHIPS = { 'free-checks-passed': '免費檢查通過', 'rules-updated-free-T0-pending': '規則已更新，待重跑免費檢查' };
  const INTEGRITY = { 'git-object-verified': 'git 物件驗證', 'unverified-against-commit': '未對 commit 驗證' };
  const PLAN_STATUS = [
    ['waiting for standing policy', '等你設定常設預算'],
    ['within policy', '在常設預算內（v0 尚未開放付費實測）'],
    ['exceeds standing policy', '超過常設預算：需要你同意（v0 尚未開放付費實測）'],
    ['taste first', '先試吃：免費靜態檢查決定付費計畫'],
    ['no paid test: owner confirmed toxic', '不需實測：已確認有毒'],
    ['no paid test: oaw cannot digest', '不需實測：OAW 無法消化'],
    ['blocked', '被擋住：高嚴重度旗標要先分流'],
    ['no paid test needed', '不需付費實測：沒有可吸收的成分']
  ];
  const PLAN_STEPS = {
    'T0': '免費靜態檢查', 'T1': '離線整合', 'T2a': '人工分流旗標', 'G': '金魚盲審我們的吸收草稿', 'TX': '可拋棄環境試跑',
    'T3a-smoke': '行為 A/B 冒煙測試', 'T4': '和現有配方整合', 'P': '齊平底線（OAW＋食物 對 單吃食物）', 'T3a': '行為 A/B 完整測試'
  };
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
  const ORIGINS = { 'url': '網址', 'scout': '覓食', 'import': '匯入' };
  const SANDBOX = {
    'isolated-venv': '隔離的 venv', 'project-copy': '專案副本', 'no-api-keys': '不帶 API key', 'no-network': '不連網',
    'disposable-vm': '可拋棄 VM'
  };
  const PLAN_ACTIONS = { 'retire': '停用', 'remove': '刪除', 'delete': '刪除', 'add': '新增', 'update': '更新', 'backup': '備份' };
  const ACTIONS = {
    'add': '加入', 'feed': '送去試吃', 'taste': '試吃', 'scout': '覓食', 'scout-pick': '挑選', 'import-report': '匯入報告',
    'plan': '實測計畫', 'absorb': '吸收', 'remove': '移除', 'builds': '版本', 'restore': '還原', 'effect': '評估',
    'policy-show': '常設預算', 'policy-set': '設定常設預算', 'triage': '分流', 'view': '更新視圖'
  };
  const RULES = [
    '沒有證據就沒有判定。星數和名氣只決定排序。',
    '食物不進專案，也不在你的電腦上執行，直到你按下吸收並安裝。',
    '「有毒」一定要經過人工確認。自動掃描只會舉旗，不會替作者貼上有毒的標籤。',
    '執行中只顯示進度和花費，不顯示即時分數。',
    '「加強」只在有實測證據時出現，否則一律顯示「未量測」。',
    '大象和金魚的報告是匯入的歷史證據：只顯示，不計入判定。',
    'Claude 和 Codex（這個網頁、catalog.py menu、oaw_status.py）讀的是同一份 view.json。'
  ];
  const UNSAFE = /[\u0000-\u001f\u007f-\u009f\u061c\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]/g;

  // ------------------------------------------------------------------ state
  const S = {
    token: '', meta: null, view: null, viewNote: null, sig: null, busy: false, lastAutoView: 0,
    prev: null, selected: new Map(), open: new Map(), plans: new Map(), importPath: new Map(),
    scoutSel: new Set(), feedResult: null, policyOpen: false, policyDraft: null, policyPending: null, log: [], uid: 0
  };
  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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
    if (part.in_current_build) return '在目前版本中';
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
    const steps = Array.isArray(food.steps) ? food.steps : [];
    const flags = food.flags || {};
    if ((food.verdict || {}).headline === 'toxic') return '經人工確認有毒';
    if (!steps[1] || steps[1].state !== 'done') return '尚未檢查';
    if (flags.open) return `${flags.open} 個旗標未分流（高 ${flags.open_high || 0}）`;
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

  async function follow(job, label) {
    while (job && job.state === 'running') {
      showBusy(label, job);
      await sleep(450);
      job = (await api('/api/job/' + encodeURIComponent(job.id))).job;
    }
    return job;
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
      await refresh(true);
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
      await refresh(true);
    }
  }

  // A poll never re-renders under the owner's cursor; the next poll or action catches up.
  function editing() {
    const node = document.activeElement;
    return !!node && /^(INPUT|TEXTAREA|SELECT)$/.test(node.tagName) && !!node.closest('#my-oaw-body, #food-cards');
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
    else if (envelope.code === 4) toast('等你輸入終端上的確認碼。', 'info');
    else toast('沒有完成：' + errorText(envelope), 'bad');
  }

  function logAction(label, envelope) {
    S.log.unshift({ at: new Date(), label: label, envelope: envelope });
    S.log.length = Math.min(S.log.length, 10);
    const box = $('log');
    box.replaceChildren(...S.log.map((entry) => {
      const env = entry.envelope || {};
      const mark = env.ok ? '✔' : env.code === 4 ? '⏸' : '✖';
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
    return new Promise((resolve) => {
      const finish = (value) => {
        ok.onclick = null;
        $('dialog-cancel').onclick = null;
        dialog.onclose = null;
        if (dialog.open) dialog.close();
        resolve(value);
      };
      ok.onclick = () => finish({ reason: reason ? reason.value.trim() : '' });
      $('dialog-cancel').onclick = () => finish(null);
      dialog.onclose = () => finish(null);
      dialog.showModal();
    });
  }

  // ------------------------------------------------------------------ render: top and my OAW
  function render() {
    renderTop();
    renderMy();
    renderScout();
    renderCards();
    renderFeedResult();
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
    if (envelope.code === 4) {
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
      items.push(el('li', { class: 'merge', title: inputs.join('\n') },
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
    toast(parts.join(' · '), (r.failed || []).length || (r.errors || []).length ? 'warn' : 'good');
  }

  async function feed() {
    const area = $('feed-urls');
    const urls = area.value.split(/[\s,]+/).filter(Boolean);
    if (!urls.length) {
      toast('先貼上至少一個 GitHub 網址。', 'warn');
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
    const head = el('p', { class: 'muted small', text: (last ? `上次覓食：${txt(last.week, 12)} · 看到 ${last.seen} · 留下 ${last.kept}` : '還沒覓食過')
      + ` · 已自動濾掉 ${scout.dropped_without_review || 0} 個無關的 repo（不經審查）` });
    if (!candidates.length) {
      box.replaceChildren(head, el('p', { class: 'muted', text: '還沒有候選：按「立即覓食」（會連網搜尋 GitHub；只記錄候選，不下載）。' }));
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

  function foodSig(food) {
    const steps = (food.steps || []).map((step) => step && step.state);
    return { steps: steps, key: JSON.stringify([steps, (food.verdict || {}).headline, food.counts, (food.components || []).map((c) => c.decision), (food.historical || []).length]) };
  }

  function renderCards() {
    const box = $('food-cards');
    const foods = S.view && Array.isArray(S.view.foods) ? S.view.foods : [];
    const first = S.prev === null;
    const next = new Map();
    const cards = foods.map((food) => {
      const sig = foodSig(food);
      next.set(food.id, sig);
      return card(food, first ? undefined : S.prev.get(food.id) || null, sig);
    });
    S.prev = next;
    if (!foods.length) box.replaceChildren(emptyState());
    else box.replaceChildren(...cards);
  }

  function emptyState() {
    return el('div', { class: 'empty' },
      el('div', { class: 'empty-icon', 'aria-hidden': 'true', text: '🍽' }),
      el('h3', { text: '還沒有食物' }),
      el('ol', {},
        el('li', { text: '在上面的投食區貼上 GitHub 網址（可以一次貼很多個）。' }),
        el('li', { text: '按「送去試吃」：系統抓固定版本、封存在專案外，跑免費的靜態檢查。' }),
        el('li', { text: '食物卡會出現在這裡，成分分成 🟢 吸收、🔴 排掉、🟡 暫留；勾選要吸收的成分，按「吸收選中的成分」。' })),
      el('p', { class: 'muted small', text: '也可以按「立即覓食」，從本週的候選清單勾選。' }));
  }

  function track(food, prev) {
    const steps = Array.isArray(food.steps) ? food.steps : [];
    const list = el('ol', { class: 'track', 'aria-label': '進度' });
    let marked = false;
    STEP_NAMES.forEach((name, index) => {
      const step = steps[index] || {};
      const done = step.state === 'done' || step.state === 'measured';
      const locked = index === 2 && step.state === 'not-run';
      let cls = 'step ' + (done ? 'done' : locked ? 'locked' : 'todo') + (index === 3 ? ' result' : '');
      if (!done && !locked && !marked) {
        cls += ' current';
        marked = true;
      }
      if (prev && prev.steps[index] !== step.state && done) cls += ' pop';
      let sub;
      if (index === 0) sub = ORIGINS[food.origin] || txt(food.origin, 20);
      else if (index === 1) sub = done ? `免費 · ${(food.flags || {}).total || 0} 旗標` : '免費 · 未試吃';
      else if (index === 2) sub = step.state === 'measured' ? '已實測' : '付費 · 未執行';
      else sub = done ? headlineLabel(food.verdict) : '—';
      list.append(el('li', { class: cls, title: txt(step.summary, 200) },
        el('span', { class: 'step-dot', text: STEP_MARKS[index] }),
        el('span', { class: 'step-name', text: name }),
        el('span', { class: 'step-sub', text: sub })));
    });
    return list;
  }

  function partRow(food, part, key) {
    const selected = selection(food.id);
    const selectable = part.disposition === 'absorb' && !part.decision && !part.in_current_build;
    const historical = part.level === 'historical-prior';
    const id = uid('part');
    const status = partState(part);
    const mark = selectable
      ? el('input', { type: 'checkbox', id: id, checked: selected.has(part.id), onchange: (e) => {
        if (e.target.checked) selected.add(part.id); else selected.delete(part.id);
        updateAbsorbButton(food.id);
      } })
      : el('span', { class: 'part-mark', 'aria-hidden': 'true', text: key === 'absorb' ? '•' : key === 'excrete' ? '×' : '…' });
    const tags = el('span', { class: 'part-tags' }, chip(KINDS[part.kind] || txt(part.kind, 20)), part.exec_class ? chip(txt(part.exec_class, 10)) : '',
      part.owner_confirms ? chip(OWNER_CONFIRMS, 'warn') : '', status ? chip(status) : '',
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
      el('label', { for: input.id, class: 'small', text: '放 digest.json、verify.json、goldfish-*.json、components.json、integration.json、proposals.md 的資料夾' }),
      el('div', { class: 'row' }, input, go));
  }

  function elephantPanel(food) {
    const reports = food.historical || [];
    const panel = el('div', { class: 'inner elephant' }, el('h4', { text: '🐘 大象報告（和 OAW 合不合）' }), chip('歷史證據 · 不計入判定', 'lv-historical-prior'));
    if (!reports.length) {
      panel.append(el('p', { class: 'muted', text: '還沒有匯入大象報告。' }), importForm(food));
      return panel;
    }
    for (const r of reports) {
      const e = r.elephant;
      panel.append(el('p', { class: 'mono small muted', text: txt(r.evidence_id, 100) }));
      if (e) {
        panel.append(kv('整合方式', txt(e.integration_mode, 60) || '—'),
          kv('養分／拉肚子風險／提議的 A/B', `${fmt(e.nutrients)} / ${fmt(e.diarrhea_risks)} / ${fmt(e.proposed_ab_tests)}`));
        if ((e.gates || []).length) panel.append(el('ul', { class: 'gates' }, e.gates.map((g) => el('li', {}, el('span', { text: txt(g.gate, 60) }), chip(txt(g.verdict, 20))))));
        if (e.what_it_does) panel.append(untrusted('大象的描述', e.what_it_does));
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
      if ((r.components || []).length) {
        panel.append(el('h5', { text: `大象提的成分分流（${r.components.length}）` }),
          groups(food, r.components, '沒有提議吸收的成分。', true),
          el('p', { class: 'muted small', text: '勾選歷史提案再按「吸收選中的成分」，只會記成待辦項目，不改程式。' }));
      }
    }
    panel.append(el('details', { class: 'small' }, el('summary', { text: '再匯入一份報告' }), importForm(food)));
    return panel;
  }

  function goldfishPanel(food) {
    const reports = food.historical || [];
    const panel = el('div', { class: 'inner goldfish' }, el('h4', { text: '🐟 金魚報告（零脈絡盲審）' }), chip('歷史證據 · 不計入判定', 'lv-historical-prior'));
    const fishes = reports.flatMap((r) => r.goldfish || []);
    if (!fishes.length) {
      panel.append(el('p', { class: 'muted', text: reports.length ? '這份紀錄沒有金魚審查。' : '還沒有匯入金魚報告。' }));
      if (!reports.length) panel.append(importForm(food));
      return panel;
    }
    for (const fish of fishes) {
      panel.append(el('div', { class: 'fish' },
        el('div', { class: 'fish-head' }, el('span', { class: 'mono', text: txt(fish.reviewer, 40) }), chip(`${fmt(fish.findings)} 項發現`),
          Object.entries(fish.by_severity || {}).map(([k, n]) => chip(`${txt(k, 20)} ${n}`))),
        fish.summary ? untrusted('金魚的結論', fish.summary) : ''));
    }
    panel.append(el('p', { class: 'muted small', text: '金魚審的是我們的吸收草稿才算數；只審食物本身不能取代（D10）。' }));
    return panel;
  }

  function planPanel(food) {
    const plan = S.plans.get(food.id);
    const panel = el('div', { class: 'inner plan' }, el('h4', { text: '實測…（系統依證據決定的測試計畫）' }));
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
          chip(PLAN_STATES[step.state] || txt(step.state, 60)), chip(step.tokens ? tokensText(step.tokens) : step.cost === 'free' ? '免費' : txt(step.cost, 30)),
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
    panel.append(list, kv('付費預估合計', tokensText(fixed) + extra),
      el('p', { class: 'muted small', text: txt(estimate.label_zh || estimate.label, 160) }),
      el('div', { class: 'row' }, el('button', { type: 'button', class: 'btn', disabled: true, text: '開始實測' }),
        el('span', { class: 'hint', text: '原型 v0 不執行付費實測：只顯示系統規劃的測試和預估花費。' + (policySet ? '' : '也還沒設定常設預算（在「我的 OAW」）。') })));
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

  function card(food, prev, sig) {
    const verdict = food.verdict || {};
    const family = FAMILY[verdict.headline] || 'unknown';
    const steps = Array.isArray(food.steps) ? food.steps : [];
    const tasted = steps[1] && steps[1].state === 'done';
    const open = openState(food.id);
    const parts = Array.isArray(food.components) ? food.components : [];
    const installed = parts.some((part) => part.in_current_build);
    let motion = '';
    if (prev === null) motion = ' arrived';
    else if (prev && prev.key !== sig.key) motion = ' advanced';
    const pinned = food.pinned || {};
    const meta = [txt(food.id, 64), pinned.commit7 ? '@' + txt(pinned.commit7, 12) : '未固定版本', INTEGRITY[pinned.integrity] || '',
      food.license ? txt(food.license, 40) : '', food.exec_class ? '執行等級 ' + txt(food.exec_class, 10) : ''].filter(Boolean).join(' · ');
    const node = el('article', { class: `card fam-${family}${motion}`, 'data-food': food.id },
      el('header', { class: 'card-head' },
        el('div', { class: `badge fam-${family}` },
          el('span', { class: 'badge-sym', 'aria-hidden': 'true', text: txt(verdict.symbol, 3) || '?' }),
          el('span', { class: 'badge-text', text: headlineLabel(verdict) })),
        el('div', { class: 'card-title' }, el('h3', { text: txt(food.display, 80) }), el('p', { class: 'meta mono', text: meta }))),
      (verdict.reasons || []).length ? el('p', { class: 'verdict-reasons', text: '判定依據：' + verdict.reasons.map((r) => txt(r, 160)).join('；') }) : '',
      track(food, prev));
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
          el('span', { text: txt(f.meaning, 120) }), f.triage ? chip(TRIAGE[f.triage] || txt(f.triage, 20)) : '')))));
    }
    if (parts.length) node.append(groups(food, parts, '沒有可以直接吸收的成分。'));
    else node.append(el('p', { class: 'muted small', text: tasted ? '沒有拆出成分。' : '試吃後會把食物拆成成分，分成吸收／排掉／暫留。' }));
    if (open.elephant) node.append(elephantPanel(food));
    if (open.goldfish) node.append(goldfishPanel(food));
    if (open.plan) node.append(planPanel(food));
    const selected = selection(food.id);
    const historyCount = (food.historical || []).length;
    node.append(el('div', { class: 'actions' },
      tasted ? '' : el('button', { type: 'button', class: 'btn primary act', text: '送去試吃', onclick: () => tasteFlow(food) }),
      el('button', { type: 'button', class: 'btn act toggle' + (open.elephant ? ' on' : ''), 'aria-pressed': String(open.elephant),
        text: '🐘 大象報告' + (historyCount ? '' : '（未匯入）'), onclick: () => togglePanel(food.id, 'elephant') }),
      el('button', { type: 'button', class: 'btn act toggle' + (open.goldfish ? ' on' : ''), 'aria-pressed': String(open.goldfish),
        text: '🐟 金魚報告' + (historyCount ? '' : '（未匯入）'), onclick: () => togglePanel(food.id, 'goldfish') }),
      el('button', { type: 'button', class: 'btn act toggle' + (open.plan ? ' on' : ''), 'aria-pressed': String(open.plan), text: '實測…', onclick: () => planFlow(food) }),
      el('button', { type: 'button', class: 'btn primary act absorb-btn', 'data-food': food.id, disabled: !selected.size,
        text: selected.size ? `吸收選中的成分（${selected.size}）` : '吸收選中的成分', onclick: () => absorbFlow(food) }),
      el('button', { type: 'button', class: 'btn danger act', disabled: !installed, text: '排掉／移除',
        title: installed ? '移除這樣食物已安裝的 skill（先預覽）' : '還沒有吸收任何會安裝的成分', onclick: () => removeFlow(food.id, food) }),
      installed ? '' : el('button', { type: 'button', class: 'btn act', text: '忘掉這樣食物', title: '從食物卡拿掉（先預覽）；決定紀錄會保留', onclick: () => forgetFlow(food) })));
    return node;
  }

  function togglePanel(foodId, name) {
    const open = openState(foodId);
    open[name] = !open[name];
    renderCards();
  }

  // ------------------------------------------------------------------ flows
  async function tasteFlow(food) {
    report(await run('taste', { food: food.id }, `試吃 ${food.id}`), `${food.id} 試吃完成`);
  }

  async function planFlow(food) {
    const open = openState(food.id);
    if (open.plan) {
      open.plan = false;
      renderCards();
      return;
    }
    const envelope = await run('plan', { food: food.id }, `${food.id} 的實測計畫`);
    if (envelope && envelope.ok) {
      S.plans.set(food.id, envelope.result.plan);
      open.plan = true;
      renderCards();
    } else report(envelope);
  }

  async function absorbFlow(food) {
    const ids = Array.from(selection(food.id));
    if (!ids.length) return;
    const preview = await run('absorb', { food: food.id, components: ids, apply: false }, '預覽吸收');
    if (!preview) return;
    if (!preview.ok) {
      report(preview);
      return;
    }
    const r = preview.result || {};
    const lines = r.creates_build
      ? ['先存一個還原點，再產生新版本，並立刻評估和預設 2.0.0 比的差異（靜態量測；品質未量測）。']
      : ['只把歷史提案記成待辦（寫進決定紀錄）：不改任何安裝檔，也不產生新版本。'];
    for (const s of r.selections || []) lines.push(`${s.id}：${s.outcome === 'installed' ? '安裝 skill ' + s.name : '記成待辦項目（不改程式）'}`);
    if ((r.writes || []).length) lines.push('會新增的檔案：', ...r.writes, '另外會寫入吸收收據：.oaw/catalog/absorbed/' + txt(food.id, 64) + '.json');
    const answer = await ask({ title: r.creates_build ? `吸收 ${txt(food.display, 60)} 的 ${ids.length} 個成分？` : `把 ${ids.length} 個歷史提案記成待辦？`,
      lines: lines, ok: r.creates_build ? '確認吸收' : '記成待辦', reason: true });
    if (!answer) return;
    const done = await run('absorb', { food: food.id, components: ids, apply: true, reason: answer.reason || '由網頁吸收' }, r.creates_build ? '吸收中' : '記成待辦');
    if (done && done.ok) {
      S.selected.delete(food.id);
      renderCards();
      const res = done.result || {};
      if (res.build) {
        const doctor = (res.doctor || {}).status;
        toast(`已吸收：新版本 ${txt(res.build, 60)} · doctor：${txt(doctor, 20)}（品質：未量測）`, doctor === 'healthy' ? 'good' : 'warn');
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
    const lines = ['先備份並存一個還原點，再移除；之後可以用「還原到這版」一鍵加回來（加回來的 skill 要重新測試）。'];
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
    const lines = ['從食物卡拿掉這樣食物：刪掉它的登記和證據摘要；決定紀錄保留（重新投食時從頭開始），LAB_HOME 的封存保留。'];
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
      renderCards();
      toast(`已匯入 ${id} 的紀錄：標成歷史證據，不計入判定`, 'good');
    } else report(envelope);
  }

  async function scoutRun() {
    const envelope = await run('scout', {}, '覓食中（連網搜尋 GitHub，只記錄候選）');
    if (envelope && envelope.ok) {
      toast(`覓食完成：留下 ${fmt(envelope.result.kept)} 個候選，自動濾掉 ${fmt((envelope.result.dropped || []).length)} 個無關 repo。`, 'good');
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
    renderCards();
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
