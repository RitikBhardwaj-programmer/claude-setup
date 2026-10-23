import { expect, test } from 'claude-code/testing'

const usage = (tokens: number) => ({
  context: { tokens, window: 1_000_000 },
  rateLimits: [],
  changed: ['context' as const],
})

const SHOT = 'mcp__Claude_Browser__computer'

test('A: no warning at 199k, one at 201k, none again at 250k', async ($, on) => {
  const toasts: string[] = []
  on('session.measure', (_, e) => ({ changed: e.changed }))
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('fs.write', () => ({ value: undefined }))
  on('env.get', () => ({ value: 'C:/Users/test' }))

  await $.session.measure(usage(199_000))
  expect(toasts.length).toBe(0)
  await $.session.measure(usage(201_000))
  expect(toasts.length).toBe(1)
  await $.session.measure(usage(250_000))
  expect(toasts.length).toBe(1)
  await $.session.measure(usage(301_000))
  expect(toasts.length).toBe(2)
})

test('C: scale is added, an explicit scale is kept', async ($, on) => {
  const seen: Record<string, unknown>[] = []
  on('tool.call', (_, e) => {
    seen.push(e as Record<string, unknown>)
    return { result: {} }
  })

  await $.tool.call({ tool: SHOT, action: 'screenshot' })
  await $.tool.call({ tool: SHOT, action: 'zoom', region: [0, 0, 10, 10] })
  await $.tool.call({ tool: SHOT, action: 'screenshot', scale: 1 })
  await $.tool.call({ tool: SHOT, action: 'left_click', coordinate: [1, 2] })
  expect(seen[0]?.scale).toBe(0.5)
  expect(seen[1]?.scale).toBe(0.5)
  expect(seen[2]?.scale).toBe(1)
  expect(seen[3]?.scale).toBe(undefined)
})

test('C: browser_batch items get the same rule', async ($, on) => {
  let got: { actions?: { name: string; input: Record<string, unknown> }[] } = {}
  on('tool.call', (_, e) => {
    got = e as typeof got
    return { result: {} }
  })

  await $.tool.call({
    tool: 'mcp__Claude_Browser__browser_batch',
    actions: [
      { name: 'computer', input: { action: 'screenshot' } },
      { name: 'computer', input: { action: 'screenshot', scale: 0.8 } },
      { name: 'navigate', input: { url: 'x' } },
    ],
  })
  expect(got.actions?.[0]?.input.scale).toBe(0.5)
  expect(got.actions?.[1]?.input.scale).toBe(0.8)
  expect(got.actions?.[2]?.input.scale).toBe(undefined)
})

test('C: visual mode (ui-design skill) skips the scale', async ($, on) => {
  let seen: Record<string, unknown> = {}
  on('skill.prompt', (_, e) => ({ text: e.text }))
  on('tool.call', (_, e) => {
    seen = e as Record<string, unknown>
    return { result: {} }
  })

  await $.skill.prompt({ skill: 'ui-design', text: 'x' })
  await $.tool.call({ tool: SHOT, action: 'screenshot' })
  expect(seen.scale).toBe(undefined)
})

test('D: the 8th Read call nudges once per turn', async ($, on) => {
  on('tool.call', () => ({ result: {} }))
  const notes: number[] = []
  for (let i = 1; i <= 10; i += 1) {
    const ran = await $.tool.call({ tool: 'Read', file_path: `/f${i}` })
    if ('context' in ran && ran.context?.length) notes.push(i)
  }
  expect(notes).toEqual([8])
})

test('D: a subagent call is not counted', async ($, on) => {
  on('tool.call', () => ({ result: {} }))
  for (let i = 1; i <= 10; i += 1) {
    const ran = await $.tool.call({ tool: 'Read', file_path: `/f${i}`, agentId: 'a1' })
    expect('context' in ran && ran.context?.length).toBeFalsy()
  }
})

