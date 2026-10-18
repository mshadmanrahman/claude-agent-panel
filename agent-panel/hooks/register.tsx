import { atom, read, update } from 'claude-code'
import type { Elements, EngineInterface, Register } from 'claude-code'

import type { AgentRow, AgentUsage, MainChat, Run, Week } from '../types'

const runAtom = atom({ plugin: 'agent-panel', key: 'run' } as const, null as Run | null)
const agentsAtom = atom({ plugin: 'agent-panel', key: 'agents' } as const, [] as AgentRow[])
const usageAtom = atom({ plugin: 'agent-panel', key: 'usage' } as const, {} as Record<string, AgentUsage>)
const nowAtom = atom({ plugin: 'agent-panel', key: 'now' } as const, 0)
const doneOpenAtom = atom({ plugin: 'agent-panel', key: 'doneOpen' } as const, false)
const minAtom = atom({ plugin: 'agent-panel', key: 'min' } as const, false)
const weekAtom = atom({ plugin: 'agent-panel', key: 'week' } as const, null as Week | null)
const mainAtom = atom({ plugin: 'agent-panel', key: 'main' } as const, null as MainChat | null)

// Each agent row's context bar is scaled to a 1M-token window.
const WINDOW = 1_000_000

// Dollars per million tokens: [input, output]. Cache read 0.1x input, write 1.25x.
const PRICES: [RegExp, number, number][] = [
  [/fable/i, 10, 50],
  [/opus/i, 4, 20],
  [/sonnet/i, 2, 10],
  [/haiku/i, 1, 5],
]

const EFFORT: Record<string, [string, string]> = {
  max: ['heavy', '#D9553B'],
  xhigh: ['heavy', '#D9553B'],
  high: ['careful', '#D99A3B'],
  medium: ['medium', '#4A9FD9'],
  low: ['light', '#3BB8A0'],
}

// Clawd as pixel art, 11 x 10 pixels, drawn two pixels per cell with half blocks.
// B body, E eye, H hat, F flag, . empty. Rows 0-1 are the hat, 7-8 the legs.
const BODY_ROWS = [
  '.BBBBBBBBB.',
  '.BEBBBBBEB.',
  'BBBBBBBBBBB',
  'BBBBBBBBBBB',
  '.BBBBBBBBB.',
]
const LEGS = [
  ['.B.B...B.B.', '.B.B...B.B.'],
  ['..B.B.B.B..', '.B.B...B.B.'],
]
const HATS: Record<string, { rows: [string, string]; color: number; accent?: number }> = {
  architect: { rows: ['...HHHHH...', '..HHHHHHH..'], color: 0x4a7fd9 },
  developer: { rows: ['...HHHHH...', '.HHHHHHHHH.'], color: 0xe8b931 },
  reviewer: { rows: ['..HHHHH....', '..HHHHHHHH.'], color: 0x9aa0a6 },
  'tech lead': { rows: ['..HHHHH....', '..HHHHHHHH.'], color: 0x9aa0a6 },
  shipper: { rows: ['..HHHH..FF.', '.HHHHHH.F..'], color: 0x3ba55c, accent: 0xf2f2f2 },
  scout: { rows: ['...........', '.HHHHHHHHHF'], color: 0x3bb8a0, accent: 0x3bb8a0 },
  explore: { rows: ['.....H.....', '...HHHHH...'], color: 0x9b6bd9 },
}
const BODY = { running: 0xd97757, done: 0xd97757, failed: 0xc0392b, scheduled: 0x8a5a44 }
const EYE = 0x2b1d17
const DEFAULT = 0x01000000

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
function base64(bytes: Uint8Array): string {
  let out = ''
  for (let i = 0; i < bytes.length; i += 3) {
    const n = ((bytes[i] ?? 0) << 16) | ((bytes[i + 1] ?? 0) << 8) | (bytes[i + 2] ?? 0)
    out += B64[(n >> 18) & 63]! + B64[(n >> 12) & 63]!
    out += i + 1 < bytes.length ? B64[(n >> 6) & 63]! : '='
    out += i + 2 < bytes.length ? B64[n & 63]! : '='
  }
  return out
}

