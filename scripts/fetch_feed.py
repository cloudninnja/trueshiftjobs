#!/usr/bin/env python3
"""TrueShift Jobs nightly feed.

Collects London jobs from official job feeds, keeps only jobs posted in the
last 30 days, removes duplicates across all feeds, sorts every job into a
London region and borough, and writes feed.json for the website.

Sources (each is skipped if its key is missing or it fails):
  - GOV.UK Teaching Vacancies open API (no key, Open Government Licence)
  - Reed Jobseeker API (secret REED_API_KEY)
  - Adzuna API (secrets ADZUNA_APP_ID and ADZUNA_APP_KEY)
  - NHS Jobs public search feed (no key needed)
  - Careerjet publisher API (secret CAREERJET_API_KEY), newest jobs per borough
  - GOV.UK Find an apprenticeship, Display advert API (secret APPRENTICESHIP_API_KEY)
  - Jobs posted by employers through the TrueShift Google Form, once approved
    (secret EMPLOYER_JOBS_CSV: the published CSV link of the sheet's Public tab)
Borough lookups use postcodes.io (free, no key).

Runs on GitHub Actions; uses only the Python standard library.
"""
import base64
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
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
CAREERJET_PAGES = int(os.environ.get("CAREERJET_PAGES", "2"))  # per borough, 100 a page
NHS_MAX_PAGES = int(os.environ.get("NHS_MAX_PAGES", "400"))  # 10 jobs a page
FAA_MAX_PAGES = int(os.environ.get("FAA_MAX_PAGES", "40"))  # 100 apprenticeships a page
REED_APPRENTICE_PAGES = int(os.environ.get("REED_APPRENTICE_PAGES", "10"))   # per keyword, 100 a page
ADZUNA_APPRENTICE_PAGES = int(os.environ.get("ADZUNA_APPRENTICE_PAGES", "4"))  # 50 a page
LONDON_LAT, LONDON_LON = 51.5072, -0.1276

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
    r"\b(senior|head of|head chef|head teacher|headteacher|director|principal|consultant|specialist|"
    r"engineer|developer|solicitor|lawyer|accountant|analyst|architect|surveyor|psycholog\w*|"
    r"psychiatr\w*|therapist|pharmacist|doctor|surgeon|registrar|dentist|executive|partner|professor|"
    r"lecturer|chief|lead|buyer|responsible individual|financial advis[eo]r|(?<!trainee )manager)\b", re.I)
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
    r"just eat rider|this is a training course|fees apply|cost of (the )?training is|paid emails|"
    r"paid surveys|earn cashback)", re.I)
# Advertisers whose "jobs" are paid training courses, paid-survey or cashback schemes, or self-employed work.
BLOCK_EMPLOYERS = ("itolrecruit", "qualifynation", "opiniongroups", "cashback", "maid2clean")
REMOTE = re.compile(r"\b(remote|work from home|working from home|home[- ]based|wfh)\b", re.I)

# Locations.
UK_POSTCODE = re.compile(r"^\s*([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\s*$", re.I)
POSTCODE_IN_TEXT = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?) ?(\d[A-Z]{2})\b")
VAGUE_LONDON = re.compile(
    r"^\s*(((north|south|east|west)(\s+(east|west))?|central|inner|outer|greater)\s*)?(london)?\s*"
    r"(,\s*(uk|united kingdom|england|gb))?\s*$", re.I)
NOT_LONDON = re.compile(
    r"^\s*(united kingdom|uk|england|great britain|gb|south east england|home based|homebased|remote|"
    r"nationwide|various locations|multiple locations)\s*$", re.I)
RULES_VERSION = 9  # bump when the rules change, so older feed jobs are not carried over

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
SOURCE_RANK = {"Employer": -1, "NHS Jobs": 0, "Careerjet": 3, "Find an apprenticeship": 0, "Teaching Vacancies": 0, "Reed": 1, "Adzuna": 2}
SITE_NAME = {"Employer": "TrueShift Jobs", "NHS Jobs": "NHS Jobs", "Careerjet": "Careerjet", "Find an apprenticeship": "Find an apprenticeship", "Teaching Vacancies": "Teaching Vacancies",
             "Reed": "Reed", "Adzuna": "Adzuna"}
APPRENTICE = re.compile(r"\bapprentice(ship)?s?\b", re.I)
GRADUATE = re.compile(r"\b(graduates?|grad scheme|trainee|junior|entry[- ]level|placement|internship|intern)\b", re.I)
GRAD_SENIOR = re.compile(r"\b(senior|lead|head|director|principal|chief|partner)\b", re.I)
# Staff who run apprenticeships, not apprentices.
APPRENTICE_STAFF = re.compile(
    r"\b(assessor|manager|lead|coach|tutor|trainer|co-?ordinator|director|head of|recruiter|consultant|"
    r"educator|portfolio|lecturer|mentor|verifier|iqa)\b", re.I)
GENERIC_WARD = {"town", "central", "village", "park", "north", "south", "east", "west", "centre", "riverside"}

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


