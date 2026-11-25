#!/usr/bin/env python3
"""Build one indexable page per audience from index.html, plus sitemap.xml and robots.txt.

Each page is a copy of the main page with its own <title>, description, canonical
link, heading, a short guide written for that audience, and the matching tab
selected. Run from the repository root: python scripts/build_pages.py
"""
import datetime as dt
import html
import json
import pathlib
import re
import shutil
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fetch_feed import BOROUGH_REGION, UK_POSTCODE  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://trueshiftjobs.com"

PAGES = [
    {
        "slug": "students", "group": "Students",
        "title": "Part-time Jobs for Students in London | TrueShift Jobs",
        "description": "Real part-time, weekend and evening jobs for students in London, updated every morning and sorted by borough. No fake adverts, no duplicates.",
        "h1": "Part-time jobs for students in London",
        "lead": "Weekend, evening and holiday jobs that fit around your studies, from real London employers.",
        "heading": "Finding a part-time job as a student in London",
        "body": [
            "Most students in London work part-time in retail, hospitality, tutoring, events or campus jobs. The jobs on this page are picked because the hours suit study: weekends, evenings, short shifts and holiday work. Every job was posted in the last 30 days and is still open, and if the same job appears on several job sites we show it once.",
            "Use the map to pick your part of London, then choose your borough, so you only see jobs you can easily reach from home or university. Switch the job type filter to part-time if you only want shorter hours.",
            "<b>Know your pay.</b> From April 2026 the National Minimum Wage is £12.71 an hour if you are 21 or over, £10.85 if you are 18 to 20 and £8.00 if you are under 18. Many London employers pay the London Living Wage of £14.80 an hour or more. We leave out adverts that pay less than the legal minimum.",
            "<b>International students:</b> if you are on a Student visa, check how many hours you are allowed to work. Students on degree-level courses can usually work up to 20 hours a week during term time, but your own visa conditions are what count, so check your eVisa before you accept a job.",
            "Never pay a fee to get a job, and be careful with adverts that ask you to message on WhatsApp or Telegram. Use our free student CV template to apply.",
        ],
    },
    {
        "slug": "new-to-the-uk", "group": "Newcomers",
        "title": "Jobs for People New to the UK in London | TrueShift Jobs",
        "description": "Real jobs in London for newcomers to the UK, including roles that need no UK experience. Updated every morning, sorted by borough, with right-to-work tips.",
        "h1": "Jobs for people new to the UK in London",
        "lead": "Real jobs that welcome people starting out in the UK, including roles with training and no UK experience needed.",
        "heading": "Getting your first job in London when you are new to the UK",
        "body": [
            "Starting work in a new country is hard when most adverts ask for UK experience. The jobs on this page are entry-level roles where employers offer training or value languages and transferable skills: warehouse, care, cleaning, hospitality, retail, customer service and admin. Every job is real, still open and posted in the last 30 days.",
            "<b>Prove your right to work.</b> Every UK employer must check that you are allowed to work. Most people do this with a share code from the GOV.UK \"Prove your right to work to an employer\" service, which you give to the employer with your date of birth. Never pay anyone to do this for you: it is free.",
            "<b>Get a National Insurance number.</b> You can apply on GOV.UK. You can usually start work before it arrives, as long as you can prove your right to work.",
            "<b>Use a UK-style CV.</b> UK CVs are usually two pages, start with a short personal statement and list your most recent job first. Most people leave out a photo, date of birth and marital status. Our free CV template for people new to the UK follows this layout.",
            "<b>Watch out for scams.</b> A real employer will never ask you to pay for a job, a uniform, training or a visa. Search by borough to find jobs near where you live.",
        ],
    },
    {
        "slug": "apprenticeships", "group": "Apprentices",
        "title": "Apprenticeships in London for School Leavers | TrueShift Jobs",
        "description": "Paid apprenticeships in London from Level 2 to degree level, for school leavers and A-level students. Updated every morning, listed until they close.",
        "h1": "Apprenticeships in London",
        "lead": "Paid jobs with training towards a qualification, from Level 2 up to degree apprenticeships.",
        "heading": "How apprenticeships work",
        "body": [
            "An apprenticeship is a real, paid job where you also train towards a recognised qualification. You can start one at 16 or over, and they cover almost every field: business, IT and digital, engineering, construction, healthcare, finance, hospitality and more.",
            "<b>Levels.</b> Level 2 is the same level as GCSEs and Level 3 is the same as A levels. Levels 4 and 5 are higher apprenticeships, and Levels 6 and 7 are degree apprenticeships, where you can earn a full degree while you work. Use the level filter on this page to see the ones that match your qualifications, or the ones you expect to get this summer.",
            "<b>Pay.</b> Apprentices must be paid at least £8.00 an hour if they are under 19 or in the first year of their apprenticeship. After that, the National Minimum Wage for your age applies. Many London employers pay more, and some degree apprenticeships pay over £20,000 a year.",
            "<b>You never pay for the training.</b> The employer and government cover it. Walk away from any \"apprenticeship\" that asks you for a course fee.",
            "Many apprenticeships start in September and close months before, so unlike other jobs on TrueShift we keep them listed until their closing date. Use our free school leaver CV template to apply.",
        ],
    },
    {
        "slug": "graduates", "group": "Graduates",
        "title": "Graduate Jobs and Schemes in London | TrueShift Jobs",
        "description": "Graduate schemes, internships, trainee and junior jobs in London, updated every morning and sorted by borough. Real, still-open adverts with no duplicates.",
        "h1": "Graduate and junior jobs in London",
        "lead": "Graduate schemes, internships, trainee and junior roles, from real London employers.",
        "heading": "Finding your first graduate job in London",
        "body": [
            "London has more graduate jobs than anywhere else in the UK, but they are spread across hundreds of sites. This page brings together graduate schemes, internships, placements, trainee roles and junior jobs from the main job sites, shows each job once and keeps only adverts that are still open.",
            "<b>Graduate schemes</b> usually last one to two years and rotate you through different teams, often with training or a professional qualification. Many recruit a year ahead and close early, so check the closing date on each advert.",
            "<b>Junior and trainee roles</b> are a quicker route in. You start in one team straight away, often with on-the-job training. They are common in finance, marketing, recruitment, IT, property and engineering. Starting salaries in London vary widely by sector, and many adverts show them, so you can compare before you apply.",
            "<b>Search by subject.</b> Type your degree subject or the kind of job you want, such as engineering, marketing or data, then pick your part of London on the map.",
            "<b>Make your CV work for you.</b> Put your degree, final-year project and any part-time or volunteering work near the top, and show what you did with numbers where you can. If you are an international graduate, check what your visa lets you do before you apply.",
        ],
    },
    {
        "slug": "parents-returning-to-work", "group": "Parents",
        "title": "Jobs for Parents Returning to Work in London | TrueShift Jobs",
        "description": "Part-time, school-hours and flexible jobs in London for parents returning to work. Real, still-open adverts, updated every morning and sorted by borough.",
        "h1": "Jobs for parents returning to work in London",
        "lead": "School-hours, term-time, part-time and flexible jobs from real London employers.",
        "heading": "Going back to work after time with your children",
        "body": [
            "Returning to work after a career break is a big step, and the right hours matter as much as the job itself. This page shows jobs that suit family life: school hours, term-time only, part-time, job shares and flexible working. Every advert was posted in the last 30 days and is still open.",
            "<b>Ask for flexible working.</b> In Great Britain you have the right to ask for flexible working from your first day in a new job, such as different hours, compressed hours or working from home some days. The employer must consider your request properly.",
            "<b>Help with childcare costs.</b> With Tax-Free Childcare, the government adds £2 for every £8 you pay towards childcare, up to £2,000 a year for each child. Working parents in England may also get up to 30 hours a week of funded childcare for children from nine months old, during term time. Check what you can get on GOV.UK.",
            "<b>Explain your career break with confidence.</b> On your CV, list the break in a single line and focus on the skills you used, such as organising, budgeting and volunteering. Our free CV template for parents returning to work shows how.",
            "Choose your borough to find work close to home and school, and use the part-time filter if you want shorter hours.",
        ],
    },
    {
        "slug": "experienced-professionals", "group": "Experienced",
        "title": "Professional and Experienced Jobs in London | TrueShift Jobs",
        "description": "Experienced and professional jobs in London, from IT and finance to engineering, education and healthcare. Updated every morning, with no duplicates.",
        "h1": "Find Professional & Skilled Jobs Across London",
        "lead": "Skilled, professional and senior roles across London, filtered by category and borough.",
        "heading": "Professional jobs across London, without the noise",
        "body": [
            "Job sites often show the same role many times through different agencies, alongside old adverts that have already been filled. This page brings together professional and senior roles from the main UK job sites and official public-sector feeds, shows each job once and keeps only adverts posted in the last 30 days.",
            "<b>Filter by category.</b> Choose IT and digital, finance and accounting, engineering and construction, education, health and care, legal, HR, sales and marketing, or the public and charity sector, then narrow it down to your part of London.",
            "<b>Check the salary.</b> Where an advert gives a salary we show it on the card. School and public-sector roles often show a full-time equivalent salary, which is reduced pro rata for part-time hours.",
            "<b>Apply direct where you can.</b> Each card links to the original advert. Where the employer has posted the job itself, we link to the employer's own page or email.",
            "<b>Spot agency duplicates.</b> When several agencies advertise the same role, we keep the earliest advert and note the other sites it appeared on, so you do not apply to the same job twice or end up with two agencies putting you forward.",
            "New roles are added every morning, and older adverts drop off after 30 days. Save the jobs you like with the Save button and come back to them later, or use the search box to look for a specific job title, skill or employer.",
        ],
    },
]


