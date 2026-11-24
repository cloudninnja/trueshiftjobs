#!/usr/bin/env python3
"""TrueShift Jobs nightly feed.

Collects London jobs from official job feeds, keeps only jobs posted in the
last 30 days, removes duplicates across all feeds, sorts every job into a
London region and borough, and writes feed.json for the website.

Sources (each is skipped if its key is missing or it fails):
  - GOV.UK Teaching Vacancies open API (no key, Open Government Licence)
  - Reed Jobseeker API (secret REED_API_KEY)
  - Adzuna API (secrets ADZUNA_APP_ID and ADZUNA_APP_KEY)
Borough lookups use postcodes.io (free, no key).

Runs on GitHub Actions; uses only the Python standard library.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEED = ROOT / "feed.json"
STATUS = ROOT / "feed-status.json"

MAX_AGE_DAYS = 30
MAX_JOBS = 5000
MIN_HOURLY = 12.71        # National Living Wage, 21 and over, from 1 April 2026
APPRENTICE_HOURLY = 8.00  # apprentice rate from 1 April 2026
UA = "TrueShiftJobs/1.0 (+https://trueshiftjobs.com)"

REED_PAGES = int(os.environ.get("REED_PAGES", "1"))      # 100 jobs a page
ADZUNA_PAGES = int(os.environ.get("ADZUNA_PAGES", "1"))  # 50 jobs a page
TV_MAX_PAGES = int(os.environ.get("TV_MAX_PAGES", "120"))

REGIONS = {
    "Central": ["City of London", "Westminster", "Camden", "Islington",
                "Kensington and Chelsea", "Lambeth", "Southwark"],
    "North": ["Barnet", "Enfield", "Haringey"],
    "East": ["Barking and Dagenham", "Bexley", "Greenwich", "Hackney", "Havering",
             "Lewisham", "Newham", "Redbridge", "Tower Hamlets", "Waltham Forest"],
    "South": ["Bromley", "Croydon", "Kingston upon Thames", "Merton", "Sutton", "Wandsworth"],
    "West": ["Brent", "Ealing", "Hammersmith and Fulham", "Harrow", "Hillingdon",
             "Hounslow", "Richmond upon Thames"],
}
BOROUGH_REGION = {b: r for r, bs in REGIONS.items() for b in bs}

# Town or area name -> borough. Matched as whole words, longest names first.
TOWNS = {
    "Barking and Dagenham": "barking, dagenham, becontree, chadwell heath",
    "Barnet": "high barnet, new barnet, east barnet, finchley, north finchley, east finchley, hendon, "
              "mill hill, golders green, colindale, burnt oak, edgware, whetstone, totteridge, "
              "brent cross, friern barnet, childs hill, west hendon",
    "Bexley": "bexleyheath, sidcup, welling, erith, crayford, belvedere, barnehurst, slade green, blackfen",
    "Brent": "wembley, harlesden, willesden, neasden, kingsbury, alperton, kensal green, stonebridge, "
             "dollis hill, park royal, queensbury, kilburn",
    "Bromley": "beckenham, orpington, penge, chislehurst, west wickham, biggin hill, petts wood, "
               "st mary cray, st paul's cray, shortlands, anerley, bickley, keston",
    "Camden": "camden town, hampstead, holborn, kentish town, swiss cottage, euston, bloomsbury, "
              "belsize park, chalk farm, gospel oak, west hampstead, primrose hill, king's cross, kings cross",
    "City of London": "the city, barbican, moorgate, liverpool street, aldgate, blackfriars, "
                      "fenchurch street, cannon street, st paul's",
    "Croydon": "purley, coulsdon, thornton heath, norbury, south norwood, upper norwood, addiscombe, "
               "selsdon, new addington, sanderstead, kenley, waddon, broad green",
    "Ealing": "acton, southall, hanwell, greenford, northolt, perivale, west ealing, northfields, "
              "ealing broadway, north acton, south acton",
    "Enfield": "edmonton, southgate, palmers green, winchmore hill, ponders end, enfield town, "
               "enfield lock, bush hill park, cockfosters, oakwood, brimsdown",
    "Greenwich": "woolwich, eltham, charlton, plumstead, kidbrooke, thamesmead, abbey wood, north greenwich",
    "Hackney": "dalston, shoreditch, hoxton, stoke newington, homerton, clapton, hackney wick, "
               "haggerston, stamford hill, london fields",
    "Hammersmith and Fulham": "hammersmith, fulham, shepherd's bush, shepherds bush, white city, "
                              "parsons green, barons court, west kensington",
    "Haringey": "tottenham, wood green, hornsey, crouch end, muswell hill, highgate, seven sisters, "
                "harringay, bounds green, turnpike lane, northumberland park, stroud green",
    "Harrow": "wealdstone, pinner, stanmore, rayners lane, south harrow, north harrow, hatch end, "
              "harrow weald, harrow on the hill, kenton",
    "Havering": "romford, hornchurch, upminster, rainham, harold wood, harold hill, collier row, "
                "gidea park, elm park",
    "Hillingdon": "uxbridge, hayes, heathrow, west drayton, ruislip, northwood, ickenham, harefield, "
                  "yiewsley, harlington, stockley park, eastcote, yeading, harmondsworth, sipson",
    "Hounslow": "feltham, isleworth, brentford, chiswick, heston, cranford, bedfont, hanworth, "
                "osterley, gunnersbury, hatton",
    "Islington": "angel, highbury, holloway, archway, finsbury park, canonbury, barnsbury, "
                 "clerkenwell, upper holloway, tufnell park, farringdon",
    "Kensington and Chelsea": "kensington, chelsea, notting hill, south kensington, earl's court, "
                              "earls court, holland park, ladbroke grove, north kensington",
    "Kingston upon Thames": "kingston, surbiton, new malden, chessington, tolworth, norbiton, berrylands",
    "Lambeth": "brixton, stockwell, vauxhall, streatham, kennington, waterloo, west norwood, "
               "tulse hill, oval, clapham",
    "Lewisham": "catford, deptford, forest hill, sydenham, brockley, new cross, hither green, "
                "grove park, blackheath, bellingham, ladywell, downham",
    "Merton": "wimbledon, mitcham, morden, raynes park, colliers wood, south wimbledon, motspur park",
    "Newham": "stratford, east ham, west ham, canning town, forest gate, plaistow, beckton, "
              "manor park, custom house, royal docks, silvertown",
    "Redbridge": "ilford, woodford, wanstead, gants hill, barkingside, goodmayes, seven kings, "
                 "south woodford, woodford green, hainault, clayhall",
    "Richmond upon Thames": "richmond, twickenham, teddington, hampton, whitton, barnes, kew, "
                            "east sheen, mortlake, hampton hill, hampton wick, st margarets",
    "Southwark": "peckham, bermondsey, camberwell, dulwich, east dulwich, elephant and castle, "
                 "london bridge, rotherhithe, walworth, nunhead, surrey quays, canada water, bankside",
    "Sutton": "cheam, carshalton, wallington, worcester park, belmont, hackbridge, north cheam",
    "Tower Hamlets": "whitechapel, bethnal green, canary wharf, poplar, stepney, mile end, bow, "
                     "limehouse, wapping, isle of dogs, shadwell, spitalfields, bromley-by-bow, "
                     "bromley by bow, millwall",
    "Waltham Forest": "walthamstow, leyton, leytonstone, chingford, highams park",
    "Wandsworth": "putney, tooting, battersea, balham, earlsfield, roehampton, southfields, "
                  "nine elms, clapham junction",
    "Westminster": "mayfair, soho, marylebone, paddington, victoria, pimlico, covent garden, "
                   "st john's wood, maida vale, bayswater, fitzrovia, oxford street, piccadilly, "
                   "leicester square, charing cross, strand, belgravia, knightsbridge, west end, "
                   "st james's, edgware road",
}
PLACE_BOROUGH = {}
for _b in BOROUGH_REGION:
    PLACE_BOROUGH[_b.lower()] = _b
for _b, _names in TOWNS.items():
    for _n in _names.split(","):
        PLACE_BOROUGH.setdefault(_n.strip().lower(), _b)
PLACE_BOROUGH["richmond upon thames"] = "Richmond upon Thames"
PLACE_BOROUGH["kingston upon thames"] = "Kingston upon Thames"
_PLACES = sorted(PLACE_BOROUGH, key=len, reverse=True)
_PLACE_RE = re.compile(r"\b(" + "|".join(re.escape(p) for p in _PLACES) + r")\b")

LONDON_POSTCODE = re.compile(
    r"^(EC|WC|E|N|NW|SE|SW|W|BR|CR|DA|EN|HA|IG|KT|RM|SM|TW|UB)\d", re.I)

# Who a job is for, and which jobs to leave out.
SENIOR = re.compile(
    r"\b(senior|head of|director|principal|consultant|specialist|engineer|developer|solicitor|"
    r"lawyer|accountant|analyst|architect|surveyor|psycholog\w*|psychiatr\w*|therapist|pharmacist|"
    r"doctor|surgeon|registrar|dentist|executive|partner|professor|lecturer|"
    r"(general|area|regional|store|project|programme|account|operations|branch|deputy) manager)\b", re.I)
ENTRY = re.compile(
    r"\b(assistant|operative|cleaner|cleaning|porter|barista|waiter|waitress|waiting|server|"
    r"bartender|bar staff|kitchen|commis|chef|cook|catering|receptionist|front of house|host|"
    r"administrator|admin|clerk|driver|delivery|courier|warehouse|picker|packer|sorter|loader|"
    r"retail|sales advisor|shop|store colleague|customer|call centre|cashier|checkout|team member|"
    r"crew|colleague|carer|care worker|support worker|healthcare|hca|domestic|housekeep\w*|"
    r"room attendant|laundry|caretaker|security|steward|attendant|lunchtime|midday|playworker|"
    r"nursery|childcare|learning support|invigilator|apprentice\w*|trainee|labourer|handyperson|"
    r"gardener|postal|postperson|postman|mail|parcel|cafe|café|restaurant|hotel|cinema|gym|"
    r"lifeguard|leisure|tutor|merchandiser|stock|replenishment)\b", re.I)
BLOCK = re.compile(
    r"(commission only|self[- ]employed|franchise|be your own boss|multi[- ]level|\bmlm\b|"
    r"telegram|whatsapp|upfront fee|registration fee|uber eats|deliveroo|gopuff|amazon flex|"
    r"just eat rider)", re.I)

GROUP_RULES = {
    "Students": re.compile(r"(weekend|evening|student|flexible|zero hours|bank|casual|retail|barista|"
                           r"waiter|waitress|bar |hospitality|cafe|café|cinema|leisure|tutor|invigilator|"
                           r"sales assistant|customer assistant|team member|crew|seasonal|christmas)", re.I),
    "Parents": re.compile(r"(term time|term-time|school hours|lunchtime|midday|teaching assistant|"
                          r"learning support|school|nursery|9[.:]30|2[.:]30|3[.:]00|job share|"
                          r"family[- ]friendly)", re.I),
    "Newcomers": re.compile(r"(no experience|training provided|full training|training given|entry level|"
                            r"entry-level|warehouse|cleaner|cleaning|porter|kitchen|picker|packer|operative|"
                            r"housekeep|room attendant|care assistant|carer|support worker|security|"
                            r"driver|delivery|labourer|team member|crew|retail|catering)", re.I),
}
SOURCE_RANK = {"Teaching Vacancies": 0, "Reed": 1, "Adzuna": 2}
SITE_NAME = {"Teaching Vacancies": "Teaching Vacancies (GOV.UK)", "Reed": "Reed", "Adzuna": "Adzuna"}

TODAY = date.today()


# ---------------------------------------------------------------- helpers
def http_json(url, data=None, headers=None, timeout=40):
    """GET (or POST when data is given) and parse JSON. Raises on failure."""
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h)
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def parse_date(s):
    """Return a date from YYYY-MM-DD..., DD/MM/YYYY or None."""
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def clean(s, limit=160):
    s = re.sub(r"<[^>]+>", " ", str(s or ""))
    s = re.sub(r"&[a-z]+;|&#\d+;", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def borough_from_text(*texts):
    for t in texts:
        if not t:
            continue
        m = _PLACE_RE.search(str(t).lower())
        if m:
            return PLACE_BOROUGH[m.group(1)]
    return None


def money(n):
    return "£{:,.2f}".format(n) if n < 100 else "£{:,.0f}".format(n)


def pay_fields(lo, hi, hint_full_time):
    """Return (hourly text or '', salary text or '', hourly floor or None)."""
    vals = [v for v in (lo, hi) if isinstance(v, (int, float)) and v > 0]
    if not vals:
        return "", "", None
    lo_v, hi_v = min(vals), max(vals)
    if hi_v < 100:  # hourly
        txt = money(lo_v) if lo_v == hi_v else money(lo_v) + " to " + money(hi_v)
        return money(lo_v), txt + " an hour", lo_v
    if hi_v < 1000:  # daily
        txt = money(lo_v) if lo_v == hi_v else money(lo_v) + " to " + money(hi_v)
        return "", txt + " a day", None
    txt = money(lo_v) if lo_v == hi_v else money(lo_v) + " to " + money(hi_v)
    return "", txt + " a year", None


def norm_emp(s):
    s = re.sub(r"\b(ltd|limited|plc|llp|uk|group|the|stores|holdings|services|& co|co)\b", " ", str(s or "").lower())
    return re.sub(r"[^a-z0-9]+", "", s)


def title_tokens(s):
    s = str(s or "").lower()
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)
    s = re.sub(r"\b(part[- ]?time|full[- ]?time|temporary|temp|permanent|perm|immediate start|urgent|"
               r"urgently|required|wanted|needed|hiring|new|job|role|vacancy|x\d+|\d+\s*(hrs|hours|h))\b", " ", s)
    s = _PLACE_RE.sub(" ", s)
    return {w for w in re.findall(r"[a-z]+", s) if len(w) > 1}


def same_job(a, b):
    if a["borough"] != b["borough"]:
        return False
    ea, eb = norm_emp(a["employer"]), norm_emp(b["employer"])
    if not (ea and eb and (ea.startswith(eb) or eb.startswith(ea))):
        return False
    ta, tb = title_tokens(a["title"]), title_tokens(b["title"])
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= 0.75


def groups_for(job, text):
    out = []
    jt = job.get("jobType")
    for g, rx in GROUP_RULES.items():
        if g in ("Students", "Parents") and jt == "Full-time":
            continue
        if rx.search(text):
            out.append(g)
    return ", ".join(out)


def keep(job, text):
    """Audience, safety and pay rules. Returns a reason to drop, or None."""
    t = job["title"]
    if BLOCK.search(t + " " + text):
        return "blocked words"
    if SENIOR.search(t):
        return "senior role"
    if job.get("jobType") != "Part-time" and not ENTRY.search(t):
        return "not entry level"
    floor = job.pop("_hourly", None)
    if floor is not None:
        if re.search(r"apprentice", t, re.I):
            if floor < APPRENTICE_HOURLY:
                return "below minimum wage"
        elif floor < MIN_HOURLY:
            return "below adult minimum wage"
    return None


def make_job(source, sid, title, employer, borough, area, job_type, lo, hi, link, posted, closes, text):
    hourly, salary, floor = pay_fields(lo, hi, job_type == "Full-time")
    job = {
        "id": source[:2].lower() + ":" + str(sid),
        "source": source,
        "title": re.sub(r"\s*[-–|(]\s*(part[- ]?time|full[- ]?time)\)?\s*$", "", clean(title, 120), flags=re.I),
        "employer": clean(employer, 100),
        "borough": borough,
        "region": BOROUGH_REGION.get(borough, ""),
        "area": clean(area, 60),
        "jobType": job_type,
        "pay": hourly,
        "salary": salary,
        "link": link,
        "posted": posted.isoformat() if posted else "",
        "closes": closes.isoformat() if closes else "",
        "found": TODAY.isoformat(),
        "_hourly": floor,
    }
    job["bestFor"] = groups_for(job, title + " " + text)
    return job


# ---------------------------------------------------------------- postcodes.io
def boroughs_for_postcodes(postcodes):
    out = {}
    pcs = sorted({p.upper().strip() for p in postcodes if p})
    for i in range(0, len(pcs), 100):
        chunk = pcs[i:i + 100]
        try:
            res = http_json("https://api.postcodes.io/postcodes", {"postcodes": chunk})
        except Exception as e:  # noqa: BLE001
            print("postcodes.io lookup failed:", e, file=sys.stderr)
            return out
        for item in res.get("result") or []:
            r = item.get("result") or {}
            d = r.get("admin_district")
            if d in BOROUGH_REGION:
                out[str(item.get("query", "")).upper().strip()] = d
    return out


def boroughs_for_points(points):
    """points: list of (lat, lon). Returns {(lat, lon): borough}."""
    out = {}
    pts = sorted({(round(a, 4), round(b, 4)) for a, b in points if a and b})
    for i in range(0, len(pts), 100):
        chunk = pts[i:i + 100]
        body = {"geolocations": [{"latitude": a, "longitude": b, "radius": 1500, "limit": 1} for a, b in chunk]}
        try:
            res = http_json("https://api.postcodes.io/postcodes", body)
        except Exception as e:  # noqa: BLE001
            print("postcodes.io reverse lookup failed:", e, file=sys.stderr)
            return out
        for (a, b), item in zip(chunk, res.get("result") or []):
            rs = item.get("result") or []
            if rs and rs[0].get("admin_district") in BOROUGH_REGION:
                out[(a, b)] = rs[0]["admin_district"]
    return out


# ---------------------------------------------------------------- sources
def fetch_teaching_vacancies(status):
    raw = []
    page, pages = 1, 1
    while page <= min(pages, TV_MAX_PAGES):
        res = http_json("https://teaching-vacancies.service.gov.uk/api/v1/jobs.json?page=%d" % page)
        pages = int((res.get("meta") or {}).get("totalPages") or 1)
        raw.extend(res.get("data") or [])
        page += 1
        time.sleep(0.3)
    status["fetched"] = len(raw)
    cands = []
    for d in raw:
        loc = d.get("jobLocation") or {}
        if isinstance(loc, list):
            loc = loc[0] if loc else {}
        addr = loc.get("address") or {}
        if isinstance(addr, list):
            addr = addr[0] if addr else {}
        pc = str(addr.get("postalCode") or "").strip()
        region = str(addr.get("addressRegion") or "")
        if not (region.lower() == "london" or LONDON_POSTCODE.match(pc)):
            continue
        cands.append((d, addr, pc))
    by_pc = boroughs_for_postcodes([pc for _, _, pc in cands])
    jobs = []
    for d, addr, pc in cands:
        borough = by_pc.get(pc.upper()) or borough_from_text(addr.get("addressLocality"), addr.get("streetAddress"))
        if not borough:
            continue
        et = [str(x).upper() for x in (d.get("employmentType") or [])]
        jt = "Part-time" if "PART_TIME" in et else ("Full-time" if "FULL_TIME" in et else "")
        sal = ((d.get("baseSalary") or {}).get("value") or {})
        text = clean(d.get("description"), 3000) + " " + str(sal.get("value") or "")
        job = make_job("Teaching Vacancies", d.get("url") or d.get("title"), d.get("title"),
                       (d.get("hiringOrganization") or {}).get("name"), borough,
                       addr.get("addressLocality"), jt, None, None, d.get("url"),
                       parse_date(d.get("datePosted")), parse_date(d.get("validThrough")), text)
        sv = clean(sal.get("value"), 80)
        if sv:
            job["salary"] = sv + (" a year" if str(sal.get("unitText", "")).upper() == "YEAR" and "year" not in sv.lower() else "")
        jobs.append((job, text))
    return jobs


def fetch_reed(key, status):
    auth = "Basic " + base64.b64encode((key + ":").encode()).decode()
    jobs, fetched = [], 0
    for borough in BOROUGH_REGION:
        for jt, flag in (("Part-time", "partTime"), ("Full-time", "fullTime")):
            for p in range(REED_PAGES):
                q = urllib.parse.urlencode({
                    "locationName": borough + ", London", "distanceFromLocation": 2,
                    flag: "true", "resultsToTake": 100, "resultsToSkip": p * 100})
                try:
                    res = http_json("https://www.reed.co.uk/api/1.0/search?" + q, headers={"Authorization": auth})
                except urllib.error.HTTPError as e:
                    if e.code in (401, 403):
                        raise
                    status.setdefault("errors", []).append("%s %s: HTTP %s" % (borough, jt, e.code))
                    break
                results = res.get("results") or []
                fetched += len(results)
                for r in results:
                    text = str(r.get("jobDescription") or "")
                    b = borough_from_text(r.get("locationName")) or borough
                    job = make_job("Reed", r.get("jobId"), r.get("jobTitle"), r.get("employerName"), b,
                                   r.get("locationName"), jt, r.get("minimumSalary"), r.get("maximumSalary"),
                                   r.get("jobUrl"), parse_date(r.get("date")), parse_date(r.get("expirationDate")), text)
                    jobs.append((job, text))
                time.sleep(0.4)
                if len(results) < 100:
                    break
    status["fetched"] = fetched
    return jobs


ADZUNA_WHAT = ("assistant operative cleaner porter barista waiter waitress bartender kitchen chef cook "
               "catering receptionist administrator driver delivery warehouse picker packer retail cashier "
               "customer team member crew carer support worker healthcare housekeeper caretaker security "
               "steward lunchtime nursery apprentice trainee labourer postal")


def fetch_adzuna(app_id, app_key, status):
    raw = []
    for region in REGIONS:
        for p in range(1, ADZUNA_PAGES + 1):
            q = urllib.parse.urlencode({
                "app_id": app_id, "app_key": app_key, "results_per_page": 50,
                "where": region + " London", "max_days_old": MAX_AGE_DAYS, "sort_by": "date",
                "what_or": ADZUNA_WHAT, "content-type": "application/json"})
            res = http_json("https://api.adzuna.com/v1/api/jobs/gb/search/%d?%s" % (p, q))
            results = res.get("results") or []
            raw.extend(results)
            time.sleep(0.5)
            if len(results) < 50:
                break
    status["fetched"] = len(raw)
    need = []
    for r in raw:
        loc = r.get("location") or {}
        b = borough_from_text(*(list(reversed(loc.get("area") or [])) + [loc.get("display_name")]))
        r["_borough"] = b
        if not b and r.get("latitude") and r.get("longitude"):
            need.append((float(r["latitude"]), float(r["longitude"])))
    by_pt = boroughs_for_points(need)
    jobs = []
    for r in raw:
        b = r.get("_borough")
        if not b and r.get("latitude") and r.get("longitude"):
            b = by_pt.get((round(float(r["latitude"]), 4), round(float(r["longitude"]), 4)))
        if not b:
            continue
        ct = r.get("contract_time")
        jt = "Part-time" if ct == "part_time" else ("Full-time" if ct == "full_time" else "")
        predicted = str(r.get("salary_is_predicted", "0")) == "1"
        lo = None if predicted else r.get("salary_min")
        hi = None if predicted else r.get("salary_max")
        text = str(r.get("description") or "")
        job = make_job("Adzuna", r.get("id"), r.get("title"), (r.get("company") or {}).get("display_name"), b,
                       (r.get("location") or {}).get("display_name"), jt, lo, hi, r.get("redirect_url"),
                       parse_date(r.get("created")), None, text)
        jobs.append((job, text))
    return jobs


# ---------------------------------------------------------------- merge
def fresh(job):
    p = parse_date(job.get("posted"))
    if not p or p > TODAY + timedelta(days=1) or (TODAY - p).days > MAX_AGE_DAYS:
        return False
    c = parse_date(job.get("closes"))
    return not (c and c < TODAY)


def dedupe(jobs):
    """One record per real job. Keeps the earliest posting date and the best link."""
    jobs = sorted(jobs, key=lambda j: (SOURCE_RANK.get(j["source"], 9), j.get("posted") or "9999"))
    kept, by_link = [], {}
    buckets = {}
    dropped = 0
    for j in jobs:
        link = re.sub(r"[?#].*$", "", str(j.get("link") or "")).rstrip("/").lower()
        match = by_link.get(link) if link else None
        if match is None:
            for k in buckets.get(j["borough"], []):
                if same_job(k, j):
                    match = k
                    break
        if match is not None:
            dropped += 1
            if j.get("posted") and (not match.get("posted") or j["posted"] < match["posted"]):
                match["posted"] = j["posted"]
            if j["source"] != match["source"]:
                also = set(match.get("alsoOn") or []) | {SITE_NAME[j["source"]]}
                match["alsoOn"] = sorted(also)
            for f in ("jobType", "pay", "salary", "closes", "bestFor"):
                if not match.get(f) and j.get(f):
                    match[f] = j[f]
            if j.get("found") and (not match.get("found") or j["found"] < match["found"]):
                match["found"] = j["found"]
            continue
        kept.append(j)
        buckets.setdefault(j["borough"], []).append(j)
        if link:
            by_link[link] = j
    return kept, dropped


def note_for(job):
    bits = ["Listed on " + SITE_NAME[job["source"]] + "."]
    if job.get("salary") and not job.get("pay"):
        bits.append(job["salary"][0].upper() + job["salary"][1:] + ".")
    elif job.get("salary") and " to " in job["salary"]:
        bits.append(job["salary"][0].upper() + job["salary"][1:] + ".")
    c = parse_date(job.get("closes"))
    if c:
        bits.append("Closes " + c.strftime("%-d %B %Y") + ".")
    bits.append("Check the advert before you apply.")
    return " ".join(bits)


def main():
    status = {"generated": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"), "sources": {}}
    collected = []

    def run(name, fn, *args):
        st = status["sources"].setdefault(name, {})
        try:
            items = fn(*args, st)
        except Exception as e:  # noqa: BLE001
            st["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
            print(name, "failed:", st["error"], file=sys.stderr)
            return
        kept, reasons = 0, {}
        for job, text in items:
            why = keep(job, text) if fresh(job) else "too old or closed"
            if why:
                reasons[why] = reasons.get(why, 0) + 1
                continue
            collected.append(job)
            kept += 1
        st["kept"] = kept
        st["dropped"] = reasons

    run("Teaching Vacancies", fetch_teaching_vacancies)
    reed_key = os.environ.get("REED_API_KEY", "").strip()
    if reed_key:
        run("Reed", fetch_reed, reed_key)
    else:
        status["sources"]["Reed"] = {"skipped": "no REED_API_KEY secret"}
    az_id, az_key = os.environ.get("ADZUNA_APP_ID", "").strip(), os.environ.get("ADZUNA_APP_KEY", "").strip()
    if az_id and az_key:
        run("Adzuna", fetch_adzuna, az_id, az_key)
    else:
        status["sources"]["Adzuna"] = {"skipped": "no ADZUNA_APP_ID / ADZUNA_APP_KEY secrets"}

    # Keep jobs from earlier nights that are still fresh, so the list builds up over 30 days.
    previous = []
    if FEED.exists():
        try:
            previous = [j for j in json.loads(FEED.read_text()).get("jobs", []) if fresh(j)]
        except Exception:  # noqa: BLE001
            previous = []
    for j in previous:
        j.pop("notes", None)
        j.setdefault("found", j.get("posted") or TODAY.isoformat())
    jobs, dupes = dedupe(collected + previous)
    jobs = [j for j in jobs if fresh(j)]
    for j in jobs:
        j.pop("_hourly", None)
        j["notes"] = note_for(j)
    jobs.sort(key=lambda j: (j.get("posted") or "", j.get("found") or ""), reverse=True)
    jobs = jobs[:MAX_JOBS]

    by_region = {r: 0 for r in REGIONS}
    by_type = {"Part-time": 0, "Full-time": 0, "Not stated": 0}
    for j in jobs:
        by_region[j["region"]] = by_region.get(j["region"], 0) + 1
        by_type[j.get("jobType") or "Not stated"] += 1
    status.update({"total": len(jobs), "duplicatesRemoved": dupes, "byRegion": by_region, "byJobType": by_type,
                   "carriedOver": len(previous)})
    FEED.write_text(json.dumps({"generated": status["generated"], "maxAgeDays": MAX_AGE_DAYS,
                                "jobs": jobs}, ensure_ascii=False, separators=(",", ":")))
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False))
    print(json.dumps(status, indent=2))
    if not jobs and all("error" in s or "skipped" in s for s in status["sources"].values()):
        print("No source worked; keeping the job going so the page still loads.", file=sys.stderr)


if __name__ == "__main__":
    main()