test('E: Browser tools are deferred, others are not', async ($, on) => {
  on('tool.describe', (_, e) => ({ description: e.description }))
  const browser = await $.tool.describe({
    tool: 'mcp__Claude_Browser__computer',
    description: 'd',
    provider: { plugin: 'engine', tier: 'core' },
  })
  const other = await $.tool.describe({
    tool: 'Bash',
    description: 'd',
    provider: { plugin: 'engine', tier: 'core' },
  })
  expect(browser.isDeferred).toBe(true)
  expect(other.isDeferred).toBe(undefined)
})

test('E: the switch turns deferral off', { options: { deferBrowserTools: false } }, async ($, on) => {
  on('tool.describe', (_, e) => ({ description: e.description }))
  const browser = await $.tool.describe({
    tool: 'mcp__Claude_Browser__computer',
    description: 'd',
    provider: { plugin: 'engine', tier: 'core' },
  })
  expect(browser.isDeferred).toBe(undefined)
})

const WARM = {
  plugin: 'token-saver',
  component: 'Pane',
  requestId: 'warm',
  props: {
    title: 'Warm sessions',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

const NOW = 1_800_000_000_000

// One status file per session: [file name, context tokens, minutes since the last reply, id]
const mountWarm = async ($: any, on: any, files: [string, number, number, string][], extra: object = {}) => {
  on('env.get', () => ({ value: 'C:/Users/test' }))
  on('session.id', () => ({ value: 'me' }))
  on('clock.now', () => ({ value: NOW }))
  on('fs.list', () => ({
    value: files.map(([name]) => ({ name, kind: 'file', size: 1, mtimeMs: NOW, isLink: false })),
  }))
  on('fs.read', (_: any, e: any) => {
    const f = files.find(([name]) => e.path.endsWith(name))
    const [, tokens, ageMin, id] = f!
    return {
      value: JSON.stringify({
        sessionId: id,
        cwd: 'C:/proj/claude-setup',
        tokens,
        startMs: NOW - 3_600_000,
        ...extra,
        lastResponseMs: NOW - ageMin * 60_000,
      }),
    }
  })
  return $.ui.mount({ ...WARM, surface: 'desktop' })
}

test('pane: groups split at 150k and 60k, largest first', async ($, on) => {
  const ui = await mountWarm($, on, [
    ['a.json', 149_000, 5, 'a'],
    ['b.json', 150_000, 5, 'b'],
    ['c.json', 59_000, 5, 'c'],
    ['d.json', 60_000, 5, 'd'],
  ])
  const text = async (re: RegExp) => (await ui.find({ type: 'Text', text: re }))?.text
  expect(await text(/^Hand off$/)).toBe('Hand off')
  expect(await text(/^Optional$/)).toBe('Optional')
  expect(await text(/^Let it go$/)).toBe('Let it go')
  expect(await text(/^150k context/)).toBeTruthy()
  expect(await text(/^149k context/)).toBeTruthy()
  expect(await text(/^60k context/)).toBeTruthy()
  expect(await text(/^59k context/)).toBeTruthy()
  expect(await text(/cache-write/)).toBe(undefined)
  await ui.unmount()
})

test('pane: empty groups are hidden, current session is tagged', async ($, on) => {
  const ui = await mountWarm($, on, [['me.json', 80_000, 5, 'me']])
  expect(await ui.find({ type: 'Text', text: /^Optional$/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /^Hand off$/ })).toBeFalsy()
  expect(await ui.find({ type: 'Text', text: /\[this session\]/ })).toBeTruthy()
  await ui.unmount()
})

test('pane: empty state', async ($, on) => {
  const ui = await mountWarm($, on, [])
  expect((await ui.find({ type: 'Text', text: /No session has a warm cache right now/ }))?.text).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /Updates every minute/ })).toBeTruthy()
  await ui.unmount()
})

test('pane: the session title leads the card', async ($, on) => {
  const ui = await mountWarm($, on, [['me.json', 80_000, 5, 'me']], { title: 'Build token-saver mod' })
  expect(await ui.find({ type: 'Text', text: /Build token-saver mod/ })).toBeTruthy()
  await ui.unmount()
})

test('pane: no title falls back to project and the real start time', async ($, on) => {
  const ui = await mountWarm($, on, [['me.json', 80_000, 5, 'me']])
  expect(await ui.find({ type: 'Text', text: /claude-setup · \d\d:\d\d/ })).toBeTruthy()
  await ui.unmount()
})