// 11x10 pixel grid of colors (-1 = transparent), shared by the terminal Raster and the desktop Svg.
function pixels(role: string, body: number, frame: number): number[][] {
  const hat = HATS[role]
  const legs = LEGS[frame % 2]!
  const px = [...(hat?.rows ?? ['...........', '...........']), ...BODY_ROWS, legs[0], legs[1], '...........']
  const color = (c: string | undefined): number =>
    c === 'B' ? body : c === 'E' ? EYE : c === 'H' ? (hat?.color ?? DEFAULT) : c === 'F' ? (hat?.accent ?? DEFAULT) : -1
  return px.map(row => Array.from({ length: 11 }, (_, x) => color(row?.[x])))
}

const spriteCache = new Map<string, string>()
function sprite(role: string, body: number, frame: number): string {
  const id = `${role}|${body}|${frame}`
  const hit = spriteCache.get(id)
  if (hit) return hit
  const g = pixels(role, body, frame)
  const words: number[] = []
  for (let r = 0; r < 10; r += 2) {
    for (let x = 0; x < 11; x++) {
      const top = g[r]?.[x] ?? -1
      const bot = g[r + 1]?.[x] ?? -1
      if (top < 0 && bot < 0) words.push(0x20, DEFAULT, DEFAULT)
      else if (top < 0) words.push(0x2584, bot, DEFAULT)
      else if (bot < 0) words.push(0x2580, top, DEFAULT)
      else if (top === bot) words.push(0x2588, top, DEFAULT)
      else words.push(0x2580, top, bot)
    }
  }
  const cells = base64(new Uint8Array(Uint32Array.from(words).buffer))
  spriteCache.set(id, cells)
  return cells
}

// Desktop avatars: one SVG per role and state, animated with SMIL so nothing re-renders per frame.
type Mood = 'running' | 'done' | 'failed' | 'scheduled'
const R = (x: number, y: number, w: number, h: number, fill: string, inner = '') =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}">${inner}</rect>`
const loop = (attr: string, values: string, dur: string, extra = '') =>
  `<animate attributeName="${attr}" values="${values}" dur="${dur}" repeatCount="indefinite" ${extra}/>`
const move = (type: string, values: string, dur: string, extra = '') =>
  `<animateTransform attributeName="transform" type="${type}" values="${values}" dur="${dur}" repeatCount="indefinite" ${extra}/>`

type Persona = {
  motion?: string // on the whole body while running
  shadow?: string // shadow rx while running
  flip?: string // discrete left/right turn while running
  arms?: (live: boolean, B: string) => string
  back?: (live: boolean) => string // drawn behind the body
  front?: (live: boolean) => string // drawn over the body
  hidesEyes?: boolean
  over?: (live: boolean) => string // above the head, never flipped
}

