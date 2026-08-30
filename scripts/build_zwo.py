#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generér Zwift .zwo-filer fra data/bike_library.json.

    python3 scripts/build_zwo.py [målmappe]

Standard målmappe: workouts/zwift/

Filerne er GENERERET. Ret dem aldrig i hånden — ret bike_library.json
og kør scriptet igen. Ellers drifter Zwift og Intervals fra hinanden,
og så er vi tilbage til to biblioteker der ikke er enige.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules"))
import bike_library as B  # noqa: E402

README = """# Zwift-workouts — Fast as 50

**Disse filer er genereret.** Kilden er `data/bike_library.json`.
Ret aldrig en .zwo-fil her; ret JSON'en og kør `python3 scripts/build_zwo.py`.

## Installation på Mac
Kopiér alle .zwo-filer til:

    ~/Documents/Zwift/Workouts/187762/

Genstart Zwift. De ligger under Workouts → Custom Workouts, sorteret
efter kategori fordi navnene starter med `FaF 0`-`FaF 6`.

## Kategorier
{cats}

## Regler
- Max {maxh} hårde cykelpas om ugen, mindst {minh} timer imellem
- Max {maxm} moderate
- Alt er i % af FTP. FTP måles **indendørs** — samme trainer, samme
  blæseropsætning, samme tid på dagen.

## Pas
{rows}
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workouts", "zwift")
    os.makedirs(out, exist_ok=True)
    lib = B.load()
    written = []
    for wid in B.ids(lib):
        fn = B.zwo_filename(wid, lib)
        with open(os.path.join(out, fn), "w", encoding="utf-8") as fh:
            fh.write(B.to_zwo(wid, lib))
        written.append((wid, fn))
        print("skrev %s" % fn)

    m = B.meta(lib)
    cats = "\n".join("- **%s**: %d pas" % (v, len(B.by_category(k, lib)))
                     for k, v in m["categories"].items())
    rows = "\n".join(
        "- `%s` — %s · %d min · %s" % (fn, B.get(wid, lib)["name"],
                                       B.get(wid, lib)["est_min"], B.load_of(wid, lib))
        for wid, fn in written)
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(README.format(cats=cats, rows=rows,
                               maxh=m["rules"]["maxHaardPerWeek"],
                               maxm=m["rules"]["maxModeratPerWeek"],
                               minh=m["rules"]["minHoursBetweenHaard"]))
    print("\n%d workouts skrevet til %s" % (len(written), out))


if __name__ == "__main__":
    main()
