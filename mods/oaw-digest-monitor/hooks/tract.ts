// The digestive tract: an SVG for surfaces that draw one (desktop, VS Code,
// mobile) and text lines for the terminal. The nine stops come from view.json;
// organs are captions only, never a claim about what a stop does (D23).

import type { DigestFood, DigestModel } from '../types'
import { WAITING_MARKS, stageIndex, verdictText } from './model'

// Three rows of three stops, the tube turning at the ends (an S that reads
// left to right, then back, then on), so it fits a pane docked beside the chat.
const LEFT = 60
const SEG = 120
const TOP = 46
const R = 42
const x = (col: number): number => LEFT + SEG * col
const y = (row: number): number => TOP + 2 * R * row
const ARC = Math.PI * R
const TUBE = `M${x(0)} ${y(0)} H${x(2)} A${R} ${R} 0 0 1 ${x(2)} ${y(1)} H${x(0)} A${R} ${R} 0 0 0 ${x(0)} ${y(2)} H${x(2)}`

export function stopPoint(index: number): { x: number; y: number; along: number } {
  const row = Math.min(2, Math.floor(index / 3))
  const col = index % 3
  return { x: row % 2 === 0 ? x(col) : x(2 - col), y: y(row), along: row * (2 * SEG + ARC) + col * SEG }
}

const VERDICT_COLORS: Record<string, string> = {
  nutritious: '#2e9e5b',
  'no-gain': '#8d939b',
  untested: '#8d939b',
  incomplete: '#b49a4c',
  regressed: '#d64545',
  diarrhea: '#c0562e',
  risky: '#e0a020',
  toxic: '#d64545',
  inedible: '#7a5cc4',
}

// Organ captions shrink with their length so four characters still fit the stop.
const ORGAN_SIZE: Record<number, number> = { 0: 11, 1: 11, 2: 10, 3: 8, 4: 6.5 }

const AUTOMATION_COLORS: Record<string, string> = {
  automated: '#2e9e5b',
  agent: '#c96a3a',
  owner: '#3b7ddd',
  mixed: '#2a9d9d',
  planned: '#9aa0a6',
}

function esc(value: string): string {
  return value.replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch] ?? ch)
}

function short(name: string, max: number): string {
  return name.length > max ? name.slice(0, max - 1) + '…' : name
}