def esc(s):
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- job lists in the HTML

def load_jobs():
    f = ROOT / "feed.json"
    try:
        jobs = json.loads(f.read_text()).get("jobs", [])
    except (OSError, ValueError):
        return []
    return sorted(jobs, key=lambda j: j.get("posted") or "", reverse=True)


def groups(j):
    return [g.strip() for g in str(j.get("bestFor") or "").split(",") if g.strip()]


def pay_text(j):
    if j.get("pay"):
        return j["pay"] + " an hour"
    return j.get("salary") or ""


def nice_date(d):
    try:
        x = dt.date.fromisoformat(d)
        return x.strftime("%-d %b %Y")
    except (TypeError, ValueError):
        return ""


def jobs_html(jobs, limit=40):
    out = []
    for j in jobs[:limit]:
        href = j.get("page") or j.get("link") or ""
        rel = "" if j.get("page") else ' rel="nofollow noopener"'
        title = esc(j.get("title", ""))
        title = '<a href="%s"%s style="color:inherit">%s</a>' % (esc(href), rel, title) if href else title
        where = ", ".join(x for x in (j.get("area"), j.get("borough")) if x)
        src = {"Employer": "Posted by employer", "Adzuna": "Jobs by Adzuna"}.get(j.get("source"), "Live advert")
        out.append(
            '<article class="ticket"><div class="t-body"><div class="t-head"><h3 class="t-title">%s</h3>'
            '<div class="pay"><small>%s</small></div></div><p class="t-emp">%s</p><p class="where">%s</p>'
            '<p class="t-note">%s%s. Posted %s.</p></div></article>'
            % (title, esc(pay_text(j)), esc(j.get("employer", "")), esc(where),
               esc(j.get("jobType") or ""), (" · " if j.get("jobType") else "") + src, nice_date(j.get("posted"))))
    return "".join(out)


