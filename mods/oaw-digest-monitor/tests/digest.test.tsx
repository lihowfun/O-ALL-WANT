import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

import { VIEW } from './fixtures'

const NOW = Date.parse('2026-11-05T08:00:00Z')
const CWD = '/work'
const PROJECT = '/work/demo'
const CATALOG = '/work/demo/.oaw/catalog'
const OAW = '/work/oaw'

const PANE = {
  plugin: 'oaw-digest-monitor',
  component: 'Pane',
  requestId: 'oaw-digest',
  props: {
    title: 'OAW 消化道',
    isFocused: false,
    bodyColumns: 48,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 60 },
    view: {},
  },
} as const

type File = { text: string; mtime: number }
type World = {
  files: Map<string, File>
  dirs: Set<string>
  runs: string[][]
  toasts: string[]
  statuses: (string | undefined)[]
  copies: string[]
  fills: string[]
  clock: { advance: (ms: number) => Promise<void> }
  answer: { exitCode: number; stdout: string; stderr: string; isStdoutTruncated: boolean; isStderrTruncated: boolean }
}

function status(fields: Record<string, unknown>): string {
  return JSON.stringify({
    schema_version: 1, skill: 'graphify', food: 'graphify', source: 'graphify@59b5ab1', stage: 'static',
    stages: ['ingest', 'quarantine', 'static', 'verdict'], progress: { done: 2, total: 3 }, arms: [], host: null,
    verdict_so_far: 'pending', updated_at: new Date(NOW).toISOString(), tier: 'T0', headline: null, stop_reason: null,
    ...fields,
  })
}