def http_text(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8-sig")
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


def tidy_area(area, borough):
    a = clean(area, 60)
    if UK_POSTCODE.match(a) or VAGUE_LONDON.match(a) or NOT_LONDON.match(a):
        return ""
    a = re.sub(r",?\s*(((north|south|east|west)(\s+(east|west))?|central|greater)\s+)?london$", "", a,
               flags=re.I).strip(" ,")
    a = re.sub(r",\s*((north|south|east|west)(\s+(east|west))?|central)$", "", a, flags=re.I).strip(" ,")
    if not a or a.lower() in ("london", "uk", "city of", (borough or "").lower()):
        return ""
    return a


def locate(loc, title, employer, text, pc_info, guess):
    """Work out a job's borough.

    Returns (borough, area, approximate, reason_to_drop). Postcodes are looked up
    exactly; place names are matched against London towns; for adverts that only
    say "London" the title, employer or a postcode in the advert is tried before
    falling back to the borough the job board matched (marked approximate).
    """
    loc = clean(loc, 80)
    if NOT_LONDON.match(loc) or REMOTE.search(str(title or "")):
        return None, "", False, "remote or not in London"
    m = UK_POSTCODE.match(loc)
    if m:
        hit = pc_info.get((m.group(1) + m.group(2)).upper())
        if hit:
            b, ward = hit
            return (b, ward, False, None) if b else (None, "", False, "outside London")
    elif not VAGUE_LONDON.match(loc):
        b = borough_from_text(loc)
        if b:
            return b, loc, False, None
        return None, "", False, "outside London"
    b = borough_from_text(title, employer)
    if b:
        return b, "", False, None
    for pm in POSTCODE_IN_TEXT.finditer(str(text or "")):
        hit = pc_info.get((pm.group(1) + pm.group(2)).upper())
        if hit and hit[0]:
            return hit[0], hit[1], False, None
    if guess:
        return guess, "", True, None
    return None, "", False, "London area not given"


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


def tidy_salary(value, unit=""):
    """Turn free-text school salaries into plain English. Returns (salary text, hourly text or '')."""
    s = clean(value, 120)
    if not s:
        return "", ""
    if re.fullmatch(r"[\d,.]+(\s*(-|–|to)\s*[\d,.]+)?", s):
        s = re.sub(r"([\d,.]+)", r"£\1", s)  # bare numbers are pounds
    elif "£" not in s:
        # money written without a pound sign, e.g. "From 18.20" or "25,000 - 27,000 per annum"
        s = re.sub(r"(?<![\w.])(\d{1,2}\.\d{2}|\d{1,3}(?:,\d{3})+|\d{4,6})(?![\w.])", r"£\1", s)
    s = re.sub(r"\bp\.\s?a\.?(?=[\s,;)]|$)", " pa ", s, flags=re.I)
    fte = bool(re.search(r"\bFTE\b|full[- ]time equivalent", s, re.I))
    actual = bool(re.search(r"\bactual\b", s, re.I))
    hourly = bool(re.search(r"\b(hourly|per hour|an hour|ph)\b|/\s*h(ou)?r\b", s, re.I))
    yearly = bool(re.search(r"\b(annually|per annum|per year|a year|pa)\b|\dpa\b", s, re.I))
    s = re.sub(r"\(\s*(FTE|actual)\s*\)|\b(FTE|actual)\b", " ", s, flags=re.I)
    s = re.sub(r"\b(annually|per annum|per year|a year|hourly|per hour|an hour|ph|pa)\b|/\s*h(ou)?r\b", " ", s, flags=re.I)
    s = re.sub(r"(\d)pa\b", r"\1", s)
    s = re.sub(r"(\d)\.00\b", r"\1", s)
    s = re.sub(r"£\s*(\d{4,})", lambda m: "£{:,}".format(int(m.group(1))), s)
    s = re.sub(r"(£[\d,.]+)\s*(-|–|to)\s*(£[\d,.]+)", r"\1 to \3", s)
    extras = []
    s = re.sub(r"\(([^()]*)\)", lambda m: extras.append(re.sub(r"\s+", " ", m.group(1)).strip(" ,;-")) or " ", s)
    extras = [e for e in extras if e]
    s = re.sub(r"\s+", " ", s).strip(" ,;-/")
    amounts = re.findall(r"£([\d,]+(?:\.\d+)?)", s)
    if not amounts:
        # A pay scale code such as "BEX 08.1" or "MPS/UPS": no amount to put a unit on.
        return ("Pay: " + s)[:110] if s else "", ""
    try:
        if not hourly and all(float(a.replace(",", "")) < 100 for a in amounts):
            hourly = True  # £14.80 is an hourly rate, whatever the unit field says
    except ValueError:
        pass
    if hourly or (not yearly and str(unit).upper() == "HOUR"):
        s += " an hour"
    elif yearly or str(unit).upper() == "YEAR":
        s += " a year"
    if fte and extras and "£" in extras[0]:
        extras[0] += " full-time equivalent"
        fte = False
    if fte:
        extras.append("full-time equivalent")
    elif actual:
        extras.append("actual pay")
    if extras:
        s += " (" + "; ".join(extras) + ")"
    hourly_txt = ""
    if hourly and amounts:
        try:
            v = float(amounts[0].replace(",", ""))
            if 5 < v < 100:
                hourly_txt = money(v)
        except ValueError:
            pass
    return s[:110], hourly_txt


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


def apprenticeship_level(text):
    t = str(text or "").lower()
    m = re.search(r"\blevel\s*([2-7])\b", t)
    if m:
        return int(m.group(1))
    for word, lv in (("degree apprentice", 6), ("higher apprentice", 4), ("advanced apprentice", 3),
                     ("intermediate apprentice", 2)):
        if word in t:
            return lv
    return None


def groups_for(job, text):
    out = []
    jt = job.get("jobType")
    if job.get("apprenticeship"):
        return "Apprentices"
    if job.get("graduate"):
        out.append("Graduates")
    for g, rx in GROUP_RULES.items():
        if g in ("Students", "Parents") and jt == "Full-time":
            continue
        if rx.search(text):
            out.append(g)
    return ", ".join(out)


def senior_pay(salary):
    """True when the advertised pay is clearly above entry level (not an FTE figure)."""
    sal = salary or ""
    nums = [float(x.replace(",", "")) for x in re.findall(r"£([\d,]+(?:\.\d+)?)", sal)]
    if not nums:
        return False
    low = min(nums)
    if "an hour" in sal:
        return low > 25
    if "a year" in sal and not re.search(r"full-time equivalent|\bFTE\b", sal, re.I):
        return low > 35000
    return False


def keep(job, text):
    """Audience, safety and pay rules. Returns a reason to drop, or None."""
    t = job["title"]
    where = job.pop("_drop", None)
    if where:
        return where
    if BLOCK.search(t + " " + text):
        return "blocked words"
    emp = norm_emp(job.get("employer"))
    if emp and any(emp.startswith(b) for b in BLOCK_EMPLOYERS):
        return "blocked advertiser"
    if not job.get("apprenticeship") and not job.get("graduate"):
        if SENIOR.search(t) or senior_pay(job.get("salary")) or (job.get("jobType") != "Part-time" and not ENTRY.search(t)):
            # Senior and professional jobs are kept, but only under the Experienced tab.
            job["experienced"] = True
            job["bestFor"] = "Experienced"
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
        "area": tidy_area(area, borough),
        "jobType": job_type,
        "pay": hourly,
        "salary": salary,
        "link": link,
        "posted": posted.isoformat() if posted else "",
        "closes": closes.isoformat() if closes else "",
        "found": TODAY.isoformat(),
        "_hourly": floor,
    }
    if source == "Find an apprenticeship" or (APPRENTICE.search(job["title"]) and not APPRENTICE_STAFF.search(job["title"])):
        job["apprenticeship"] = True
        lv = apprenticeship_level(str(title) + " " + str(text))
        if lv:
            job["level"] = lv
    t0 = str(job["title"])
    if not job.get("apprenticeship") and GRADUATE.search(t0) and not GRAD_SENIOR.search(t0) and \
            ("graduate" in t0.lower() or not re.search(r"\bmanager\b", t0, re.I)):
        job["graduate"] = True
    job["bestFor"] = groups_for(job, title + " " + text)
    return job