def put_jobs(page, jobs):
    return re.sub(r"<!--JOBS-->.*?<!--/JOBS-->", lambda m: "<!--JOBS-->" + jobs_html(jobs) + "<!--/JOBS-->",
                  page, count=1, flags=re.S)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ---------------------------------------------------------------- borough pages

def categories(base):
    m = re.search(r"const CATS=(\[.*?\]);\n", base)
    cats = json.loads(m.group(1)) if m else []
    return [(c[0], c[1], re.compile(c[2], re.I)) for c in cats]


def category_of(j, cats):
    for key, label, rx in cats:
        if rx.search(j.get("title", "")):
            return label
    return None


def borough_page(base, borough, jobs, cats, all_jobs_count):
    region = BOROUGH_REGION[borough]
    here = [j for j in jobs if j.get("borough") == borough]
    n = len(here)
    pt = sum(1 for j in here if j.get("jobType") == "Part-time")
    ft = sum(1 for j in here if j.get("jobType") == "Full-time")
    ap = sum(1 for j in here if j.get("apprenticeship"))
    gr = sum(1 for j in here if "Graduates" in groups(j))
    top_cats = [c for c, _ in Counter(filter(None, (category_of(j, cats) for j in here))).most_common(3)]
    top_emps = [e for e, _ in Counter(j.get("employer") for j in here if j.get("employer")).most_common(3)]
    areas = [a for a, _ in Counter(j.get("area") for j in here if j.get("area")).most_common(4)]
    near = sorted(b for b, r in BOROUGH_REGION.items() if r == region and b != borough)
    p = {
        "slug": slug(borough), "group": None,
        "title": "Jobs in %s, London: Part-time and Full-time | TrueShift Jobs" % borough,
        "description": "%d real, still-open jobs in %s, London, updated every morning. Part-time, full-time, apprenticeships and graduate roles, with no duplicates or scams." % (n, borough),
        "h1": "Jobs in %s, London" % borough,
        "lead": "%d real, still-open jobs in %s, updated every morning, from part-time shifts to professional roles." % (n, borough),
        "heading": "Working in %s" % borough,
    }
    body = [
        "Right now there are <b>%d jobs</b> in %s on TrueShift Jobs: %d part-time and %d full-time%s%s. Every job was posted in the last 30 days and is still open, and if the same job is on several job sites we show it once."
        % (n, borough, pt, ft, (", including %d apprenticeship%s" % (ap, "" if ap == 1 else "s")) if ap else "",
           (" and %d graduate or junior role%s" % (gr, "" if gr == 1 else "s")) if gr else ""),
    ]
    if top_cats:
        body.append("The most common kinds of work here at the moment are %s." % ", ".join(c.lower() for c in top_cats))
    if top_emps:
        body.append("Employers hiring in %s include %s." % (borough, ", ".join(esc(e) for e in top_emps)))
    if areas:
        body.append("Jobs are spread across areas such as %s." % ", ".join(esc(a) for a in areas))
    body.append("%s is in %s London. Nearby boroughs with jobs include %s." % (
        borough, region, ", ".join('<a href="/jobs/%s/">%s</a>' % (slug(b), b) for b in near)))
    body.append("From April 2026 the National Minimum Wage is £12.71 an hour for workers aged 21 and over, and many London employers pay the London Living Wage of £14.80. We leave out adverts below the legal minimum, and you should never pay a fee to get a job.")
    p["body"] = body
    out = build_page(base, p, borough_jobs=here)
    out = out.replace("<script>window.PAGE_GROUP=None;</script>\n", "")
    out = out.replace("<script>", "<script>window.PAGE_BOROUGH=%s;window.PAGE_REGION=%s;</script>\n<script>"
                      % (json.dumps(borough), json.dumps(region)), 1)
    return out