const PERSONAS: Record<string, Persona> = {
  // Blue hard hat and round glasses, holding up a blueprint whose system diagram draws itself while it works.
  architect: {
    arms: (live, B) => R(4, 12, 2, 2, B) + R(20, 11, 2, 2, B, live ? loop('y', '11;10;11', '0.7s') : ''),
    back: () => R(9, 4, 8, 2, '#4A7FD9') + R(7, 6, 12, 3, '#4A7FD9') + R(12.5, 3.6, 1, 5.4, '#2F5FA8') + R(5, 8.4, 16, 1, '#2F5FA8'),
    front: live =>
      `<circle cx="9.5" cy="12" r="1.8" fill="none" stroke="#2B1D17" stroke-width="0.5"/>` +
      `<circle cx="16.5" cy="12" r="1.8" fill="none" stroke="#2B1D17" stroke-width="0.5"/>` +
      R(11.3, 11.7, 3.4, 0.5, '#2B1D17') +
      
      R(22, 8, 7, 9, '#2F5FA8') + R(21.6, 7.4, 7.8, 1, '#4A7FD9') + R(21.6, 16.6, 7.8, 1, '#4A7FD9') +
      `<path d="M24.3 9.2 h2.4 v1.6 h-2.4 Z M25.5 10.8 V12.2 M23.9 12.2 H27.2 M23.9 12.2 V13.6 M27.2 12.2 V13.6 M22.8 13.6 h2.2 v1.6 h-2.2 Z M26.1 13.6 h2.2 v1.6 h-2.2 Z" fill="none" stroke="#EAF3FF" stroke-width="0.5" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0"></path>`,
  },
  // Boy Scout: campaign hat and neckerchief, hops, raises the binoculars to scan, turns, spots something.
  scout: {
    arms: (live, B) =>
      `<g transform="translate(0 ${live ? -3.5 : 0})">${live ? move('translate', '0 -3.5;0 -4.5;0 -3.5', '0.7s') : ''}${R(5, 14, 2, 2, B)}${R(19, 14, 2, 2, B)}</g>`,
    back: () =>
      R(10, 2, 6, 1, '#B08A55') + R(12.5, 2, 1, 1, '#8C6A3E') + R(9, 3, 8, 1, '#B08A55') + R(8, 4, 10, 2.4, '#B08A55') +
      R(8, 5.4, 10, 0.8, '#6B4F3A') + R(3, 6.4, 20, 1.4, '#B08A55') + R(3, 7.8, 20, 0.4, '#8C6A3E'),
    front: live =>
      R(8, 14, 10, 1, '#D9553B') + R(9, 15, 8, 1, '#D9553B') + R(11, 16, 4, 1, '#D9553B') + R(12, 14, 2, 1.2, '#FFD54A') +
      `<g transform="translate(0 ${live ? 0 : 4.5})">${live ? move('translate', '0 0;0 -1;0 0', '0.7s') : ''}` +
      R(7, 10, 4, 3, '#33363B') + R(15, 10, 4, 3, '#33363B') + R(11, 11, 4, 1, '#33363B') +
      R(8, 11, 1, 1, '#8FD3FF') + R(16, 11, 1, 1, '#8FD3FF') + `</g>`,
  },
  // In the zone: headphones on, bobs to the beat, types fast, code floats up off the screen.
  developer: {
    arms: (live, B) =>
      R(7, 18, 2, 1.4, B, live ? loop('y', '18;17;18', '0.24s') : '') +
      R(17, 18, 2, 1.4, B, live ? loop('y', '17;18;17', '0.24s') : ''),
    back: () => R(6, 6, 14, 1, '#33363B') + R(5, 7, 1, 4, '#33363B') + R(20, 7, 1, 4, '#33363B'),
    front: live =>
      R(4, 10, 2, 3, '#E8B931') + R(20, 10, 2, 3, '#E8B931') +
      (live ? R(6, 12, 14, 2, '#9FE8FF', loop('opacity', '0.15;0.35;0.15', '0.5s')) : '') +
      R(8, 14, 10, 5, '#5F6670') + R(12.5, 16, 1, 1, '#9AA0A6') + R(6, 19, 14, 1, '#9AA0A6'),
  },
  // Inspects: sweeps a magnifying glass across the work.
  reviewer: {
    back: () => R(7, 6, 12, 3, '#9AA0A6') + R(13, 8, 8, 1, '#6B7076'),
    front: live =>
      `<g>${live ? move('translate', '0 0;1 0;0 0', '0.7s') : ''}<circle cx="9.5" cy="12" r="2.6" fill="#CFE9FF" fill-opacity="0.45" stroke="#33363B" stroke-width="0.6"/>${R(11.2, 14, 1, 1, '#6B4F3A')}${R(12, 15, 1, 1, '#6B4F3A')}${R(12.8, 16, 1, 1, '#6B4F3A')}</g>`,
  },
  // Carries the box out the door with big hops.
  shipper: {
    arms: (_l, B) => R(5, 6, 2, 4, B) + R(19, 6, 2, 4, B),
    back: live => `<g>${live ? move('translate', '0 0;0 -1;0 0', '0.6s') : ''}${R(7, 0, 12, 6, '#C68B4E')}${R(12.5, 0, 1, 6, '#E9D3A6')}</g>`,
  },
  explore: {
    flip: move('scale', '1 1;-1 1', '4s', 'calcMode="discrete" keyTimes="0;0.5"'),
    back: () => R(11, 2, 4, 2, '#9B6BD9') + R(9, 4, 8, 2, '#9B6BD9') + R(7, 6, 12, 3, '#9B6BD9') + R(12, 4, 1, 1, '#FFD54A'),
  },
    agent: {},
  // The main chat: a captain's cap, white top, navy band, gold badge, brim over the brow.
  main: {
    back: () =>
      R(7, 2, 12, 1, '#C9CED6') + R(5, 3, 16, 1, '#C9CED6') + R(6, 3, 14, 1, '#FFFFFF') + R(5, 4, 16, 2, '#FFFFFF') +
      R(5, 6, 16, 1, '#C9CED6') + R(7, 7, 12, 2, '#1F2A44') + R(12, 6, 2, 2, '#E8B931'),
        front: () => R(7, 9, 12, 1, '#111827') + R(8, 10, 10, 1, '#111827'),
  },
}
PERSONAS['tech lead'] = PERSONAS.reviewer!

