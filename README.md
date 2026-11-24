# TrueShift Jobs

Free list of checked, still-open part-time jobs across London for students, parents returning to work and people new to the UK.

Live site: https://trueshiftjobs.com

How it updates:

- `index.html` holds the jobs checked by Claude. It is rebuilt every morning from the TrueShift jobs sheet.
- `feed.json` holds jobs from official job feeds (GOV.UK Teaching Vacancies, Reed and, if set up, Adzuna). The **Nightly job feed** workflow (`.github/workflows/feed.yml`) refreshes it every day at about 05:17 UK time using `scripts/fetch_feed.py`. It keeps only London jobs posted in the last 30 days, removes duplicates across the feeds and sorts each job into a region and borough.
- `feed-status.json` says how the last feed run went.

Keys are stored as repository secrets: `REED_API_KEY`, and optionally `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.

Please don't edit `index.html` or `feed.json` by hand, as the next update will replace them.

© 2026 TrueShift Jobs. All rights reserved.