// The engine beneath the plugin: a small file tree, a process runner that records
// what it was asked to run, and the display calls the pane makes.
function world(on: On, options: { view?: string | null; status?: string | null; project?: boolean; cwd?: string; root?: string } = {}): World {
  const clock = mock.clock(on, { now: NOW })
  mock.store(on)
  const w: World = {
    files: new Map(),
    dirs: new Set([CWD, '/', OAW, `${OAW}/scripts`]),
    runs: [],
    toasts: [],
    statuses: [],
    copies: [],
    fills: [],
    clock,
    answer: { exitCode: 0, stdout: 'preview only: re-run with --apply', stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
  }
  w.files.set(`${OAW}/scripts/catalog.py`, { text: '', mtime: NOW - 5000 })
  w.files.set(`${OAW}/scripts/catalog_core.py`, { text: '', mtime: NOW - 5000 })
  if (options.project !== false) {
    for (const dir of [PROJECT, `${PROJECT}/.oaw`, CATALOG]) w.dirs.add(dir)
    const view = options.view === undefined ? JSON.stringify(VIEW) : options.view
    if (view !== null) w.files.set(`${CATALOG}/view.json`, { text: view, mtime: NOW - 1000 })
    w.files.set(`${CATALOG}/registry.json`, { text: '{}', mtime: NOW - 2000 })
    if (options.status) w.files.set(`${CATALOG}/status.json`, { text: options.status, mtime: NOW - 500 })
  }
  const missing = (path: string) => ({ deny: `ENOENT: ${path}` })

  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.cwd', () => ({ value: options.cwd ?? CWD }))
  on('session.root', () => ({ value: options.root ?? options.cwd ?? CWD }))
  for (let dir = options.cwd ?? CWD; dir.length > 1; dir = dir.slice(0, dir.lastIndexOf('/')) || '/') w.dirs.add(dir)
  on('command.register', () => ({ value: { command: 'oaw-digest' } }))
  on('tool.register', () => ({ value: { tool: 'mcp__oaw-digest-monitor__status' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.toast', (_, e) => {
    w.toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.status', (_, e) => {
    w.statuses.push(e.text)
    return { value: undefined }
  })
  on('ui.copy', (_, e) => {
    w.copies.push(e.text)
    return { value: { isCopied: true } }
  })
  on('prompt.fill', (_, e) => {
    w.fills.push(e.text)
    return { isFilled: true }
  })
  on('fs.exists', (_, e) => ({ value: w.dirs.has(e.path) || w.files.has(e.path) }))
  on('fs.stat', (_, e) => {
    const file = w.files.get(e.path)
    if (file) return { value: { kind: 'file', size: file.text.length, mtimeMs: file.mtime, isLink: false } }
    if (w.dirs.has(e.path)) return { value: { kind: 'dir', size: 0, mtimeMs: 0, isLink: false } }
    return missing(e.path)
  })
  on('fs.read', (_, e) => {
    const file = w.files.get(e.path)
    if (!file) return missing(e.path)
    return { value: file.text }
  })
  on('fs.list', (_, e) => {
    const prefix = e.path === '/' ? '/' : `${e.path}/`
    const names = new Set<string>()
    for (const dir of w.dirs) if (dir.startsWith(prefix) && dir !== e.path) names.add(dir.slice(prefix.length).split('/')[0] ?? '')
    return { value: [...names].filter(Boolean).map(name => ({ name, kind: 'dir' as const, size: 0, mtimeMs: 0, isLink: false })) }
  })
  on('process.run', (_, e) => {
    w.runs.push([...e.argv])
    return { value: { ...w.answer } }
  })
  return w
}

async function start($: Engine, surface: 'desktop' | 'terminal' = 'desktop') {
  await $.session.start({ cwd: CWD, surface, isInteractive: true })
}

test('finds the project and the OAW checkout, and draws every food on the tract', async ($, on) => {
  const w = world(on)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const svg = await ui.find({ type: 'Svg' })
  const source = String(svg?.props.source ?? '')
  for (const name of ['Graphify-Labs/graphify', 'microsoft/TokenEconomizer', 'thedotmack/claude-mem', 'arXiv:2606.03979', 'alexyc9381/court-skill', 'sweet-notes']) expect(source).toContain(name)
  expect(source).toContain('入口')
  expect(String(svg?.props.alt ?? '')).toContain('靜態：microsoft/TokenEconomizer')
  expect(String(svg?.props.alt ?? '')).toContain('分流：alexyc9381/court-skill、Graphify-Labs/graphify')
  expect(await ui.find({ type: 'Text', text: /送進 5/ })).toBeDefined()
  // D28: nothing in this ledger waits on the owner; the paper waits for the one release of the branch.
  expect(w.statuses.at(-1)).toBe('🍽 OAW 消化道 · 1 樣等發布')
  expect(await ui.find({ type: 'Text', text: /^等發布：1 個單位在 claude\/oaw-2（1 樣食物），合併 PR 時一次決定$/ })).toBeDefined()
  await ui.unmount()

  const term = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await term.find({ type: 'Text', text: /胃.*靜態.*▲tokeneconomizer»/ })).toBeDefined()
  expect(await term.find({ type: 'Text', text: /全身.*版本.*○arxiv-2606-03979↑/ })).toBeDefined()
  expect(await term.find({ type: 'Text', text: /大腸.*分流.*court-skill.*graphify/ })).toBeDefined()
  await term.unmount()
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`a selected food explains its blocker; a terminal-only action copies the command (${surface})`, async ($, on) => {
    const w = world(on)
    await start($, surface)
    const ui = await $.ui.mount({ ...PANE, surface })
    await ui.press({ key: 'food:tokeneconomizer' })
    expect(await ui.find({ type: 'Text', text: /^卡在哪：靜態：23 個高嚴重度旗標（只供參考）；下一步：Claude 在試吃區試吃/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^依據：/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^你不處理會怎樣：/ })).toBeDefined()
    await ui.press({ key: 'act:triage' })
    expect(w.copies.at(-1)).toContain(`${OAW}/scripts/catalog.py menu --target ${PROJECT}`)
    expect(w.runs.length).toBe(0)
    await ui.press({ key: 'ask' })
    expect(w.fills.at(-1)).toContain('食物：microsoft/TokenEconomizer（tokeneconomizer，repo）')
    expect(w.fills.at(-1)).toContain('自動（Claude 接手）')
    expect(w.fills.at(-1)).toMatch(/問題：$/)
    await ui.unmount()
  })
}

test('a changing action previews first and applies only after confirm', async ($, on) => {
  const w = world(on)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.press({ key: 'food:sweet-notes' })
  await ui.press({ key: 'pick:sn-index' })
  await ui.press({ key: 'act:absorb' })
  expect(w.runs.length).toBe(1)
  expect(w.runs[0]).toEqual(['python3', `${OAW}/scripts/catalog.py`, 'absorb', 'sweet-notes', '--components', 'sn-index', '--target', PROJECT])
  expect(await ui.find({ type: 'Text', text: /preview only/ })).toBeDefined()
  await ui.press({ key: 'confirm' })
  expect(w.runs.length).toBe(2)
  expect(w.runs[1]).toContain('--apply')
  expect(w.runs[1]).toContain('--components')
  await ui.unmount()
})

test('removing needs a reason before it applies', async ($, on) => {
  const view = JSON.parse(JSON.stringify(VIEW)) as { foods: { id: string; pipeline: { actions: unknown[] } }[] }
  const sweet = view.foods.find(f => f.id === 'sweet-notes')
  if (sweet) {
    sweet.pipeline.actions = [{ id: 'remove-food', stage: 'build', endpoint: 'remove', where: 'both', label_zh: '移除', params: { name: 'sweet-notes', food: true } }]
  }
  const w = world(on, { view: JSON.stringify(view) })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.press({ key: 'food:sweet-notes' })
  await ui.press({ key: 'act:remove-food' })
  expect(w.runs[0]).toEqual(['python3', `${OAW}/scripts/catalog.py`, 'remove', 'sweet-notes', '--food', '--target', PROJECT])
  await ui.input({ key: 'reason', text: '' })
  expect(w.runs.length).toBe(1)
  await ui.input({ key: 'reason', text: 'not needed' })
  expect(w.runs[1]).toEqual(['python3', `${OAW}/scripts/catalog.py`, 'remove', 'sweet-notes', '--food', '--reason', 'not needed', '--apply', '--target', PROJECT])
  await ui.unmount()
})

test('a running taste moves on the tract, and its end raises a toast', async ($, on) => {
  const w = world(on, { status: status({}) })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const source = String((await ui.find({ type: 'Svg' }))?.props.source ?? '')
  expect(source).toContain('class="wave"')
  expect(source).toContain('class="live"')
  expect(w.statuses.at(-1)).toBe('🍽 試吃中：Graphify-Labs/graphify · 靜態')

  w.files.set(`${CATALOG}/status.json`, { text: status({ stage: 'done', headline: 'risky' }), mtime: NOW + 1500 })
  await w.clock.advance(2000)
  expect(w.toasts.at(-1)).toMatch(/^試吃完成：Graphify-Labs\/graphify · ▲ 有疑慮/)
  const after = String((await ui.find({ type: 'Svg' }))?.props.source ?? '')
  expect(after).not.toContain('class="live"')
  await ui.unmount()
})

test('a stopped taste says why', async ($, on) => {
  world(on, { status: status({ stage: 'quarantine', food: 'claude-mem', stop_reason: 'Refused: snapshot exceeds the 50 MB limit.' }) })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /上次試吃停止：thedotmack\/claude-mem · Refused: snapshot exceeds/ })).toBeDefined()
  await ui.unmount()
})