const avatarCache = new Map<string, string>()
function avatarSvg(role: string, mood: Mood): string {
  const id = `${role}|${mood}`
  const hit = avatarCache.get(id)
  if (hit) return hit
  const p = PERSONAS[role] ?? PERSONAS.agent!
  const live = mood === 'running'
  const B = mood === 'failed' ? '#C0392B' : '#D97757'
  const E = '#2B1D17'
  const blink = (x: number) =>
    R(x, 11, 1, 2, E, live ? loop('height', '2;2;0.3;2', '0.9s', 'keyTimes="0;0.8;0.9;1"') + loop('y', '11;11;12.2;11', '0.9s', 'keyTimes="0;0.8;0.9;1"') : '')
  const eyes =
    mood === 'done' && (role === 'architect' || role === 'main')
      ? blink(9) + blink(16)
      : mood === 'done'
      ? R(8, 12, 1, 1, E) + R(9, 11, 1, 1, E) + R(10, 12, 1, 1, E) + R(15, 12, 1, 1, E) + R(16, 11, 1, 1, E) + R(17, 12, 1, 1, E)
      : mood === 'failed'
        ? R(8, 10, 1, 1, E) + R(10, 10, 1, 1, E) + R(9, 11, 1, 1, E) + R(8, 12, 1, 1, E) + R(10, 12, 1, 1, E) +
          R(15, 10, 1, 1, E) + R(17, 10, 1, 1, E) + R(16, 11, 1, 1, E) + R(15, 12, 1, 1, E) + R(17, 12, 1, 1, E)
        : mood === 'scheduled'
          ? R(8, 12, 3, 0.6, E) + R(15, 12, 3, 0.6, E)
          : p.hidesEyes ? '' : blink(9) + blink(16)
  const legs = [7, 10, 15, 18].map(x => R(x, 17, 1, 3, B)).join('')
  const figure =
    (p.back?.(live) ?? '') +
    legs +
    R(6, 9, 14, 8, B) +
    (p.arms ? p.arms(live, B) : R(4, 12, 2, 2, B) + R(20, 12, 2, 2, B)) +
    eyes +
    (p.front?.(live) ?? '')
  const turned = live && p.flip ? `<g transform="translate(13 0)"><g>${p.flip}<g transform="translate(-13 0)">${figure}</g></g></g>` : figure
  const zzz =
    mood === 'scheduled'
      ? `<text x="20" y="5" font-size="4" font-family="monospace" font-weight="bold" fill="#9AA0A6">z</text><text x="23" y="2" font-size="3" font-family="monospace" font-weight="bold" fill="#9AA0A6">z</text>`
      : ''
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-3 -3 33 27" shape-rendering="crispEdges">` +
    `<ellipse cx="13" cy="21.6" rx="7" ry="0.9" fill="#000" fill-opacity="0.18">${live && p.shadow ? p.shadow : ''}</ellipse>` +
    `<g${mood === 'scheduled' ? ' opacity="0.55"' : ''}>${live && p.motion ? p.motion : ''}${turned}</g>` +
    (p.over?.(live) ?? '') +
    zzz +
    `</svg>`
  avatarCache.set(id, svg)
  return svg
}

