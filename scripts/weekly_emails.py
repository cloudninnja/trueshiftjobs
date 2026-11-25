"""Prepare the weekly job emails in MailerLite as drafts.

1. Reads confirmed subscribers in the "Job alerts" group and puts each one into
   a "Weekly - <job type>" group that matches the job types they ticked.
2. Builds one email per job type with the newest jobs from the last 7 days,
   grouped by area of London.
3. Saves each email as a DRAFT campaign. Nothing is sent: the owner checks the
   drafts in MailerLite and presses Send.

Subscriber emails are only handled in memory and never printed or saved.
Writes counts (no personal data) to weekly-email-status.json.
"""
import datetime
import html
import json
import os
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request

API = "https://connect.mailerlite.com/api"
KEY = os.environ.get("MAILERLITE_API_KEY", "").strip()
ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://trueshiftjobs.com"
FROM = "hello@trueshiftjobs.com"
PREFIX = "Weekly jobs"
DAYS = 7
PER_AREA = 6

# Interest wording on the sign-up form -> (feed group, label, page slug)
TYPES = {
    "Student jobs": ("Students", "student jobs", "students"),
    "Apprenticeships": ("Apprentices", "apprenticeships", "apprenticeships"),
    "Graduate jobs": ("Graduates", "graduate jobs", "graduates"),
    "Professional jobs": ("Experienced", "professional jobs", "experienced-professionals"),
    "Jobs for people new to the UK": ("Newcomers", "jobs for people new to the UK", "new-to-the-uk"),
    "Jobs for parents returning to work": ("Parents", "jobs for parents returning to work", "parents-returning-to-work"),
    "All jobs": (None, "jobs", ""),
}
AREAS = ["Central", "East", "South", "West", "North"]


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Accept": "application/json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read().decode() or "{}"
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def all_pages(path):
    items, cursor = [], None
    while True:
        sep = "&" if "?" in path else "?"
        st, d = call("GET", path + (sep + "cursor=" + urllib.parse.quote(cursor) if cursor else ""))
        if st != 200:
            raise SystemExit("MailerLite returned %s for %s" % (st, path.split("?")[0]))
        items += d.get("data", [])
        cursor = (d.get("meta") or {}).get("next_cursor")
        if not cursor:
            return items


def groups_by_name():
    return {g["name"]: g["id"] for g in all_pages("/groups?limit=100")}


def ensure_group(name, existing):
    if name not in existing:
        st, g = call("POST", "/groups", {"name": name})
        if st not in (200, 201):
            raise SystemExit("Could not create group %s: %s" % (name, st))
        existing[name] = g["data"]["id"]
    return existing[name]


def wanted_types(sub):
    raw = ((sub.get("fields") or {}).get("interests") or "").strip()
    picked = [t for t in TYPES if t != "All jobs" and t in raw]
    return picked or ["All jobs"]


def fresh_jobs():
    try:  # the live site has today's jobs; the repository copy is only a fallback
        with urllib.request.urlopen(SITE + "/feed.json", timeout=60) as r:
            jobs = json.loads(r.read().decode())["jobs"]
    except Exception:  # noqa: BLE001
        jobs = json.loads((ROOT / "feed.json").read_text())["jobs"]
    since = (datetime.date.today() - datetime.timedelta(days=DAYS)).isoformat()
    out = [j for j in jobs if (j.get("posted") or j.get("found") or "") >= since and j.get("link")]
    out.sort(key=lambda j: (j.get("posted") or "", bool(j.get("pay") or j.get("salary"))), reverse=True)
    return out


ENTRY = {"Students", "Newcomers", "Parents", "Apprentices"}


def pay_text(j):
    sal = (j.get("salary") or "").strip()
    if sal and len(sal) <= 45:
        return sal
    m = re.search(r"£[\d,]+(?:\.\d+)?(?: to £[\d,]+(?:\.\d+)?)?", sal)
    unit = next((u for u in ("an hour", "a day", "a week", "a month", "a year") if u in sal), "")
    if m:
        return (m.group(0) + " " + unit).strip()
    return j.get("pay") or "Pay in advert"


def too_senior(j):
    sal = j.get("salary") or ""
    nums = [float(x.replace(",", "")) for x in re.findall(r"£([\d,]+(?:\.\d+)?)", sal)]
    if not nums:
        return False
    low = min(nums)
    if "an hour" in sal:
        return low > 25
    if "a year" in sal and "full-time equivalent" not in sal and "FTE" not in sal:
        return low > 35000
    return False


def job_row(j):
    pay = pay_text(j)
    area, borough = j.get("area") or "", j.get("borough") or ""
    where = "%s, %s" % (area, borough) if area and area != borough else borough
    bits = [html.escape(j.get("employer") or ""), html.escape(where), html.escape(pay)]
    if j.get("jobType"):
        bits.append(html.escape(j["jobType"]))
    credit = '<br><span style="font-size:12px;color:#6b7c8f">Jobs by Adzuna</span>' if j.get("source") == "Adzuna" else ""
    link = html.escape(j["link"], quote=True)
    return ('<tr><td style="padding:12px 0;border-bottom:1px solid #e3ebf3">'
            '<a href="%s" style="font-size:16px;font-weight:700;color:#0b4f8a;text-decoration:none">%s</a>'
            '<div style="font-size:14px;color:#33475b;margin-top:4px">%s</div>%s</td></tr>'
            % (link, html.escape(j.get("title") or "Job"), " &middot; ".join(b for b in bits if b), credit))


