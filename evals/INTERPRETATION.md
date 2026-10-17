# What this benchmark supports

The corrected baseline and Tripwire both classified **86 of 120 cases correctly
(71.7%)**, with **0/60 strict false positives** each. This does **not** establish an
overall accuracy advantage for Tripwire. The 95% Wilson upper bound for strict FPR
is about 6%, before accounting for the convenience sample's selection bias.

Tripwire's scam precision was higher (88.9% versus 81.0%), but recall was lower
(64% versus 68%). Warning false positives were higher (20% versus 16.7%). Median
latency was 21.87 seconds versus 1.31 seconds. Costs are unknown. Both systems
completed without inference errors in the corrected comparison.

Tripwire did better on the 40 selected UCI SMS cases (85% versus 70% accuracy),
but worse on the synthetic cases and historical URL-only cases. These are small,
selected strata, not evidence of general superiority or a commercial comparison.

The defensible product distinction demonstrated here is **investigative output**:
76 successful Droid sessions, 12 preserved analysis scripts, and three real Chalk
sandbox attempts. The sandbox outcomes were a DNS failure/blank image, a Cuttly
404, and a FedEx access-denied page. No live phishing form was captured in this
benchmark. The separate controlled demo smoke is not part of benchmark accuracy.
An author review found 21/32 sampled evidence claims fully grounded; ten were
partly grounded and one unsupported. This is not independent expert validation.

The baseline originally had 27 incomplete responses with a 128-token cap. The
final pass changed only that cap to 1,024 and repeated **all** baseline cases;
model, prompt and labels stayed fixed. All original Tripwire predictions were
reused unchanged, with source/input checks. This post-hoc correction is disclosed
in RESULTS.md and the chart; do not use the truncated baseline's 59.2% score to
claim a win. Original outputs remain under `runs/full-v2/`.

Chalk run `9e278dce-1ee1-426c-aeb8-5961e73a284c` succeeded with 240 rows, zero row
errors, and every output and all eight SQL scorer values verified locally. It
replayed saved predictions rather than making new inference calls. See
`runs/full-v3-baseline-headroom/chalk_receipt.json` and `chalk_rows.json`.

All three allowed benchmark slots are consumed (interrupted v1, full v2, baseline
correction v3). Do not rerun or tune on this frozen set. Further product changes
need separate development cases; report/chart regeneration needs no API calls.
