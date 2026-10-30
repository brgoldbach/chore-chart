"""Chore chart server: UI, storage, sheet rendering, printing, and auto-print.

Related Documentation: DOCS.md ("Backup", "Data").
"""

import json
import os
import re
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

from schedule import UNIT_DAYS, add_months, calendar_rows, due_sections, duration, parse_month, year_hours
from sheet import PERSON_COLORS, PRESETS, PRINTOUT_DEFAULTS, clean_options, render

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
CHORES_FILE = DATA_DIR / "chores.json"
OWNERS_FILE = DATA_DIR / "owners.json"
DAILY_FILE = DATA_DIR / "daily.json"
DONE_FILE = DATA_DIR / "done.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
PRINTOUT_FILE = DATA_DIR / "printout.json"
INDEX_FILE = Path(__file__).parent / "static" / "index.html"
PORT = int(os.environ.get("PORT", 8099))
QUEUE = "chores"
MEDIA = {"letter": "na_letter_8.5x11in", "a4": "iso_a4_210x297mm"}
MONTH_PATTERN = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
TIME_PATTERN = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
EXPORT_VERSION = 5
LAYOUT_NAME_MAX = 30
# Every chore field added after the first release needs a default here, so older files still load.
CHORE_DEFAULTS = {"minutes": None, "season": None, "note": "", "shared": False, "weekday": None}
DEFAULT_SETTINGS = {"printer_name": "", "printer_uri": "", "paper_size": "letter",
                    "auto_print": False, "auto_print_time": "07:00",
                    "last_auto_print": "", "auto_print_status": ""}
EDITABLE_SETTINGS = {"printer_name": str, "printer_uri": str, "paper_size": str,
                     "auto_print": bool, "auto_print_time": str}

# Under the Supervisor the app shares the host network, so only ingress may connect.
TRUSTED_CLIENT = "172.30.32.2" if "SUPERVISOR_TOKEN" in os.environ else None

# Held across each read-modify-write, so saves from two people never mix.
save_lock = threading.Lock()


class BadRequest(Exception):
    pass


class PrintError(Exception):
    pass


def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save_json(path, data):
    # Replace atomically so a power cut never leaves a half-written file.
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2))
    temp.replace(path)


def load_chores():
    return [{**CHORE_DEFAULTS, **chore} for chore in load_json(CHORES_FILE, [])]


def save_chores(chores):
    """Save `chores` and drop the check-offs of deleted chores. Call under save_lock."""
    save_json(CHORES_FILE, chores)
    ids = {chore["id"] for chore in chores}
    save_json(DONE_FILE, {chore_id: keys for chore_id, keys in load_json(DONE_FILE, {}).items()
                          if chore_id in ids})


def load_owners():
    return load_json(OWNERS_FILE, [])


def load_daily():
    return load_json(DAILY_FILE, [])


def load_settings():
    return {**DEFAULT_SETTINGS, **load_json(SETTINGS_FILE, {})}


def load_printout():
    """Return {"options", "saved", "colors"}: the printout options, the saved layouts, and each person's color.

    Options and saved layouts have every option filled in. `colors` maps owner names to PERSON_COLORS names.
    """
    stored = load_json(PRINTOUT_FILE, {})

    def known(options):
        # An option that a later version removed is dropped, so its old files still load.
        return clean_options({name: value for name, value in options.items() if name in PRINTOUT_DEFAULTS})

    return {"options": known(stored.get("options", {})),
            "saved": [{"name": layout["name"], "options": known(layout["options"])}
                      for layout in stored.get("saved", [])],
            "colors": {name: color for name, color in stored.get("colors", {}).items() if color in PERSON_COLORS}}