# ---------------------------------------------------------------- postcodes.io
def nice_ward(ward, postcode):
    """A ward name people will recognise, or the postcode district when the ward name is too generic."""
    w = clean(ward, 60)
    if w and w.lower() not in GENERIC_WARD and len(w) > 3:
        return w
    m = UK_POSTCODE.match(str(postcode or ""))
    return m.group(1).upper() if m else ""


def pc_key(p):
    return re.sub(r"\s+", "", str(p or "")).upper()


def postcode_info(postcodes, status=None):
    """{POSTCODE without spaces: (London borough or '' if outside London, ward name)} for valid postcodes."""
    out = {}
    pcs = sorted({pc_key(p) for p in postcodes if p})
    for i in range(0, len(pcs), 100):
        chunk = pcs[i:i + 100]
        try:
            res = http_json("https://api.postcodes.io/postcodes", {"postcodes": chunk})
        except Exception as e:  # noqa: BLE001
            print("postcodes.io lookup failed:", e, file=sys.stderr)
            if status is not None:
                status["postcodeLookupError"] = str(e)[:200]
            return out
        for item in res.get("result") or []:
            r = item.get("result") or {}
            if not r:
                continue
            d = r.get("admin_district")
            out[pc_key(item.get("query"))] = (d if d in BOROUGH_REGION else "",
                                             nice_ward(r.get("admin_ward"), r.get("postcode")))
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
    by_pc = postcode_info([pc for _, _, pc in cands], status)
    jobs = []
    for d, addr, pc in cands:
        hit = by_pc.get(pc_key(pc))
        if hit and not hit[0]:
            continue  # postcode is outside London
        borough = (hit and hit[0]) or borough_from_text(addr.get("addressLocality"), addr.get("streetAddress"))
        if not borough:
            continue
        locality = addr.get("addressLocality") or (hit[1] if hit else "")
        et = [str(x).upper() for x in (d.get("employmentType") or [])]
        jt = "Part-time" if "PART_TIME" in et else ("Full-time" if "FULL_TIME" in et else "")
        sal = ((d.get("baseSalary") or {}).get("value") or {})
        text = clean(d.get("description"), 3000) + " " + str(sal.get("value") or "")
        job = make_job("Teaching Vacancies", d.get("url") or d.get("title"), d.get("title"),
                       (d.get("hiringOrganization") or {}).get("name"), borough,
                       locality, jt, None, None, d.get("url"),
                       parse_date(d.get("datePosted")), parse_date(d.get("validThrough")), text)
        sv, hourly = tidy_salary(sal.get("value"), sal.get("unitText"))
        if sv:
            job["salary"] = sv
        if hourly:
            job["pay"] = hourly
        jobs.append((job, text))
    return jobs


