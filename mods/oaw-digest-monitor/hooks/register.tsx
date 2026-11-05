// OAW 消化道 (oaw-digest-monitor): the official skill-intake process (D19, D23)
// as a pane beside the chat. Each food is a bolus on the tract at its real stop;
// the selected food shows where it is stuck, why, and what happens if nobody acts,
// with that stop's actions as buttons. Actions run OAW's own catalog.py (preview
// first, --apply only after a second press), so the CLI, the web page, the menu
// and this pane share one engine and one view.json.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { DigestAction, DigestFood, DigestModel, DigestPending, DigestProblem } from '../types'
import {
  PREVIEWED,
  NEEDS_REASON,
  VIEW_SOURCES,
  actionArgv,
  addArgv,
  askBrief,
  baseName,
  joinPath,
  liveText,
  parentPath,
  parseView,
  pythonArgv,
  stageChain,
  stageIndex,
  terminalCommand,
  verdictText,
  viewArgv,
  waitingCount,
  type Runner,
} from './model'
import { tractAlt, tractLines, tractSvg } from './tract'

const PLUGIN = 'oaw-digest-monitor'
const PANE = 'oaw-digest'
const TITLE = 'OAW 消化道'
const POLL_MS = 2000
const LONG_MS = 600_000

// Change a tag when that value's fields change: an earlier version's value is declined.
const modelAtom = atom({ plugin: 'oaw-digest-monitor', key: 'model' } as const, null, { shape: 'model-1' })
const problemAtom = atom({ plugin: 'oaw-digest-monitor', key: 'problem' } as const, null)
const selectedAtom = atom({ plugin: 'oaw-digest-monitor', key: 'selected' } as const, null)
const picksAtom = atom({ plugin: 'oaw-digest-monitor', key: 'picks' } as const, [])
const pendingAtom = atom({ plugin: 'oaw-digest-monitor', key: 'pending' } as const, null)
const busyAtom = atom({ plugin: 'oaw-digest-monitor', key: 'busy' } as const, null)
const messageAtom = atom({ plugin: 'oaw-digest-monitor', key: 'message' } as const, null)

type Options = { project: string; oawCheckout: string; python: string; motion: boolean }
type Where = { project: string | null; oaw: string | null }

// Module variables are per load; everything a drawing reads lives in $.state.
let options: Options = { project: '', oawCheckout: '', python: 'python3', motion: true }
let where: Where | null = null
let lastStamp = ''
let lastLive: { food: string; isRunning: boolean } | null = null
let loading = false
// What the last search looked at, for the pane's explanation and the status tool.
let trace: { bases: string[]; scanned: number; checked: number; errors: string[]; remembered: string | null } = {
  bases: [], scanned: 0, checked: 0, errors: [], remembered: null,
}

function note(error: unknown, what: string): void {
  if (trace.errors.length < 4) trace.errors.push(`${what}: ${error instanceof Error ? error.message : String(error)}`.slice(0, 200))
}

async function stat(path: string, $: EngineInterface): Promise<number | null> {
  try {
    return (await $.fs.stat(path)).mtimeMs
  } catch (error) {
    // A missing file is the normal answer; anything else is worth saying.
    if (!/ENOENT|no such|not found|missing/i.test(String(error))) note(error, `stat ${path}`)
    return null
  }
}

async function readText($: EngineInterface, path: string): Promise<string | null> {
  try {
    const value = await $.fs.read(path)
    return typeof value === 'string' ? value : null
  } catch {
    return null
  }
}

// Find the OAW project (a folder with .oaw/catalog) and the OAW checkout that holds
// scripts/catalog.py: the configured ones, else around the session's root and its
// current folder (a session that moved into a subfolder still finds a sibling
// project): each of those folders, its parents, and the direct children of the
// nearest parents; newest catalog first.
const PARENTS = 8
const PARENTS_WITH_CHILDREN = 6
const CHILDREN = 80

