import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

const NAME = 'token-saver'
const WARM_PANE = 'warm'
const STEP = 100_000
const CACHE_MIN = 60
const MAX_AGE_MS = 24 * 60 * 60 * 1000
const BROWSER_PREFIX = 'mcp__Claude_Browser__'
const VISUAL_SKILLS = ['ui-design', 'frontend-design:frontend-design', 'artifact-design', 'dataviz']

const warnLevel = atom({ plugin: 'token-saver', key: 'warnLevel' } as const, 0)
const hiddenLevel = atom({ plugin: 'token-saver', key: 'hiddenLevel' } as const, 0)
const isVisual = atom({ plugin: 'token-saver', key: 'isVisual' } as const, false)
const tick = atom({ plugin: 'token-saver', key: 'tick' } as const, 0)

type Row = { id: string; project: string; tokens: number; minutesLeft: number; cost: number; isMine: boolean }
type Item = { name?: string; input?: Record<string, unknown> }

// 200k, 300k, 400k ...; 0 below the first threshold.
export const levelFor = (tokens: number, first: number): number =>
  tokens < first ? 0 : first + Math.floor((tokens - first) / STEP) * STEP

// Adds scale 0.5 to a screenshot or zoom that sets none; an explicit scale stays.
export const withScale = (input: Record<string, unknown>): Record<string, unknown> =>
  (input.action === 'screenshot' || input.action === 'zoom') && input.scale === undefined
    ? { ...input, scale: 0.5 }
    : input

const k = (n: number) => `${Math.round(n / 1000)}k`

const baseName = (path: string) => path.split(/[\\/]/).filter(Boolean).pop() ?? path

