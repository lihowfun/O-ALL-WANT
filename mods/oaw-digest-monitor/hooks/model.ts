// Pure functions: OAW's view.json and status.json -> the pane's model, and the
// catalog.py argument vectors the pane's buttons run. No `$` here, so the tests
// can feed fixtures straight in.
//
// The display rules are OAW's own (scripts/oaw_status.py, docs/SKILL_INTAKE.md):
// a verdict always carries its symbol and text, every effect names its evidence
// level, a stop the record does not explain says so, and a running taste is
// live state from status.json, never view data.

import type {
  DigestAction,
  DigestComponent,
  DigestFood,
  DigestLive,
  DigestModel,
  DigestStage,
} from '../types'

export const VIEW_SCHEMA = 'oaw-catalog-view/3'
// A status.json not touched for this long while "running" is shown as possibly
// interrupted (oaw_status.py uses the same 10 minutes).
export const STALE_MS = 600_000
// Files build_view() reads; a newer one means view.json may be out of date.
export const VIEW_SOURCES = ['registry.json', 'decisions.jsonl', 'builds.json', 'policy.json', 'scout.json', 'effect.json']

// Who a food waits on (catalog_core.PIPELINE_WAITING_ZH) -> the bolus badge. D28: the agent is the default
// actor, so only `owner` is the blue "!"; `release` is one decision for the whole branch, never per food.
export const WAITING_MARKS: Record<string, { badge: string; color: string; label: string }> = {
  owner: { badge: '!', color: '#3b7ddd', label: '等你' },
  agent: { badge: '»', color: '#c96a3a', label: 'Claude 接手' },
  release: { badge: '↑', color: '#1f9488', label: '等發布' },
  optional: { badge: '?', color: '#8d939b', label: '可選' },
}

export const LEVELS_ZH: Record<string, string> = {
  measured: '實測',
  'static-measured': '靜態量測',
  'not-measured': '未量測',
  'historical-prior': '歷史證據',
}

// Fallback stage table, used only when view.json carries none (never seen with schema /2).
const FALLBACK_STAGES: DigestStage[] = ([
  ['intake', '入口', '口'], ['quarantine', '封存', '食道'], ['static', '靜態', '胃'], ['plan', '計畫', '十二指腸'],
  ['review', '盲審', '肝'], ['test', '實測', '小腸'], ['sort', '分流', '大腸'], ['approve', '核准', '門靜脈'], ['build', '版本', '全身'],
] as const).map(([id, label, organ]) => ({ id, label, organ, automation: 'mixed', automationZh: '部分自動', summary: '' }))

// Bidi controls, zero-width and other control characters never reach the screen.
const UNSAFE = /[\u0000-\u001f\u007f-\u009f؜​-‏‪-‮⁠-⁤⁦-⁩﻿]/g

export function text(value: unknown, max = 400): string {
  if (typeof value !== 'string') return ''
  const clean = value.replace(UNSAFE, ' ').replace(/ {2,}/g, ' ').trim()
  return clean.length > max ? clean.slice(0, max - 1) + '…' : clean
}

const num = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) ? value : 0)
const obj = (value: unknown): Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])

export function baseName(path: string): string {
  const parts = path.replace(/[\\/]+$/, '').split(/[\\/]/)
  return parts[parts.length - 1] || path
}

export function joinPath(dir: string, ...parts: string[]): string {
  const sep = dir.includes('\\') && !dir.includes('/') ? '\\' : '/'
  return [dir.replace(/[\\/]+$/, ''), ...parts].join(sep)
}

export function parentPath(path: string): string | null {
  const trimmed = path.replace(/[\\/]+$/, '')
  const cut = Math.max(trimmed.lastIndexOf('/'), trimmed.lastIndexOf('\\'))
  if (cut <= 0) return cut === 0 && trimmed.length > 1 ? trimmed.slice(0, 1) : null
  const parent = trimmed.slice(0, cut)
  return /^[A-Za-z]:$/.test(parent) ? parent + '\\' : parent
}

