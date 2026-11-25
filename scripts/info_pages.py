#!/usr/bin/env python3
"""Write the site's information pages (About, Contact, Privacy and so on).

Run from the repository root: python scripts/info_pages.py
Each page is plain HTML in its own folder, for example /about/index.html.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://trueshiftjobs.com"
UPDATED = "25 November 2026"
FEEDBACK = "https://docs.google.com/forms/d/e/1FAIpQLSeW3k2cq7yW0AW4c_R-y6liaAuuLxNshU0PUutiYNMoTfz62w/viewform"
EMAIL = ""  # set to e.g. "hello@trueshiftjobs.com" once forwarding works

NAV = [("about", "About us"), ("contact", "Contact us"), ("privacy", "Privacy policy"), ("cookies", "Cookie policy"),
       ("terms", "Terms of use"), ("accessibility", "Accessibility"), ("data-sources", "Data sources"),
       ("advertise", "Advertise with us")]


def contact_line():
    bits = ['use our <a href="%s">contact form</a>' % FEEDBACK]
    if EMAIL:
        bits.append('email <a href="mailto:%s">%s</a>' % (EMAIL, EMAIL))
    return " or ".join(bits)


PAGES = {
    "about": ("About TrueShift Jobs", "A free London job site that shows real, current jobs and leaves out the noise.", f"""
<p>Job hunting in London can be exhausting. The same vacancy appears ten times through different agencies, adverts stay up long after the job has gone, and some "jobs" turn out to be paid training courses or scams.</p>
<p>TrueShift Jobs was built to fix that. Every morning we collect real, current vacancies across London, remove duplicates, drop anything older than 30 days, filter out scam wording and pay below the legal minimum, and sort every job by borough.</p>
<h2>Who it is for</h2>
<p>We focus on people who are often poorly served by big job boards: students looking for part-time work, people new to the UK, school leavers looking for apprenticeships, graduates, parents returning to work, and experienced professionals who want a cleaner list.</p>
<h2>How it works</h2>
<ul>
<li>Thousands of jobs come from official job feeds every night. See <a href="/data-sources/">Data sources</a>.</li>
<li>A smaller number are checked one by one against eight checks, such as a real employer, legal pay and no fees, and are marked "Checked".</li>
<li>Employers can post jobs for free. Every employer post is checked by a person before it goes live.</li>
</ul>
<h2>What we are not</h2>
<p>TrueShift Jobs is not an employer or a recruitment agency. We do not take applications, and we never charge jobseekers. When you apply, you apply on the employer's or job site's own advert.</p>
<p>TrueShift Jobs was started in 2026 by an IT consultant based in London. Questions or ideas? Please {contact_line()}.</p>
"""),
    "contact": ("Contact us", "Questions, ideas, a broken link, or a job that has closed? We would like to hear from you.", f"""
<h2>Jobseekers and general questions</h2>
<p>Please <a href="{FEEDBACK}">use our contact form</a>. Tell us what you need, and include your email address if you would like a reply.</p>
{('<p>You can also email <a href="mailto:%s">%s</a>.</p>' % (EMAIL, EMAIL)) if EMAIL else ''}
<h2>Employers</h2>
<p>To advertise a vacancy for free, <a href="/post-a-job/">post a job</a>. Every post is checked by a person before it goes live. For featured listings or partnerships, see <a href="/advertise/">Advertise with us</a>.</p>
<h2>Report a problem with a job</h2>
<p>If a job looks like a scam, asks you for money, or has closed, please tell us through the <a href="{FEEDBACK}">contact form</a> with a link to the job. We review reports and remove jobs that break our rules.</p>
<h2>Privacy requests</h2>
<p>To ask about personal data we hold, write "Privacy request" in the <a href="{FEEDBACK}">contact form</a>. See our <a href="/privacy/">privacy policy</a>.</p>
<p>We are a small team, so please allow a few working days for a reply.</p>
"""),
    "privacy": ("Privacy policy", "What personal data TrueShift Jobs uses, and why. We keep it to a minimum.", f"""
