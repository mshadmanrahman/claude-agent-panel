export type Fill = { tokens: number; percent: number }

declare module 'claude-code' {
  interface PluginState {
    'context-band': { fill: Fill | null; snoozedAt: number }
  }
}