async function discover($: EngineInterface): Promise<Where> {
  trace = { bases: [], scanned: 0, checked: 0, errors: [], remembered: null }
  const bases: string[] = []
  for (const [name, read] of [['root', () => $.session.root()], ['cwd', () => $.session.cwd()]] as const) {
    try {
      const base = await read()
      if (base && !bases.includes(base)) bases.push(base)
    } catch (error) {
      note(error, name)
    }
  }
  trace.bases = [...bases]
  let remembered: string | null = null
  try {
    const value = await $.store.get('lastProject')
    remembered = typeof value === 'string' && value ? value : null
  } catch (error) {
    note(error, 'store')
  }
  trace.remembered = remembered
  const near: string[] = remembered ? [remembered] : []
  const scan: string[] = []
  for (const base of bases) {
    let dir: string | null = base
    for (let i = 0; dir && i < PARENTS; i += 1) {
      if (!near.includes(dir)) near.push(dir)
      if (i < PARENTS_WITH_CHILDREN && !scan.includes(dir)) scan.push(dir)
      dir = parentPath(dir)
    }
  }
  const children: string[] = []
  for (const dir of scan) {
    try {
      trace.scanned += 1
      for (const entry of (await $.fs.list(dir)).slice(0, 400)) {
        if (entry.kind !== 'dir' || entry.name.startsWith('.')) continue
        const child = joinPath(dir, entry.name)
        if (!near.includes(child) && !children.includes(child)) children.push(child)
        if (children.length >= CHILDREN * scan.length) break
      }
    } catch (error) {
      note(error, `list ${dir}`)
    }
  }
  const candidates = [...near, ...children]
  trace.checked = candidates.length

  let project: string | null = options.project.trim() || null
  if (!project) {
    let newest = -1
    for (const candidate of candidates) {
      const mtime = await stat(joinPath(candidate, '.oaw', 'catalog', 'view.json'), $)
      if (mtime !== null && mtime > newest) {
        newest = mtime
        project = candidate
      }
    }
  }
  // A project that has OAW but no catalog yet: still the project (the pane offers the entry).
  for (const marker of [['.oaw', 'catalog'], ['.oaw']]) {
    if (project) break
    for (const candidate of candidates) {
      if (await $.fs.exists(joinPath(candidate, ...marker))) {
        project = candidate
        break
      }
    }
  }

  let oaw: string | null = options.oawCheckout.trim() || null
  if (!oaw) {
    let newest = -1
    for (const candidate of [...(project ? [project] : []), ...candidates]) {
      const core = await stat(joinPath(candidate, 'scripts', 'catalog_core.py'), $)
      if (core !== null && core > newest && (await $.fs.exists(joinPath(candidate, 'scripts', 'catalog.py')))) {
        newest = core
        oaw = candidate
      }
    }
  }
  if (project) {
    try {
      await $.store.set('lastProject', project)
    } catch (error) {
      note(error, 'store')
    }
  }
  return { project, oaw }
}

function searchedText(): string {
  const errors = trace.errors.length > 0 ? ` 讀取錯誤：${trace.errors.join('；')}` : ''
  return `（找過：${trace.bases.join('、') || '沒有拿到 session 資料夾'}，往上 ${PARENTS} 層，掃了 ${trace.scanned} 個資料夾的子資料夾，共 ${trace.checked} 個位置。${errors}）`
}

function runner(model: DigestModel | null): Runner | null {
  const project = model?.project ?? where?.project
  const oaw = model?.oaw ?? where?.oaw
  return project && oaw ? { python: pythonArgv(options.python), oaw, project } : null
}

function statusLine(model: DigestModel): string | undefined {
  const live = liveText(model)
  if (model.live?.isRunning && live) return `🍽 ${live}`
  const waiting = waitingCount(model)
  return waiting > 0 ? `🍽 OAW 消化道 · ${waiting} 樣等你` : undefined
}