<p>This policy explains how TrueShift Jobs ("we", "us") handles personal data when you use trueshiftjobs.com. We aim to collect as little as possible.</p>
<h2>Jobseekers browsing the site</h2>
<ul>
<li><b>No accounts and no tracking.</b> You do not need to sign up. We do not use analytics, advertising trackers or tracking cookies.</li>
<li><b>Saved jobs and filters stay on your device.</b> If you save a job or choose filters, they are stored in your own browser (local storage) so the site remembers them. We never receive this information. You can clear it at any time by clearing your browser's site data.</li>
<li><b>Hosting.</b> The site is hosted on GitHub Pages. Like any web host, GitHub receives technical information such as your IP address when your browser requests a page, to deliver it and keep the service secure. See GitHub's privacy statement.</li>
<li><b>Links to other sites.</b> When you click "Apply", you leave our site and go to the employer's or job site's own advert, which has its own privacy policy.</li>
</ul>
<h2>Contact form and employer job posts</h2>
<p>Our contact form and our employer job form run on Google Forms. If you use them, we receive what you type in, such as your message, name, email address and job details. We use this only to reply to you, to check and publish job adverts, and to deal with problems. Google processes this data for us under its own terms.</p>
<p>When an employer job is published, only the job details are shown on the site (such as the job title, company, location, pay and how to apply). The poster's name and email address are never published.</p>
<h2>Our lawful basis</h2>
<p>We rely on our legitimate interests in running a free job site, answering messages and checking job adverts, and on your request when you ask us to publish a job.</p>
<h2>How long we keep data</h2>
<p>We keep contact messages for up to 12 months and employer posts for up to 12 months after the job closes, unless we need them longer to deal with a complaint or a legal requirement.</p>
<h2>Your rights</h2>
<p>Under UK data protection law you can ask to see, correct or delete personal data we hold about you, and you can object to how we use it. To make a request, please {contact_line()} and write "Privacy request". You also have the right to complain to the Information Commissioner's Office (ico.org.uk).</p>
<p>Last updated {UPDATED}.</p>
"""),
    "cookies": ("Cookie policy", "Short version: we do not use cookies.", f"""
<p>TrueShift Jobs does not set any cookies, and we do not use analytics or advertising trackers.</p>
<h2>Local storage</h2>
<p>To make the site easier to use, your browser stores two small items in its local storage on your own device:</p>
<ul>
<li><b>trueshift-saved</b>: the jobs you choose to save.</li>
<li><b>trueshift-filters</b>: your last filters, such as your area and the group you picked.</li>
</ul>
<p>These stay on your device and are never sent to us. You can delete them at any time by clearing this site's data in your browser settings.</p>
<h2>Fonts</h2>
<p>The site's font is hosted on our own site, so loading a page does not contact any font service.</p>
<h2>Other websites</h2>
<p>Our contact and employer forms run on Google Forms, and our "Apply" links go to other job sites. Those sites may use their own cookies, as explained in their own cookie policies.</p>
<p>Last updated {UPDATED}.</p>
"""),
    "terms": ("Terms of use", "The rules for using TrueShift Jobs. Please read them before you use the site.", f"""