def fetch_reed(key, status):
    auth = "Basic " + base64.b64encode((key + ":").encode()).decode()
    raw, fetched = {}, 0
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
                    jid = r.get("jobId")
                    if jid not in raw:
                        raw[jid] = (r, jt, borough)  # borough = the first borough search that found it
                time.sleep(0.4)
                if len(results) < 100:
                    break
    for borough in BOROUGH_REGION:  # apprenticeships borough by borough, so vague "London" adverts get a best guess
        q = urllib.parse.urlencode({"keywords": "apprentice", "locationName": borough + ", London",
                                    "distanceFromLocation": 2, "resultsToTake": 100})
        try:
            res = http_json("https://www.reed.co.uk/api/1.0/search?" + q, headers={"Authorization": auth})
        except urllib.error.HTTPError as e:
            status.setdefault("errors", []).append("%s apprentice: HTTP %s" % (borough, e.code))
            continue
        results = res.get("results") or []
        fetched += len(results)
        for r in results:
            if r.get("jobId") not in raw:
                raw[r.get("jobId")] = (r, "", borough)
        time.sleep(0.4)
    for kw in ("apprentice", "apprenticeship"):  # then across London
        for p in range(REED_APPRENTICE_PAGES):
            q = urllib.parse.urlencode({"keywords": kw, "locationName": "London", "distanceFromLocation": 15,
                                        "resultsToTake": 100, "resultsToSkip": p * 100})
            try:
                res = http_json("https://www.reed.co.uk/api/1.0/search?" + q, headers={"Authorization": auth})
            except urllib.error.HTTPError as e:
                status.setdefault("errors", []).append("%s search: HTTP %s" % (kw, e.code))
                break
            results = res.get("results") or []
            fetched += len(results)
            for r in results:
                if r.get("jobId") not in raw:
                    raw[r.get("jobId")] = (r, "", None)
            time.sleep(0.4)
            if len(results) < 100:
                break
    status["fetched"] = fetched
    status["uniqueFromSearches"] = len(raw)
    pcs = []
    for r, _, _ in raw.values():
        loc = clean(r.get("locationName"), 80)
        if UK_POSTCODE.match(loc):
            pcs.append(loc)
        pcs += [m.group(1) + m.group(2) for m in POSTCODE_IN_TEXT.finditer(str(r.get("jobDescription") or ""))][:2]
    pc_info = postcode_info(pcs, status)
    jobs = []
    for jid, (r, jt, guess) in raw.items():
        text = clean(r.get("jobDescription"), 3000)
        b, area, is_approx, why = locate(r.get("locationName"), r.get("jobTitle"), r.get("employerName"),
                                         text, pc_info, guess)
        job = make_job("Reed", jid, r.get("jobTitle"), r.get("employerName"), b or "",
                       area, jt, r.get("minimumSalary"), r.get("maximumSalary"),
                       r.get("jobUrl"), parse_date(r.get("date")), parse_date(r.get("expirationDate")), text)
        if is_approx:
            job["approx"] = True
        if why:
            job["_drop"] = why
        jobs.append((job, text))
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
    for p in range(1, ADZUNA_APPRENTICE_PAGES + 1):  # apprenticeships across London
        q = urllib.parse.urlencode({
            "app_id": app_id, "app_key": app_key, "results_per_page": 50, "where": "London",
            "max_days_old": MAX_AGE_DAYS, "sort_by": "date", "what_or": "apprentice apprenticeship",
            "content-type": "application/json"})
        res = http_json("https://api.adzuna.com/v1/api/jobs/gb/search/%d?%s" % (p, q))
        results = res.get("results") or []
        raw.extend(results)
        time.sleep(0.5)
        if len(results) < 50:
            break
    seen, uniq = set(), []
    for r in raw:
        if r.get("id") not in seen:
            seen.add(r.get("id"))
            uniq.append(r)
    raw = uniq
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
        title = str(r.get("title") or "")
        is_approx = False
        if not b:
            b = borough_from_text(title, (r.get("company") or {}).get("display_name"))
        if not b and r.get("latitude") and r.get("longitude"):
            b = by_pt.get((round(float(r["latitude"]), 4), round(float(r["longitude"]), 4)))
            areas = (r.get("location") or {}).get("area") or []
            is_approx = bool(b) and (len(areas) < 3 or bool(VAGUE_LONDON.match(str(areas[-1]))))
        if not b:
            continue
        ct = r.get("contract_time")
        jt = "Part-time" if ct == "part_time" else ("Full-time" if ct == "full_time" else "")
        if not jt:
            jt = ("Part-time" if re.search(r"part[- ]?time", title, re.I)
                  else "Full-time" if re.search(r"full[- ]?time", title, re.I) else "")
        predicted = str(r.get("salary_is_predicted", "0")) == "1"
        lo = None if predicted else r.get("salary_min")
        hi = None if predicted else r.get("salary_max")
        text = str(r.get("description") or "")
        job = make_job("Adzuna", r.get("id"), r.get("title"), (r.get("company") or {}).get("display_name"), b,
                       (r.get("location") or {}).get("display_name"), jt, lo, hi, r.get("redirect_url"),
                       parse_date(r.get("created")), None, text)
        if is_approx:
            job["approx"] = True
        if REMOTE.search(title):
            job["_drop"] = "remote or not in London"
        jobs.append((job, text))
    return jobs