// Working indicator: three dots dimming in turn. The rest state is full brightness, since every pane redraw restarts the animation.
const dotsCache = new Map<string, string>()
function dotsSvg(color: string): string {
  const hit = dotsCache.get(color)
  if (hit) return hit
  const dot = (cx: number, begin: string) =>
    `<circle cx="${cx}" cy="5" r="1.6" fill="${color}">` +
    `<animate attributeName="opacity" values="1;0.45;1;1" keyTimes="0;0.25;0.5;1" dur="0.8s" begin="${begin}" repeatCount="indefinite"/>` +
    `</circle>`
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 8">${dot(3, '0s')}${dot(8, '0.13s')}${dot(13, '0.26s')}</svg>`
  dotsCache.set(color, svg)
  return svg
}

function roleOf(type: string, description: string): string {
  const s = `${type} ${description}`.toLowerCase()
  if (/architect|plan/.test(s)) return 'architect'
  if (/develop|build/.test(s)) return 'developer'
  if (/tech.?lead/.test(s)) return 'tech lead'
  if (/review|verify|gate/.test(s)) return 'reviewer'
  if (/ship|deploy/.test(s)) return 'shipper'
  if (/scout/.test(s)) return 'scout'
  if (/explore/.test(s)) return 'explore'
  return 'agent'
}

function modelName(id: string): string {
  const m = id.match(/(opus|sonnet|haiku|fable)-(\d+)(?:-(\d))?/i)
  if (!m) return id
  const f = m[1] ?? ''
  const fam = f.charAt(0).toUpperCase() + f.slice(1)
  return m[3] ? `${fam} ${m[2]}.${m[3]}` : `${fam} ${m[2]}`
}

function price(model: string, u: { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number | null; cache_creation_input_tokens?: number | null }): number {
  const p = PRICES.find(([re]) => re.test(model)) ?? PRICES[1]!
  const inn = p[1] / 1e6
  return (
    u.input_tokens * inn +
    (u.cache_read_input_tokens ?? 0) * inn * 0.1 +
    (u.cache_creation_input_tokens ?? 0) * inn * 1.25 +
    u.output_tokens * (p[2] / 1e6)
  )
}