function parseParams(value: unknown): Record<string, string | boolean | string[]> {
  const out: Record<string, string | boolean | string[]> = {}
  for (const [key, raw] of Object.entries(obj(value))) {
    if (typeof raw === 'string') out[key] = text(raw, 200)
    else if (typeof raw === 'boolean') out[key] = raw
    else if (Array.isArray(raw)) out[key] = raw.map(item => text(item, 200)).filter(Boolean)
  }
  return out
}

function parseAction(value: unknown): DigestAction {
  const a = obj(value)
  return {
    id: text(a.id, 40),
    endpoint: text(a.endpoint, 40),
    label: text(a.label_zh, 80),
    where: text(a.where, 12) || 'both',
    params: parseParams(a.params),
  }
}

function sourceText(food: Record<string, unknown>): string {
  const pinned = obj(food.pinned)
  if (food.kind === 'paper') {
    const paper = obj(food.paper)
    const arxiv = text(paper.arxiv_id, 40)
    const where = arxiv ? `arXiv:${arxiv}` : '本機 PDF'
    const version = text(pinned.version, 8) || text(paper.version, 8)
    const sha = text(pinned.pdf_sha12, 12)
    return sha ? `${where} ${version} · sha256 ${sha}`.replace(/ {2,}/g, ' ') : `${where} · 還沒封存（未固定版本）`
  }
  const url = text(food.repo, 200) || '本機 repo（路徑不公開）'
  const commit = text(pinned.commit7, 12)
  return commit ? `${url} @ ${commit}` : `${url} · 還沒封存（未固定版本）`
}

export function parseFood(value: unknown): DigestFood | null {
  const f = obj(value)
  const id = text(f.id, 64)
  if (!id) return null
  const p = obj(f.pipeline)
  const v = obj(f.verdict)
  const b = obj(p.blocker)
  const c = obj(f.counts)
  const stages: Record<string, string> = {}
  for (const [key, state] of Object.entries(obj(p.stages))) stages[text(key, 20)] = text(state, 12)
  const stageNotes: Record<string, string> = {}
  for (const [key, note] of Object.entries(obj(p.stage_notes_zh))) {
    const clean = text(note, 400)
    if (clean) stageNotes[text(key, 20)] = clean
  }
  const t = obj(f.tasting)
  const tastingLabel = text(t.verdict_label_zh, 40)
  const components: DigestComponent[] = list(f.components)
    .map(raw => {
      const part = obj(raw)
      return {
        id: text(part.id, 80),
        name: text(part.name, 120) || text(part.id, 80),
        disposition: text(part.disposition, 12),
        canAbsorb: part.can_absorb === true,
      }
    })
    .filter(part => part.id)
    .slice(0, 80)
  return {
    id,
    display: text(f.display, 80) || id,
    kind: f.kind === 'paper' ? 'paper' : 'repo',
    source: sourceText(f),
    stage: text(p.stage, 20),
    stageLabel: text(p.stage_label_zh, 12),
    state: text(p.state, 12),
    stateZh: text(p.state_zh, 12),
    stages,
    waiting: text(p.waiting_on, 12) || 'none',
    waitingZh: text(p.waiting_zh, 40),
    note: text(p.note_zh, 600),
    stageNotes,
    tasting: tastingLabel ? `${tastingLabel}（${text(t.date, 10) || '日期沒寫'}）` : null,
    verdict: {
      headline: text(v.headline, 20),
      symbol: text(v.symbol, 4),
      label: text(v.label_zh, 20) || text(v.label, 20),
      level: text(v.level, 30),
    },
    counts: { absorb: num(c.absorb), hold: num(c.hold), excrete: num(c.excrete) },
    blocker: {
      where: text(b.where_zh, 400),
      basis: list(b.basis_zh).map(item => text(item, 400)).filter(Boolean),
      ifIgnored: text(b.if_ignored_zh, 400),
      unknown: list(b.unknown_zh).map(item => text(item, 400)).filter(Boolean),
    },
    actions: list(p.actions).map(parseAction).filter(action => action.id && action.endpoint),
    components,
  }
}