def _tag(e):
    return e.tag.split("}")[-1].lower()


def _kids(e):
    return {_tag(c): c for c in list(e)}


def _txt(e):
    return clean("".join(e.itertext()), 3000) if e is not None else ""


def _first(k, *names):
    for n in names:
        if k.get(n) is not None:
            return k.get(n)
    return None


def any_date(s):
    s = str(s or "").strip()
    d = parse_date(s[:10])
    if d:
        return d
    try:
        return parsedate_to_datetime(s).date()
    except (TypeError, ValueError):
        return None


def fetch_nhs(status):
    """NHS Jobs public search feed: London vacancies, newest first, until adverts pass 30 days old."""
    raw, page, stop = [], 1, False
    cutoff = TODAY - timedelta(days=MAX_AGE_DAYS)
    while page <= NHS_MAX_PAGES and not stop:
        q = urllib.parse.urlencode({"location": "London", "distance": 15, "sort": "publicationDateDesc", "page": page})
        text = http_text("https://www.jobs.nhs.uk/api/v1/search_xml?" + q)
        if page == 1:
            status["sample"] = text[:1500]
        root = ET.fromstring(text.encode("utf-8"))
        items = [e for e in root.iter() if _tag(e) in ("vacancydetails", "vacancy", "item")]
        if not items:
            break
        for e in items:
            k = _kids(e)
            posted = any_date(_txt(_first(k, "postdate", "publicationdate", "pubdate")))
            if posted and posted < cutoff:
                stop = True
            raw.append(k)
        if len(items) < 10:
            break
        page += 1
        time.sleep(0.3)
    status["fetched"] = len(raw)
    status["pages"] = page
    locs = []
    for k in raw:
        node = _first(k, "locations", "location")
        texts = [_txt(x) for x in node.iter() if _txt(x)] if node is not None else []
        k["_locs"] = texts
        for t in texts:
            m = POSTCODE_IN_TEXT.search(t.upper())
            if m:
                locs.append(m.group(1) + m.group(2))
    info = postcode_info(locs, status)
    jobs = []
    for k in raw:
        borough, area = None, ""
        for t in k["_locs"]:
            m = POSTCODE_IN_TEXT.search(t.upper())
            hit = info.get(pc_key(m.group(1) + m.group(2))) if m else None
            if hit and hit[0]:
                borough, area = hit[0], t.split(",")[0]
                break
            if not hit:
                b = borough_from_text(t)
                if b:
                    borough, area = b, t.split(",")[0]
                    break
        title = _txt(k.get("title"))
        employer = _txt(_first(k, "employer", "employername"))
        desc = _txt(k.get("description"))
        wp = (_txt(k.get("workingpattern")) + " " + _txt(k.get("type"))).lower()
        both = (wp + " " + title + " " + desc).lower()
        if re.search(r"part[- ]?time|\bbank\b|job share|flexible hours", both):
            jt = "Part-time"
        elif re.search(r"full[- ]?time", both):
            jt = "Full-time"
        else:
            jt = ""
        sal_txt, hourly = tidy_salary(_txt(k.get("salary")), "YEAR")
        link = _txt(_first(k, "url", "link", "guid"))
        vid = _txt(_first(k, "id", "reference")) or link
        job = make_job("NHS Jobs", vid, title, employer, borough or "", area, jt, None, None, link,
                       any_date(_txt(_first(k, "postdate", "publicationdate", "pubdate"))),
                       any_date(_txt(_first(k, "closedate", "closingdate"))), title + " " + desc)
        if sal_txt:
            job["salary"] = sal_txt
        if hourly:
            job["pay"] = hourly
        if not borough:
            job["_drop"] = "outside London"
        jobs.append((job, title + " " + desc))
    return jobs


def runner_ip():
    try:
        return http_text("https://api.ipify.org", timeout=15).strip()
    except Exception:  # noqa: BLE001
        return "127.0.0.1"