def validate_printout(changes, current, owners):
    """Return `current` with `changes` applied: new "options" merge in; new "saved" and "colors" replace.

    Colors of people who are not in `owners` drop out.
    """
    if not isinstance(changes, dict) or not set(changes) <= {"options", "saved", "colors"}:
        raise BadRequest("Invalid printout.")
    options, saved = changes.get("options", {}), changes.get("saved", current["saved"])
    colors = changes.get("colors", current["colors"])
    if (not isinstance(options, dict) or not isinstance(saved, list) or not isinstance(colors, dict)
            or not all(isinstance(layout, dict) and set(layout) == {"name", "options"} for layout in saved)):
        raise BadRequest("Invalid printout.")
    if not all(color in PERSON_COLORS for color in colors.values()):
        raise BadRequest("Unknown color.")
    try:
        options = clean_options({**current["options"], **options})
        saved = [{"name": layout["name"], "options": clean_options(layout["options"])} for layout in saved]
    except ValueError as error:
        raise BadRequest(str(error))
    names = clean_names([layout["name"] for layout in saved], "layout names")
    if any(len(name) > LAYOUT_NAME_MAX for name in names):
        raise BadRequest(f"A layout name can have at most {LAYOUT_NAME_MAX} characters.")
    if {name.lower() for name in names} & {name.lower() for name in PRESETS}:
        raise BadRequest("A built-in layout already has that name.")
    return {"options": options, "saved": [{**layout, "name": name} for layout, name in zip(saved, names)],
            "colors": {name: color for name, color in colors.items() if name in owners}}


def printout_reply(printout):
    """Return `printout` with what the Printout card shows beside it: the built-in layouts and the color names."""
    palette = {name: "#%02x%02x%02x" % color for name, color in PERSON_COLORS.items()}
    return {**printout, "presets": PRESETS, "palette": palette}


def clean_names(names, label):
    """Return `names` trimmed. Reject blanks and repeats that differ only in case."""
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise BadRequest(f"Expected a list of {label}.")
    names = [name.strip() for name in names]
    if "" in names or len({name.lower() for name in names}) != len(names):
        raise BadRequest(f"{label.capitalize()} must be unique and not blank.")
    return names


def validate_owners(owners, chores):
    owners = clean_names(owners, "owner names")
    in_use = {owner for chore in chores for owner in chore["owners"]} - set(owners)
    if in_use:
        raise BadRequest(f"Reassign the chores of {', '.join(sorted(in_use))} first.")
    return owners


def rename_owner(owners, chores, old, new):
    """Return the owners and chores with owner `old` renamed to `new` everywhere."""
    if old not in owners or not isinstance(new, str):
        raise BadRequest("Unknown owner.")
    renamed = clean_names([new if owner == old else owner for owner in owners], "owner names")
    new = renamed[owners.index(old)]
    return renamed, [{**chore, "owners": [new if owner == old else owner for owner in chore["owners"]]}
                     for chore in chores]


def validate_chores(chores, owners):
    """Return the chores in stored form. Assign an ID to each new chore."""
    if not isinstance(chores, list):
        raise BadRequest("Expected a list of chores.")
    valid = []
    for raw in chores:
        try:
            chore = {**CHORE_DEFAULTS, **raw}
            item = {"id": str(chore.get("id") or uuid.uuid4().hex),
                    "name": chore["name"].strip(),
                    "owners": [owner.strip() for owner in chore["owners"]],
                    "every": int(chore["every"]), "unit": chore["unit"], "align": chore["align"],
                    "minutes": int(chore["minutes"]) if chore["minutes"] else None,
                    "season": [int(month) for month in chore["season"]] if chore["season"] else None,
                    "note": chore["note"].strip(),
                    "shared": bool(chore["shared"]),
                    "weekday": (int(chore["weekday"]) if chore["weekday"] is not None and chore["unit"] == "week"
                                else None)}
        except (KeyError, TypeError, ValueError, AttributeError):
            raise BadRequest(f"Malformed chore: {raw}")
        name = item["name"] or "unnamed"
        season = item["season"]
        if (not item["name"] or item["every"] < 1 or item["unit"] not in UNIT_DAYS
                or not MONTH_PATTERN.fullmatch(str(item["align"]))
                or (item["minutes"] is not None and item["minutes"] < 0)
                or (item["weekday"] is not None and not 0 <= item["weekday"] <= 6)
                or (season and (len(season) != 2 or not all(1 <= month <= 12 for month in season)))):
            raise BadRequest(f"Invalid chore: {name}")
        if len(set(item["owners"])) != len(item["owners"]) or not set(item["owners"]) <= set(owners):
            raise BadRequest(f"Unknown or repeated owner in: {name}")
        if item["shared"] and len(item["owners"]) < 2:
            raise BadRequest(f"A shared chore needs 2 or more owners: {name}")
        valid.append(item)
    return valid