function parseStages(pipeline: Record<string, unknown>): DigestStage[] {
  const names = obj(pipeline.automation_zh)
  const stages = list(pipeline.stages)
    .map(raw => {
      const s = obj(raw)
      const automation = text(s.automation, 12)
      return {
        id: text(s.id, 20),
        label: text(s.label_zh, 12),
        organ: text(s.organ_zh, 8),
        automation,
        automationZh: text(names[automation], 12),
        summary: text(s.summary_zh, 400),
      }
    })
    .filter(stage => stage.id && stage.label)
  return stages.length > 0 ? stages : FALLBACK_STAGES
}

// status.json -> what is running now. A stage the pipeline does not map is
// still reported (pipelineStage null) so the pane never hides a live taste.
export function parseLive(statusText: string | null, liveStages: Record<string, string>, nowMs: number): DigestLive | null {
  if (!statusText) return null
  let raw: unknown
  try {
    raw = JSON.parse(statusText)
  } catch {
    return null
  }
  const s = obj(raw)
  const food = text(s.food, 64) || text(s.skill, 64)
  const stage = text(s.stage, 20)
  if (!food || !stage) return null
  const updatedAt = text(s.updated_at, 40)
  const updatedMs = Date.parse(updatedAt)
  const stopReason = text(s.stop_reason, 300) || null
  const isFinished = stage === 'done' || stage === 'verdict'
  const isStale = Number.isFinite(updatedMs) ? nowMs - updatedMs > STALE_MS : true
  return {
    food,
    stage,
    pipelineStage: text(liveStages[stage], 20) || null,
    isRunning: !isFinished && !stopReason && !isStale,
    isStale: !isFinished && !stopReason && isStale,
    headline: text(s.headline, 20) || null,
    stopReason,
    updatedAt,
  }
}

export type ParsedView = { model: DigestModel } | { problem: string }

export function parseView(
  viewText: string,
  where: { project: string; oaw: string | null },
  statusText: string | null,
  isViewStale: boolean,
  nowMs: number,
): ParsedView {
  let raw: unknown
  try {
    raw = JSON.parse(viewText)
  } catch {
    return { problem: 'view.json 不是有效的 JSON：請按「重算」或執行 catalog.py view。' }
  }
  const view = obj(raw)
  if (view.schema !== VIEW_SCHEMA) {
    return { problem: `view.json 的格式是 ${text(view.schema, 40) || '（沒寫）'}，這個 mod 讀的是 ${VIEW_SCHEMA}：請用同一版 OAW 重算。` }
  }
  const pipeline = obj(view.pipeline)
  const funnel = obj(view.funnel)
  const liveStages: Record<string, string> = {}
  for (const [key, value] of Object.entries(obj(pipeline.live_stages))) liveStages[key] = text(value, 20)
  const symbols: Record<string, string> = {}
  for (const [key, value] of Object.entries(obj(pipeline.symbols))) symbols[key] = text(value, 4)
  const statesZh: Record<string, string> = {}
  for (const [key, value] of Object.entries(obj(pipeline.states_zh))) statesZh[key] = text(value, 12)
  const foods = list(view.foods).map(parseFood).filter((food): food is DigestFood => food !== null)
  const release = obj(view.release_pending)
  return {
    model: {
      project: where.project,
      projectName: baseName(where.project),
      oaw: where.oaw,
      stages: parseStages(pipeline),
      symbols,
      statesZh,
      legend: list(pipeline.legend).map(item => text(item, 12)).filter(Boolean),
      foods,
      funnel: {
        submitted: num(funnel.submitted),
        tasted: num(funnel.tasted),
        measured: num(funnel.measured),
        agentTasted: num(funnel.agent_tasted),
        absorbedParts: num(funnel.absorbed_parts),
        rebuiltUnits: num(funnel.rebuilt_units),
      },
      release: {
        foods: list(release.foods).map(item => text(item, 64)).filter(Boolean),
        units: num(release.units),
        branches: list(release.branches).map(item => text(item, 80)).filter(Boolean),
      },
      isViewStale,
      live: parseLive(statusText, liveStages, nowMs),
      loadedAt: new Date(nowMs).toISOString(),
    },
  }
}