<h2>About the service</h2>
<p>TrueShift Jobs is a free website that lists job vacancies in London. We are not an employer, a recruitment agency or a party to any job application or employment relationship. Using the site is free for jobseekers.</p>
<h2>Job listings</h2>
<ul>
<li>Most jobs come from third-party job feeds and are filtered automatically, not checked one by one. Jobs marked "Checked" or "Posted by employer" have been reviewed, but we cannot guarantee that any job is accurate, available or suitable.</li>
<li>Always read the full advert on the employer's or job site's own page, and check the details before you apply.</li>
<li>No real employer should ask you to pay a fee for a job, training, a uniform or a check. If you are asked for money, do not pay, and please report the job to us.</li>
</ul>
<h2>Employers posting jobs</h2>
<ul>
<li>You must only post genuine vacancies that you are authorised to advertise, with accurate details and pay that meets UK minimum wage law.</li>
<li>You must not charge applicants any fee, and adverts must comply with UK equality law.</li>
<li>We may edit, decline or remove any post at our discretion, without notice.</li>
</ul>
<h2>Acceptable use</h2>
<p>Do not misuse the site, attempt to disrupt it, or copy large parts of it by automated means.</p>
<h2>Liability</h2>
<p>The site is provided "as is". To the extent the law allows, we are not liable for any loss arising from your use of the site, from job listings, or from websites we link to. Nothing in these terms limits liability that cannot be limited by law.</p>
<h2>Changes and law</h2>
<p>We may update these terms from time to time; the date below shows the latest version. These terms are governed by the law of England and Wales.</p>
<p>Questions? Please {contact_line()}. Last updated {UPDATED}.</p>
"""),
    "accessibility": ("Accessibility", "We want everyone to be able to find a job on TrueShift Jobs.", f"""
<p>We aim to meet the Web Content Accessibility Guidelines (WCAG) 2.2 at level AA.</p>
<h2>What we do</h2>
<ul>
<li>Plain, simple English and short sentences.</li>
<li>Text and buttons with strong colour contrast.</li>
<li>Pages that work on phones, tablets and computers, and with zoom up to 200%.</li>
<li>Buttons and filters that work with a keyboard and screen readers, with clear labels.</li>
<li>No pop-ups, no auto-playing media and no cookie banners.</li>
</ul>
<h2>Known limitations</h2>
<ul>
<li>Job adverts on other websites, which our "Apply" buttons link to, are outside our control and may be less accessible.</li>
<li>The London area map is also available as a borough list in the filters, for anyone who finds the map hard to use.</li>
<li>We have not yet had a formal independent accessibility audit.</li>
</ul>
<h2>Tell us about a problem</h2>
<p>If something on the site is hard to use, please {contact_line()} and tell us the page and the problem. We will try to fix it quickly.</p>
<p>Last reviewed {UPDATED}.</p>
"""),
    "data-sources": ("Data sources", "Where the jobs on TrueShift Jobs come from, and how we credit them.", f"""
<p>Every job links to its original advert. We collect jobs every morning, keep only those in London posted in the last 30 days (apprenticeships stay until they close), show each job once, and filter out pay below the legal minimum and common scam wording.</p>
<h2>Job feeds</h2>
<ul>
<li><b>Reed</b>: vacancies from <a href="https://www.reed.co.uk">reed.co.uk</a>, through the Reed Jobseeker API.</li>
<li><b>Adzuna</b>: <a href="https://www.adzuna.co.uk">Jobs by Adzuna</a>, through the Adzuna API.</li>
<li><b>NHS Jobs</b>: public vacancies from <a href="https://www.jobs.nhs.uk">jobs.nhs.uk</a>.</li>
<li><b>Teaching Vacancies</b>: school jobs from <a href="https://teaching-vacancies.service.gov.uk">GOV.UK Teaching Vacancies</a>, used under the Open Government Licence v3.0.</li>
</ul>
<h2>Jobs checked one by one</h2>
<p>Each night we also look for jobs on employers' own career sites and on public job sites such as GOV.UK Find a job, Civil Service Jobs, council job sites and other job boards, and check each one against eight checks before it is marked "Checked".</p>
<h2>Employer posts</h2>
<p>Employers can post jobs directly through our free form. Each post is checked by a person before it is published, and marked "Posted by employer".</p>
<h2>Locations</h2>
<p>We match postcodes to London boroughs using <a href="https://postcodes.io">postcodes.io</a>. Contains OS data © Crown copyright and database right. Contains Royal Mail data © Royal Mail copyright and database right. Contains National Statistics data © Crown copyright and database right.</p>
<h2>Pay rates and guidance</h2>
<p>Minimum wage rates and guidance on our pages are based on GOV.UK information and were last checked on {UPDATED}.</p>
<p>All trademarks belong to their owners. If you think a listing should not appear here, please {contact_line()}.</p>
"""),
    "advertise": ("Advertise with us", "Reach students, school leavers, graduates, parents returning to work and people new to the UK across London.", f"""
