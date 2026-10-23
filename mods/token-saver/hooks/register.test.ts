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
const mountWarm = async ($: any, on: any, files: [string, number, number, string][]) => {
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