async function sessionsDir($: any): Promise<string | undefined> {
  const home = (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME'))
  return home ? `${String(home).replace(/[\\/]$/, '')}/.claude/token-saver/sessions` : undefined
}

async function loadRows($: any): Promise<Row[]> {
  const dir = await sessionsDir($)
  if (!dir) return []
  const now = await $.clock.now()
  const mine = await $.session.id()
  const entries = await $.fs.list(dir).catch(() => [])
  const rows: Row[] = []
  for (const entry of entries) {
    if (entry.kind !== 'file' || !entry.name.endsWith('.json')) continue
    if (now - entry.mtimeMs > MAX_AGE_MS) continue
    try {
      const data = JSON.parse(await $.fs.read(`${dir}/${entry.name}`))
      const age = (now - Number(data.lastResponseMs)) / 60000
      if (!(age >= 0 && age < CACHE_MIN)) continue
      const tokens = Number(data.tokens) || 0
      rows.push({
        id: entry.name.replace(/\.json$/, ''),
        project: baseName(String(data.cwd ?? '')),
        tokens,
        minutesLeft: Math.max(0, Math.ceil(CACHE_MIN - age)),
        cost: tokens * 2,
        isMine: data.sessionId === mine,
      })
    } catch {
      // A half-written or foreign file is skipped.
    }
  }
  return rows.sort((a, b) => b.cost - a.cost)
}

const rowText = (r: Row) =>
  `${r.isMine ? '* ' : ''}${r.project}: context ${k(r.tokens)}, cache ends in ~${r.minutesLeft} min, ` +
  `a cold restart costs ~${k(r.cost)} cache-write units`

const NOTE =
  'token-saver: many Read/Grep/Glob calls this turn. For broad exploration, ' +
  'use the Explore subagent so the main context stays small.'

export const register: Register = (on, options) => {
  const warnAt = Number(options.warnTokens) || 200_000
  const exploreAfter = Number(options.exploreAfter) || 8
  const isShrinkOn = options.shrinkScreenshots !== false
  const isDeferOn = options.deferBrowserTools !== false

  let reads = 0
  let hasNudged = false

  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'warm', description: 'Show sessions whose prompt cache is probably still warm' })
    await $.command.register({
      name: 'token-saver',
      description: 'token-saver settings: /token-saver visual on|off',
    })
    $.clock.every(60_000, async () => {
      try {
        const now = await $.clock.now()
        await update($, tick, () => now)
      } catch {
        // A failed refresh only leaves the pane one minute stale.
      }
    })
    return next(e)
  })

  // ---- A + B: handoff warning, and the per-session file the /warm pane reads ----
  on('session.measure', async ($, e, next) => {
    try {
      const tokens = e.context.tokens ?? 0
      const level = levelFor(tokens, warnAt)
      const warned = await read($, warnLevel)
      if (level > warned) {
        await update($, warnLevel, () => level)
        $.ui.toast(`Context ${k(tokens)}: hand off at the next breakpoint`)
      } else if (level < warned) {
        await update($, warnLevel, () => level)
        await update($, hiddenLevel, () => 0)
      }
      const dir = await sessionsDir($)
      if (dir && e.changed.includes('context')) {
        const sessionId = await $.session.id()
        await $.fs.write(
          `${dir}/${sessionId}.json`,
          JSON.stringify({ sessionId, cwd: await $.session.cwd(), tokens, lastResponseMs: await $.clock.now() }),
        )
        const now = await $.clock.now()
        await update($, tick, () => now)
      }
    } catch {
      // Never let a bug here touch the session.
    }
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const level = await read($, warnLevel)
    if (level === 0 || level === (await read($, hiddenLevel))) return next(e)
    const { Box, Button, Text } = $.ui.resolve(e)
    return (
      <Box>
        <Text>Context {k(level)}+: hand off at the next breakpoint </Text>
        <Button key="handoff" label="Fill /context-handoff" onPress={() => $.prompt.fill({ text: '/context-handoff' })} />
        <Button key="hide" label="Hide" onPress={() => update($, hiddenLevel, () => level)} />
      </Box>
    )
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'warm' }, async $ => {
    const rows = await loadRows($)
    const opened = await $.ui.open({ id: WARM_PANE, title: 'Warm sessions' }).catch(() => ({ isPlaced: false }))
    if (opened.isPlaced) return { text: 'Warm sessions pane opened (estimate from the 1-hour cache TTL).' }
    return {
      text: rows.length
        ? `Warm sessions (estimate, 1-hour cache TTL):\n${rows.map(rowText).join('\n')}`
        : 'No session wrote a response in the last 60 minutes.',
    }
  })

  on('ui.render', { component: 'Pane', requestId: WARM_PANE }, async ($, e) => {
    await read($, tick)
    const { Box, Text } = $.ui.resolve(e)
    const rows = await loadRows($)
    return (
      <Box flexDirection="column">
        <Text dimColor>Estimate: the cache state is inferred from a 1-hour TTL, not read from the server.</Text>
        {rows.length === 0 && <Text>No session wrote a response in the last 60 minutes.</Text>}
        {rows.map(r => (
          <Text>{rowText(r)}</Text>
        ))}
      </Box>
    )
  }).catch(($, e, next) => next(e))

  // ---- C: screenshot auto-scale ----
  on('skill.prompt', async ($, e, next) => {
    const full = e.pluginName ? `${e.pluginName}:${e.skill}` : e.skill
    if (VISUAL_SKILLS.includes(e.skill) || VISUAL_SKILLS.includes(full) || e.skill === 'frontend-design') await update($, isVisual, () => true)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('agent.spawn', async ($, e, next) => {
    if (e.subagentType === 'design-review') await update($, isVisual, () => true)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'token-saver' }, async ($, e) => {
    const [what, value] = e.args.trim().split(/\s+/)
    if (what !== 'visual' || (value !== 'on' && value !== 'off')) {
      return { text: 'Use /token-saver visual on|off. "on" keeps full-size screenshots.' }
    }
    await update($, isVisual, () => value === 'on')
    return { text: `Visual mode ${value}: screenshots ${value === 'on' ? 'keep full size' : 'shrink to scale 0.5'}.` }
  })

  on('tool.call', { tool: 'mcp__Claude_Browser__computer' }, async ($, e, next) => {
    if (!isShrinkOn || (await read($, isVisual))) return next(e)
    return next(withScale(e as Record<string, unknown>) as typeof e)
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'mcp__Claude_Browser__browser_batch' }, async ($, e, next) => {
    if (!isShrinkOn || (await read($, isVisual))) return next(e)
    const actions = (e as { actions?: Item[] }).actions
    if (!Array.isArray(actions)) return next(e)
    const shrunk = actions.map(a =>
      a && a.name === 'computer' && a.input ? { ...a, input: withScale(a.input) } : a,
    )
    return next({ ...e, actions: shrunk } as typeof e)
  }).catch(($, e, next) => next(e))

  // ---- D: Explore nudge (main agent only) ----
  on('prompt.submit', async ($, e, next) => {
    reads = 0
    hasNudged = false
    return next(e)
  }).catch(($, e, next) => next(e))

  for (const tool of ['Read', 'Grep', 'Glob'] as const) {
    on('tool.call', { tool: tool as 'Read' }, async ($, e, next) => {
      if ((e as { agentId?: string }).agentId) return next(e)
      reads += 1
      const ran = await next(e)
      if (reads < exploreAfter || hasNudged || ran.deny !== undefined) return ran
      hasNudged = true
      return { ...ran, context: [...(ran.context ?? []), NOTE] }
    }).catch(($, e, next) => next(e))
  }

  // ---- E: defer the Browser-pane tools ----
  on('tool.describe', async ($, e, next) => {
    const ran = await next(e)
    return isDeferOn && e.tool.startsWith(BROWSER_PREFIX) ? { ...ran, isDeferred: true } : ran
  }).catch(($, e, next) => next(e))
}