# ---------------------------------------------------------------- employer job pages

def job_schema(j):
    posted = j.get("posted") or dt.date.today().isoformat()
    closes = j.get("closes") or (dt.date.fromisoformat(posted) + dt.timedelta(days=30)).isoformat()
    desc = "".join("<p>%s</p>" % esc(x) for x in re.split(r"\n+", j.get("description") or j.get("about") or j.get("title")) if x.strip())
    addr = {"@type": "PostalAddress", "addressLocality": j.get("area") or j.get("borough"),
            "addressRegion": "London", "addressCountry": "GB"}
    if UK_POSTCODE.match(j.get("area") or ""):
        addr["postalCode"] = j["area"]
        addr["addressLocality"] = j.get("borough")
    org = {"@type": "Organization", "name": j.get("employer")}
    if j.get("website"):
        org["sameAs"] = j["website"]
    data = {
        "@context": "https://schema.org/", "@type": "JobPosting",
        "title": j.get("title"), "description": desc,
        "datePosted": posted, "validThrough": closes + "T23:59",
        "employmentType": "PART_TIME" if j.get("jobType") == "Part-time" else "FULL_TIME",
        "hiringOrganization": org,
        "jobLocation": {"@type": "Place", "address": addr},
        "directApply": False,
    }
    amt = None
    unit = None
    if j.get("pay"):
        amt, unit = j["pay"], "HOUR"
    else:
        m = re.search(r"£([\d,]+(?:\.\d+)?)\s+a (year|week|month)", j.get("salary") or "")
        if m:
            amt, unit = m.group(1), {"year": "YEAR", "week": "WEEK", "month": "MONTH"}[m.group(2)]
    if amt:
        try:
            v = float(str(amt).replace("£", "").replace(",", ""))
            data["baseSalary"] = {"@type": "MonetaryAmount", "currency": "GBP",
                                  "value": {"@type": "QuantitativeValue", "value": v, "unitText": unit}}
        except ValueError:
            pass
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def employer_page(j):
    url = SITE + j["page"]
    title = "%s at %s, %s | TrueShift Jobs" % (j.get("title"), j.get("employer"), j.get("borough"))
    apply = j.get("link") or ""
    apply_label = "Apply by email" if apply.startswith("mailto:") else "Apply now"
    desc = "".join("<p>%s</p>" % esc(x) for x in re.split(r"\n+", j.get("description") or j.get("about") or "") if x.strip())
    facts = [("Where", ", ".join(x for x in (j.get("area"), j.get("borough")) if x)), ("Job type", j.get("jobType")),
             ("Hours", j.get("hours")), ("Pay", pay_text(j)), ("Posted", nice_date(j.get("posted"))),
             ("Closes", nice_date(j.get("closes")))]
    rows = "".join("<tr><th>%s</th><td>%s</td></tr>" % (k, esc(v)) for k, v in facts if v)
    return """<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(meta)s">
<link rel="canonical" href="%(url)s">
<script type="application/ld+json">%(schema)s</script>
<style>
body{margin:0;font:17px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;background:#f3f7fb;color:#0b2540}
.wrap{max-width:760px;margin:0 auto;padding:24px 20px 48px}
.top{background:#0b2540;color:#fff}.top a{color:#9fd3ff;font-weight:700;text-decoration:none}
h1{font-size:1.8rem;line-height:1.25;margin:28px 0 4px}.emp{font-size:1.15rem;margin:0 0 18px;color:#36506b}
table{border-collapse:collapse;margin:0 0 20px}th{text-align:left;padding:4px 18px 4px 0;color:#36506b;font-weight:600}td{padding:4px 0}
.apply{display:inline-block;background:#0b2540;color:#fff;padding:12px 22px;border-radius:999px;text-decoration:none;font-weight:700;margin:8px 0 24px}
.box{background:#fff;border:1px solid #d6e2ee;border-radius:14px;padding:6px 22px}.note{font-size:.9rem;color:#36506b}
</style>
</head>
<body>
<header class="top"><div class="wrap" style="padding:16px 20px"><a href="/">TrueShift Jobs</a></div></header>
<main class="wrap">
<h1>%(h1)s</h1>
<p class="emp">%(emp)s</p>
<table>%(rows)s</table>
%(apply_html)s
<div class="box">%(desc)s</div>
<p class="note">This job was posted directly by the employer and checked by a person before going live. Never pay a fee to apply for a job.</p>
<p><a href="/jobs/%(bslug)s/">More jobs in %(borough)s</a> · <a href="/">All London jobs</a></p>
</main>
</body>
</html>
""" % {"title": esc(title), "meta": esc(("%s at %s in %s, London. %s" % (j.get("title"), j.get("employer"), j.get("borough"), j.get("about") or ""))[:155]),
       "url": url, "schema": job_schema(j), "h1": esc(j.get("title")), "emp": esc(j.get("employer")), "rows": rows,
       "apply_html": ('<a class="apply" href="%s" rel="noopener">%s</a>' % (esc(apply), apply_label)) if apply else "",
       "desc": desc or "<p>See the advert for full details.</p>", "bslug": slug(j.get("borough") or ""), "borough": esc(j.get("borough") or "London")}