// ----------------------------------------------------------------- commands

export type Runner = { python: string[]; oaw: string; project: string }

export function pythonArgv(setting: string): string[] {
  const parts = setting.trim().split(/\s+/).filter(Boolean)
  return parts.length > 0 ? parts : ['python3']
}

function catalog(run: Runner, ...args: string[]): string[] {
  return [...run.python, joinPath(run.oaw, 'scripts', 'catalog.py'), ...args, '--target', run.project]
}

// ------------------------------------------------------------- EGM switch (D33)

export type EgmPosition = 'on' | 'auto' | 'off'
export const EGM_POSITIONS: EgmPosition[] = ['on', 'auto', 'off']
export const EGM_LABELS: Record<EgmPosition, string> = { on: '開', auto: '自動', off: '關' }
export const EGM_MEANING: Record<EgmPosition, string> = {
  on: '每個 deep 任務都跑完整 EGM 設計審查（品質優先，比較貴）',
  auto: '用目前證據最好的設計審查，X2 出結果前是一次全新 context 審查（預設）',
  off: '不跑 EGM：deep 只做計畫和 code review（省 token）',
}

/** The switch from .oaw/settings.json text; a missing file is the default (auto). */
export function parseEgmSetting(text: string | null): { position: EgmPosition | null; isDefault: boolean; problem: string | null } {
  if (text === null) return { position: 'auto', isDefault: true, problem: null }
  try {
    const data = JSON.parse(text) as { review?: { egm?: unknown } }
    const value = data && typeof data === 'object' ? data.review?.egm : undefined
    if (value === undefined) return { position: 'auto', isDefault: true, problem: null }
    if (typeof value === 'string' && (EGM_POSITIONS as string[]).includes(value)) {
      return { position: value as EgmPosition, isDefault: false, problem: null }
    }
    return { position: null, isDefault: false, problem: '.oaw/settings.json 的 review.egm 不是 on、auto 或 off' }
  } catch {
    return { position: null, isDefault: false, problem: '.oaw/settings.json 讀不懂：修正或刪掉它' }
  }
}

/** Sets the switch through OAW's own helper, which locks and checks the file. */
export function egmArgv(run: Runner, position: EgmPosition): string[] {
  return [...run.python, joinPath(run.oaw, 'scripts', 'oaw_mode.py'), 'egm', position, '--root', run.project, '--json']
}

export function addArgv(run: Runner, urls: string[]): string[] {
  return catalog(run, 'add', ...urls)
}

export function viewArgv(run: Runner): string[] {
  return catalog(run, 'view')
}

// Actions that change project state preview first (OAW's own contract: without
// --apply the CLI only previews). `null` means the action is terminal-only.
export const PREVIEWED = new Set(['forget', 'absorb', 'remove', 'restore'])
export const NEEDS_REASON = new Set(['remove'])

export function actionArgv(
  run: Runner,
  action: DigestAction,
  food: DigestFood,
  options: { apply: boolean; reason?: string; components?: string[] },
): string[] | null {
  if (action.where === 'terminal') return null
  const apply = options.apply ? ['--apply'] : []
  const reason = options.reason?.trim() ? ['--reason', options.reason.trim()] : []
  const param = (key: string): string => {
    const value = action.params[key]
    return typeof value === 'string' ? value : ''
  }
  switch (action.endpoint) {
    case 'taste':
      return catalog(run, 'taste', param('food') || food.id)
    case 'forget':
      return catalog(run, 'forget', param('food') || food.id, ...(options.apply ? reason : []), ...apply)
    case 'absorb': {
      const parts = options.components ?? []
      if (parts.length === 0) return null
      return catalog(run, 'absorb', param('food') || food.id, '--components', parts.join(','), ...(options.apply ? reason : []), ...apply)
    }
    case 'remove': {
      const name = param('name') || food.id
      const isFood = action.params.food === true
      return catalog(run, 'remove', name, ...(isFood ? ['--food'] : []), ...(options.apply ? reason : []), ...apply)
    }
    case 'restore': {
      const build = param('build')
      return build ? catalog(run, 'restore', build, ...apply) : null
    }
    default:
      return null
  }
}