def validate_settings(changes, current, today):
    """Return `current` with the user's `changes` applied."""
    if (not isinstance(changes, dict) or not set(changes) <= EDITABLE_SETTINGS.keys()
            or not all(isinstance(value, EDITABLE_SETTINGS[key]) for key, value in changes.items())):
        raise BadRequest("Invalid settings.")
    settings = {**current, **changes}
    settings["printer_uri"] = settings["printer_uri"].strip()
    if settings["paper_size"] not in MEDIA or not TIME_PATTERN.fullmatch(settings["auto_print_time"]):
        raise BadRequest("Invalid settings.")
    if settings["auto_print"] and not current["auto_print"]:
        # Count this month as printed, so turning auto-print on does not print at once.
        settings["last_auto_print"] = f"{today:%Y-%m}"
    return settings


def should_auto_print(now, settings):
    """Return True if this month's auto-print is due and not yet sent."""
    hour, minute = map(int, settings["auto_print_time"].split(":"))
    first = now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
    return settings["auto_print"] and now >= first and settings["last_auto_print"] != f"{now:%Y-%m}"


def month_param(query):
    text = query.get("month", [date.today().strftime("%Y-%m")])[0]
    if not MONTH_PATTERN.fullmatch(text):
        raise BadRequest("month must be YYYY-MM.")
    return parse_month(text)


def sections_for(month):
    done = {(chore_id, key) for chore_id, keys in load_json(DONE_FILE, {}).items() for key in keys}
    return due_sections(load_chores(), load_owners(), month, done)


def render_month(month):
    printout = load_printout()
    return render(month, sections_for(month), load_daily(), load_settings()["paper_size"], printout["options"],
                  printout["colors"])


