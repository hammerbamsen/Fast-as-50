# -*- coding: utf-8 -*-
"""
Fast as Fifty — udledning af zone-strenge.

ÉT sted der kender matematikken. Alt andet kalder derive().

Kilder (skrives i hånden):   thresholdSec, ftpW, runPct, bikePct
Udledte (skriv dem ALDRIG):  run, bikeWatt, runThreshold, bikeFtpW

Løb — pace i sek/km af tærskel og %-bånd:
    hurtig  = ceil(thr * 100 / hi)
    langsom = ceil(thr * 100 / lo) - 1
Højere pct = hurtigere = færre sekunder. Derfor er hi den hurtige ende.

Cykel — watt:
    watt = round(pct / 100 * ftp)
"""
from __future__ import annotations

import math


def fmt_pace(sec: int) -> str:
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def _fast(thr: float, pct: float) -> int:
    return math.ceil(thr * 100.0 / pct)


def _slow(thr: float, pct: float) -> int:
    return math.ceil(thr * 100.0 / pct) - 1


def run_zones(threshold_sec: int, run_pct: dict) -> dict:
    out = {}
    for z, (lo, hi) in run_pct.items():
        if lo is None:
            out[z] = f">{fmt_pace(_fast(threshold_sec, hi))}/km"
        elif hi is None:
            out[z] = f"<{fmt_pace(_slow(threshold_sec, lo))}/km"
        else:
            out[z] = (f"{fmt_pace(_fast(threshold_sec, hi))}-"
                      f"{fmt_pace(_slow(threshold_sec, lo))}/km")
    return out


def bike_watt(ftp_w: int, bike_pct: dict) -> dict:
    def w(p):
        return round(p / 100.0 * ftp_w)

    out = {}
    for z, (lo, hi) in bike_pct.items():
        if lo is None:
            out[z] = f"<{w(hi)} W"
        elif hi is None:
            out[z] = f">{w(lo)} W"
        else:
            out[z] = f"{w(lo)}-{w(hi)} W"
    return out


def derive(zones: dict) -> dict:
    """
    Returnerer en NY zones-dict hvor alle udledte felter er genberegnet
    ud fra thresholdSec / ftpW / runPct / bikePct. Muterer ikke input.
    """
    z = dict(zones)
    thr = int(z["thresholdSec"])
    ftp = int(z["ftpW"])

    z["runThreshold"] = f"{fmt_pace(thr)}/km"
    z["bikeFtpW"] = ftp
    z["run"] = run_zones(thr, z["runPct"])
    z["bikeWatt"] = bike_watt(ftp, z["bikePct"])
    return z


def set_zones(zones: dict, threshold_sec: int | None = None,
              ftp_w: int | None = None) -> dict:
    """Sæt kilde-værdier og genberegn alt udledt. Validerer input."""
    z = dict(zones)
    if threshold_sec is None and ftp_w is None:
        raise ValueError("set_zones kræver thresholdSec og/eller ftpW")
    if threshold_sec is not None:
        threshold_sec = int(threshold_sec)
        if not 150 <= threshold_sec <= 480:
            raise ValueError(f"thresholdSec {threshold_sec} uden for 150-480 sek/km")
        z["thresholdSec"] = threshold_sec
    if ftp_w is not None:
        ftp_w = int(ftp_w)
        if not 100 <= ftp_w <= 500:
            raise ValueError(f"ftpW {ftp_w} uden for 100-500 W")
        z["ftpW"] = ftp_w
    return derive(z)
