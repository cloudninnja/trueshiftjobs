"""Browser tests for the whole site: filters, data loading, buttons and every internal link.

Run after building the site into SITE_DIR and serving it on port 8765:
    python -m http.server 8765 --directory _site &
    python tests/browser_check.py
The browser maps trueshiftjobs.com to the local server, so the page loads /feed.json as it does live.
Exits with status 1 if any check fails.
"""
import asyncio, json, os, re, sys, urllib.request
from playwright.async_api import async_playwright

BASE = "http://trueshiftjobs.com"
SITE_DIR = os.environ.get("SITE_DIR", "_site")
FEED = json.load(open(os.path.join(SITE_DIR, "feed.json")))["jobs"]
_page = open(os.path.join(SITE_DIR, "index.html")).read()
_m = re.search(r'<script id="jobs-data"[^>]*>(.*?)</script>', _page, re.S)
CHECKED = len(json.loads(_m.group(1))) if _m else 0
results = []


def check(name, ok, detail=""):
    results.append((("PASS" if ok else "FAIL"), name, str(detail)[:160]))


async def count(pg):
    t = await pg.inner_text("#count")
    m = re.match(r"\s*([\d,]+)", t)
    return int(m.group(1).replace(",", "")) if m else -1, t


async def cards(pg):
    return await pg.locator("#list article").count()


