# -*- coding: utf-8 -*-
"""Kælder-cykelbiblioteket — én kilde til sandhed.

data/bike_library.json er masteren. Herfra genereres BÅDE
  * Intervals.icu workout_doc (via to_intervals) — søndags-cronen
  * Zwift .zwo-filer (via to_zwo) — scripts/build_zwo.py

Ret ALDRIG en .zwo-fil i hånden. Ret JSON'en og kør build_zwo.py.
Samme fejl som slog Master_Plan.xlsx ihjel 16/7-2026.
"""
import json
import os
import xml.sax.saxutils as _sx

_HERE = os.path.dirname(os.path.abspath(__file__))
_JSON = os.path.normpath(os.path.join(_HERE, "..", "..", "data", "bike_library.json"))

_cache = None


def load(path=None):
    """Læs biblioteket. Cacher, medmindre en eksplicit sti gives."""
    global _cache
    if path:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    if _cache is None:
        with open(_JSON, encoding="utf-8") as fh:
            _cache = json.load(fh)
    return _cache


def meta(lib=None):
    return (lib or load())["meta"]


def all_workouts(lib=None):
    return (lib or load())["workouts"]


def ids(lib=None):
    return [w["id"] for w in all_workouts(lib)]


def get(wid, lib=None):
    for w in all_workouts(lib):
        if w["id"] == wid:
            return w
    raise KeyError("ukendt workout-id: %s" % wid)


def by_category(cat, lib=None):
    return [w for w in all_workouts(lib) if w["category"] == cat]


def load_of(wid, lib=None):
    """Belastning: "let" | "moderat" | "haard". Sat pr. workout, ikke udledt."""
    return get(wid, lib)["load"]


def is_hard(wid, lib=None):
    """Tæller passet som en hård dag i Friel 5+2-reglen?"""
    return load_of(wid, lib) == "haard"


def check_week(wids, lib=None):
    """Valider en uges valgte kælderpas mod reglerne i meta.rules.

    Returnerer liste af advarsler — tom liste = ugen er lovlig.
    Kaldes af søndagscheck-in FØR pas skrives til plan.json.
    """
    lib = lib or load()
    r = meta(lib)["rules"]
    warn = []
    hard = [w for w in wids if load_of(w, lib) == "haard"]
    mod = [w for w in wids if load_of(w, lib) == "moderat"]
    if len(hard) > r["maxHaardPerWeek"]:
        warn.append("%d hårde pas — max er %d (Friel 5+2, 72t restitution ved 50+): %s"
                    % (len(hard), r["maxHaardPerWeek"], ", ".join(hard)))
    if len(mod) > r["maxModeratPerWeek"]:
        warn.append("%d moderate pas — max er %d: %s"
                    % (len(mod), r["maxModeratPerWeek"], ", ".join(mod)))
    for w in wids:
        if "fedtoxidation" in get(w, lib).get("tags", []) and hard:
            warn.append("%s (lav glykogen) må ikke ligge i en uge med hårde pas tæt på "
                        "— hold mindst en dag fri på hver side" % w)
    return warn


# ── varighed ────────────────────────────────────────────────────
def _sec(mins):
    return int(round(float(mins) * 60))


def _step_seconds(s):
    if s["type"] == "reps":
        return s["n"] * sum(_step_seconds(x) for x in s["steps"])
    return _sec(s["min"])


def duration_seconds(wid, lib=None):
    return sum(_step_seconds(s) for s in get(wid, lib)["steps"])


# ── Intervals.icu ───────────────────────────────────────────────
def _pw(a, b=None):
    return {"start": a, "end": a if b is None else b, "units": "%ftp"}


def _cad(rpm):
    return {"start": rpm, "end": rpm, "units": "rpm"}


def _iv_step(s):
    t = s["type"]
    if t == "ramp":
        d = {"ramp": True, "power": _pw(s["from"], s["to"]), "duration": _sec(s["min"])}
        if s.get("kind"):
            d[s["kind"]] = True
        if s.get("text"):
            d["text"] = s["text"]
        return d
    if t == "free":
        return {"text": s["text"], "duration": _sec(s["min"])}
    if t == "reps":
        d = {"reps": s["n"], "text": s.get("text") or "%dx" % s["n"],
             "steps": [_iv_step(x) for x in s["steps"]]}
        return d
    d = {"power": _pw(s["pct"]), "duration": _sec(s["min"])}
    if s.get("text"):
        d["text"] = "%s %d%% FTP" % (s["text"], s["pct"])
    if s.get("cad"):
        d["cadence"] = _cad(s["cad"])
    return d


def _iv_desc(s, indent=""):
    t = s["type"]
    if t == "ramp":
        return "%s- %s %s ramp %d-%d%% FTP" % (
            indent, s.get("text", "Ramp"), _fmt_min(s["min"]), s["from"], s["to"])
    if t == "free":
        return "%s- %s %s freeride" % (indent, s["text"], _fmt_min(s["min"]))
    if t == "reps":
        inner = "\n".join(_iv_desc(x, indent) for x in s["steps"])
        return "\n%s%dx %s\n%s\n" % (indent, s["n"], s.get("text", ""), inner)
    cad = " @ %d rpm" % s["cad"] if s.get("cad") else ""
    return "%s- %s %s %d%% FTP%s" % (
        indent, s.get("text", "Blok"), _fmt_min(s["min"]), s["pct"], cad)