async function load($: EngineInterface, why: 'start' | 'poll' | 'manual'): Promise<void> {
  if (loading) return
  loading = true
  try {
    if (!where || why !== 'poll') where = await discover($)
    if (!where.project) {
      const problem: DigestProblem = {
        kind: 'no-project',
        text: `這裡找不到 OAW 專案（.oaw/）。在 OAW 專案或它的上層資料夾開 Claude Code，或在 mod 設定填 project。${searchedText()}`,
        project: null,
        oaw: where.oaw,
      }
      await update($, problemAtom, () => problem)
      await update($, modelAtom, () => null)
      $.ui.status(undefined)
      return
    }
    const catalogDir = joinPath(where.project, '.oaw', 'catalog')
    const viewPath = joinPath(catalogDir, 'view.json')
    const statusPath = joinPath(catalogDir, 'status.json')
    const viewTime = await stat(viewPath, $)
    const statusTime = await stat(statusPath, $)
    const stamp = `${where.project}|${viewTime}|${statusTime}`
    const current = await read($, modelAtom)
    if (why === 'poll' && stamp === lastStamp && !current?.live?.isRunning) return
    lastStamp = stamp

    const viewText = viewTime === null ? null : await readText($, viewPath)
    if (viewText === null) {
      const problem: DigestProblem = {
        kind: 'no-view',
        text: '這個專案還沒有消化紀錄：在下面貼 GitHub repo 或 arXiv 網址送去試吃，或按「重算」。',
        project: where.project,
        oaw: where.oaw,
      }
      await update($, problemAtom, () => problem)
      await update($, modelAtom, () => null)
      $.ui.status(undefined)
      return
    }
    let isViewStale = false
    for (const name of VIEW_SOURCES) {
      const source = await stat(joinPath(catalogDir, name), $)
      if (source !== null && viewTime !== null && source > viewTime + 1000) isViewStale = true
    }
    const statusText = statusTime === null ? null : await readText($, statusPath)
    const parsed = parseView(viewText, { project: where.project, oaw: where.oaw }, statusText, isViewStale, await $.clock.now())
    if ('problem' in parsed) {
      const problem: DigestProblem = { kind: 'bad-view', text: parsed.problem, project: where.project, oaw: where.oaw }
      await update($, problemAtom, () => problem)
      await update($, modelAtom, () => null)
      return
    }
    const model = parsed.model
    await update($, problemAtom, () => null)
    await update($, modelAtom, () => model)

    // A taste that was running and no longer is: say how it ended.
    const live = model.live
    if (lastLive?.isRunning && live && live.food === lastLive.food && !live.isRunning) {
      const food = model.foods.find(f => f.id === live.food)
      const name = food?.display ?? live.food
      $.ui.toast(live.stopReason ? `試吃停止：${name}：${live.stopReason}` : `試吃完成：${name} · ${food ? verdictText(food) : live.headline ?? ''}`)
    }
    lastLive = live ? { food: live.food, isRunning: live.isRunning } : null
    $.ui.status(statusLine(model))
  } finally {
    loading = false
  }
}

async function runCommand(
  $: EngineInterface,
  label: string,
  argv: string[],
  cwd: string,
): Promise<{ ok: boolean; code: number; out: string }> {
  await update($, busyAtom, () => label)
  await update($, messageAtom, () => ({ kind: 'info' as const, text: `${label}…` }))
  try {
    const result = await $.process.run(argv, { cwd, timeoutMs: LONG_MS })
    const out = [result.stdout, result.stderr].filter(Boolean).join('\n').replace(/\r/g, '').trim()
    return { ok: result.exitCode === 0, code: result.exitCode, out: out.length > 4000 ? out.slice(0, 4000) + '\n…' : out }
  } catch (error) {
    return { ok: false, code: -1, out: error instanceof Error ? error.message : String(error) }
  } finally {
    await update($, busyAtom, () => null)
  }
}