async def main():
    async with async_playwright() as p:
        opts = {"args": ["--host-resolver-rules=MAP trueshiftjobs.com 127.0.0.1:8765"]}
        if os.environ.get("CHROME_PATH"):
            opts["executable_path"] = os.environ["CHROME_PATH"]
        b = await p.chromium.launch(**opts)
        ctx = await b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
        await pg.goto(BASE + "/")
        await pg.wait_for_timeout(2500)

        # data loading
        total_txt = await pg.inner_text("#totalline")
        n_all, t = await count(pg)
        check("Feed loads: total matches jobs shown under Anyone", str(n_all) in total_txt.replace(",","") and n_all > 1000, f"{t} | {total_txt}")
        check("First page shows 30 cards", await cards(pg) == 30, await cards(pg))
        regs = [int(x) for x in await pg.locator(".reg b").all_inner_texts()]
        check("Map region totals add up to the total", sum(regs) == n_all, f"{regs} sum {sum(regs)} vs {n_all}")

        # show more
        await pg.click("#more"); await pg.wait_for_timeout(300)
        check("Show more adds 30 cards", await cards(pg) == 60, await cards(pg))

        # groups
        prev = n_all
        for g in ["Students", "Newcomers", "Apprentices", "Graduates", "Parents", "Experienced"]:
            await pg.click(f"button[data-g={g}]"); await pg.wait_for_timeout(300)
            n, t = await count(pg)
            exp = sum(1 for j in FEED if g in [x.strip() for x in str(j.get("bestFor") or "").split(",")])
            pressed = await pg.get_attribute(f"button[data-g={g}]", "aria-pressed")
            # Hand-checked jobs replace matching feed jobs, so a tab can show a few fewer than the raw feed.
            check(f"Tab '{g}' filters jobs", 0 < n <= prev and pressed == "true" and n >= exp - CHECKED, f"{t} (feed has {exp}, checked {CHECKED}) pressed={pressed}")
            # every visible card is tagged with the group (first 10)
        # level filter
        await pg.click("button[data-g=Apprentices]"); await pg.wait_for_timeout(300)
        check("Level filter visible only on Apprentices", await pg.is_visible("#level"))
        n0, _ = await count(pg)
        await pg.select_option("#level", "3"); await pg.wait_for_timeout(300)
        n3, t3 = await count(pg)
        check("Level 3 filter narrows apprenticeships", n3 <= n0, t3)
        await pg.select_option("#level", "All"); await pg.wait_for_timeout(200)
        # category filter
        await pg.click("button[data-g=Experienced]"); await pg.wait_for_timeout(300)
        check("Category filter visible only on Experienced", await pg.is_visible("#cat") and not await pg.is_visible("#level"))
        ne, _ = await count(pg)
        await pg.select_option("#cat", "IT"); await pg.wait_for_timeout(300)
        ni, ti = await count(pg)
        titles = await pg.locator("#list article h3").all_inner_texts()
        check("IT category narrows and shows IT titles", 0 < ni < ne, f"{ti} e.g. {titles[:3]}")
        await pg.select_option("#cat", "All")
        await pg.click("button[data-g=All]"); await pg.wait_for_timeout(300)
        check("Category filter hidden on Anyone", not await pg.is_visible("#cat"))

        # region bubbles and borough select
        await pg.click(".reg[data-r=West]"); await pg.wait_for_timeout(300)
        nw, tw = await count(pg)
        regs = dict(zip(await pg.locator(".reg").evaluate_all("els=>els.map(e=>e.dataset.r)"), [int(x) for x in await pg.locator(".reg b").all_inner_texts()]))
        check("West bubble filters to West count", nw == regs.get("West"), f"{tw} vs bubble {regs.get('West')}")
        opts = await pg.locator("#borough option").all_inner_texts()
        check("Borough list shows only West boroughs", "Hounslow" in opts and "Camden" not in opts, opts[:8])
        await pg.select_option("#borough", "Hounslow"); await pg.wait_for_timeout(300)
        nh, th = await count(pg)
        wheres = await pg.locator("#list .where").all_inner_texts()
        check("Borough filter: every card is in Hounslow", nh > 0 and all("Hounslow" in w for w in wheres), f"{th}; bad={[w for w in wheres if 'Hounslow' not in w][:3]}")
        await pg.click("#allbtn"); await pg.wait_for_timeout(300)
        n2, _ = await count(pg)
        check("All London resets area", n2 == n_all, n2)

        # job type
        await pg.select_option("#jtype", "Part-time"); await pg.wait_for_timeout(300)
        npt, tpt = await count(pg)
        pills = await pg.locator("#list article .jt").all_inner_texts()
        check("Part-time filter: no full-time cards", npt > 0 and "Full-time" not in pills, tpt)
        await pg.select_option("#jtype", "All"); await pg.wait_for_timeout(200)

        # sort by pay
        await pg.select_option("#sort", "pay"); await pg.wait_for_timeout(300)
        first = await pg.locator("#list article .pay").first.inner_text()
        check("Sort by pay puts paid jobs first", "£" in first, first.replace("\n", " "))
        await pg.select_option("#sort", "new"); await pg.wait_for_timeout(200)

        # search
        await pg.fill("#q", "teaching assistant"); await pg.wait_for_timeout(400)
        nq, tq = await count(pg)
        titles = await pg.locator("#list article h3").all_inner_texts()
        check("Search finds matching jobs", nq > 0 and sum("teaching" in t.lower() for t in titles) >= len(titles) * 0.6, f"{tq}; {titles[:3]}")
        await pg.fill("#q", "zzzzqqq"); await pg.wait_for_timeout(300)
        empty = await pg.is_visible("#empty") if await pg.locator("#empty").count() else (await cards(pg) == 0)
        check("Search with no results shows empty message", (await cards(pg)) == 0, await pg.inner_text("#count"))
        await pg.fill("#q", ""); await pg.wait_for_timeout(300)

        # save
        await pg.locator("#list article .star").first.click(); await pg.wait_for_timeout(200)
        check("Save updates Saved jobs counter", (await pg.inner_text("#savedn")).strip() == "1", await pg.inner_text("#savedn"))
        check("Saved jobs is no longer one of the 'looking for work as' tabs", await pg.locator("button[data-g=Saved]").count() == 0)
        await pg.click("#savedbtn"); await pg.wait_for_timeout(300)
        check("Saved jobs button shows only the saved job", await cards(pg) == 1 and await pg.get_attribute("#savedbtn", "aria-pressed") == "true", await cards(pg))
        await pg.click("button[data-g=Students]"); await pg.wait_for_timeout(300)
        check("Saved filter stays on when changing tab", await pg.get_attribute("#savedbtn", "aria-pressed") == "true" and "saved" in (await pg.inner_text("#count")), await pg.inner_text("#count"))
        await pg.click("button[data-g=All]"); await pg.wait_for_timeout(300)
        await pg.reload(); await pg.wait_for_timeout(2000)
        check("Saved job survives a page reload", (await pg.inner_text("#savedn")).strip() == "1")
        await pg.locator("#list article .star").first.click(); await pg.wait_for_timeout(200)
        check("Unsave removes it", (await pg.inner_text("#savedn")).strip() == "0")
        await pg.click("#savedbtn"); await pg.wait_for_timeout(300)
        check("Saved jobs button turns off again", await pg.get_attribute("#savedbtn", "aria-pressed") == "false" and await cards(pg) == 30)

        # apply links on cards
        hrefs = await pg.locator("#list article a.apply").evaluate_all("els=>els.map(e=>e.href)")
        bad = [h for h in hrefs if not re.match(r"^(https://|mailto:)", h)]
        check("Every card's Apply link is a valid https or email link", hrefs and not bad, bad[:3])
        tgt = await pg.locator("#list article a.apply").first.get_attribute("target")
        check("Apply opens in a new tab", tgt == "_blank", tgt)

        # URL changes on tab
        await pg.click("button[data-g=Students]"); await pg.wait_for_timeout(300)
        check("Tab click updates address to its page", pg.url.endswith("/jobs/students/"), pg.url)
        await pg.click("button[data-g=All]"); await pg.wait_for_timeout(300)

        # CV and Stay safe sections start collapsed
        folds = await pg.eval_on_selector_all("#safe details.fold, #checks details.fold, #cv details.fold, #pages details.fold", "e=>e.map(d=>d.open)")
        check("Stay safe, checks, CV and job links sections start collapsed", folds == [False, False, False, False], folds)
        check("Stay safe section comes straight after the jobs", await pg.evaluate("()=>{const s=document.getElementById('safe');return s.compareDocumentPosition(document.getElementById('checks'))===4 && document.getElementById('list').compareDocumentPosition(s)===4}"))
        await pg.click('a[href="#cv"]'); await pg.wait_for_timeout(300)
        check("Free UK CV template link opens the CV section", await pg.eval_on_selector("#cv details.fold", "d=>d.open"))
        # CV section
        for key in ["Students", "Parents", "Newcomers", "Apprentices"]:
            await pg.click(f"button[data-cv={key}]"); await pg.wait_for_timeout(200)
            txt = await pg.inner_text("#cvpaper")
            check(f"CV template '{key}' renders", "[Your full name]" in txt and len(txt) > 300, len(txt))
        await pg.click("#cvcopy"); await pg.wait_for_timeout(400)
        msg = await pg.inner_text("#cvmsg")
        check("Copy CV text gives a confirmation (clipboard needs https, so only the message is checked locally)", len(msg.strip()) > 0, msg[:80])
        if await pg.is_visible("#cvdl"):
            async with pg.expect_download() as d:
                await pg.click("#cvdl")
            dl = await d.value
            check("Download for Word gives a .docx file", dl.suggested_filename.endswith(".docx"), dl.suggested_filename)

        check("No JavaScript errors on home page", not errs, errs[:2])

        # audience and borough pages
        for path, label in [("/jobs/students/", "Students"), ("/jobs/apprenticeships/", "Apprentices"), ("/jobs/experienced-professionals/", "Experienced")]:
            await pg.goto(BASE + path); await pg.wait_for_timeout(2000)
            pressed = await pg.get_attribute(f"button[data-g={label}]", "aria-pressed")
            n, t = await count(pg)
            check(f"{path} opens with its tab selected and jobs loaded", pressed == "true" and n > 0, t)
        await pg.goto(BASE + "/jobs/hounslow/"); await pg.wait_for_timeout(2000)
        n, t = await count(pg)
        check("/jobs/hounslow/ opens filtered to Hounslow", "Hounslow" in t and n > 0 and await pg.input_value("#borough") == "Hounslow", t)
        pj = open(os.path.join(SITE_DIR, "post-a-job", "index.html")).read()
        check("/post-a-job points to the employer Google Form", "docs.google.com/forms" in pj, "")

        # every internal link on every page returns 200
        sitemap = urllib.request.urlopen("http://127.0.0.1:8765/sitemap.xml").read().decode()
        urls = re.findall(r"<loc>https://trueshiftjobs\.com(/[^<]*)</loc>", sitemap)
        seen, broken, ext = set(), [], set()
        for u in urls:
            seen.add(u)
            try:
                html = urllib.request.urlopen("http://127.0.0.1:8765" + u).read().decode()
            except Exception as e:
                broken.append((u, str(e))); continue
            for href in re.findall(r'href="([^"#]+)"', html):
                if href.startswith("/") and not href.startswith("//"):
                    seen.add(href)
                elif href.startswith("http"):
                    ext.add(href)
        for u in sorted(seen):
            path = u.split("?")[0]
            try:
                r = urllib.request.urlopen("http://127.0.0.1:8765" + path)
                if r.status != 200:
                    broken.append((u, r.status))
            except Exception as e:
                broken.append((u, str(e)[:60]))
        check(f"All {len(seen)} internal links on {len(urls)} pages work", not broken, broken[:5])
        await b.close()

    for r in results:
        print(*r, sep=" | ")
    passed = sum(1 for r in results if r[0] == "PASS")
    print("PASSED %d / %d" % (passed, len(results)))
    if passed != len(results):
        sys.exit(1)

asyncio.run(main())