def build_page(base, p, borough_jobs=None):
    url = "%s/jobs/%s/" % (SITE, p["slug"])
    out = base
    out = re.sub(r"<title>.*?</title>", "<title>%s</title>" % esc(p["title"]), out, count=1)
    out = re.sub(r'<meta name="description" content="[^"]*">',
                 '<meta name="description" content="%s">' % esc(p["description"]), out, count=1)
    out = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % url, out, count=1)
    out = re.sub(r'<meta property="og:title" content="[^"]*">',
                 '<meta property="og:title" content="%s">' % esc(p["title"]), out, count=1)
    out = re.sub(r'<meta property="og:description" content="[^"]*">',
                 '<meta property="og:description" content="%s">' % esc(p["description"]), out, count=1)
    out = re.sub(r'<meta property="og:url" content="[^"]*">', '<meta property="og:url" content="%s">' % url, out, count=1)
    out = re.sub(r"<h1>.*?</h1>", "<h1>%s</h1>" % esc(p["h1"]), out, count=1)
    out = re.sub(r'<p class="lead">.*?</p>', '<p class="lead">%s</p>' % esc(p["lead"]), out, count=1, flags=re.S)
    # Select this audience's tab before the page script runs.
    out = out.replace("<script>", "<script>window.PAGE_GROUP=%s;</script>\n<script>" % (json.dumps(p["group"]) if p["group"] else "None"), 1)
    if borough_jobs is not None:
        out = put_jobs(out, borough_jobs)
    elif p.get("group"):
        out = put_jobs(out, [j for j in JOBS if p["group"] in groups(j)])
    guide = ('<section class="band info seo" id="guide">\n  <div class="wrap">\n    <h2>%s</h2>\n%s\n'
             '    <p><a href="/">See all London jobs</a></p>\n  </div>\n</section>\n\n'
             % (esc(p["heading"]), "\n".join("    <p>%s</p>" % b for b in p["body"])))
    marker = '<section class="band info" id="checks">'
    assert marker in out
    fq = FAQS.get(p.get("group") or "")
    if fq:
        schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}} for q, a in fq["q"]]}
        items = "".join("<details><summary>%s</summary><p>%s</p></details>" % (q, a) for q, a in fq["q"])
        out = out.replace('<section class="band info" id="sfaq" hidden>', '<section class="band info" id="sfaq" data-g="%s">' % p["group"], 1)
        out = out.replace('<h2 id="faqh"></h2>', '<h2 id="faqh">%s</h2>' % esc(fq["h"]), 1)
        out = out.replace('<div class="faq" id="faqlist"></div>', '<div class="faq" id="faqlist">%s</div>' % items, 1)
        out = out.replace("</head>", '<script type="application/ld+json">%s</script>\n</head>' % json.dumps(schema, ensure_ascii=False), 1)
    out = out.replace(marker, guide + marker, 1)
    return out