// The command an owner types in their own terminal (triage needs a code typed back there).
export function terminalCommand(run: Runner | null, action: DigestAction, food: DigestFood): string {
  const target = run ? run.project : '<專案資料夾>'
  const script = run ? joinPath(run.oaw, 'scripts', 'catalog.py') : 'scripts/catalog.py'
  const py = run ? run.python.join(' ') : 'python3'
  if (action.endpoint === 'triage') return `${py} ${script} menu --target ${quote(target)}`
  return `${py} ${script} ${action.endpoint} ${food.id} --target ${quote(target)}`
}

function quote(path: string): string {
  return /[\s'"]/.test(path) ? `"${path.replace(/"/g, '\\"')}"` : path
}

// ----------------------------------------------------------------- words

export function stageIndex(model: DigestModel, stage: string): number {
  return model.stages.findIndex(s => s.id === stage)
}

export function stageChain(model: DigestModel, food: DigestFood): string {
  return model.stages
    .map(stage => `${stage.label}${model.symbols[food.stages[stage.id] ?? 'todo'] ?? '○'}`)
    .join(' ')
}

export function verdictText(food: DigestFood): string {
  const level = LEVELS_ZH[food.verdict.level] ?? food.verdict.level
  const label = food.verdict.label || '還沒判定'
  return `${food.verdict.symbol ? food.verdict.symbol + ' ' : ''}${label}${level ? `（${level}）` : ''}`
}

export function liveText(model: DigestModel): string | null {
  const live = model.live
  if (!live) return null
  const food = model.foods.find(f => f.id === live.food)
  const name = food?.display ?? live.food
  const stage = model.stages.find(s => s.id === live.pipelineStage)?.label ?? live.stage
  if (live.isRunning) return `試吃中：${name} · ${stage}`
  if (live.stopReason) return `上次試吃停止：${name} · ${live.stopReason}`
  if (live.isStale) return `${name} 停在${stage}超過 10 分鐘沒有更新：可能中斷了`
  return null
}

export function waitingCount(model: DigestModel, waiting = 'owner'): number {
  return model.foods.filter(food => food.waiting === waiting).length
}

// The one release the owner decides for the whole branch (D21, D28), or null when nothing waits for it.
export function releaseText(model: DigestModel): string | null {
  if (model.release.foods.length === 0) return null
  const branches = model.release.branches.join('、') || '工作分支'
  return `等發布：${model.release.units} 個單位在 ${branches}（${model.release.foods.length} 樣食物），合併 PR 時一次決定`
}

export function waitingLabel(food: DigestFood): string {
  return WAITING_MARKS[food.waiting]?.label ?? ''
}

export function askBrief(model: DigestModel, food: DigestFood): string {
  const lines = [
    `關於 OAW 消化道的問題（專案 ${model.projectName}）`,
    `食物：${food.display}（${food.id}，${food.kind === 'paper' ? '論文' : 'repo'}）`,
    `來源：${food.source}`,
    `現在：${food.stageLabel} · ${food.stateZh} · ${food.waitingZh}`,
    `判定：${verdictText(food)} · 成分 吸收 ${food.counts.absorb}、暫留 ${food.counts.hold}、排掉 ${food.counts.excrete}`,
  ]
  if (food.note) lines.push(`說明：${food.note}`)
  for (const stage of model.stages) {
    const note = food.stageNotes[stage.id]
    if (note) lines.push(`${stage.label}：${note}`)
  }
  lines.push(`卡在哪：${food.blocker.where || '紀錄裡沒有寫'}`)
  lines.push(`依據：${food.blocker.basis.join('；') || '紀錄裡沒有寫'}`)
  lines.push(`你不處理會怎樣：${food.blocker.ifIgnored || '紀錄裡沒有寫'}`)
  if (food.blocker.unknown.length > 0) lines.push(`紀錄沒寫的：${food.blocker.unknown.join('；')}`)
  lines.push('問題：')
  return lines.join('\n')
}
