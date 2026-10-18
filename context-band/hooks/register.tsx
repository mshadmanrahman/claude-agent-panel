import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Fill } from '../types'

// Show the band once the context window is this full, in percent.
const WARN = 60

const fill = atom({ plugin: 'context-band', key: 'fill' } as const, null)
const snoozedAt = atom({ plugin: 'context-band', key: 'snoozedAt' } as const, 0)

const refresh = async ($: EngineInterface) => {
  const { context } = await $.session.usage()
  const tokens = context.tokens ?? 0
  const next: Fill = { tokens, percent: context.percent ?? (tokens / context.window) * 100 }
  await update($, fill, () => next)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => { await refresh($); return next(e) })
  on('turn.complete', async ($, e, next) => { await refresh($); return next(e) })
  on('session.compact', async ($, e, next) => { const r = await next(e); await refresh($); return r })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const now = await read($, fill)
    const snooze = await read($, snoozedAt)
    if (e.props.hasSurvey || now === null || now.percent < WARN || now.tokens < snooze + 50_000) {
      return next(e)
    }
    const { Box, Button, Text } = $.ui.resolve(e)
    const k = Math.round(now.tokens / 1000)

    // Stack above whatever the bands beneath draw (the agent band), never replace it.
    const below = await next(e)
    return (
      <Box flexDirection="column" gap={2}>
      <Box key="ctx-band">
        <Text bold>Context {Math.round(now.percent)}%</Text>
        <Text> ({k}K tokens){' '}</Text>
        <Button
          key="compact"
          label="Compact now"
          onPress={async () => {
            let why = ''
            try {
              const r = await $.session.compact()
              if (r.skip === undefined) return refresh($)
              why = r.skip
            } catch (err) {
              why = String(err)
            }
            const { isFilled } = await $.prompt.fill({ text: '/compact' })
            $.ui.toast(isFilled ? `Compact did not start (${why}). /compact is in the box: press Enter` : `Compact did not start (${why}). Type /compact`)
          }}
        />
        <Text> </Text>
        <Button key="snooze" label="Later" onPress={() => update($, snoozedAt, () => now.tokens)} />
      </Box>
      {below}
      </Box>
    )
  })
}
