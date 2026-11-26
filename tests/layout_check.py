"""Layout and accessibility tests for key pages at 8 screen sizes.

Fails on: sideways scrolling, cut-off text, overlapping controls, page errors,
the site font not loading, and any accessibility problem found by axe-core
(WCAG 2.1 A and AA plus best practice, checked at phone and laptop sizes).
Small tap targets and decorative items past the edge are reported as warnings.

Run after building the site into _site and serving it on port 8765:
    npm install --no-save axe-core@4
    python tests/layout_check.py
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

AXE = open(os.environ.get("AXE_PATH", "node_modules/axe-core/axe.min.js")).read()
SHOTS = os.environ.get("SHOTS", "")
BASE = "http://trueshiftjobs.com"
SIZES = [("phone-s", 360, 740, True), ("phone", 390, 844, True), ("tablet", 768, 1024, True),
         ("laptop", 1280, 800, False), ("desktop", 1440, 900, False), ("fhd", 1920, 1080, False),
         ("zoom67", 2880, 1620, False), ("zoom50", 3840, 2160, False)]
PAGES = [("home", "/"), ("students", "/jobs/students/"), ("experienced", "/jobs/experienced-professionals/"),
         ("hounslow", "/jobs/hounslow/"), ("about", "/about/"), ("privacy", "/privacy/"),
         ("advertise", "/advertise/"), ("unsubscribe", "/unsubscribe/")]
only = sys.argv[1:]  # optional filters

CHECKS = r"""
() => {
  const W = document.documentElement.clientWidth, out = {};
  out.overflowX = document.documentElement.scrollWidth - W;
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const inScroller = e => !!e.closest('.chips');
  out.offRight = [...document.querySelectorAll('body *')].filter(e => vis(e) && !inScroller(e) && e.getBoundingClientRect().right > W + 1)
    .slice(0, 6).map(e => e.tagName + '.' + (typeof e.className === 'string' ? e.className : '') + ' R' + Math.round(e.getBoundingClientRect().right));
  out.clippedText = [...document.querySelectorAll('h1,h2,h3,p,a,button,label,select,span,li,small,b')].filter(e => vis(e) && !inScroller(e) &&
     (e.scrollWidth > e.clientWidth + 2) && ['hidden','clip'].includes(getComputedStyle(e).overflowX) )
    .slice(0, 6).map(e => e.tagName + ':' + (e.innerText || e.value || '').slice(0, 40));
  // small tap targets (mobile)
  out.smallTargets = [...document.querySelectorAll('a,button,select,input')].filter(e => vis(e)).filter(e => {
      const r = e.getBoundingClientRect(); return (r.height < 24 || r.width < 24) && !e.closest('p,li,td,.t-note,.stamp');
    }).slice(0, 8).map(e => (e.innerText || e.getAttribute('aria-label') || e.tagName).trim().slice(0, 30) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height));
  // overlapping siblings in key containers
  const ov = [];
  for (const sel of ['.bar', '.chips', '.regions', '.stypes', '.countbtns', '.t-head', '.t-meta', '.t-foot', '.hero-meta', 'header .meta', '.pagelinks']) {
    document.querySelectorAll(sel).forEach(c => {
      const kids = [...c.children].filter(vis).map(k => [k, k.getBoundingClientRect()]);
      for (let i = 0; i < kids.length; i++) for (let j = i + 1; j < kids.length; j++) {
        const a = kids[i][1], b = kids[j][1];
        const x = Math.min(a.right, b.right) - Math.max(a.left, b.left), y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (x > 2 && y > 2) ov.push(sel + ': ' + (kids[i][0].innerText || kids[i][0].tagName).slice(0, 20) + ' / ' + (kids[j][0].innerText || kids[j][0].tagName).slice(0, 20));
      }
    });
  }
  out.overlaps = ov.slice(0, 6);
  out.fontOK = document.fonts.check('16px "Hanken Grotesk"');
  return out;
}
"""

async def main():
    async with async_playwright() as p:
        opts = {"args": ["--host-resolver-rules=MAP trueshiftjobs.com 127.0.0.1:8765"]}
        if os.environ.get("CHROME_PATH"):
            opts["executable_path"] = os.environ["CHROME_PATH"]
        b = await p.chromium.launch(**opts)
        report = {}
        for name, path in PAGES:
            if only and name not in only:
                continue
            for sz, w, h, mob in SIZES:
                ctx = await b.new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob)
                pg = await ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
                await pg.goto(BASE + path)
                await pg.wait_for_timeout(1800)
                r = await pg.evaluate(CHECKS)
                r["jsErrors"] = errs
                if sz in ("phone", "laptop"):
                    await pg.add_script_tag(content=AXE)
                    ax = await pg.evaluate("async () => { const r = await axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21aa','best-practice']}); return r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length, ex: v.nodes.slice(0,2).map(n => n.target.join(' ') + ' :: ' + (n.failureSummary||'').split('\\n')[1]) })) }")
                    r["axe"] = ax
                if SHOTS:
                    os.makedirs(SHOTS, exist_ok=True)
                    await pg.screenshot(path=f"{SHOTS}/{name}-{sz}.png", full_page=False)
                report[f"{name}@{sz}"] = r
                await ctx.close()
        await b.close()
        fails, warns = [], []
        for k, r in report.items():
            if r.get("overflowX", 0) > 1:
                fails.append(f"{k}: page scrolls sideways by {r['overflowX']}px")
            for x, label in (("clippedText", "text cut off"), ("overlaps", "controls overlap"), ("jsErrors", "page error")):
                if r.get(x):
                    fails.append(f"{k}: {label}: {r[x][:3]}")
            if not r.get("fontOK"):
                fails.append(f"{k}: site font did not load")
            for v in r.get("axe", []):
                fails.append(f"{k}: accessibility ({v['impact']}) {v['id']} x{v['n']}: {v['ex'][:1]}")
            for x, label in (("smallTargets", "small tap targets"), ("offRight", "past the right edge")):
                if r.get(x):
                    warns.append(f"{k}: {label}: {r[x][:3]}")
        for w in warns:
            print("WARN |", w[:300])
        for f in fails:
            print("FAIL |", f[:300])
        print("LAYOUT %d pages x %d sizes checked: %d failures, %d warnings" % (len(PAGES), len(SIZES), len(fails), len(warns)))
        if fails:
            sys.exit(1)

asyncio.run(main())
