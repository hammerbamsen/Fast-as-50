# Ændring 9/9-2026 — ryddede dage slettes nu i Intervals og Outlook

Branch `claude/0909-tomme-dage` oven på main efter blok 9 (PR #12). Ingen push.
Tests: **612 passed, 1 skipped** (før 607; +5 i ny `scripts/test_build_workouts_plan.py`). `schemas/validate.py` grøn.

## Fejlen (QA 9/9)
Forslaget til uge 3-8 fjernede svømningen om fredagen, så 2/10, 9/10, 23/10 og 30/10 fik `entries: []` i plan.json. Efter en manuel kørsel af "Byg workouts" stod de fire svømmepas alligevel tilbage i Intervals.

`make_plan()` løber `days[].entries` igennem og laver én tuple pr. entry. En dag uden entries giver derfor ingen tuple, kommer aldrig i `by_date`, og `run_plan` besøger den ikke — og det er kun i besøget at `delete_existing()` + `outlook_delete_by_date()` kaldes. Sletning skete altså kun på dage der havde noget at oprette. En hviledag (`entries: [{workout: null}]`) blev ryddet korrekt; en helt tom dag blev det ikke.

De fire events er slettet manuelt i Intervals 9/9.

## Rettelsen
`scripts/build_workouts.py::make_plan`: en dag uden entries giver nu `(dato, None, note)` — samme repræsentation som en hviledag. `run_plan` besøger datoen, sletter i Intervals og Outlook, opretter intet og tæller den som hviledag. Dagens `note` bruges hvis den findes, ellers "ingen pas i planen".

`scripts/test_build_workouts_plan.py` (ny, 5 tests): ryddet dag → hviledag-tuple, note bevares, manglende `entries`-nøgle kaster ikke, hviledag og `(valgfri)`-navn uændret, og en test mod den faktiske plan.json der kræver at de fire fredage er med.

CI (`ci-pytest.yml`) og CLAUDE.md kører nu `scripts/test_*.py` i stedet for kun `test_health_report.py`, så nye testfiler i `scripts/` ikke bliver glemt.

## Ikke berørt
Live-flowet (`apply_edit.py`) havde ikke fejlen: det sletter pr. dato i `dates_changed` før det opretter fra `entries`, så en tom dag ryddes korrekt. Det er kun ugens byg-script der udledte datolisten fra pas i stedet for fra dage.
