import json
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
EMAIL = "hello@trueshiftjobs.com"

NAV = [("about", "About us"), ("contact", "Contact us"), ("privacy", "Privacy policy"), ("cookies", "Cookie policy"),
       ("terms", "Terms of use"), ("accessibility", "Accessibility"), ("data-sources", "Data sources"),
       ("advertise", "Advertise with us")]


def contact_line():
    bits = ['use our <a href="%s">contact form</a>' % FEEDBACK]
    if EMAIL:
        bits.append('email <a href="mailto:%s">%s</a>' % (EMAIL, EMAIL))
    return " or ".join(bits)


PAGES = {
    "about": ("About TrueShift Jobs", "Why I built a free London job site that shows real, current jobs and leaves out the noise.", f"""
<h2>Why TrueShift Jobs exists</h2>
<p>I'm Vamsi Are, an IT consultant based in London. TrueShift Jobs started at my own kitchen table, helping my daughter look for an apprenticeship.</p>
<p>What should have been exciting quickly became frustrating. The same vacancy appeared again and again through different agencies. Adverts stayed up long after the job had gone. Some "apprenticeships" turned out to be paid training courses, and some adverts paid less than the legal minimum. We spent hours searching and very little of that time went on jobs that were really there.</p>
<p>I realised that if it was this hard for us, it was harder still for many others: students looking for part-time work, parents going back to work after raising children, and people who have just moved to the UK and don't yet know what a genuine advert looks like, or that a real employer never asks you to pay.</p>
<p>I spend my working days building systems that automate tedious work for businesses, so I pointed those skills at this problem. TrueShift Jobs does the boring filtering for you.</p>
<h2>What it does</h2>
<ul>
<li>Collects real, current London vacancies every morning from official job feeds. See <a href="/data-sources/">Data sources</a>.</li>
<li>Shows each job once, even when it appears on several job sites.</li>
<li>Removes adverts older than 30 days, scam wording, paid-course "jobs" and pay below the legal minimum. Apprenticeships stay until their closing date, because they are often advertised months ahead.</li>
<li>Sorts everything by borough, so you can find work close to home.</li>
<li>Groups jobs for students, people new to the UK, apprentices, graduates, parents returning to work and experienced professionals.</li>
<li>Lets employers post jobs for free. Every employer post is checked by a person before it goes live.</li>
</ul>
<h2>What it is not</h2>
<p>TrueShift Jobs is not an employer or a recruitment agency. We don't take applications, and we never charge jobseekers. When you apply, you apply on the employer's or job site's own advert.</p>
<p>It is free for jobseekers and always will be. If it saves you even one wasted application, it has done its job.</p>
<p>Vamsi Are, founder. Questions or ideas? Please {contact_line()}.</p>
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
<li><b>No accounts and no tracking.</b> You do not need to sign up to use the site. We do not use advertising trackers or tracking cookies.</li>
<li><b>Visitor statistics.</b> We use Cloudflare Web Analytics to count visits and see which pages are popular. It does not use cookies, does not track you across websites and does not build a profile of you. It records things like the page visited, the website you came from, your country and your type of device.</li>
<li><b>Saved jobs and filters stay on your device.</b> If you save a job or choose filters, they are stored in your own browser (local storage) so the site remembers them. We never receive this information. You can clear it at any time by clearing your browser's site data.</li>
<li><b>Hosting.</b> The site is hosted on GitHub Pages. Like any web host, GitHub receives technical information such as your IP address when your browser requests a page, to deliver it and keep the service secure. See GitHub's privacy statement.</li>
<li><b>Links to other sites.</b> When you click "Apply", you leave our site and go to the employer's or job site's own advert, which has its own privacy policy.</li>
</ul>
<h2>Contact form and employer job posts</h2>
<p>Our contact form and our employer job form run on Google Forms. If you use them, we receive what you type in, such as your message, name, email address and job details. We use this only to reply to you, to check and publish job adverts, and to deal with problems. Google processes this data for us under its own terms.</p>
<p>When an employer job is published, only the job details are shown on the site (such as the job title, company, location, pay and how to apply). The poster's name and email address are never published.</p>
<h2>Job alert emails</h2>
<p>If you choose to sign up for job emails, we collect your email address and the job types and areas you pick. We store them with MailerLite, the email service we use to send job emails, which processes them for us under its own terms. We first send you an email asking you to confirm, and we only send job emails once you have confirmed. We use your details only to send you new jobs from TrueShift Jobs. We never sell them or share them with employers or advertisers.</p>
<p>Every email will include a way to unsubscribe, and you can unsubscribe at any time on our <a href="/unsubscribe/">unsubscribe page</a>. You can also ask us to remove your email address at any time using our <a href="{FEEDBACK}">contact form</a>, and we will delete it.</p>
<h2>Our lawful basis</h2>
<p>We rely on our legitimate interests in running a free job site, answering messages and checking job adverts, on your request when you ask us to publish a job, and on your consent for job alert emails. You can withdraw your consent at any time.</p>
<h2>How long we keep data</h2>
<p>We keep job alert email addresses until you unsubscribe or ask us to remove them. We keep contact messages for up to 12 months and employer posts for up to 12 months after the job closes, unless we need them longer to deal with a complaint or a legal requirement.</p>
<h2>Your rights</h2>
<p>Under UK data protection law you can ask to see, correct or delete personal data we hold about you, and you can object to how we use it. To make a request, please {contact_line()} and write "Privacy request". You also have the right to complain to the Information Commissioner's Office (ico.org.uk).</p>
<p>Last updated {UPDATED}.</p>
"""),
    "cookies": ("Cookie policy", "Short version: we do not use cookies.", f"""
<p>TrueShift Jobs does not set any cookies, and we do not use advertising trackers. We count visits with Cloudflare Web Analytics, which works without cookies and does not track you across websites.</p>
<h2>Local storage</h2>
<p>To make the site easier to use, your browser stores two small items in its local storage on your own device:</p>
<ul>
<li><b>trueshift-saved</b>: the jobs you choose to save.</li>
<li><b>trueshift-filters</b>: your last filters, such as your area and the group you picked.</li>
<li><b>ts_alert</b>: a note that you have signed up for job emails, so the sign-up box does not ask again.</li>
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
<li>Areas of London can be chosen from a simple list of buttons, and every borough is also in the borough filter.</li>
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


UNSUB_FORM = "https://docs.google.com/forms/d/e/1FAIpQLScDtESWm1REt6qY-0XykjFTtQqhb0BNfjro9y86yxT9iJomBA/formResponse"
UNSUB_ENTRY = "entry.95951508"

UNSUB_BODY = """
<p>Enter the email address you signed up with and we will stop sending you job emails. We will delete your address from our list.</p>
<form id="unsub" novalidate>
<label for="uemail"><b>Email address</b></label>
<div class="urow"><input id="uemail" type="email" autocomplete="email" inputmode="email" required><button type="submit" id="usend">Unsubscribe me</button></div>
<p id="umsg" role="status" aria-live="polite"></p>
</form>
<p>Changed your mind? You can sign up again at any time on the <a href="/">home page</a>. Questions? See our <a href="/privacy/">privacy policy</a>.</p>
<style>
.urow{display:flex;gap:10px;margin-top:6px;flex-wrap:wrap}.urow input{flex:1 1 240px;min-height:48px;font:inherit;padding:0 14px;border:1px solid #9bb3c9;border-radius:12px}
.urow button{min-height:48px;padding:0 20px;font:inherit;font-weight:700;border:0;border-radius:999px;background:#0a2540;color:#fff;cursor:pointer}.urow button:disabled{opacity:.6}
.urow input:focus-visible,.urow button:focus-visible{outline:3px solid #0b4f8a;outline-offset:2px}
#umsg{font-weight:700;min-height:1.2em}#umsg.err{color:#b3123a}
</style>
<script>
(function(){
  var ACTION=%s, ENTRY=%s;
  var f=document.getElementById('unsub'), e=document.getElementById('uemail'), m=document.getElementById('umsg'), b=document.getElementById('usend');
  try{var q=new URLSearchParams(location.search).get('email');if(q)e.value=q}catch(x){}
  function say(t,bad){m.textContent=t;m.className=bad?'err':''}
  f.addEventListener('submit',function(ev){ev.preventDefault();var v=e.value.trim();
    if(!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$/.test(v)){say('Please enter a valid email address.',true);e.focus();return}
    if(!ENTRY){say('Sorry, unsubscribing is not available yet. Please use our contact form.',true);return}
    var body=new URLSearchParams();body.append(ENTRY,v);b.disabled=true;say('Sending...');
    fetch(ACTION,{method:'POST',mode:'no-cors',body:body}).then(function(){say("Done. You will not get any more job emails from us. We will remove "+v+" from our list.");f.reset()})
      .catch(function(){say('Sorry, that did not go through. Please check your connection and try again.',true)}).finally(function(){b.disabled=false})});
})();
</script>
""" % (json.dumps(UNSUB_FORM), json.dumps(UNSUB_ENTRY))

PAGES["unsubscribe"] = ("Unsubscribe from job emails", "Stop getting job emails from TrueShift Jobs.", UNSUB_BODY)


CF = '<!-- Cloudflare Web Analytics --><script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{"token": "9e7884d556a84616886e38aff893e657"}\'></script><!-- End Cloudflare Web Analytics -->'


def page(slug, title, lead, body):
    nav = " · ".join('<a href="/%s/">%s</a>' % (s, n) for s, n in NAV)
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | TrueShift Jobs</title>{'<meta name="robots" content="noindex">' if slug == "unsubscribe" else ""}
<meta name="description" content="{lead}">
<link rel="canonical" href="{SITE}/{slug}/">
<style>
@font-face{{font-family:'Hanken Grotesk';font-weight:400;font-display:swap;src:url(/fonts/hanken-grotesk-400.woff2) format('woff2')}}
@font-face{{font-family:'Hanken Grotesk';font-weight:700;font-display:swap;src:url(/fonts/hanken-grotesk-700.woff2) format('woff2')}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;display:flex;flex-direction:column;font:17px/1.65 "Hanken Grotesk",system-ui,-apple-system,"Segoe UI",sans-serif;background:#f3f7fb;color:#0a2540}}
.top{{background:#0a2540;color:#fff}}.top .wrap{{padding:16px 20px;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.top a{{color:#8fd3ff;font-weight:700;text-decoration:none}}
.wrap{{max-width:760px;margin:0 auto;padding:28px 20px 40px}}main.wrap{{flex:1 0 auto;width:100%}}
h1{{font-size:2rem;line-height:1.2;margin:8px 0 6px}}.lead{{font-size:1.15rem;color:#4b6178;margin:0 0 22px}}
h2{{font-size:1.25rem;margin:28px 0 6px}}a{{color:#0b4f8a}}ul{{padding-left:22px}}li{{margin-bottom:6px}}
footer{{background:#0a2540;color:#c5ddec;font-size:.92rem}}footer a{{color:#8fd3ff}}footer .wrap{{padding:22px 20px}}
</style>
</head>
<body>
<header class="top"><div class="wrap"><a href="/">TrueShift Jobs</a><a href="/">Find jobs</a></div></header>
<main class="wrap">
<h1>{title}</h1>
<p class="lead">{lead}</p>
{body.strip()}
</main>
<footer><div class="wrap"><p>{nav}</p><p>&copy; 2026 TrueShift Jobs. Free for jobseekers, always.</p></div></footer>
{CF}
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
