from datetime import datetime, tzinfo, timedelta
import re
from typing import List, Tuple
from maubot_life_tracking import db
import csv
from io import StringIO


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


def render_csv(ors: List[Tuple[db.Outreach, List[db.Response]]]) -> str:
    out = StringIO()
    fieldnames = ["room_id", "outreach_event_id", "prompt_name", "outreach_timestamp_utc", "outreach_message", "response_event_id", "response_timestamp_utc", "response_message"]
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for outreach, responses in ors:
        ofields = dict(
            room_id=outreach.room_id,
            outreach_event_id=outreach.event_id,
            prompt_name=outreach.prompt_name,
            outreach_timestamp_utc=outreach.timestamp.isoformat(),
            outreach_message=outreach.message,
        )
        if not responses:
            writer.writerow(ofields)
        for response in responses:
            row = dict(
                response_event_id=response.event_id,
                response_timestamp_utc=response.timestamp.isoformat(),
                response_message=response.message,
                **ofields
            )
            writer.writerow(row)
    return out.getvalue()