def run(*command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise PrintError(f"{command[0]} timed out. Is the printer on?")
    if result.returncode:
        raise PrintError(result.stderr.strip() or f"{command[0]} failed.")
    return result.stdout.strip()


def parse_browse(output):
    """Return {name: {"model", "address"}} from `avahi-browse --parsable --resolve` output.

    Only resolved IPv4 entries count. Avahi escapes characters in names as
    decimal byte codes, for example \\032 for a space.
    """
    printers = {}
    for line in output.splitlines():
        fields = line.split(";")
        if len(fields) < 10 or fields[0] != "=" or fields[2] != "IPv4":
            continue
        name = re.sub(r"\\(\d{3})", lambda match: chr(int(match.group(1))), fields[3])
        txt = dict(re.findall(r'"([^"=]+)=([^"]*)"', ";".join(fields[9:])))
        printers[name] = {"model": txt.get("ty", ""),
                          "address": f"ipp://{fields[7]}:{fields[8]}/{txt.get('rp', 'ipp/print')}"}
    return printers


def browse_printers():
    return parse_browse(run("avahi-browse", "--resolve", "--parsable", "--terminate", "_ipp._tcp"))


def find_printers():
    """Return the IPP printers on the LAN, found through Avahi (Bonjour).

    Each URI names the printer's IPP service, not its IP address, so the
    printer stays found after its IP changes.
    """
    return [{"name": name, "model": printer["model"], "uri": f"dnssd://{quote(name, safe='')}._ipp._tcp.local/"}
            for name, printer in sorted(browse_printers().items())]


def printer_address(uri):
    """Return an address CUPS can connect to for a saved printer URI.

    musl cannot resolve the .local host name behind a dnssd:// URI, so look
    up the printer's current IP address through Avahi at each print.
    """
    if not uri.startswith("dnssd://"):
        return uri
    name = unquote(uri.removeprefix("dnssd://").split("._ipp._tcp", 1)[0])
    printer = browse_printers().get(name)
    if not printer:
        raise PrintError(f"{name} is not on the network. Is it on?")
    return printer["address"]


def print_sheet(month):
    settings = load_settings()
    if not settings["printer_uri"]:
        raise PrintError("Choose a printer in Settings.")
    with tempfile.NamedTemporaryFile(suffix=".pdf") as file:
        file.write(render_month(month).output())
        file.flush()
        # Recreate the queue on each print: the container's CUPS config does not persist.
        run("lpadmin", "-p", QUEUE, "-E", "-v", printer_address(settings["printer_uri"]), "-m", "everywhere")
        run("lp", "-d", QUEUE, "-o", f"media={MEDIA[settings['paper_size']]}", file.name)
    return f"Sent {month:%B %Y} to the printer."


def auto_print_loop():
    retry_at = datetime.min
    while True:
        now = datetime.now()
        if now >= retry_at and should_auto_print(now, load_settings()):
            stamp = f"{now:%b} {now.day} at {now:%H:%M}"
            try:
                print_sheet(parse_month(f"{now:%Y-%m}"))
                update = {"last_auto_print": f"{now:%Y-%m}",
                          "auto_print_status": f"Printed {now:%B %Y} on {stamp}."}
            except PrintError as error:
                retry_at = now + timedelta(hours=1)
                update = {"auto_print_status": f"Failed on {stamp}: {error} Trying again in 1 hour."}
            with save_lock:
                save_json(SETTINGS_FILE, {**load_settings(), **update})
        time.sleep(60)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.route({"/": self.index, "/api/chores": self.get_chores, "/api/owners": self.get_owners,
                    "/api/daily": self.get_daily, "/api/settings": self.get_settings,
                    "/api/printout": self.get_printout, "/api/printers": self.get_printers, "/api/due": self.get_due,
                    "/api/year": self.get_year, "/api/export": self.get_export, "/sheet.pdf": self.get_sheet})

    def do_PUT(self):
        self.route({"/api/chores": self.put_chores, "/api/owners": self.put_owners, "/api/daily": self.put_daily,
                    "/api/settings": self.put_settings, "/api/printout": self.put_printout})

    def do_POST(self):
        self.route({"/api/print": self.post_print, "/api/done": self.post_done, "/api/import": self.post_import,
                    "/api/owners/rename": self.post_rename_owner})

    def route(self, routes):
        if TRUSTED_CLIENT and self.client_address[0] != TRUSTED_CLIENT:
            return self.send_json(403, {"error": "Forbidden."})
        url = urlsplit(self.path)
        handler = routes.get(url.path)
        if not handler:
            return self.send_json(404, {"error": "Not found."})
        try:
            handler(parse_qs(url.query))
        except BadRequest as error:
            self.send_json(400, {"error": str(error)})
        except PrintError as error:
            self.send_json(502, {"error": str(error)})

    def send(self, status, content_type, body, headers={}):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, data):
        self.send(status, "application/json", json.dumps(data).encode())

    def read_json(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise BadRequest("Body is not JSON.")

    def index(self, query):
        self.send(200, "text/html; charset=utf-8", INDEX_FILE.read_bytes())

    def get_chores(self, query):
        self.send_json(200, load_chores())

    def put_chores(self, query):
        body = self.read_json()
        with save_lock:
            chores = validate_chores(body, load_owners())
            save_chores(chores)
        self.send_json(200, chores)

    def get_export(self, query):
        data = {"version": EXPORT_VERSION, "owners": load_owners(), "daily": load_daily(), "chores": load_chores(),
                "printout": load_printout()}
        self.send(200, "application/json", json.dumps(data, indent=2).encode(),
                  {"Content-Disposition": 'attachment; filename="chore-chart.json"'})

    def post_import(self, query):
        body = self.read_json()
        if not isinstance(body, dict):
            raise BadRequest("Expected a file exported from Chore Chart.")
        owners = validate_owners(body.get("owners"), [])
        chores = validate_chores(body.get("chores"), owners)
        # A file from before the daily list or the printout existed leaves the current one as it is.
        daily = clean_names(body.get("daily", load_daily()), "daily chores")
        printout = (validate_printout(body["printout"], {"options": PRINTOUT_DEFAULTS, "saved": [], "colors": {}},
                                      owners)
                    if "printout" in body else load_printout())
        with save_lock:
            save_json(OWNERS_FILE, owners)
            save_json(DAILY_FILE, daily)
            save_json(PRINTOUT_FILE, printout)
            save_chores(chores)
        self.send_json(200, {"owners": owners, "daily": daily, "chores": chores, "printout": printout})

    def get_owners(self, query):
        self.send_json(200, load_owners())

    def put_owners(self, query):
        body = self.read_json()
        with save_lock:
            owners = validate_owners(body, load_chores())
            save_json(OWNERS_FILE, owners)
        self.send_json(200, owners)

    def post_rename_owner(self, query):
        body = self.read_json()
        try:
            old, new = body["from"], body["to"]
        except (KeyError, TypeError):
            raise BadRequest("Expected from and to.")
        with save_lock:
            before = load_owners()
            owners, chores = rename_owner(before, load_chores(), old, new)
            printout = load_printout()
            renamed = owners[before.index(old)]
            printout["colors"] = {renamed if name == old else name: color for name, color in printout["colors"].items()}
            save_json(OWNERS_FILE, owners)
            save_json(PRINTOUT_FILE, printout)
            save_chores(chores)
        self.send_json(200, {"owners": owners, "chores": chores, "colors": printout["colors"]})

    def get_daily(self, query):
        self.send_json(200, load_daily())

    def put_daily(self, query):
        daily = clean_names(self.read_json(), "daily chores")
        with save_lock:
            save_json(DAILY_FILE, daily)
        self.send_json(200, daily)

    def get_settings(self, query):
        self.send_json(200, load_settings())

    def put_settings(self, query):
        body = self.read_json()
        with save_lock:
            settings = validate_settings(body, load_settings(), date.today())
            save_json(SETTINGS_FILE, settings)
        self.send_json(200, settings)

    def get_printout(self, query):
        self.send_json(200, printout_reply(load_printout()))

    def put_printout(self, query):
        body = self.read_json()
        with save_lock:
            printout = validate_printout(body, load_printout(), load_owners())
            save_json(PRINTOUT_FILE, printout)
        self.send_json(200, printout_reply(printout))

    def get_printers(self, query):
        self.send_json(200, find_printers())

    def get_due(self, query):
        month = month_param(query)
        sections, daily = sections_for(month), load_daily()
        printout = load_printout()
        sheet = render(month, sections, daily, load_settings()["paper_size"], printout["options"], printout["colors"])
        # fpdf2 holds the font files open until output(), so a sheet rendered only for its page count leaks them.
        sheet.output()
        self.send_json(200, {"title": sheet.heading, "pages": sheet.pages_count, "fitted": sheet.fitted, "daily": daily,
                             "sections": sections})

    def get_year(self, query):
        chores, owners = load_chores(), load_owners()
        start = month_param(query)
        months = [add_months(start, offset) for offset in range(12)]
        hours = year_hours(chores, owners, months)

        def cell(minutes):
            return {"minutes": minutes, "label": duration(minutes) if minutes else ""}

        self.send_json(200, {
            "months": [{"month": f"{month:%Y-%m}",
                        "label": f"{month:%b %Y}" if offset == 0 or month.month == 1 else f"{month:%b}"}
                       for offset, month in enumerate(months)],
            "hours": [{"owner": person, "label": person or "No owner", "cells": [cell(value) for value in minutes],
                       "total": cell(sum(minutes))} for person, minutes in hours],
            "totals": [cell(sum(minutes[position] for _, minutes in hours)) for position in range(len(months))],
            "total": cell(sum(sum(minutes) for _, minutes in hours)),
            "calendar": calendar_rows(chores, owners, months),
        })

    def get_sheet(self, query):
        month = month_param(query)
        self.send(200, "application/pdf", bytes(render_month(month).output()),
                  {"Content-Disposition": f'inline; filename="chores-{month:%Y-%m}.pdf"'})

    def post_print(self, query):
        self.send_json(200, {"message": print_sheet(month_param(query))})

    def post_done(self, query):
        body = self.read_json()
        try:
            chore_id, key, done = body["id"], body["key"], bool(body["done"])
        except (KeyError, TypeError):
            raise BadRequest("Expected id, key, and done.")
        with save_lock:
            if chore_id not in {chore["id"] for chore in load_chores()}:
                raise BadRequest("Unknown chore.")
            marks = load_json(DONE_FILE, {})
            keys = set(marks.get(chore_id, []))
            if done:
                keys.add(key)
            else:
                keys.discard(key)
            marks[chore_id] = sorted(keys)
            save_json(DONE_FILE, marks)
        self.send_json(200, {"done": done})


if __name__ == "__main__":
    threading.Thread(target=auto_print_loop, daemon=True).start()
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