def build_email(label, slug, jobs):
    page = SITE + ("/jobs/%s/" % slug if slug else "/")
    utm = "?utm_source=mailerlite&utm_medium=email&utm_campaign=weekly"
    sections = []
    for area in AREAS:
        here = [j for j in jobs if j.get("region") == area][:PER_AREA]
        if not here:
            continue
        sections.append('<h2 style="font-size:18px;color:#0a2540;margin:26px 0 4px">%s London</h2>'
                        '<table role="presentation" width="100%%" cellpadding="0" cellspacing="0">%s</table>'
                        % (area, "".join(job_row(j) for j in here)))
    total = len(jobs)
    return """<!DOCTYPE html><html><body style="margin:0;background:#f3f7fb">
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="background:#f3f7fb"><tr><td align="center" style="padding:20px 12px">
<table role="presentation" width="100%%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;font-family:Arial,Helvetica,sans-serif">
<tr><td style="background:#0a2540;border-radius:12px 12px 0 0;padding:20px 24px">
<div style="color:#8fd3ff;font-weight:700;font-size:15px">TrueShift Jobs</div>
<div style="color:#ffffff;font-size:22px;font-weight:700;margin-top:6px">New %s in London this week</div>
</td></tr>
<tr><td style="padding:8px 24px 24px">
<p style="font-size:15px;color:#33475b;line-height:1.5">Here are the newest %s from the last 7 days, grouped by area. You chose: <b>{$areas}</b>. Every job is real and still open, and Apply takes you to the employer's own advert.</p>
%s
<p style="text-align:center;margin:28px 0 8px"><a href="%s%s" style="display:inline-block;background:#0a2540;color:#ffffff;text-decoration:none;font-weight:700;padding:12px 22px;border-radius:999px">See all %s new %s on TrueShift Jobs</a></p>
<p style="font-size:13px;color:#6b7c8f;line-height:1.5;margin-top:24px">Tip: real employers never ask you to pay for a job, training or a DBS check.</p>
</td></tr>
<tr><td style="padding:16px 24px 22px;border-top:1px solid #e3ebf3;font-size:12px;color:#6b7c8f;line-height:1.5">
You are getting this because you signed up for job emails at trueshiftjobs.com. To change your job types or areas, sign up again on the site with the same email.
<a href="{$unsubscribe}" style="color:#0b4f8a">Unsubscribe</a>.
</td></tr></table></td></tr></table></body></html>""" % (
        html.escape(label), html.escape(label), "".join(sections), page, utm, total, html.escape(label))


def main():
    status = {"date": datetime.date.today().isoformat()}
    if not KEY:
        raise SystemExit("MAILERLITE_API_KEY secret is missing")
    groups = groups_by_name()
    if "Job alerts" not in groups:
        raise SystemExit("The Job alerts group is missing in MailerLite")
    subs = all_pages("/groups/%s/subscribers?filter[status]=active&limit=1000" % groups["Job alerts"])
    status["confirmedSubscribers"] = len(subs)

    # Sort subscribers into one group per job type.
    type_group = {t: ensure_group("%s - %s" % (PREFIX, t), groups) for t in TYPES}
    members = {t: set() for t in TYPES}
    for s in subs:
        for t in wanted_types(s):
            members[t].add(s["id"])
    for t, gid in type_group.items():
        current = {s["id"] for s in all_pages("/groups/%s/subscribers?limit=1000" % gid)}
        for sid in members[t] - current:
            call("POST", "/subscribers/%s/groups/%s" % (sid, gid))
        for sid in current - members[t]:
            call("DELETE", "/subscribers/%s/groups/%s" % (sid, gid))
    status["subscribersByType"] = {t: len(v) for t, v in members.items()}

    # Remove last week's unsent drafts so only this week's are waiting.
    removed = 0
    for c in all_pages("/campaigns?filter[status]=draft&limit=100"):
        if (c.get("name") or "").startswith(PREFIX + " - "):
            if call("DELETE", "/campaigns/%s" % c["id"])[0] in (200, 204):
                removed += 1
    status["oldDraftsRemoved"] = removed

    jobs = fresh_jobs()
    status["newJobsThisWeek"] = len(jobs)
    made = {}
    for t, (feed_group, label, slug) in TYPES.items():
        if not members[t]:
            continue
        mine = [j for j in jobs if feed_group is None or feed_group in (j.get("bestFor") or "")]
        if feed_group in ENTRY:
            mine = [j for j in mine if not too_senior(j)]
        if not mine:
            made[t] = "no new jobs this week"
            continue
        subject = "%d new %s in London this week" % (len(mine), label)
        body = {"name": "%s - %s - %s" % (PREFIX, t, status["date"]), "type": "regular",
                "emails": [{"subject": subject, "from_name": "TrueShift Jobs", "from": FROM,
                            "content": build_email(label, slug, mine)}],
                "groups": [type_group[t]]}
        st, c = call("POST", "/campaigns", body)
        made[t] = "draft ready" if st in (200, 201) else "failed (%s: %s)" % (st, c.get("message"))
    status["drafts"] = made
    (ROOT / "weekly-email-status.json").write_text(json.dumps(status, indent=1))
    print(json.dumps(status, indent=1))


if __name__ == "__main__":
    main()