def _fmt_min(m):
    """Minutter som tekst. Under et minut vises i sekunder — '0.5m' er ulaeseligt."""
    m = float(m)
    if m < 1:
        return "%ds" % int(round(m * 60))
    return "%dm" % int(m) if m == int(m) else ("%.2fm" % m).rstrip("0").rstrip(".") + "m"


def to_intervals(wid, lib=None):
    """Returnér workout i build_workouts.py's format."""
    w = get(wid, lib)
    desc = "\n".join(_iv_desc(s) for s in w["steps"]).strip()
    tail = "\n\nFORMÅL: " + w["purpose"]
    if not w.get("erg", True):
        tail += "\n\n⚠ IKKE ERG-MODE — du styrer selv effekten."
    if w.get("notes"):
        tail += "\n\n" + w["notes"]
    return {
        "name": w["name"],
        "type": "Ride",
        "moving_time": duration_seconds(wid, lib),
        "description": desc + tail,
        "workout_doc": {"steps": [_iv_step(s) for s in w["steps"]]},
    }


# ── Zwift .zwo ──────────────────────────────────────────────────
def _msgs(s, offset=0):
    out = ""
    for off, txt in s.get("msgs", []):
        out += '\n            <textevent timeoffset="%d" message="%s"/>' % (
            int(off) + offset, _sx.quoteattr(txt)[1:-1])
    return out


def _zwo_step(s):
    t = s["type"]
    if t == "ramp":
        tag = {"warmup": "Warmup", "cooldown": "Cooldown"}.get(s.get("kind"), "Ramp")
        a = 'Duration="%d" PowerLow="%.4f" PowerHigh="%.4f"' % (
            _sec(s["min"]), s["from"] / 100.0, s["to"] / 100.0)
    elif t == "free":
        tag, a = "FreeRide", 'Duration="%d" FlatRoad="1"' % _sec(s["min"])
    elif t == "reps":
        inner = s["steps"]
        # IntervalsT kan kun rumme et rent on/off-par
        if len(inner) == 2 and all(x["type"] == "steady" for x in inner) \
                and not any(x.get("cad") or x.get("msgs") for x in inner):
            on, off = inner
            a = ('Repeat="%d" OnDuration="%d" OffDuration="%d" '
                 'OnPower="%.4f" OffPower="%.4f"' % (
                     s["n"], _sec(on["min"]), _sec(off["min"]),
                     on["pct"] / 100.0, off["pct"] / 100.0))
            body = _msgs(s)
            if s.get("text"):
                body = ('\n            <textevent timeoffset="0" message="%s"/>'
                        % _sx.quoteattr(s["text"])[1:-1]) + body
            if body:
                return "        <IntervalsT %s>%s\n        </IntervalsT>\n" % (a, body)
            return "        <IntervalsT %s/>\n" % a
        # ellers: rul ud
        out = ""
        for i in range(s["n"]):
            for j, x in enumerate(inner):
                y = dict(x)
                if i == 0 and j == 0 and s.get("text"):
                    y["msgs"] = [[0, s["text"]]] + list(x.get("msgs", []))
                out += _zwo_step(y)
        return out
    else:
        tag = "SteadyState"
        a = 'Duration="%d" Power="%.4f"' % (_sec(s["min"]), s["pct"] / 100.0)
        if s.get("cad"):
            a += ' Cadence="%d"' % s["cad"]
    if t == "ramp" and s.get("kind") is None:
        tag = "Ramp"
    body = _msgs(s)
    if s.get("text") and t == "steady" and not s.get("msgs"):
        pass  # teksten står i beskrivelsen; ingen grund til at spamme skærmen
    if body:
        return "        <%s %s>%s\n        </%s>\n" % (tag, a, body, tag)
    return "        <%s %s/>\n" % (tag, a)


def to_zwo(wid, lib=None):
    w = get(wid, lib)
    desc = w["purpose"]
    if not w.get("erg", True):
        desc += "  [IKKE ERG-MODE — du styrer selv effekten.]"
    if w.get("notes"):
        desc += "  " + w["notes"]
    body = "".join(_zwo_step(s) for s in w["steps"])
    tags = "".join('<tag name="%s"/>' % _sx.quoteattr(t)[1:-1] for t in w.get("tags", []))
    return (
        '<workout_file>\n'
        '    <author>K. Hammerby / Fast as 50</author>\n'
        '    <name>%s</name>\n'
        '    <description>%s</description>\n'
        '    <sportType>bike</sportType>\n'
        '    <tags>%s</tags>\n'
        '    <workout>\n%s    </workout>\n'
        '</workout_file>\n' % (
            _sx.escape(w["name"]), _sx.escape(desc), tags, body)
    )


def zwo_filename(wid, lib=None):
    n = get(wid, lib)["name"]
    for a, b in [("æ", "ae"), ("ø", "oe"), ("å", "aa"), ("Æ", "Ae"), ("Ø", "Oe"),
                 ("Å", "Aa"), (" ", "_"), ("/", "-"), (".", ""), (",", "")]:
        n = n.replace(a, b)
    return n + ".zwo"
