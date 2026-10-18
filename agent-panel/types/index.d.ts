export type AgentStatus = 'running' | 'done' | 'failed'

export type AgentRow = {
  key: string
  agentId?: string
  description: string
  type: string
  role: string
  model: string
  status: AgentStatus
  startedAt: number
  endedAt?: number
  engineTokens?: number
}

export type AgentUsage = {
  model: string
  effort?: string
  tokens: number
  ctx: number
  steps?: number
  cost: number
}

export type MainChat = AgentUsage & {
  steps: number
  activeMs: number
  turnStartedAt?: number
}

export type Week = {
  used: number
  elapsed: number
  verdict: string
}

export type Run = {
  workflow: string
  ticket?: string
  startedAt: number
  scheduled: string[]
}

declare module 'claude-code' {
  interface PluginState {
    'agent-panel': {
      run: Run | null
      agents: AgentRow[]
      usage: Record<string, AgentUsage>
      now: number
      doneOpen: boolean
      min: boolean
      week: Week | null
      main: MainChat | null
    }
  }
}