def fetch_careerjet(key, status):
    """Careerjet publisher API: newest jobs borough by borough (vague locations get the searched borough)."""
    auth = "Basic " + base64.b64encode((key + ":").encode()).decode()
    ip = runner_ip()
    raw, fetched = {}, 0
    for borough in BOROUGH_REGION:
        for page in range(1, CAREERJET_PAGES + 1):
            q = urllib.parse.urlencode({"locale_code": "en_GB", "location": borough + ", London", "radius": 3,
                                        "sort": "date", "page_size": 100, "page": page, "fragment_size": 300,
                                        "user_ip": ip, "user_agent": UA})
            try:
                res = http_json("https://search.api.careerjet.net/v4/query?" + q,
                                headers={"Authorization": auth, "Referer": "https://trueshiftjobs.com/"})
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", "replace")[:300]
                except Exception:  # noqa: BLE001
                    pass
                status["httpError"] = "%s %s" % (e.code, body)
                status["keyLength"] = len(key)
                raise
            if res.get("type") != "JOBS":
                status.setdefault("locationMessages", {})[borough] = res.get("message")
                break
            jobs = res.get("jobs") or []
            fetched += len(jobs)
            for r in jobs:
                k = r.get("url") or (str(r.get("title")) + "|" + str(r.get("company")))
                if k not in raw:
                    raw[k] = (r, borough)
            if page >= int(res.get("pages") or 1) or len(jobs) < 100:
                break
            time.sleep(0.4)
        time.sleep(0.3)
    status["fetched"] = fetched
    status["uniqueFromSearches"] = len(raw)
    out = []
    for k, (r, guess) in raw.items():
        loc = clean(r.get("locations"), 80)
        text = clean(r.get("description"), 3000)
        b, area, is_approx, why = locate(loc, r.get("title"), r.get("company"), text, {}, guess)
        wh = (str(r.get("title")) + " " + text).lower()
        jt = "Part-time" if re.search(r"part[- ]?time", wh) else ("Full-time" if re.search(r"full[- ]?time", wh) else "")
        st = str(r.get("salary_type") or "").upper()
        lo, hi = r.get("salary_min"), r.get("salary_max")
        job = make_job("Careerjet", k, r.get("title"), r.get("company"), b or "", area, jt,
                       lo if st == "H" else None, hi if st == "H" else None, r.get("url"),
                       any_date(r.get("date")), None, text)
        if st != "H" and r.get("salary"):
            job["salary"] = tidy_salary(r.get("salary"), {"Y": "YEAR", "M": "", "W": "", "D": ""}.get(st, ""))[0]
        if is_approx:
            job["approx"] = True
        if why:
            job["_drop"] = why
        out.append((job, text))
    return out


def faa_pay(wage):
    """(hourly text, salary text, hourly floor) from a Find an apprenticeship wage object."""
    wage = wage or {}
    wt = str(wage.get("wageType") or "")
    amt = wage.get("wageAmount")
    unit = str(wage.get("wageUnit") or "")
    if wt == "ApprenticeshipMinimum":
        return money(APPRENTICE_HOURLY), "Apprentice minimum wage (" + money(APPRENTICE_HOURLY) + " an hour)", None
    if wt == "NationalMinimum":
        return "", "National Minimum Wage for your age", None
    if wt == "CompetitiveSalary":
        return "", "Competitive salary", None
    if isinstance(amt, (int, float)) and amt > 0:
        if unit == "Annually":
            return "", money(amt) + " a year", None
        if unit == "Monthly":
            return "", money(amt) + " a month", None
        if unit == "Weekly":
            return "", money(amt) + " a week", None
        return pay_fields(amt, amt, True)
    return "", "", None


def fetch_apprenticeships(key, status):
    """GOV.UK Find an apprenticeship: every advert within 20 miles of central London, newest first."""
    headers = {"X-Version": "2", "Ocp-Apim-Subscription-Key": key}
    raw, page, pages = [], 1, 1
    while page <= min(pages, FAA_MAX_PAGES):
        q = urllib.parse.urlencode({"Lat": LONDON_LAT, "Lon": LONDON_LON, "DistanceInMiles": 20,
                                    "PageSize": 100, "PageNumber": page, "Sort": "AgeDesc"})
        res = http_json("https://api.apprenticeships.education.gov.uk/vacancies/vacancy?" + q, headers=headers)
        pages = int(res.get("totalPages") or 1)
        raw.extend(res.get("vacancies") or [])
        page += 1
        time.sleep(0.3)
    status["fetched"] = len(raw)
    pcs = [a.get("postcode") for v in raw for a in (v.get("addresses") or []) if a.get("postcode")]
    info = postcode_info(pcs, status)
    jobs = []
    for v in raw:
        hit, pc = None, ""
        for a in v.get("addresses") or []:
            h = info.get(pc_key(a.get("postcode")))
            if h and h[0]:
                hit, pc = h, a.get("postcode")
                break
        course = v.get("course") or {}
        text = " ".join(str(x or "") for x in (v.get("description"), course.get("title")))
        hours = v.get("hoursPerWeek")
        jt = "Part-time" if isinstance(hours, (int, float)) and 0 < hours < 30 else "Full-time"
        job = make_job("Find an apprenticeship", v.get("vacancyReference"), v.get("title"), v.get("employerName"),
                       hit[0] if hit else "", hit[1] if hit else "", jt, None, None,
                       v.get("vacancyUrl"), parse_date(v.get("postedDate")), parse_date(v.get("closingDate")), text)
        job["pay"], job["salary"], _ = faa_pay(v.get("wage"))
        if isinstance(course.get("level"), int) and 2 <= course["level"] <= 7:
            job["level"] = course["level"]
        ctitle = re.sub(r"\s*\(level \d\)\s*$", "", clean(course.get("title"), 90), flags=re.I)
        if ctitle:
            job["course"] = ctitle[0].upper() + ctitle[1:]
        st = parse_date(v.get("startDate"))
        if st:
            job["start"] = st.isoformat()
        wk = clean((v.get("wage") or {}).get("workingWeekDescription"), 120)
        if isinstance(hours, (int, float)) and hours > 0:
            job["hours"] = ("%g hours a week" % hours) + (". " + wk if wk else "")
        elif wk:
            job["hours"] = wk
        if not hit:
            job["_drop"] = "outside London"
        jobs.append((job, text))
    return jobs


def apply_link(text):
    t = clean(text, 300)
    m = re.search(r"https?://\S+", t)
    if m:
        return m.group(0).rstrip(".,)")
    m = re.search(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", t)
    if m:
        return "mailto:" + m.group(0)
    m = re.search(r"\b(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)*\.(co\.uk|com|org|uk|net|org\.uk|london)(/\S*)?", t, re.I)
    if m:
        return "https://" + m.group(0)
    return ""


MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                       "september", "october", "november", "december"], 1)}