test('measure: the status file gets the app title and the real start time', async ($, on) => {
  const written: Record<string, string> = {}
  const dir = (name: string) => ({ name, kind: 'directory', size: 0, mtimeMs: 0, isLink: false })
  const file = (name: string, mtimeMs: number) => ({ name, kind: 'file', size: 1, mtimeMs, isLink: false })
  const base = 'C:/Users/test/AppData/Local/Claude-Data'
  const deep = `${base}/x/claude-code-sessions/acct/org`
  const p = (e: { path: string }) => e.path.replaceAll('\\', '/')
  on('env.get', (_, e) => ({ value: e.name === 'LOCALAPPDATA' ? 'C:/Users/test/AppData/Local' : 'C:/Users/test' }))
  on('session.id', () => ({ value: 'cli-1' }))
  on('session.cwd', () => ({ value: 'C:/proj/claude-setup' }))
  on('session.usage', () => ({ value: { startedAt: 1_700_000_000_000, context: {}, rateLimits: [] } }) as any)
  on('clock.now', () => ({ value: NOW }))
  on('session.measure', (_, e) => ({ changed: e.changed }))
  on('fs.list', (_, e: any) => ({
    value:
      p(e) === base ? [dir('x')]
      : p(e) === `${base}/x/claude-code-sessions` ? [dir('acct')]
      : p(e) === `${base}/x/claude-code-sessions/acct` ? [dir('org')]
      : p(e) === deep ? [file('local_other.json', 2), file('local_mine.json', 1)]
      : [],
  }) as any)
  on('fs.read', (_, e: any) => ({
    value: p(e).endsWith('local_mine.json') ? JSON.stringify({ cliSessionId: 'cli-1', title: 'Real title' })
      : p(e).endsWith('local_other.json') ? JSON.stringify({ cliSessionId: 'cli-2', title: 'Other' })
      : '',
  }))
  on('fs.write', (_, e: any) => {
    written[p(e)] = e.text
    return { value: undefined }
  })

  await $.session.measure({ context: { tokens: 90_000, window: 1_000_000 }, rateLimits: [], changed: ['context'] })
  const saved = JSON.parse(written['C:/Users/test/.claude/token-saver/sessions/cli-1.json'] ?? '{}')
  expect(saved.title).toBe('Real title')
  expect(saved.startMs).toBe(1_700_000_000_000)
})

test('pane: Hand off fills the prompt, with title and app id for another session, and sends nothing', async ($, on) => {
  const filled: string[] = []
  let sends = 0
  on('session.send', () => {
    sends += 1
    return { isDelivered: true } as any
  })
  on('prompt.fill', (_: any, e: any) => {
    filled.push(e.text)
    return { isFilled: true } as any
  })
  on('ui.toast', () => ({ value: undefined }))
  const ui = await mountWarm($, on, [['other.json', 200_000, 5, 'other'], ['me.json', 100_000, 5, 'me']], {})
  await ui.press({ key: 'handoff-other' })
  expect(filled[0]).toMatch(/^Ask session "claude-setup · \d\d:\d\d" \(other\) to run \/context-handoff and show me the handoff text\.$/)
  await ui.press({ key: 'handoff-me' })
  expect(filled[1]).toBe('/context-handoff')
  expect(sends).toBe(0)
  await ui.unmount()
})

test('pane: Hand off names the desktop id and title when the status file has them', async ($, on) => {
  const filled: string[] = []
  on('prompt.fill', (_: any, e: any) => {
    filled.push(e.text)
    return { isFilled: true } as any
  })
  on('ui.toast', () => ({ value: undefined }))
  const ui = await mountWarm($, on, [['other.json', 200_000, 5, 'other']], {
    title: 'Total tokens consumed',
    appId: 'local_6a6bc6cc-17f4-4f36-91bf-3b5050617aad',
  })
  await ui.press({ key: 'handoff-other' })
  expect(filled[0]).toContain('"Total tokens consumed" (local_6a6bc6cc-17f4-4f36-91bf-3b5050617aad)')
  await ui.unmount()
})
