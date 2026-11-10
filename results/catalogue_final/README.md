# Typed, probabilistic event catalogue for UCI 1158 (Morocco smart-meter feeder data)

Release of the paper *Grid event or data artefact? Hierarchical weak supervision for anomaly attribution in multi-city
feeder telemetry*. Built from the UCI Machine Learning Repository dataset 1158 (licence: CC BY 4.0) without manual labels.

## Files
- `catalogue.csv`: one row per item (rule-engine v1 item or detector-only candidate).
- `episodes.csv`: items linked into episodes, with the sequence of final labels (e.g. `A2(1.00) → A2(1.00) → A1(0.99)`).
- `key_events.csv`: the key events of the paper (guide ids C01–C12) with their final labels.

## Columns of `catalogue.csv`
| Column | Meaning |
|---|---|
| item_id | `D###` dead, `F###` fill, `K###` clock, `T###` transfer (rule engine v1); `XS###` detector-only candidate in the south (main detector), `XM###` in Marrakech (NB3 detector) |
| system | `south` (Laâyoune, Boujdour, Foum El Oued: one shared 10-min logger, A) or `Marrakech` (30 min, kW) |
| kind | dead (x = 0 or x ≤ 5 % of expected), fill (held or straight-line interpolated values), clock (a clock-change day), transfer (a load-transfer day), detector |
| source | `rule` (an item of the rule engine) or `detector` (a detector-only candidate: no rule covers it) |
| start, end | the item's span, timestamps **as recorded** (no clock correction); end exclusive |
| duration_h, cities, zones, n_cities, n_zones | extent; zone codes L1–L5, B1–B3, F1–F7, M1–M2 |
| episode | the episode the item belongs to (items sharing boundaries) |
| label | final type: A1 zero-fill gap, A2 simultaneous fill, A3 single-zone fill, A4 clock error, G1 regional outage, G2 city outage, G3 unplanned feeder outage, G4 planned work, G5 load transfer, N normal / untyped |
| confidence | the probability of the label |
| family | artefact (A*), grid event (G*), normal / untyped (N) |
| label_source | how the distribution was obtained: fusion of label model and end model with the main detector (south dead/fill and south candidates), NB3 fusion (Marrakech), or the label model alone (clock and transfer items) |
| votes | the rule votes on the item (`rule:label`) |
| p_A1 … p_N | the probability of each type |

## How to read it
- **Artefacts (A\*) should be imputed** before using the series; **grid events (G\*) are real** and should be kept and flagged.
- **Labels on the real data are not validated against external records.** They were validated on injected events: attribution macro-F1 0.91–0.94 and detection F1 0.72–0.91 (paper, NB4).
- **Detector-only candidates labelled N are untyped, not normal:** anomalies outside the typology (partial drops, surges, short disturbances).
- Item ids are stable only for this release: they change if the rule engine is re-run with other parameters.
- G1 does not occur on the real data; every multi-city dead event comes with hold or straight-line-fill evidence.
