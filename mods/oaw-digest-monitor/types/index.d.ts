// The oaw-digest-monitor contract: what the pane reads from $.state.
// Every value is derived from the OAW project's own files (.oaw/catalog/view.json
// and status.json); nothing here is a second source of truth.

export type DigestStage = {
  id: string
  label: string
  organ: string
  automation: string
  automationZh: string
  summary: string
}

export type DigestAction = {
  id: string
  endpoint: string
  label: string
  where: string
  params: Record<string, string | boolean | string[]>
}

export type DigestComponent = {
  id: string
  name: string
  disposition: string
  canAbsorb: boolean
}

export type DigestFood = {
  id: string
  display: string
  kind: 'repo' | 'paper'
  source: string
  stage: string
  stageLabel: string
  state: string
  stateZh: string
  stages: Record<string, string>
  waiting: string
  waitingZh: string
  note: string
  stageNotes: Record<string, string>
  tasting: string | null
  verdict: { headline: string; symbol: string; label: string; level: string }
  counts: { absorb: number; hold: number; excrete: number }
  blocker: { where: string; basis: string[]; ifIgnored: string; unknown: string[] }
  actions: DigestAction[]
  components: DigestComponent[]
}

// The project's EGM switch (owner decision D33), read from .oaw/settings.json and set through scripts/oaw_mode.py.
export type EgmView = {
  position: 'on' | 'auto' | 'off' | null
  isDefault: boolean
  problem: string | null
}

export type DigestLive = {
  food: string
  stage: string
  pipelineStage: string | null
  isRunning: boolean
  isStale: boolean
  headline: string | null
  stopReason: string | null
  updatedAt: string
}

export type DigestModel = {
  project: string
  projectName: string
  oaw: string | null
  stages: DigestStage[]
  symbols: Record<string, string>
  statesZh: Record<string, string>
  legend: string[]
  foods: DigestFood[]
  funnel: { submitted: number; tasted: number; measured: number; agentTasted: number; absorbedParts: number; rebuiltUnits: number }
  release: { foods: string[]; units: number; branches: string[] }
  isViewStale: boolean
  live: DigestLive | null
  loadedAt: string
}

export type DigestProblem = { kind: 'no-project' | 'no-view' | 'bad-view'; text: string; project: string | null; oaw: string | null }

export type DigestPending = {
  food: string
  action: string
  label: string
  components: string[]
  preview: string
  needsReason: boolean
}

export type DigestMessage = { kind: 'ok' | 'error' | 'info'; text: string }

declare module 'claude-code' {
  interface PluginState {
    'oaw-digest-monitor': {
      model: Shaped<DigestModel | null>
      problem: DigestProblem | null
      selected: string | null
      picks: string[]
      pending: DigestPending | null
      busy: string | null
      message: DigestMessage | null
      egm: EgmView | null
    }
  }
}
