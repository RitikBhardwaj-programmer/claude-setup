// Layout check for a report page. Paste into the browser tool (javascript_exec) after the page loads.
// Works when screenshots fail (the app window in the background stops page drawing).
// Returns: horizontal overflow, overlapping SVG labels, labels outside their SVG, text spilling
// out of SVG boxes, broken images, local (non-http) links, console-visible problems to fix.
(() => {
  const svgs = {};
  document.querySelectorAll('svg').forEach((s, i) => {
    const ts = [...s.querySelectorAll('text')].map(t => [t.textContent.trim(), t.getBoundingClientRect()]).filter(t => t[1].width > 0);
    if (ts.length < 4) return;
    const overlap = [];
    for (let a = 0; a < ts.length; a++) for (let b = a + 1; b < ts.length; b++) {
      const A = ts[a][1], B = ts[b][1];
      if (A.left < B.right - 1 && B.left < A.right - 1 && A.top < B.bottom - 1 && B.top < A.bottom - 1) overlap.push(ts[a][0] + ' | ' + ts[b][0]);
    }
    const sb = s.getBoundingClientRect();
    const outside = ts.filter(([, r]) => r.left < sb.left - 1 || r.right > sb.right + 1 || r.top < sb.top - 1 || r.bottom > sb.bottom + 1).map(t => t[0]);
    const boxes = [...s.querySelectorAll('rect.box')].map(r => r.getBoundingClientRect());
    const spill = ts.filter(([, r]) => boxes.some(B => r.left >= B.left && r.left <= B.right && r.top >= B.top && r.bottom <= B.bottom + 2 && r.right > B.right + 1)).map(t => t[0]);
    const id = (s.closest('[id]') || {}).id || ('svg' + i);
    if (overlap.length || outside.length || spill.length) svgs[id] = { overlap, outside, spill };
  });
  const de = document.documentElement;
  return {
    title: document.title,
    viewport: innerWidth,
    horizontalOverflow: innerWidth > 0 && de.scrollWidth > innerWidth + 1 ? de.scrollWidth - innerWidth : 0,
    svgProblems: svgs,
    brokenImages: [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src')),
    localLinks: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(h => !/^(https?:|#|mailto:)/.test(h)),
    headings: [...document.querySelectorAll('h2')].length,
    note: innerWidth === 0 ? 'viewport is 0: the pane is hidden; set a size with resize_window first' : 'ok'
  };
})();
