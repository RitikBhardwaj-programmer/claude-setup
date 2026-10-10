---
name: ui-design
description: "Design rules and a visual feedback loop for building or changing a user interface: web pages, dashboards, components, forms, and mobile app screens (React, HTML/CSS, React Native/Expo, Flutter). Use it whenever a task creates or restyles UI, when the user says 'make it look better', 'design a dashboard/page/screen', 'fix the layout', 'polish the UI', or types /ui-design. It makes Claude look at its own output (screenshot, compare, fix), use the project's real design tokens, and avoid the generic 'AI look'. Skip it for backend-only work and for one-line text or colour changes."
---

# /ui-design

Claude's UI output looks generic for a statistical reason: without constraints the model picks the most common choices in its training data (Inter font, purple gradient, centred hero with three cards). The fix is three things: **eyes** (look at the result), **taste** (explicit design rules) and **real tokens** (the project's own values and components).

## 1. Before you build

1. Find the project's design source, in this order. Use it instead of inventing values.
   - Tokens or a style guide in the project's CLAUDE.md, `design-tokens.json`, `tailwind.config.*`, CSS variables or a theme file.
   - A component library already in the repo (shadcn/ui, MUI, a `components/` folder). Reuse its components.
   - A Figma, Storybook or shadcn MCP server, if one is connected.
2. If nothing exists, write a short design plan first and show it:
   - The primary job of the screen in one sentence ("spot failing services in 5 seconds").
   - An aesthetic direction in 3–5 words and why it fits the audience.
   - 4–6 named hex colours, defined once as CSS variables (`--bg`, `--ink`, `--accent`...).
   - A type pair and a type scale; a spacing scale (for example 4, 8, 12, 16, 24, 32, 48).
   - An ASCII wireframe for each main screen.
3. If the `frontend-design` skill (official Anthropic plugin) is available, follow it for aesthetics. This skill adds the loop and the checks; it does not replace that one.

## 2. Design rules

- **Hierarchy through contrast.** Jump about 3x in size between display and body text, not 1.5x. Use weight contrast (for example 300 against 700/800), not 400 against 500.
- **One theme.** Every colour, radius, shadow and spacing value comes from a variable or token. No magic numbers (hard-coded one-off values like `margin: 13px`).
- **Avoid the AI look** unless the brief asks for it: Inter/Roboto/Arial as the only font, purple-to-blue gradients, glassmorphism, a centred hero with three identical icon cards, the same rounded card with one soft shadow everywhere, ALL-CAPS eyebrow labels on every section, "→" on every button. When you drop one default, do not fall into the next most common one.
- **Motion:** one purposeful moment (a staggered load, a state change), not many scattered effects. Respect `prefers-reduced-motion`.
- **Dashboards:** the most important number is the most visible thing. Label units. Plan empty, loading and error states for every panel. Use the `dataviz` skill for charts when it is available.
- **Accessibility (WCAG 2.1 AA):** text contrast at least 4.5:1 (3:1 for large text and UI parts), visible keyboard focus, real `<button>`/`<label>`/headings in order, alt text, no meaning by colour alone. Do not add ARIA attributes to make a checker pass; use the right native element.
- **UX writing:** active verbs on buttons ("Save changes", not "Submit"), sentence case, errors that say what happened and how to fix it, empty states that say what to do next.

### Mobile screens (React Native, Flutter, mobile web)
- Touch targets at least 44×44 pt (iOS) or 48×48 dp (Android).
- Respect safe areas (notch, home indicator, status bar).
- Support dynamic type (OS text scaling) without clipping.
- Follow the platform's conventions (Apple HIG, Material 3) for navigation and controls.

## 3. The visual loop (eyes)

Never finish a UI task without looking at it.

1. **Run it.** In the Claude desktop app, add the dev server to `.claude/launch.json` and open it with `preview_start`; the Browser pane then shows each change. Otherwise use Claude in Chrome or Playwright MCP.
2. **Look at three widths:** 1440, 768 and 375 px (mobile: 375×812). Resize first; a hidden pane reports width 0.
3. **Compare and list.** Screenshot, then compare against the mock, the screenshot the user gave, or the design plan. Write the differences as a list before fixing anything.
4. **Fix and look again** until the list is empty. If screenshots fail, check with page JavaScript: horizontal overflow (`scrollWidth > innerWidth`), overlapping elements, broken images, console errors.
5. **Mobile apps:** use the device screenshot tool you have (Expo MCP, an Android emulator, iOS simulator tools on macOS). On Windows without these, check the web build at 375×812.

## 4. Review before you say done

For a significant UI change, spawn the `design-review` agent (fresh context). Give it the URL, the brief and the files changed. Fix its Blocker and High-Priority items, and list the rest for the user.

Then report honestly:
- what you checked visually and at which widths;
- what you could not check (for example a real screen reader or a real device);
- that a human should still test with a keyboard and, for public pages, a screen reader. AI review misses many issues that expert reviewers find.