export function tractSvg(model: DigestModel, selected: string | null, motion: boolean): string {
  const running = model.live?.isRunning ? model.live : null
  const parts: string[] = []
  parts.push(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 262" width="360" height="262" role="img">',
    '<style>',
    'svg{--bg:#fbf7f4;--tube:#e6d5ca;--lumen:#f8eee8;--text:#2b2b2b;--muted:#6b6b6b;--stop:#ffffff;--trail:#3b7ddd;--wave:#d9b8a6;font-family:system-ui,"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif}',
    '@media (prefers-color-scheme: dark){svg{--bg:#24201e;--tube:#5b4a41;--lumen:#3b312c;--text:#ece6e2;--muted:#a9a2a0;--stop:#262220;--trail:#6aa2f0;--wave:#7d6355}}',
    '.tube{fill:none;stroke:var(--tube);stroke-width:24;stroke-linecap:round;stroke-linejoin:round}',
    '.lumen{fill:none;stroke:var(--lumen);stroke-width:14;stroke-linecap:round;stroke-linejoin:round}',
    '.trail{fill:none;stroke:var(--trail);stroke-width:4;stroke-linecap:round;opacity:.75}',
    '.wave{fill:none;stroke:var(--wave);stroke-width:14;stroke-dasharray:5 23;stroke-linecap:round}',
    '.organ{font-size:10px;fill:var(--text);text-anchor:middle;dominant-baseline:central}',
    '.label{font-size:11px;fill:var(--text);text-anchor:middle;font-weight:600}',
    '.mode{font-size:8.5px;fill:var(--muted);text-anchor:middle}',
    '.badge{font-size:8px;fill:#fff;text-anchor:middle;dominant-baseline:central;font-weight:700}',
    '.more{font-size:9px;fill:var(--muted)}',
  )
  if (motion) {
    parts.push(
      '.wave{animation:wave 1.4s linear infinite}@keyframes wave{to{stroke-dashoffset:-28}}',
      '.live{animation:pulse 1.1s ease-in-out infinite;transform-box:fill-box;transform-origin:center}',
      '@keyframes pulse{50%{transform:scale(1.4)}}',
      '@media (prefers-reduced-motion: reduce){.wave,.live{animation:none}}',
    )
  }
  parts.push('</style>')
  // Its own backdrop: the labels keep their contrast whichever theme the host draws around it.
  parts.push('<rect x="0" y="0" width="360" height="262" rx="12" fill="var(--bg)"/>')
  parts.push(`<path class="tube" d="${TUBE}"/>`, `<path class="lumen" d="${TUBE}"/>`)
  if (running) parts.push(`<path class="wave" d="${TUBE}"/>`)

  // The selected food's travelled path, mouth to where it stands now.
  const chosen = model.foods.find(food => food.id === selected) ?? null
  if (chosen) {
    const at = stageIndex(model, chosen.stage)
    if (at > 0) {
      const length = stopPoint(at).along
      parts.push(`<path class="trail" d="${TUBE}" stroke-dasharray="${length.toFixed(1)} 2000"/>`)
    }
  }

  model.stages.slice(0, 9).forEach((stage, index) => {
    const { x, y } = stopPoint(index)
    const color = AUTOMATION_COLORS[stage.automation] ?? '#9aa0a6'
    const dash = stage.automation === 'planned' ? ' stroke-dasharray="3 2"' : ''
    const state = chosen ? chosen.stages[stage.id] : undefined
    const ring = state === 'blocked' ? '#d64545' : state === 'current' ? 'var(--trail)' : null
    if (ring) parts.push(`<circle cx="${x}" cy="${y}" r="19" fill="none" stroke="${ring}" stroke-width="2.5"/>`)
    parts.push(
      `<g><title>${esc(`${stage.label}（${stage.organ}）· ${stage.automationZh || stage.automation}${stage.summary ? '：' + stage.summary : ''}`)}</title>`,
      `<circle cx="${x}" cy="${y}" r="15" fill="var(--stop)" stroke="${color}" stroke-width="2"${dash}/>`,
      `<text class="organ" x="${x}" y="${y}" style="font-size:${ORGAN_SIZE[Math.min(4, stage.organ.length)] ?? 6.5}px">${esc(short(stage.organ, 4))}</text></g>`,
      `<text class="label" x="${x}" y="${y + 31}">${esc(stage.label)}</text>`,
      `<text class="mode" x="${x}" y="${y + 42}">${esc(stage.automationZh)}</text>`,
    )
  })

  // Boluses sit on their stop, side by side; more than five become "+n".
  const byStage = new Map<string, DigestFood[]>()
  for (const food of model.foods) {
    const shown = running && running.food === food.id && running.pipelineStage ? running.pipelineStage : food.stage
    byStage.set(shown, [...(byStage.get(shown) ?? []), food])
  }
  for (const [stage, foods] of byStage) {
    const index = stageIndex(model, stage)
    if (index < 0 || index > 8) continue
    const { x, y } = stopPoint(index)
    const visible = foods.slice(0, 5)
    visible.forEach((food, i) => {
      const bx = x + (i - (visible.length - 1) / 2) * 15
      const by = y - 27
      const isLive = running?.food === food.id
      const isChosen = food.id === selected
      const fill = VERDICT_COLORS[food.verdict.headline] ?? '#8d939b'
      const tip = `${food.display} · ${food.stageLabel} ${food.stateZh} · ${verdictText(food)}${food.waitingZh ? ' · ' + food.waitingZh : ''}${isLive ? ' · 試吃中' : ''}`
      parts.push(
        `<g><title>${esc(tip)}</title>`,
        `<circle${isLive && motion ? ' class="live"' : ''} cx="${bx}" cy="${by}" r="${isChosen ? 7.5 : 6}" fill="${fill}"${isChosen ? ' stroke="var(--text)" stroke-width="1.6"' : ' stroke="var(--stop)" stroke-width="1"'}/>`,
      )
      const mark = WAITING_MARKS[food.waiting]
      if (mark) {
        parts.push(
          `<circle class="w-${esc(food.waiting)}" cx="${bx + 6}" cy="${by - 6}" r="4.6" fill="${mark.color}"/>`,
          `<text class="badge" x="${bx + 6}" y="${by - 6}">${esc(mark.badge)}</text>`,
        )
      }
      parts.push('</g>')
    })
    if (foods.length > visible.length) {
      parts.push(`<text class="more" x="${x + 42}" y="${y - 22}">+${foods.length - visible.length}</text>`)
    }
  }
  parts.push('</svg>')
  return parts.join('')
}

export function tractAlt(model: DigestModel): string {
  const where = model.stages
    .map(stage => {
      const here = model.foods.filter(food => food.stage === stage.id).map(food => food.display)
      return here.length > 0 ? `${stage.label}：${here.join('、')}` : null
    })
    .filter(Boolean)
  return `OAW 消化道，九站：${model.stages.map(s => s.label).join('、')}。${where.length > 0 ? where.join('；') : '還沒有食物'}。`
}

// The terminal has no Svg: one line per stop, the foods standing there after it.
export function tractLines(model: DigestModel, selected: string | null, frame: number): string[] {
  const running = model.live?.isRunning ? model.live : null
  const organWidth = Math.max(...model.stages.map(stage => stage.organ.length), 1)
  return model.stages.map((stage, index) => {
    const here = model.foods.filter(food => {
      const shown = running && running.food === food.id && running.pipelineStage ? running.pipelineStage : food.stage
      return shown === stage.id
    })
    const pipe = index === model.stages.length - 1 ? '└' : index === 0 ? '┌' : '│'
    const chosen = model.foods.find(food => food.id === selected)
    const mark = chosen ? (model.symbols[chosen.stages[stage.id] ?? 'todo'] ?? '○') : '·'
    const foods = here
      .map(food => {
        const live = running?.food === food.id ? (frame % 2 === 0 ? '◉' : '○') : food.verdict.symbol || '•'
        const badge = WAITING_MARKS[food.waiting]?.badge ?? ''
        return `${live}${short(food.id, 24)}${badge}`
      })
      .join('  ')
    return `${pipe} ${mark} ${stage.organ.padEnd(organWidth, '　')} ${stage.label}${foods ? '  ' + foods : ''}`
  })
}