def read_advert(text):
    """Pick job details out of an advert the employer pasted into the form."""
    t = str(text or "").replace("\r", "")
    flat = clean(t, 5000)
    out = {}
    m = re.search(r"(?im)^\s*(?:job title|role|position)\s*[:\-]\s*(.+)$", t)
    if m:
        out["title"] = clean(m.group(1), 90)
    else:
        for line in t.split("\n"):
            line = clean(line, 200)
            if line and not re.match(r"https?://", line) and len(line) <= 90:
                out["title"] = line.rstrip(".:")
                break
    m = re.search(r"£\s?\d[\d,]*(?:\.\d{1,2})?(?:\s*(?:-|–|to)\s*£?\s?\d[\d,]*(?:\.\d{1,2})?)?"
                  r"(?:\s*(?:per|an|a|/)\s*(?:hour|hr|year|annum|week|month)|\s*p\.?\s?[ah]\.?)?", flat, re.I)
    if m:
        out["pay"] = m.group(0).strip()
    m = re.search(r"(\d{1,2}(?:\.\d)?(?:\s*(?:-|–|to)\s*\d{1,2}(?:\.\d)?)?)\s*hours?(?:\s*(?:per|a)\s*week)?", flat, re.I)
    if m:
        out["hours"] = m.group(0).strip()
    if re.search(r"apprentice", flat, re.I):
        out["type"] = "Apprenticeship"
    elif re.search(r"part[- ]?time", flat, re.I):
        out["type"] = "Part-time"
    elif re.search(r"full[- ]?time", flat, re.I):
        out["type"] = "Full-time"
    m = re.search(r"(?:closing date|closes|deadline|apply by)[^0-9a-z]{0,10}(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", flat, re.I)
    if m:
        y = int(m.group(3)); y = y + 2000 if y < 100 else y
        try:
            out["closes"] = date(y, int(m.group(2)), int(m.group(1))).strftime("%d/%m/%Y")
        except ValueError:
            pass
    else:
        m = re.search(r"(?:closing date|closes|deadline|apply by)\D{0,10}(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)\s+(\d{4})", flat, re.I)
        if m and m.group(2).lower() in MONTHS:
            try:
                out["closes"] = date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).strftime("%d/%m/%Y")
            except ValueError:
                pass
    m = POSTCODE_IN_TEXT.search(t.upper())
    if m:
        out["postcode"] = m.group(1) + " " + m.group(2)
    a = apply_link(flat)
    if a:
        out["apply"] = a
    return out


def fetch_employer_posts(url, status):
    """Approved jobs from the employer Google Form (published Public tab, CSV)."""
    rows = list(csv.reader(io.StringIO(http_text(url))))
    status["fetched"] = max(0, len(rows) - 1)
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]
    status["columns"] = [h.strip() for h in rows[0]]

    def col(*words):
        for i, h in enumerate(head):
            if any(w in h for w in words):
                return i
        return None
    idx = {k: col(*w) for k, w in {
        "time": ("timestamp",), "title": ("job title",), "company": ("company name", "employer"),
        "borough": ("borough",), "area": ("area", "postcode"), "type": ("job type",), "hours": ("hours",),
        "pay": ("pay", "salary"), "closes": ("closing",), "apply": ("how to apply", "apply"),
        "desc": ("description", "about the job"), "status": ("status",), "website": ("website",),
        "advert": ("paste", "your job advert")}.items()}
    jobs = []
    auto = status.setdefault("autoFilled", [])
    for r in rows[1:]:
        sheet = lambda k: (r[idx[k]].strip() if idx[k] is not None and idx[k] < len(r) else "")
        if idx["status"] is not None and sheet("status").lower() != "approved":
            continue
        ad = read_advert(sheet("advert")) if sheet("advert") else {}
        if ad.get("postcode") and not sheet("area"):
            ad["area"] = ad["postcode"]
        if not sheet("apply") and not ad.get("apply") and sheet("website"):
            ad["apply"] = sheet("website")
        if not sheet("desc") and sheet("advert"):
            ad["desc"] = sheet("advert")
        filled = [k for k in ("title", "type", "hours", "pay", "closes", "apply", "area", "desc") if not sheet(k) and ad.get(k)]
        get = lambda k: sheet(k) or ad.get(k, "")
        if not get("title"):
            status.setdefault("needsDetails", []).append(sheet("company") or "(no company)")
            continue
        if filled:
            auto.append({"title": get("title"), "filled": filled})
        borough = get("borough") if get("borough") in BOROUGH_REGION else borough_from_text(get("borough"), get("area"))
        if not borough and UK_POSTCODE.match(get("area")):
            hit = postcode_info([get("area")]).get(pc_key(get("area")))
            borough = hit[0] if hit else None
        if not borough and sheet("advert"):
            borough = borough_from_text(sheet("advert")[:600])
        jtype = get("type").lower()
        jt = "Part-time" if "part" in jtype else "Full-time"
        pay_txt = clean(get("pay"), 80)
        nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", pay_txt)]
        lo = min(nums) if nums else None
        hourly = lo is not None and lo < 100
        desc = clean(get("desc"), 600)
        full_desc = clean(get("desc"), 3000)
        text = " ".join([get("title"), desc, get("hours")])
        sid = hashlib.sha1((get("time") + "|" + get("title") + "|" + get("company")).encode()).hexdigest()[:12]
        job = make_job("Employer", sid, get("title"), get("company"), borough or "", get("area"), jt,
                       lo if hourly else None, lo if hourly else None, apply_link(get("apply")),
                       parse_date(get("time")) or TODAY, parse_date(get("closes")), text)
        if not hourly and pay_txt:
            job["salary"] = tidy_salary(pay_txt)[0] or pay_txt
        if get("hours"):
            job["hours"] = clean(get("hours"), 120)
        if desc:
            job["about"] = desc[:300]
            job["description"] = full_desc
        site = get("website")
        if site:
            job["website"] = site if site.startswith("http") else "https://" + site
        job["page"] = "/jobs/posted/%s/" % sid
        if "apprentice" in jtype:
            job["apprenticeship"] = True
            job["bestFor"] = "Apprentices"
        if not borough:
            job["_drop"] = "London area not given"
        elif not job["link"]:
            job["_drop"] = "no way to apply"
        jobs.append((job, text))
    return jobs