function outcome(label: string, result: { ok: boolean; code: number; out: string }): { kind: 'ok' | 'error' | 'info'; text: string } {
  const tail = result.out.split('\n').slice(-6).join('\n')
  if (result.ok) return { kind: 'ok', text: `${label}：完成${tail ? '\n' + tail : ''}` }
  if (result.code === 3) return { kind: 'info', text: `${label}：需要你在自己的終端輸入確認碼（catalog.py menu）。\n${tail}` }
  return { kind: 'error', text: `${label}：失敗（結束碼 ${result.code}）${tail ? '\n' + tail : ''}` }
}

async function startAction($: EngineInterface, model: DigestModel, food: DigestFood, action: DigestAction): Promise<void> {
  const run = runner(model)
  if (!run) {
    await update($, messageAtom, () => ({ kind: 'error' as const, text: '找不到 OAW checkout（scripts/catalog.py）：在 mod 設定填 oawCheckout。' }))
    return
  }
  if (await read($, busyAtom)) return
  const components = action.endpoint === 'absorb' ? await read($, picksAtom) : []
  const argv = actionArgv(run, action, food, { apply: false, components })
  if (!argv) {
    await update($, messageAtom, () => ({ kind: 'info' as const, text: '先在上面勾選要吸收的成分。' }))
    return
  }
  const label = `${food.display} · ${action.label}`
  const result = await runCommand($, label, argv, run.oaw)
  if (PREVIEWED.has(action.endpoint) && result.ok) {
    const pending: DigestPending = {
      food: food.id,
      action: action.id,
      label,
      components,
      preview: result.out || '（預覽沒有輸出）',
      needsReason: NEEDS_REASON.has(action.endpoint),
    }
    await update($, pendingAtom, () => pending)
    await update($, messageAtom, () => ({ kind: 'info' as const, text: `${label}：這是預覽，還沒有改任何東西。` }))
    return
  }
  await update($, messageAtom, () => outcome(label, result))
  if (action.endpoint === 'taste' && result.ok) $.ui.toast(`試吃結束：${food.display}`)
  await load($, 'manual')
}

async function confirmPending($: EngineInterface, reason: string): Promise<void> {
  const pending = await read($, pendingAtom)
  const model = await read($, modelAtom)
  const run = runner(model)
  if (!pending || !model || !run) return
  const food = model.foods.find(f => f.id === pending.food)
  const action = food?.actions.find(a => a.id === pending.action)
  if (!food || !action) {
    await update($, pendingAtom, () => null)
    await update($, messageAtom, () => ({ kind: 'error' as const, text: '這個動作已經不在這一站了：畫面已更新，請重新選。' }))
    return
  }
  if (pending.needsReason && !reason.trim()) {
    await update($, messageAtom, () => ({ kind: 'info' as const, text: '這個動作要寫原因。' }))
    return
  }
  const argv = actionArgv(run, action, food, { apply: true, reason: reason || `由 ${TITLE} mod 套用`, components: pending.components })
  if (!argv) return
  await update($, pendingAtom, () => null)
  const result = await runCommand($, `${pending.label}（套用）`, argv, run.oaw)
  await update($, messageAtom, () => outcome(`${pending.label}（套用）`, result))
  await update($, picksAtom, () => [])
  await load($, 'manual')
}

async function addFoods($: EngineInterface, value: string): Promise<void> {
  const urls = value.split(/\s+/).map(url => url.trim()).filter(Boolean).slice(0, 20)
  const model = await read($, modelAtom)
  const run = runner(model)
  if (urls.length === 0) return
  if (!run) {
    await update($, messageAtom, () => ({ kind: 'error' as const, text: '找不到 OAW 專案或 OAW checkout：在 mod 設定填 project 和 oawCheckout。' }))
    return
  }
  if (await read($, busyAtom)) return
  const argv = addArgv(run, urls)
  const label = `送去試吃 ${urls.length} 樣`
  const result = await runCommand($, label, argv, run.oaw)
  await update($, messageAtom, () => outcome(label, result))
  await load($, 'manual')
}

