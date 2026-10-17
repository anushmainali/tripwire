# Frozen benchmark v1

120 unique messages: 60 safe, 50 scam, 10 suspicious. This is a convenience benchmark,
not a population estimate or a comparison against commercial products. Labels were
fixed before obtaining predictions. All 120 cases are the benchmark; development
smokes must use separate examples. Do not tune prompts on benchmark errors and then
present the same sample as an unseen test set.

| Source | Cases | Label policy |
|---|---:|---|
| UCI SMS Spam Collection | 40 | Seeded 20 distinct ham → safe; 20 selected spam separately reviewed → 10 scam / 10 suspicious |
| Original synthetic examples | 40 | 20 scams, 20 legitimate look-alikes; explicitly marked synthetic |
| UCI PhiUSIIL | 40 | Seeded 20 phishing (source 0), 20 legitimate (source 1); historical source labels |

`fixtures/eval_set.csv` is the tracked frozen sample. Root `data/` remains gitignored.
Recreate it with `python -m scripts.datasets.build --download`, or copy the frozen
CSV to `data/eval_set.csv` without downloading anything. The manifest records seed,
archive checksums, sample checksum, and class counts. The builder fetches **only two
fixed UCI archive URLs**, never the hosts represented in their rows. No raw website
content or source-derived website features are passed to either system.

`source_row` is the one-based data row (excluding CSV headers); SMS source rows are
one-based lines. Original SMS text is preserved except surrounding whitespace.
UCI spam means unsolicited messaging, not confirmed fraud: selected messages have
explicit independent labeling rationales in the CSV. These labels are author review,
not expert adjudication. Ham and synthetic safe labels mean no observed scam signs,
not independently verified sender identity. PhiUSIIL labels date to the corpus and
may not describe a site's current state; expired or reassigned URLs are a limitation.
Bare URLs also lack the conversation context available in other strata.

Frozen `detonate` flags default to false. Benchmark v1 selects exactly three cases
by CLI before predictions: `url-69188` (first phishing URL in frozen order),
`url-154131` (first benign URL), and `synthetic-039` (official-domain delivery notice).
The run saves these effective input flags and selected IDs in its manifest. The benchmark must not visit any case URL on the
laptop. RDAP may contact registries only. Enable any small detonation sample only
through the Lead's verified Chalk sandbox path, and report its exact size separately.
Synthetic scam hosts use reserved `.example` domains; failure to resolve them is
expected and cannot count as proof of maliciousness. Do not call live Photon here.

## Attribution and licenses

- Almeida, T. & Hidalgo, J. (2011). *SMS Spam Collection*. UCI Machine Learning
  Repository. [Dataset and CC BY 4.0 license](https://archive.ics.uci.edu/dataset/228/sms+spam+collection).
  DOI: https://doi.org/10.24432/C5CC84. Adaptation: selected sample and scam-specific labels.
- Prasad, A. & Chandra, S. (2024). *PhiUSIIL Phishing URL (Website)*. UCI Machine
  Learning Repository. [Dataset, label convention and CC BY 4.0 license](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset).
  Associated paper: https://doi.org/10.1016/j.cose.2023.103545.
  Adaptation: URL-only balanced subset; historical labels retained.
- Synthetic messages were authored for Tripwire; brand alerts are illustrative, not
  actual messages or endorsements from those brands. Original corpus phone numbers
  and URLs are research data; do not contact them.

## Metric definitions (frozen before predictions)

Primary: exact three-class accuracy. Scam precision/recall: `scam` is the positive
class; `suspicious` is not counted as a detected scam. Strict false-positive rate:
scam predictions among gold-safe cases. Also report **warning FPR**, any non-safe
prediction among gold-safe cases, so caution/abstention cannot hide false alarms.
Show all class counts, errors/fallbacks, confusion matrices and source strata.
System failures remain in denominators and are incorrect for exact accuracy even
if the fallback label coincidentally matches; show successful-call accuracy separately.
Latency includes each attempted case; missing cost is unknown, never zero.
Evidence correctness requires documented review of individual claims and support;
nonempty evidence is not correctness. Report reviewed claims and sample size.
