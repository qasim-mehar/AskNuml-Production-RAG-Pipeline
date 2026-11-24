# Lane B past-paper fixture corpus

Labeled ground truth for question segmentation and metadata extraction (L1, L12).
Every file below is synthetic and checked in; no test touches the network.

| Fixture | Source kind | Provenance |
| --- | --- | --- |
| `digital-past-paper.pdf` | digital PDF | Two-page PDF generated for this lane; text is plain Helvetica/WinAnsi `Tj` streams. |
| `digital-past-paper.html` | HTML | Synthetic past paper with a marks table; built from the foundation HTML fixture style. |
| `urdu-past-paper.html` | HTML (Urdu) | Synthetic Urdu paper using Arabic-Indic numerals (`۱`, `۲`, `۲۰`); proves L7 round-trip. |
| `scanned-past-paper-transcription.txt` | scanned page | Checked-in transcription of `tests/fixtures/pdf/scanned-past-paper-page.png` (8×8 PNG). It is NOT OCR output; MinerU is parked. |
| `expected/*.json` | ground truth | Question count, question numbers/pages/text, metadata values and table structures, labeled before the extractor was written. |
| `../pdf/digital-course-outline.pdf` | negative case | The existing one-page course outline is labeled as a non-past paper: 0 questions, no exam year/term/type/department; parsing it must raise a typed `ParseError`. |

`expected/*.json` is the single source of truth for the accuracy numbers reported
in the Lane B handoff. `service/evaluate.py` computes segmentation and metadata
scores from these files; Lane F may reuse them as golden material.
