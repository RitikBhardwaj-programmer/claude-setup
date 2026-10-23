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

type Row = { id: string; label: string; tokens: number; minutesLeft: number; isMine: boolean }
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

// Which advice group a session falls in, by context size.
export const sectionOf = (tokens: number): 'Hand off' | 'Optional' | 'Let it go' =>
  tokens >= 150_000 ? 'Hand off' : tokens >= 60_000 ? 'Optional' : 'Let it go'

const SECTIONS = ['Hand off', 'Optional', 'Let it go'] as const

const clock = (ms: number) => {
  const d = new Date(ms)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

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
        label: data.title
          ? String(data.title)
          : Number(data.startMs) > 0
            ? `${baseName(String(data.cwd ?? ''))} · ${clock(Number(data.startMs))}`
            : baseName(String(data.cwd ?? '')),
        tokens,
        minutesLeft: Math.max(0, Math.ceil(CACHE_MIN - age)),
        isMine: data.sessionId === mine,
      })
    } catch {
      // A half-written or foreign file is skipped.
    }
  }
  return rows.sort((a, b) => b.tokens - a.tokens)
}

// The desktop app keeps one JSON file per session (its own id "local_<uuid>", its title, and the engine's
// id as cliSessionId; the title is what this mod reads) three folders under Claude-Data/<x>/claude-code-sessions. Undocumented, so every
// failure here only means "no title, no link".
async function findAppSession($: any, cliId: string): Promise<string | undefined> {
  const local = await $.env.get('LOCALAPPDATA')
  if (!local) return undefined
  const root = String(local).replace(/[\\/]$/, '') + '/Claude-Data'
  const dirs = async (d: string) => (await $.fs.list(d).catch(() => [])).filter((x: any) => x.kind === 'directory')
  for (const a of await dirs(root)) {
    for (const b of await dirs(`${root}/${a.name}/claude-code-sessions`)) {
      for (const c of await dirs(`${root}/${a.name}/claude-code-sessions/${b.name}`)) {
        const folder = `${root}/${a.name}/claude-code-sessions/${b.name}/${c.name}`
        const files = (await $.fs.list(folder).catch(() => []))
          .filter((f: any) => f.kind === 'file' && f.name.startsWith('local_') && f.name.endsWith('.json'))
          .sort((x: any, y: any) => y.mtimeMs - x.mtimeMs)
          .slice(0, 60)
        for (const f of files) {
          const text = await $.fs.read(`${folder}/${f.name}`).catch(() => '')
          if (text.includes(cliId)) return `${folder}/${f.name}`
        }
      }
    }
  }
  return undefined
}

const HANDOFF_ASK =
  'token-saver: the user pressed "Hand off" for this session in the /warm pane. ' +
  'Please run the context-handoff skill now and show the user the handoff text, so they can continue in a new session.'

// Own session: fill the prompt (never submits). Another session: send it a message asking for the handoff.
async function handOff($: any, r: Row): Promise<void> {
  try {
    if (r.isMine) {
      await $.prompt.fill({ text: '/context-handoff' })
      $.ui.toast('Prompt filled with /context-handoff: press Enter to run it')
      return
    }
    const sent = await $.session.send({ to: { sessionId: r.id }, text: HANDOFF_ASK })
    $.ui.toast(sent.isDelivered ? `Asked "${r.label}" to run /context-handoff` : `Not sent: ${sent.reason ?? 'unknown reason'}`)
  } catch {
    $.ui.toast('Could not send the hand-off request')
  }
}

const detail = (r: Row) => `${k(r.tokens)} context · cold in ${r.minutesLeft} min`

const rowText = (r: Row) => `${r.isMine ? '(this session) ' : ''}${r.label}: ${detail(r)}`

const NOTE =
  'token-saver: many Read/Grep/Glob calls this turn. For broad exploration, ' +
  'use the Explore subagent so the main context stays small.'

export const register: Register = (on, options) => {
  const warnAt = Number(options.warnTokens) || 200_000
  const exploreAfter = Number(options.exploreAfter) || 8
  const isShrinkOn = options.shrinkScreenshots !== false
  const isDeferOn = options.deferBrowserTools !== false

  let reads = 0
  let appSession: string | undefined
  let hookTitle = ''
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

  // The title the engine reports on a prompt (may be empty before the session is named).
  on('classic.UserPromptSubmit', async ($, e, next) => {
    if (typeof e.session_title === 'string' && e.session_title) hookTitle = e.session_title
    return next(e)
  }).catch(($, e, next) => next(e))

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
        const file = `${dir}/${sessionId}.json`
        const now = await $.clock.now()
        const { startedAt } = await $.session.usage()
        let title = hookTitle
        try {
          appSession ??= await findAppSession($, sessionId)
          if (appSession) {
            const meta = JSON.parse(await $.fs.read(appSession))
            if (typeof meta.title === 'string' && meta.title) title = meta.title
          }
        } catch {
          appSession = undefined
        }
        await $.fs.write(
          file,
          JSON.stringify({
            sessionId,
            cwd: await $.session.cwd(),
            tokens,
            title,
            startMs: startedAt,
            lastResponseMs: now,
          }),
        )
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
    const { Box, Button, Text } = $.ui.resolve(e)
    const rows = await loadRows($)
    return (
      <Box flexDirection="column">
        <Text bold>Before a break</Text>
        <Text dimColor>Cache expires about 1 h after the last reply (estimate, not read from the server).</Text>
        {rows.length === 0 && (
          <Box marginTop={1}>
            <Text>No session has a warm cache right now.</Text>
          </Box>
        )}
        {SECTIONS.map(section => {
          const group = rows.filter(r => sectionOf(r.tokens) === section)
          if (group.length === 0) return null
          return (
            <Box flexDirection="column" marginTop={1}>
              <Text bold color="warning">{section}</Text>
              {group.map(r => (
                <Box flexDirection="row" justifyContent="space-between" marginTop={1} paddingLeft={1}>
                  <Box flexDirection="column">
                    <Text bold>
                      {r.label}
                      {r.isMine && <Text dimColor> [this session]</Text>}
                    </Text>
                    <Text dimColor>
                      {k(r.tokens)} context · <Text dimColor={r.minutesLeft >= 10} color={r.minutesLeft < 10 ? 'warning' : undefined}>cold in {r.minutesLeft} min</Text>
                    </Text>
                  </Box>
                  <Button key={`handoff-${r.id}`} label="Hand off" onPress={() => handOff($, r)} />
                </Box>
              ))}
            </Box>
          )
        })}
        <Box marginTop={1}>
          <Text dimColor>Updates every minute</Text>
        </Box>
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