test('a status not touched for ten minutes is shown as possibly interrupted', async ($, on) => {
  world(on, { status: status({ updated_at: new Date(NOW - 11 * 60_000).toISOString() }) })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /可能中斷了/ })).toBeDefined()
  expect(String((await ui.find({ type: 'Svg' }))?.props.source ?? '')).not.toContain('class="wave"')
  await ui.unmount()
})

test('a session that moved into a nested folder still finds a sibling project', async ($, on) => {
  const w = world(on, { cwd: '/work/records/digestion/ingest/graphify', root: '/work/records/digestion/ingest/graphify' })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /送進 5/ })).toBeDefined()
  expect(w.toasts.at(-1)).toMatch(/^OAW 消化道：demo 有 6 樣食物，0 樣等你/)
  await ui.unmount()
})

test('no OAW project is explained', async ($, on) => {
  world(on, { project: false })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /找不到 OAW 專案.*找過：\/work，往上 8 層/ })).toBeDefined()
  await ui.unmount()
})

test('the status tool tells the model what the pane found', async ($, on) => {
  world(on)
  await start($)
  const answer = await $.tool.call({ tool: 'mcp__oaw-digest-monitor__status' })
  const result = (answer as { result?: unknown }).result
  expect(typeof result).toBe('string')
  const status = JSON.parse(String(result)) as { project: string; oawCheckout: string; foods: { id: string }[] }
  expect(status.project).toBe('/work/demo')
  expect(status.oawCheckout).toBe('/work/oaw')
  expect(status.foods.map(f => f.id)).toContain('graphify')
})

test('a project with no view yet is explained', async ($, on) => {
  world(on, { view: null })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /還沒有消化紀錄/ })).toBeDefined()
  await ui.unmount()
})

test('a view of another schema is explained', async ($, on) => {
  world(on, { view: JSON.stringify({ schema: 'oaw-catalog-view/1', foods: [] }) })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /格式是 oaw-catalog-view\/1/ })).toBeDefined()
  await ui.unmount()
})

test('motion off draws the same tract without animation', { options: { motion: false } }, async ($, on) => {
  world(on, { status: status({}) })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const source = String((await ui.find({ type: 'Svg' }))?.props.source ?? '')
  expect(source).toContain('class="wave"')
  expect(source).not.toContain('animation')
  await ui.unmount()
})

