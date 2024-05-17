from datetime import datetime, tzinfo, timedelta
import re


DATETIME_RE = re.compile(r"(today|tom|tomorrow|\d\d\d\d-\d\d-\d\d)\s+\d\d\:\d\d")
INTERVAL_RE = re.compile(r"(\d+)(d|h|m|s)")


def parse_datetime(inp: str, tz: tzinfo) -> datetime:
    inp = inp.lower()
    if not DATETIME_RE.fullmatch(inp):
        raise ValueError(f"datetime should match regex: {DATETIME_RE}")
    parts = inp.split()
    if parts[0] == "today":
        parse = f"{datetime.now(tz).strftime('%Y-%m-%d')} {parts[1]}"
    elif parts[0] in ["tom", "tomorrow"]:
        parse = f"{(datetime.now(tz)+timedelta(days=1)).strftime('%Y-%m-%d')} {parts[1]}"
    else:
        parse = f"{parts[0]} {parts[1]}"
    return datetime.strptime(parse, "%Y-%m-%d %H:%M").replace(tzinfo=tz)


def parse_interval(inp: str) -> timedelta:
    inp = inp.lower()
    match = INTERVAL_RE.fullmatch(inp)
    if not match:
        raise ValueError(f"interval should match regex: {DATETIME_RE}")
    n = int(match.group(1))
    if match.group(2) == "s":
        return timedelta(seconds=n)
    elif match.group(2) == "m":
        return timedelta(minutes=n)
    elif match.group(2) == "h":
        return timedelta(hours=n)
    return timedelta(days=n)


def render_template(template: str, now: datetime) -> str:
    date = now.strftime("%A, %B %-d, %Y")
    return template.replace("$(date)", date)
