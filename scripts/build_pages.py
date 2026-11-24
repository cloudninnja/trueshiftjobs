#!/usr/bin/env python3
"""Build one indexable page per audience from index.html, plus sitemap.xml and robots.txt.

Each page is a copy of the main page with its own <title>, description, canonical
link, heading, a short guide written for that audience, and the matching tab
selected. Run from the repository root: python scripts/build_pages.py
"""
import datetime as dt
import html
import pathlib
import re

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
        "h1": "Jobs for experienced professionals in London",
        "lead": "Skilled, professional and senior roles across London, filtered by category and borough.",
        "heading": "Professional jobs across London, without the noise",
        "body": [
            "Job sites often show the same role many times through different agencies, alongside old adverts that have already been filled. This page brings together professional and senior roles from Reed, Adzuna and Teaching Vacancies, shows each job once and keeps only adverts posted in the last 30 days.",
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


def build_page(base, p):
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
    out = out.replace("<script>", "<script>window.PAGE_GROUP=%r;</script>\n<script>" % p["group"], 1)
    guide = ('<section class="band info seo" id="guide">\n  <div class="wrap">\n    <h2>%s</h2>\n%s\n'
             '    <p><a href="/">See all London jobs</a></p>\n  </div>\n</section>\n\n'
             % (esc(p["heading"]), "\n".join("    <p>%s</p>" % b for b in p["body"])))
    marker = '<section class="band info" id="checks">'
    assert marker in out
    out = out.replace(marker, guide + marker, 1)
    return out


def main():
    base = (ROOT / "index.html").read_text()
    for p in PAGES:
        words = len(re.sub(r"<[^>]+>", " ", " ".join(p["body"])).split())
        assert 200 <= words <= 320, (p["slug"], words)
        d = ROOT / "jobs" / p["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(build_page(base, p))
        print("built /jobs/%s/ (%d words)" % (p["slug"], words))
    today = dt.date.today().isoformat()
    urls = [SITE + "/"] + ["%s/jobs/%s/" % (SITE, p["slug"]) for p in PAGES]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append("  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>daily</changefreq></url>" % (u, today))
    sm.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sm) + "\n")
    (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)


if __name__ == "__main__":
    main()