test('pasting a link sends it to be tasted', async ($, on) => {
  const w = world(on)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  await ui.input({ key: 'add', text: 'https://github.com/example/a  arXiv:2606.03979' })
  expect(w.runs[0]).toEqual(['python3', `${OAW}/scripts/catalog.py`, 'add', 'https://github.com/example/a', 'arXiv:2606.03979', '--target', PROJECT])
  await ui.unmount()
})

test('agent and release are drawn apart from the owner, and a tasting or absorption shows at its stop', async ($, on) => {
  const view = JSON.parse(JSON.stringify(VIEW)) as { foods: { id: string; pipeline: { waiting_on: string; waiting_zh: string } }[] }
  // One food that only the owner can move, to see the three badges side by side.
  const mem = view.foods.find(f => f.id === 'claude-mem')
  if (mem) {
    mem.pipeline.waiting_on = 'owner'
    mem.pipeline.waiting_zh = '等你'
  }
  const w = world(on, { view: JSON.stringify(view) })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const source = String((await ui.find({ type: 'Svg' }))?.props.source ?? '')
  expect(source).toContain('class="w-owner"')
  expect(source).toContain('fill="#3b7ddd"/><text class="badge" x="')
  expect(source).toMatch(/class="w-agent"[^>]*fill="#c96a3a"\/><text class="badge"[^>]*>»</)
  expect(source).toMatch(/class="w-release"[^>]*fill="#1f9488"\/><text class="badge"[^>]*>↑</)
  expect(w.statuses.at(-1)).toBe('🍽 OAW 消化道 · 1 樣等你 · 1 樣等發布')
  expect(await ui.find({ type: 'Text', text: /! 等你　» Claude 接手　↑ 等發布（合併 PR 時一次決定）　\? 可選/ })).toBeDefined()

  await ui.press({ key: 'food:arxiv-2606-03979' })
  expect(await ui.find({ type: 'Text', text: /^卡在哪：版本：1 個單位已在 claude\/oaw-2 重建，等發布（合併 PR 時一次決定）/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^核准：D21 吸收：1 個單位（sl\.wake-sleep-cycle\/manual-pass A 級）/ })).toBeDefined()
  await ui.press({ key: 'food:graphify' })
  expect(await ui.find({ type: 'Text', text: /^分流：試吃判定：沒證明比原生好（不收）/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^實測：試吃 2026-11-05：N 4 次（評分 4）、G 4 次（評分 4，食物組）/ })).toBeDefined()
  await ui.unmount()

  const answer = await $.tool.call({ tool: 'mcp__oaw-digest-monitor__status' })
  const status = JSON.parse(String((answer as { result?: unknown }).result)) as {
    foods: { id: string; waitingOn: string; tasting: string | null }[]
    release: { text: string; units: number }
  }
  expect(status.foods.find(f => f.id === 'arxiv-2606-03979')?.waitingOn).toBe('release')
  expect(status.foods.find(f => f.id === 'graphify')?.tasting).toBe('沒證明比原生好（不收）（2026-11-05）')
  expect(status.release.units).toBe(1)
})

test('the EGM switch shows the project setting and sets it through oaw_mode.py', async ($, on) => {
  const w = world(on)
  w.files.set(`${PROJECT}/.oaw/settings.json`, { text: JSON.stringify({ review: { egm: 'on' } }), mtime: NOW - 100 })
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: /每個 deep 任務都跑完整 EGM/ })).toBeDefined()
  const before = w.runs.length
  w.answer = { exitCode: 0, stdout: '{"egm": "off"}', stderr: '', isStdoutTruncated: false, isStderrTruncated: false }
  w.files.set(`${PROJECT}/.oaw/settings.json`, { text: JSON.stringify({ review: { egm: 'off' } }), mtime: NOW })
  await ui.press({ key: 'egm:off' })
  expect(w.runs.length).toBe(before + 1)
  expect(w.runs[w.runs.length - 1]).toEqual(['python3', `${OAW}/scripts/oaw_mode.py`, 'egm', 'off', '--root', PROJECT, '--json'])
  expect(w.toasts).toContain('EGM 審查已切到「關」')
  expect(await ui.find({ type: 'Text', text: /不跑 EGM/ })).toBeDefined()
  await ui.unmount()
})

test('without a settings file the EGM switch is the default, auto', async ($, on) => {
  const w = world(on)
  await start($)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /X2 出結果前是一次全新 context 審查（預設）/ })).toBeDefined()
  expect(w.runs.length).toBe(0)
  await ui.unmount()
})

