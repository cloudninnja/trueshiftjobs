"""Quick checks of the job rules. Run with: python -m pytest tests -q"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))

import fetch_feed as feed  # noqa: E402
import weekly_emails as weekly  # noqa: E402


def test_senior_pay_moves_high_salaries_to_experienced():
    assert feed.senior_pay("£50,000 a year")
    assert feed.senior_pay("£77.79 an hour")


def test_entry_level_pay_stays():
    assert not feed.senior_pay("£15.45 an hour")
    assert not feed.senior_pay("£29,561 to £29,983 a year")
    assert not feed.senior_pay("")


def test_full_time_equivalent_is_not_treated_as_senior():
    assert not feed.senior_pay("£43,339 a year (full-time equivalent)")


def test_weekly_email_pay_shows_unit():
    assert weekly.pay_text({"salary": "£13.00 an hour"}) == "£13.00 an hour"
    long = {"salary": "£12,317 to £24,634 a year Full time salary £29,000 pro rata for 20 hours"}
    assert weekly.pay_text(long) == "£12,317 to £24,634 a year"
    assert weekly.pay_text({}) == "Pay in advert"


def test_weekly_email_hides_senior_jobs_from_entry_emails():
    assert weekly.too_senior({"salary": "£50,000 a year"})
    assert not weekly.too_senior({"salary": "£12.71 an hour"})


def test_rules_version_is_set():
    assert isinstance(feed.RULES_VERSION, int) and feed.RULES_VERSION >= 9
