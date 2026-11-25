"""One-off MailerLite setup and capability check.

Creates the "Job alerts" group and the Interests and Areas fields if they are
missing, then checks whether this plan allows creating email campaigns through
the API by making a draft and deleting it straight away. Nothing is sent.
Writes the results (no keys, no subscriber data) to mailerlite-status.json.
"""
import json
import os
import pathlib
import urllib.error
import urllib.request

API = "https://connect.mailerlite.com/api"
KEY = os.environ.get("MAILERLITE_API_KEY", "").strip()
ROOT = pathlib.Path(__file__).resolve().parent.parent


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Accept": "application/json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode() or "{}"
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}


def main():
    out = {"keyPresent": bool(KEY)}
    if not KEY:
        out["error"] = "MAILERLITE_API_KEY secret is missing"
    else:
        st, me = call("GET", "/groups?limit=100")
        out["authOk"] = st == 200
        if st != 200:
            out["error"] = "API returned %s: %s" % (st, me.get("message"))
        else:
            groups = {g["name"]: g["id"] for g in me.get("data", [])}
            if "Job alerts" not in groups:
                st, g = call("POST", "/groups", {"name": "Job alerts"})
                out["groupCreate"] = st
                if st in (200, 201):
                    groups["Job alerts"] = g["data"]["id"]
            out["jobAlertsGroupId"] = groups.get("Job alerts")

            st, f = call("GET", "/fields?limit=100")
            keys = {x["key"]: x["name"] for x in f.get("data", [])}
            for name in ("Interests", "Areas"):
                if name.lower() not in keys:
                    st2, _ = call("POST", "/fields", {"name": name, "type": "text"})
                    out["fieldCreate_" + name] = st2
            st, f = call("GET", "/fields?limit=100")
            out["fields"] = sorted(x["key"] for x in f.get("data", []))

            st, forms = call("GET", "/forms/embedded?limit=50")
            out["embeddedForms"] = [{"id": x.get("id"), "name": x.get("name")} for x in forms.get("data", [])] if st == 200 else st

            if out.get("jobAlertsGroupId"):
                body = {"name": "API check - safe to delete", "type": "regular",
                        "emails": [{"subject": "API check", "from_name": "TrueShift Jobs",
                                    "from": "hello@trueshiftjobs.com",
                                    "content": "<html><body><p>API check</p><p><a href=\"{$unsubscribe}\">Unsubscribe</a></p></body></html>"}],
                        "groups": [out["jobAlertsGroupId"]]}
                st, c = call("POST", "/campaigns", body)
                out["campaignWithContent"] = st
                out["campaignMessage"] = c.get("message")
                if c.get("errors"):
                    out["campaignErrors"] = c["errors"]
                cid = (c.get("data") or {}).get("id")
                if cid:
                    out["campaignDeleted"] = call("DELETE", "/campaigns/%s" % cid)[0]
                if st not in (200, 201):
                    body["emails"][0].pop("content")
                    st, c = call("POST", "/campaigns", body)
                    out["campaignWithoutContent"] = st
                    out["campaignMessage2"] = c.get("message")
                    cid = (c.get("data") or {}).get("id")
                    if cid:
                        out["campaignDeleted2"] = call("DELETE", "/campaigns/%s" % cid)[0]
    (ROOT / "mailerlite-status.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