# ---------------------------------------------------------------- merge
def fresh(job):
    c = parse_date(job.get("closes"))
    if job.get("apprenticeship") and c:
        # Apprenticeships are advertised months ahead: keep them while they are still open.
        p = parse_date(job.get("posted"))
        return c >= TODAY and not (p and p > TODAY + timedelta(days=1))
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
    bits = ["Posted directly by the employer."] if job["source"] == "Employer" else \
        ["Listed on " + SITE_NAME[job["source"]] + "."]
    if job.get("about"):
        bits.append(job["about"].rstrip(".") + ".")
    if job.get("apprenticeship"):
        lv = job.get("level")
        course = job.get("course")
        head = ("Level %d apprenticeship" % lv) if lv else "Apprenticeship"
        bits.append(head + (": " + course if course else "") + ".")
        s = parse_date(job.get("start"))
        if s:
            bits.append("Starts " + s.strftime("%-d %B %Y") + ".")
    if job.get("salary") and not job.get("pay"):
        bits.append(job["salary"][0].upper() + job["salary"][1:] + ".")
    elif job.get("salary") and " to " in job["salary"]:
        bits.append(job["salary"][0].upper() + job["salary"][1:] + ".")
    c = parse_date(job.get("closes"))
    if c:
        bits.append("Closes " + c.strftime("%-d %B %Y") + ".")
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
    emp_csv = os.environ.get("EMPLOYER_JOBS_CSV", "").strip()
    if emp_csv:
        run("Employer", fetch_employer_posts, emp_csv)
    else:
        status["sources"]["Employer"] = {"skipped": "no EMPLOYER_JOBS_CSV secret"}
    run("NHS Jobs", fetch_nhs)
    # Careerjet only accepts calls from fixed, declared IP addresses, which GitHub's runners do not have.
    # Switched off unless CAREERJET_ENABLED=1 (for example on a server with a fixed IP).
    cj_key = os.environ.get("CAREERJET_API_KEY", "").strip() if os.environ.get("CAREERJET_ENABLED") == "1" else ""
    if cj_key:
        run("Careerjet", fetch_careerjet, cj_key)
    else:
        status["sources"]["Careerjet"] = {"skipped": "switched off: needs a fixed IP address"}
    faa_key = os.environ.get("APPRENTICESHIP_API_KEY", "").strip()
    if faa_key:
        run("Find an apprenticeship", fetch_apprenticeships, faa_key)
    else:
        status["sources"]["Find an apprenticeship"] = {"skipped": "no APPRENTICESHIP_API_KEY secret"}
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
            prev = json.loads(FEED.read_text())
            if prev.get("rulesVersion") == RULES_VERSION:
                previous = [j for j in prev.get("jobs", []) if fresh(j)]
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
    by_level = {}
    by_group = {}
    for j in jobs:
        for g in [x.strip() for x in str(j.get("bestFor") or "").split(",") if x.strip()] or ["(none)"]:
            by_group[g] = by_group.get(g, 0) + 1
        if j.get("apprenticeship"):
            lv = str(j.get("level") or "not stated")
            by_level[lv] = by_level.get(lv, 0) + 1
        by_region[j["region"]] = by_region.get(j["region"], 0) + 1
        by_type[j.get("jobType") or "Not stated"] += 1
    status.update({"total": len(jobs), "duplicatesRemoved": dupes, "byRegion": by_region, "byJobType": by_type,
                   "carriedOver": len(previous), "areaApproximate": sum(1 for j in jobs if j.get("approx")),
                   "apprenticeships": sum(by_level.values()), "apprenticeshipLevels": by_level,
                   "byGroup": by_group})
    FEED.write_text(json.dumps({"generated": status["generated"], "maxAgeDays": MAX_AGE_DAYS,
                                "rulesVersion": RULES_VERSION, "jobs": jobs}, ensure_ascii=False, separators=(",", ":")))
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False))
    print(json.dumps(status, indent=2))
    if not jobs and all("error" in s or "skipped" in s for s in status["sources"].values()):
        print("No source worked; keeping the job going so the page still loads.", file=sys.stderr)


if __name__ == "__main__":
    main()