const k = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}k` : `${n}`)
const clock = (ms: number) => {
  const s = Math.max(0, Math.floor(ms / 1000))
  const h = Math.floor(s / 3600)
  const mm = String(Math.floor((s % 3600) / 60)).padStart(h ? 2 : 1, '0')
  const ss = String(s % 60).padStart(2, '0')
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

const WEEK = 7 * 24 * 3600 * 1000

// Weekly usage against the share of the week elapsed, shown on the band's totals line.
async function refreshWeek($: EngineInterface) {
  try {
    const { rateLimits } = await $.session.usage()
    const week = rateLimits.find(r => r.kind.includes('seven_day'))
    if (!week?.resetsAt) return update($, weekAtom, () => null)
    const left = Math.max(0, new Date(week.resetsAt).getTime() - (await $.clock.now()))
    const elapsed = Math.min(1, Math.max(0.01, 1 - left / WEEK))
    const pace = week.percentUsed / (elapsed * 100)
    const verdict = pace > 1.15 ? 'over pace' : pace > 1 ? 'ahead of pace' : pace < 0.85 ? 'under pace' : 'on pace'
    await update($, weekAtom, () => ({ used: Math.round(week.percentUsed), elapsed: Math.round(elapsed * 100), verdict }))
  } catch {
    // No usage this tick; the next turn retries.
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await refreshWeek($)
    // Tick the clock and poll agent status while anything runs.
    // A reload drops the previous environment's timers, so this never stacks.
    // Every 5 seconds: each pane redraw restarts the avatar and dot animations, so fewer redraws means fewer snaps.
    $.clock.every(5000, async () => {
      try {
      const agents = await read($, agentsAtom)
      const now = await $.clock.now()
      const main = await read($, mainAtom)
      if (main?.turnStartedAt) await update($, nowAtom, () => now)
      if (!agents.some(a => a.status === 'running' || (a.endedAt && now - a.endedAt < 600_000))) return
      await update($, nowAtom, () => now)
      const list = await $.agent.list()
      const byId = new Map(list.map(a => [a.id, a.status]))
      await update($, agentsAtom, rows =>
        rows.map((r): AgentRow => {
          if (r.status !== 'running') return r
          const st = r.agentId ? byId.get(r.agentId) : undefined
          // Unknown to the engine: no id after 15 minutes, or an id the list has dropped. Close the row.
          if (!st) {
            const lost = r.agentId ? now - r.startedAt > 10_000 : now - r.startedAt > 900_000
            return lost ? { ...r, status: r.agentId ? 'done' : 'failed', endedAt: now } : r
          }
          if (st === 'running' || st === 'pending')
            return r.status === 'running' ? r : { ...r, status: 'running', endedAt: undefined }
          return { ...r, status: st === 'completed' ? 'done' : 'failed', endedAt: now }
        }),
      )
      } catch {
        // A failed poll skips one tick; the next second retries.
      }
    })
    return next(e)
  })

  on('agent.spawn', async ($, e, next) => {
    const now = await $.clock.now()
    // The first subagent after a quiet spell starts a fresh run.
    const run = await read($, runAtom)
    const prior = await read($, agentsAtom)
    const idle = !prior.some(a => a.status === 'running' || (a.endedAt ?? 0) > now - 120_000)
    if (!run || (idle && now - run.startedAt > 120_000)) {
      await update($, runAtom, () => ({ workflow: 'Subagents', startedAt: now, scheduled: [] }))
      await update($, agentsAtom, () => [])
      await update($, usageAtom, () => ({}))
    }
    const role = roleOf(e.subagentType, e.description)
    const row: AgentRow = {
      key: e.tool_use_id,
      description: e.description,
      type: e.subagentType,
      role,
      model: e.model ?? e.parentModel,
      status: 'running',
      startedAt: now,
    }
    await update($, agentsAtom, rows => [...rows, row].slice(-40))
    await update($, nowAtom, () => now)
    await update($, runAtom, run =>
      run ? { ...run, scheduled: run.scheduled.filter((r, i) => i !== run.scheduled.indexOf(role)) } : run,
    )
    const res = await next(e)
    if (res.deny !== undefined) {
      await update($, agentsAtom, rows => rows.map((r): AgentRow => (r.key === row.key ? { ...r, status: 'failed', endedAt: now } : r)))
    } else {
      await update($, agentsAtom, rows =>
        rows.map(r => (r.key === row.key ? { ...r, agentId: res.agentId, model: res.model } : r)),
      )
    }
    return res
  })

  // A foreground Agent call resolves when its subagent is finished.
  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    const res = await next(e)
    const out = res.result as { totalDurationMs?: number; totalTokens?: number } | undefined
    if (res.deny !== undefined || res.isError || out?.totalDurationMs !== undefined) {
      const now = await $.clock.now()
      const failed = res.deny !== undefined || !!res.isError
      await update($, agentsAtom, rows =>
        rows.map((r): AgentRow =>
          r.key === e.tool_use_id && r.status === 'running'
            ? { ...r, status: failed ? 'failed' : 'done', endedAt: now, engineTokens: out?.totalTokens }
            : r,
        ),
      )
      await update($, nowAtom, () => now)
    }
    return res
  })

    // The main chat's own row: working from turn.start to its turn.complete. Subagent runs raise no turn.start.
  on('turn.start', async ($, e, next) => {
    const now = await $.clock.now()
    await update($, mainAtom, m => ({ ...(m ?? { model: '', tokens: 0, ctx: 0, steps: 0, cost: 0, activeMs: 0 }), turnStartedAt: now }))
    await update($, nowAtom, () => now)
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (!e.agentId) await refreshWeek($)
    if (!e.agentId)
      await update($, mainAtom, m => (m ? { ...m, turnStartedAt: undefined, activeMs: m.activeMs + e.durationMs } : m))
    return next(e)
  })

  on('turn.step', async function* ($, e, next) {
    const res = yield* next(e)
    if (!res.usage) return res
    const u = res.usage
    const ctx = u.input_tokens + (u.cache_read_input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0)
    const effort = typeof e.effort === 'string' ? e.effort : undefined
    if (!e.agentId) {
      await update($, mainAtom, m => {
        const prev = m ?? { model: u.model, tokens: 0, ctx: 0, steps: 0, cost: 0, activeMs: 0 }
        return {
          ...prev,
          model: u.model,
          effort: effort ?? prev.effort,
          tokens: prev.tokens + ctx + u.output_tokens,
          ctx: ctx + u.output_tokens,
          steps: prev.steps + 1,
          cost: prev.cost + price(u.model, u),
        }
      })
      return res
    }
    const id = e.agentId
    await update($, usageAtom, all => {
      const prev = all[id] ?? { model: u.model, tokens: 0, ctx: 0, cost: 0, steps: 0 }
      return {
        ...all,
        [id]: {
          model: u.model,
          effort: effort ?? prev.effort,
          tokens: prev.tokens + ctx + u.output_tokens,
          ctx: ctx + u.output_tokens,
          steps: (prev.steps ?? 0) + 1,
          cost: prev.cost + price(u.model, u),
        },
      }
    })
    return res
  })

  // The band above the prompt: totals, one row per agent, finished agents folded into one row.
  // Whatever the plugins beneath draw (the context band) stays on top.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const below = await next(e)
    if (e.props.hasSurvey) return below
    const ui = $.ui.resolve(e)
    const { Box, Text, Button } = ui
    const Svg = e.surface === 'terminal' ? undefined : (ui as Partial<Elements['desktop']>).Svg
    const run = await read($, runAtom)
    const agents = await read($, agentsAtom)
    const usage = await read($, usageAtom)
    const now = (await read($, nowAtom)) || (await $.clock.now())
    const doneOpen = await read($, doneOpenAtom)
    const main = await read($, mainAtom)
    // Older sessions stored this as text; ignore that until the next refresh.
    const weekRaw = await read($, weekAtom)
    const week = weekRaw && typeof weekRaw === 'object' ? weekRaw : null
    const min = await read($, minAtom)
    // Narrow bands drop the model and context columns first.
    const wide = e.props.bodyColumns >= 80

    const rows = agents.map(a => ({ a, u: a.agentId ? usage[a.agentId] : undefined }))
    // Totals include the main chat: its whole session plus this run's subagents.
    const cost = (main?.cost ?? 0) + rows.reduce((s, r) => s + (r.u?.cost ?? 0), 0)
    const tokens = (main?.tokens ?? 0) + rows.reduce((s, r) => s + (r.u?.tokens ?? 0), 0)
    // Time is the longer of the main chat's working time and this run's wall clock, since subagents can outlast a turn.
    const mainMs = main ? main.activeMs + (main.turnStartedAt ? now - main.turnStartedAt : 0) : 0
    const started = run?.startedAt ?? agents[0]?.startedAt ?? now
    const running = rows.filter(r => r.a.status === 'running')
    const finished = rows.filter(r => r.a.status !== 'running').reverse()
    if (!main?.steps && !agents.length && !week) return below

    const Avatar = (p: { id: string; role: string; mood: Mood }) =>
      Svg ? (
        <Box key={`av-${p.id}`} flexShrink={0}>
          <Svg key={`svg-${p.id}-${p.mood}`} source={avatarSvg(p.role, p.mood)} alt={`${p.role} avatar`} width={50} height={41} />
        </Box>
      ) : null

    const Bar = (p: { id: string; pct: number; color: string }) => {
      const w = 6
      const fill = Math.min(w, Math.round((p.pct / 100) * w))
      return (
        <Box key={`bar-${p.id}`} flexDirection="row" flexShrink={0}>
          <Text color={p.color}>{'━'.repeat(fill)}</Text>
          <Text dimColor>{'━'.repeat(w - fill)}</Text>
        </Box>
      )
    }

    const Row = ({ a, u, time, markOverride }: { a: AgentRow; u?: AgentUsage; time?: string; markOverride?: [string, string] }) => {
      const eff = u?.effort ? EFFORT[u.effort] : undefined
      const ctx = a.engineTokens ?? u?.ctx ?? 0
      const mark = a.status === 'running' ? '…' : a.status === 'done' ? '✓' : '✗'
      const markColor = a.status === 'running' ? '#D97757' : a.status === 'done' ? '#3BA55C' : '#C0392B'
      const [shownMark, shownColor] = markOverride ?? [mark, markColor]
      return (
        <Box key={`row-${a.key}`} flexDirection="row" gap={1} alignItems="center">
          {Avatar({ id: a.key, role: a.role, mood: a.status })}
          {a.status === 'running' && !markOverride && Svg ? (
            <Box key={`dots-${a.key}`} flexShrink={0}>
              <Svg source={dotsSvg(markColor)} alt="working" width={20} height={10} />
            </Box>
          ) : (
            <Text color={shownColor} bold>{shownMark}</Text>
          )}
          <Box flexShrink={1} minWidth={0}><Text bold wrap="truncate-end">{a.description}</Text></Box>
          {wide && eff && <Text color={eff[1]}>{eff[0]}</Text>}
          {wide && <Text dimColor wrap="truncate-end">{modelName(u?.model ?? a.model)}</Text>}
          <Box flexGrow={1} />
          {wide && u && Bar({ id: a.key, pct: Math.round((u.ctx / WINDOW) * 100), color: eff?.[1] ?? '#D97757' })}
          {wide && u && <Text dimColor>{k(ctx)}</Text>}
          <Text dimColor>{time ?? clock((a.endedAt ?? now) - a.startedAt)}</Text>
          <Text dimColor>≈${(u?.cost ?? 0).toFixed(2)}</Text>
        </Box>
      )
    }

    const doneCost = finished.reduce((s, r) => s + (r.u?.cost ?? 0), 0)
    const failed = finished.filter(r => r.a.status === 'failed').length

    return (
      // The app's empty notice slot sits in "below"; keep it out of the row gap so it adds no space above Agents.
      <Box flexDirection="column">
        {below}
        <Box flexDirection="column" gap={1}>
        <Box key="totals" flexDirection="row" gap={1} alignItems="center">
          <Text bold>
            {`Agents${min && running.length ? ` · ${running.length} running` : ''}`}
          </Text>
          <Text dimColor>
            ≈${cost.toFixed(2)} · {k(tokens)} · {clock(Math.max(mainMs, agents.length ? now - started : 0))}
          </Text>
          <Box flexGrow={1} />
          {week && <Text dimColor>Usage</Text>}
          {week && (() => {
            const w = 10
            const fill = Math.min(w, Math.round((week.used / 100) * w))
            const color = ({ 'over pace': '#C0392B', 'ahead of pace': '#D99A3B', 'under pace': '#3BA55C' } as Record<string, string>)[week.verdict] ?? '#9AA0A6'
            return (
              <Box key="week-bar" flexDirection="row" flexShrink={0}>
                <Text color={color}>{'█'.repeat(fill)}</Text>
                <Text dimColor>{'░'.repeat(w - fill)}</Text>
              </Box>
            )
          })()}
          {week && <Text dimColor wrap="truncate-end">{`${week.used}% / ${week.elapsed}% Week, ${week.verdict.replace(/\b\w/g, c => c.toUpperCase())}`}</Text>}
          <Button key="min-toggle" label={min ? 'Show agents' : 'Hide'} onPress={() => update($, minAtom, v => !v)} />
        </Box>
        {!min && main && main.steps > 0 &&
          Row({
            a: {
              key: 'main-chat',
              description: 'Main agent',
              type: 'main',
              role: 'main',
              model: main.model,
              status: main.turnStartedAt ? 'running' : 'done',
              startedAt: 0,
            },
            u: main,
            time: clock(mainMs),
            markOverride: main.turnStartedAt ? undefined : ['◦', '#9AA0A6'],
          })}
        {!min && running.map(r => Row({ a: r.a, u: r.u }))}
        {!min && run && run.scheduled.length > 0 && (
          <Text key="scheduled" dimColor wrap="truncate-end">◷ Next: {run.scheduled.join(', ')}</Text>
        )}
        {!min && finished.length > 0 && (
          <Box key="done-row" flexDirection="row" gap={1} alignItems="center">
          <Text dimColor>{`${finished.length - failed} done${failed ? `, ${failed} failed` : ''} · ≈$${doneCost.toFixed(2)}`}</Text>
          <Button key="done-toggle" label={doneOpen ? 'Hide' : 'Show'} onPress={() => update($, doneOpenAtom, v => !v)} />
          </Box>
        )}
        {!min && doneOpen && finished.map(r => Row({ a: r.a, u: r.u }))}
        </Box>
      </Box>
    )
  })
}