<h2>Post a job for free</h2>
<p>Posting a vacancy on TrueShift Jobs is free. <a href="/post-a-job/">Post a job</a> in about a minute: paste your advert, add your company name and email, and we do the rest. Every post is checked by a person before it goes live, and it appears on the right borough page and in the right groups, such as students or parents returning to work.</p>
<p>Published employer jobs get their own page on our site, marked up so search engines can show them in job searches.</p>
<h2>Coming soon</h2>
<ul>
<li><b>Featured jobs</b>: pin your vacancy to the top of a borough or group for 14 days.</li>
<li><b>Borough partners</b>: councils, colleges and charities can sponsor a borough page to promote local jobs and support services.</li>
</ul>
<p>Interested in featured jobs or a partnership? Please {contact_line()} and tell us about your organisation.</p>
<h2>Our standards</h2>
<p>We only accept genuine vacancies that pay at least the UK minimum wage and never charge applicants. We do not accept adverts for paid courses presented as jobs, commission-only roles or schemes that ask jobseekers for money.</p>
"""),
}


def page(slug, title, lead, body):
    nav = " · ".join('<a href="/%s/">%s</a>' % (s, n) for s, n in NAV)
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | TrueShift Jobs</title>
<meta name="description" content="{lead}">
<link rel="canonical" href="{SITE}/{slug}/">
<style>
@font-face{{font-family:'Hanken Grotesk';font-weight:400;font-display:swap;src:url(/fonts/hanken-grotesk-400.woff2) format('woff2')}}
@font-face{{font-family:'Hanken Grotesk';font-weight:700;font-display:swap;src:url(/fonts/hanken-grotesk-700.woff2) format('woff2')}}
*{{box-sizing:border-box}}
body{{margin:0;font:17px/1.65 "Hanken Grotesk",system-ui,-apple-system,"Segoe UI",sans-serif;background:#f3f7fb;color:#0a2540}}
.top{{background:#0a2540;color:#fff}}.top .wrap{{padding:16px 20px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.top a{{color:#8fd3ff;font-weight:700;text-decoration:none}}
.wrap{{max-width:760px;margin:0 auto;padding:28px 20px 40px}}
h1{{font-size:2rem;line-height:1.2;margin:8px 0 6px}}.lead{{font-size:1.15rem;color:#4b6178;margin:0 0 22px}}
h2{{font-size:1.25rem;margin:28px 0 6px}}a{{color:#0b4f8a}}ul{{padding-left:22px}}li{{margin-bottom:6px}}
footer{{background:#0a2540;color:#c5ddec;font-size:.92rem}}footer a{{color:#8fd3ff}}footer .wrap{{padding:22px 20px}}
</style>
</head>
<body>
<div class="top"><div class="wrap"><a href="/">TrueShift Jobs</a><a href="/">Find jobs</a></div></div>
<main class="wrap">
<h1>{title}</h1>
<p class="lead">{lead}</p>
{body.strip()}
</main>
<footer><div class="wrap"><p>{nav}</p><p>&copy; 2026 TrueShift Jobs. Free for jobseekers, always.</p></div></footer>
</body>
</html>
"""


def main():
    for slug, (title, lead, body) in PAGES.items():
        d = ROOT / slug
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(page(slug, title, lead, body))
        print("wrote /%s/" % slug)


if __name__ == "__main__":
    main()