async function recompute($: EngineInterface): Promise<void> {
  const model = await read($, modelAtom)
  const problem = await read($, problemAtom)
  const project = model?.project ?? problem?.project ?? where?.project
  const oaw = model?.oaw ?? problem?.oaw ?? where?.oaw
  if (!project || !oaw) {
    await load($, 'manual')
    return
  }
  const result = await runCommand($, '重算 view.json', viewArgv({ python: pythonArgv(options.python), oaw, project }), oaw)
  await update($, messageAtom, () => outcome('重算 view.json', result))
  await load($, 'manual')
}

export const register: Register = (on, opts) => {
  const raw = (opts ?? {}) as Record<string, unknown>
  options = {
    project: typeof raw.project === 'string' ? raw.project : '',
    oawCheckout: typeof raw.oawCheckout === 'string' ? raw.oawCheckout : '',
    python: typeof raw.python === 'string' && raw.python.trim() ? raw.python : 'python3',
    motion: raw.motion !== false,
  }

  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({ name: 'oaw-digest', description: '打開 OAW 消化道：每樣 skill 食物在哪一站、卡在哪、能做什麼' })
    await $.tool.register({
      name: 'status',
      description:
        'OAW digestive tract (oaw-digest-monitor): which OAW project and checkout the pane found, how it searched, and each food\'s stop, state, verdict and who it waits on. Read-only.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    })
    await load($, 'start')
    const model = await read($, modelAtom)
    if (model) {
      void $.ui.open({ id: PANE, title: TITLE })
      $.ui.toast(`${TITLE}：${model.projectName} 有 ${model.foods.length} 樣食物，${waitingCount(model)} 樣等你（/oaw-digest 打開）`)
    }
    $.clock.every(POLL_MS, () => {
      void load($, 'poll')
    })
    return started
  })

  on('tool.call', { tool: 'mcp__oaw-digest-monitor__status' }, async $ => {
    await load($, 'manual')
    const model = await read($, modelAtom)
    const problem = await read($, problemAtom)
    // A tool's result reaches the model as text.
    return {
      result: JSON.stringify({
        project: model?.project ?? problem?.project ?? null,
        oawCheckout: model?.oaw ?? problem?.oaw ?? null,
        problem: problem?.text ?? null,
        search: trace,
        live: model?.live ?? null,
        foods: (model?.foods ?? []).map(f => ({
          id: f.id, stop: f.stageLabel, state: f.stateZh, verdict: verdictText(f), waiting: f.waitingZh,
          components: f.counts, actions: f.actions.map(a => a.label),
        })),
      }, null, 1),
    }
  })

  on('command.run', { command: 'oaw-digest' }, async $ => {
    await load($, 'manual')
    await $.ui.open({ id: PANE, title: TITLE })
    const model = await read($, modelAtom)
    const problem = await read($, problemAtom)
    if (problem) return { text: `${TITLE}：${problem.text}` }
    return { text: `${TITLE}已打開：${model?.foods.length ?? 0} 樣食物，${model ? waitingCount(model) : 0} 樣等你。` }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const model = await read($, modelAtom)
    const problem = await read($, problemAtom)
    const selected = await read($, selectedAtom)
    const picks = await read($, picksAtom)
    const pending = await read($, pendingAtom)
    const busy = await read($, busyAtom)
    const message = await read($, messageAtom)
    const columns = e.props.bodyColumns
    const food = model?.foods.find(f => f.id === selected) ?? null

    let entry = null
    if (e.surface === 'terminal' || e.surface === 'desktop' || e.surface === 'vscode') {
      const { Input } = $.ui.resolve(e)
      entry = (
        <Input
          key="add"
          label="你點名"
          placeholder="GitHub repo 或 arXiv 網址，可以一次多個（空白隔開）"
          submitLabel="送去試吃"
          onSubmit={(value: string) => void addFoods($, value)}
        />
      )
    }

    let tract = null
    if (model && e.surface === 'terminal') {
      tract = (
        <Box flexDirection="column">
          {tractLines(model, selected, 0).map(line => (
            <Text wrap="truncate-end">{line}</Text>
          ))}
        </Box>
      )
    } else if (model && (e.surface === 'desktop' || e.surface === 'vscode' || e.surface === 'mobile')) {
      const { Svg } = $.ui.resolve(e)
      tract = (
        <Svg
          source={tractSvg(model, selected, options.motion)}
          alt={tractAlt(model)}
          isInteractive={true}
          width={Math.min(360, Math.max(220, columns * 8))}
        />
      )
    }

    let reasonField = null
    if (e.surface === 'terminal' || e.surface === 'desktop' || e.surface === 'vscode') {
      const { Input } = $.ui.resolve(e)
      reasonField = (
        <Input
          key="reason"
          label="原因（必填）"
          placeholder="為什麼要這樣做"
          submitLabel="確認套用"
          onSubmit={(value: string) => void confirmPending($, value)}
        />
      )
    } else {
      reasonField = <Text dimColor>這個動作要寫原因：請在桌面或終端操作。</Text>
    }

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="column">
          <Text bold>
            {TITLE}
            {model ? <Text dimColor> · {model.projectName}</Text> : null}
          </Text>
          {model && (
            <Text dimColor>
              送進 {model.funnel.submitted} · 試吃過 {model.funnel.tasted} · 實測 {model.funnel.measured} · 已吸收成分 {model.funnel.absorbedParts}
            </Text>
          )}
          {model && liveText(model) && <Text color={model.live?.isRunning ? 'claude' : 'warning'}>{liveText(model)}</Text>}
          {model?.isViewStale && <Text color="warning">紀錄比畫面新：畫面可能過期，按「重算」。</Text>}
          {problem && <Text color={problem.kind === 'bad-view' ? 'error' : 'warning'}>{problem.text}</Text>}
          {model && !model.oaw && <Text dimColor>沒找到 OAW checkout，按鈕會停用：在 mod 設定填 oawCheckout。</Text>}
        </Box>

        {tract}
        {model && (
          <Text dimColor wrap="wrap">
            {model.legend.map(key => `${model.symbols[key] ?? ''} ${model.statesZh[key] ?? key}`).join('  ')}　! 等你　? 可選
          </Text>
        )}

        {model && model.foods.length === 0 && <Text dimColor>還沒有食物：在下面貼網址送去試吃。</Text>}
        {model && model.foods.length > 0 && (
          <Box flexDirection="column">
            {model.foods.map(f => (
              <Button
                key={`food:${f.id}`}
                plain
                onPress={() => {
                  void update($, selectedAtom, current => (current === f.id ? null : f.id))
                  void update($, picksAtom, () => [])
                  void update($, pendingAtom, () => null)
                }}
              >
                {f.id === selected ? '▸ ' : '  '}
                {f.verdict.symbol || '•'} {f.display}
                <Text dimColor>
                  {' '}
                  · {f.stageLabel} {model.symbols[f.state] ?? ''} {f.waiting === 'owner' ? '· 等你' : f.waiting === 'optional' ? '· 可選' : ''}
                  {model.live?.isRunning && model.live.food === f.id ? ' · 試吃中' : ''}
                </Text>
              </Button>
            ))}
          </Box>
        )}

        {model && food && (
          <Box flexDirection="column" gap={1} borderStyle="round" paddingX={1}>
            <Box flexDirection="column">
              <Text bold>
                {food.display} <Text dimColor>（{food.kind === 'paper' ? '論文' : 'repo'}）</Text>
              </Text>
              <Text dimColor wrap="wrap">{food.source}</Text>
              <Text>判定：{verdictText(food)}</Text>
              <Text wrap="wrap">
                第 {Math.max(1, stageIndex(model, food.stage) + 1)}/{model.stages.length} 站：{stageChain(model, food)}
              </Text>
              <Text>
                成分：<Text color="success">吸收 {food.counts.absorb}</Text> · <Text color="warning">暫留 {food.counts.hold}</Text> ·{' '}
                <Text color="error">排掉 {food.counts.excrete}</Text>
              </Text>
              {food.note && <Text wrap="wrap">{food.note}</Text>}
            </Box>

            <Box flexDirection="column">
              <Text bold>卡點說明</Text>
              <Text wrap="wrap">卡在哪：{food.blocker.where || '紀錄裡沒有寫'}</Text>
              <Text wrap="wrap">依據：{food.blocker.basis.join('；') || '紀錄裡沒有寫'}</Text>
              <Text wrap="wrap">你不處理會怎樣：{food.blocker.ifIgnored || '紀錄裡沒有寫'}</Text>
              {food.blocker.unknown.length > 0 && <Text dimColor wrap="wrap">紀錄沒寫的：{food.blocker.unknown.join('；')}</Text>}
            </Box>

            {food.actions.some(a => a.endpoint === 'absorb') && (
              <Box flexDirection="column">
                <Text bold>選要吸收的成分</Text>
                {food.components.filter(c => c.canAbsorb).length === 0 && <Text dimColor>沒有可以吸收的成分。</Text>}
                {food.components
                  .filter(c => c.canAbsorb)
                  .map(c => (
                    <Button
                      key={`pick:${c.id}`}
                      plain
                      onPress={() =>
                        void update($, picksAtom, list => (list.includes(c.id) ? list.filter(id => id !== c.id) : [...list, c.id]))
                      }
                    >
                      {picks.includes(c.id) ? '☑ ' : '☐ '}
                      {c.name}
                    </Button>
                  ))}
              </Box>
            )}

            <Box flexDirection="row" flexWrap="wrap" gap={1}>
              {food.actions.map(action =>
                action.where === 'terminal' ? (
                  <Button
                    key={`act:${action.id}`}
                    onPress={() => {
                      const command = terminalCommand(runner(model), action, food)
                      void $.ui.copy({ text: command })
                      void update($, messageAtom, () => ({
                        kind: 'info' as const,
                        text: `「${action.label}」要你在自己的終端輸入確認碼，指令已複製：\n${command}`,
                      }))
                    }}
                  >
                    {action.label}（複製終端指令）
                  </Button>
                ) : (
                  <Button
                    key={`act:${action.id}`}
                    variant={action.endpoint === 'taste' ? 'primary' : undefined}
                    onPress={() => void startAction($, model, food, action)}
                  >
                    {busy ? `${action.label}（等前一個做完）` : action.label}
                  </Button>
                ),
              )}
              <Button
                key="ask"
                onPress={() => {
                  void $.prompt.fill({ text: askBrief(model, food), mode: 'replace' })
                  $.ui.toast('卡點資料已放進輸入框：在最後打上你的問題再送出')
                }}
              >
                問 Claude 這個卡點
              </Button>
            </Box>

            {pending && pending.food === food.id && (
              <Box flexDirection="column" gap={1}>
                <Text bold>預覽：{pending.label}</Text>
                <Text dimColor wrap="wrap">
                  {pending.preview}
                </Text>
                {pending.needsReason ? (
                  reasonField
                ) : (
                  <Box flexDirection="row" gap={1}>
                    <Button key="confirm" variant="primary" onPress={() => void confirmPending($, '')}>
                      確認套用
                    </Button>
                    <Button key="cancel" onPress={() => void update($, pendingAtom, () => null)}>
                      取消
                    </Button>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        )}

        {message && (
          <Text color={message.kind === 'error' ? 'error' : message.kind === 'ok' ? 'success' : undefined} wrap="wrap">
            {busy ? '⏳ ' : ''}
            {message.text}
          </Text>
        )}

        {entry}

        <Box flexDirection="row" gap={1}>
          <Button key="refresh" onPress={() => void load($, 'manual')}>
            重新整理
          </Button>
          <Button key="recompute" onPress={() => void recompute($)}>
            重算
          </Button>
          {model && (
            <Text dimColor>
              {baseName(model.project)} · {new Date(model.loadedAt).toLocaleTimeString()}
            </Text>
          )}
        </Box>
      </Box>
    )
  })
}