JOBS = []
FAQS = json.loads((ROOT / "scripts" / "faqs.json").read_text())


def main():
    global JOBS
    JOBS = load_jobs()
    orig = base = (ROOT / "index.html").read_text()
    base = re.sub(r"/\*FAQS\*/.*?/\*/FAQS\*/", lambda m: "/*FAQS*/const FAQS=%s;/*/FAQS*/" % json.dumps(FAQS, ensure_ascii=False).replace("</", "<\\/"), base, count=1, flags=re.S)
    heads = {"All": {"title": html.unescape(re.search(r"<title>(.*?)</title>", base).group(1)),
                     "h1": html.unescape(re.sub(r"<[^>]+>", "", re.search(r"<h1>(.*?)</h1>", base, re.S).group(1))),
                     "lead": html.unescape(re.sub(r"<[^>]+>", "", re.search(r'<p class="lead">(.*?)</p>', base, re.S).group(1)))},
             "Saved": {"title": "Your saved jobs | TrueShift Jobs", "h1": "Your saved jobs",
                       "lead": "Jobs you have saved on this device. Jobs that close are removed automatically."}}
    for p in PAGES:
        if p.get("group"):
            heads[p["group"]] = {"title": p["title"], "h1": p["h1"], "lead": p["lead"]}
    base = re.sub(r"/\*HEADS\*/.*?/\*/HEADS\*/", lambda m: "/*HEADS*/const HEADS=%s;/*/HEADS*/" % json.dumps(heads, ensure_ascii=False).replace("</", "<\\/"), base, count=1, flags=re.S)
    # The home page gets the newest jobs written into its HTML too.
    home = put_jobs(base, JOBS)
    if home != orig:
        (ROOT / "index.html").write_text(home)
        base = home
    urls = [SITE + "/"]
    for p in PAGES:
        words = len(re.sub(r"<[^>]+>", " ", " ".join(p["body"])).split())
        assert 200 <= words <= 320, (p["slug"], words)
        d = ROOT / "jobs" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(build_page(base, p))
        urls.append("%s/jobs/%s/" % (SITE, p["slug"]))
        print("built /jobs/%s/ (%d words)" % (p["slug"], words))
    cats = categories(base)
    for b in sorted(BOROUGH_REGION):
        d = ROOT / "jobs" / slug(b)
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(borough_page(base, b, JOBS, cats, len(JOBS)))
        urls.append("%s/jobs/%s/" % (SITE, slug(b)))
    print("built %d borough pages" % len(BOROUGH_REGION))
    for info in ("about", "contact", "privacy", "cookies", "terms", "accessibility", "data-sources", "advertise"):
        if (ROOT / info / "index.html").exists():
            urls.append("%s/%s/" % (SITE, info))
    posted = ROOT / "jobs" / "posted"
    if posted.exists():
        shutil.rmtree(posted)  # closed jobs disappear with their pages
    emp = [j for j in JOBS if j.get("source") == "Employer" and j.get("page")]
    for j in emp:
        d = ROOT / j["page"].strip("/")
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(employer_page(j))
        urls.append(SITE + j["page"])
    print("built %d employer job pages" % len(emp))
    today = dt.date.today().isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append("  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>daily</changefreq></url>" % (u, today))
    sm.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n")
    (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)


if __name__ == "__main__":
    main()
