# Japanese ASR CER Evaluation Tool

[日本語](README.md) | English

This project compares Japanese speech-recognition reference transcripts
(`label`) with recognition hypotheses, calculates Character Error Rate
(CER), and generates character-level alignments to help identify
substitutions, deletions, and insertions.

The tool uses **jiwer 4.0.0** to calculate edit distance and optimal
alignment. Normalization is controlled by Boolean options in a YAML
configuration file. Input formats are TSV and JSONL. Output formats are
a human-readable `.cer` report, TSV, and JSONL. Each run creates exactly
one output file.

## 1. Features and Scope

-   Calculates per-utterance CER and corpus-level CER weighted by the
    total number of reference characters.
-   Reports the number of reference characters (`N`), correct characters
    (`C`), substitutions (`S`), deletions (`D`), and insertions (`I`).
-   Applies the same normalization rules to reference and hypothesis
    text.
-   Supports Unicode NFKC normalization, lowercasing, kana conversion,
    format-character removal, punctuation removal, symbol removal, and
    whitespace removal.
-   Displays character alignment using `lab` and `rec`. Insertions and
    deletions are represented by blank positions in the corresponding
    row.
-   Validates fields, duplicate UIDs, missing UIDs, and unexpected UIDs.
-   Prevents existing output files from being overwritten.

This tool calculates CER only. It does not calculate WER or MER, perform
speech recognition, split audio, tokenize Japanese, convert number
expressions, or remove fillers. It does not generate separate
measurement-condition or rule-log files.

## 2. Requirements and Installation

The runtime environment is Python 3.

Dependencies:

``` text
jiwer==4.0.0
PyYAML==6.0.3
```

Run the following commands from the repository root.
Install dependencies in the same Python environment used to run the tool:

``` bash
python -m pip install -r requirements.txt
```

The project does not require a Japanese morphological dictionary,
`kanjize`, or `num2words`.

## 3. Quick Start

Audio files are not required for text-based evaluation. You can run the
tool with the sample files in `examples/cer_test`. The current sample
inputs have been modified and contain missing UIDs, so the default
strict mode will report an error. Add the corresponding recognition
records before running the command:

``` bash
python compute_cer.py \
  --ref examples/cer_test/ref.tsv \
  --hyp examples/cer_test/hyp.tsv \
  --rules rules/ja.yaml \
  --output result.cer
```

The output format is determined by the file extension:

``` bash
# TSV: suitable for viewing and filtering in a spreadsheet
python compute_cer.py --ref examples/cer_test/ref.tsv --hyp examples/cer_test/hyp.tsv --output result.tsv

# JSONL: suitable for programmatic processing
python compute_cer.py --ref examples/cer_test/ref.tsv --hyp examples/cer_test/hyp.tsv --output result.jsonl
```

Only the specified output file is created; no additional report
directory is generated. Existing files are never overwritten, so use a
new filename for each run. Missing parent directories are created
automatically.

## 4. Project Structure

``` text
japanese-cer-evaluator/
├── LICENSE                 # MIT License
├── README.md               # Japanese documentation
├── README_en.md            # English documentation
├── compute_cer.py          # Command-line entry point
├── pipeline.py             # Input validation, scoring, alignment, and output
├── normalization.py        # Configuration validation and text normalization
├── requirements.txt        # Python dependencies
├── test_compute_cer.py     # Automated tests
├── rules/
│   ├── ja.yaml              # Default Japanese normalization rules
│   └── raw.yaml             # Disable all normalization
└── examples/
    └── cer_test/
        ├── ref.tsv          # Sample reference transcripts
        └── hyp.tsv          # Sample recognition results
```

## 5. Input Format

Specify the reference and hypothesis files with `--ref` and `--hyp`,
respectively. They may use different supported formats.

Only regular `.tsv` and `.jsonl` files are accepted. The tool does not
directly read audio files, directories, standalone JSON files, or
vendor-specific result formats.

### 5.1 TSV

Files must use UTF-8 encoding. UTF-8 BOM is supported.

The first row must contain exactly two columns, in this order: `uid` and
`text`. Columns must be separated by actual tab characters.

``` tsv
uid text
utt_0001    今日は晴れです。
utt_0002    気温は23.5度でした。
```

If the text contains tabs, quotation marks, or newlines, escape them
according to standard TSV quoting rules. It is recommended to generate
TSV files with `csv.writer(..., delimiter='\\t')`.

### 5.2 JSONL

Each non-empty line must be a JSON object containing exactly two string
fields: `uid` and `text`.

``` jsonl
{"uid":"utt_0001","text":"今日は晴れです。"}
{"uid":"utt_0002","text":"気温は23.5度でした。"}
```

An empty transcript must be represented as `"text": ""`, not `null`.
Empty lines are ignored.

### 5.3 UID Matching and Missing Records

-   UIDs must be non-empty, must not contain tabs or newlines, and must
    be unique within each file.
-   UIDs are matched exactly. The tool does not remove file extensions
    or leading/trailing spaces, or change letter case.
-   The two files may use different row orders. Results follow the order
    of the reference file.
-   Duplicate UIDs and UIDs found in the hypothesis but not in the
    reference cause an error.
-   By default, a reference UID without a matching hypothesis causes an
    error. Use `--missing empty` to treat a missing hypothesis as an
    empty transcript.
-   Each file must contain at least one record. An individual transcript
    may be empty.

Example:

``` bash
python compute_cer.py \
  --ref reference.tsv \
  --hyp hypothesis.jsonl \
  --missing empty \
  --output result.cer
```

## 6. YAML Normalization Rules

By default, the tool loads `rules/ja.yaml` from the project directory.
Copy the configuration file and modify its options as needed, then
specify it with `--rules`.

All eight fields must be present. Values must be unquoted YAML Boolean
values (`True` or `False`). Unknown fields, missing fields, and string
values such as `"True"` are rejected.

Example configuration:

``` yaml
unicode_nfkc: True
lowercase: True
kana_to_hiragana: False
remove_format_characters: True
remove_whitespace: True
remove_punctuation: True
remove_symbols: False
preserve_numeric_symbols: True
```

| Option | Default | Description |
| --- | --- | --- |
| `unicode_nfkc` | `True` | Applies NFKC normalization to unify full-width/half-width forms and compatibility characters. |
| `lowercase` | `True` | Converts text to lowercase using Python's `lower()` method. |
| `kana_to_hiragana` | `False` | Converts Katakana characters in the range `ァ`--`ヶ` to their corresponding Hiragana characters. |
| `remove_format_characters` | `True` | Removes Unicode format characters in category `Cf`. |
| `remove_whitespace` | `True` | Removes characters recognized as whitespace by `isspace()`. |
| `remove_punctuation` | `True` | Removes Unicode punctuation characters in category `P`. |
| `remove_symbols` | `False` | Removes Unicode symbol characters in category `S`. |
| `preserve_numeric_symbols` | `True` | Protects selected symbols in recognized numeric expressions when punctuation or symbols are removed. |

The processing order is fixed:

**NFKC → lowercase → kana conversion → format-character removal →
punctuation removal → symbol removal → whitespace removal**

The order of fields in the YAML file does not change the processing
order.

### 6.1 Common Normalization Examples

| Reference | Hypothesis | Result with default rules |
| --- | --- | --- |
| `ＡＢＣ１２３` | `abc123` | Match |
| `ｶﾞｯｺｳ` | `ガッコウ` | Match |
| `こんにちは、世界！` | `こんにちは世界` | Match |
| `東京 大阪` | `東京大阪` | Match |
| `カタカナ` | `かたかな` | Mismatch; enable kana conversion if desired |
| `スーパー` | `スパー` | Mismatch; the long-vowel mark is retained |
| `二十三` | `23` | Mismatch; number expressions are not converted |

NFKC does more than normalize character width. It may also expand
compatibility characters, for example, `①` → `1` and `㍿` → `株式会社`.

Kana conversion only covers the specified code-point range. It is not a
full pronunciation conversion and does not convert Kanji into kana.

### 6.2 Punctuation, Symbols, and Numeric Formats

Punctuation removal is based on Unicode categories. It includes Japanese
punctuation, middle dots, quotation marks, brackets, hyphens, and other
punctuation characters.

Symbol removal is controlled independently. It includes mathematical
symbols, currency symbols, and some emoji.

When `preserve_numeric_symbols` is enabled, the tool protects numeric
expressions matching this pattern:

-   An optional ASCII plus or minus sign
-   One or more consecutive ASCII digits
-   An optional decimal point followed by digits
-   An optional trailing percent sign

Examples include `23.5`, `-23.5%`, and `100%`. NFKC is applied first by
default, so full-width digits are usually converted into ASCII digits
before protection is applied.

A decimal point inside a recognized number is preserved, while a
sentence-final English period is still removed. This is pattern-based
protection, not semantic number parsing. Dates, times, thousands
separators, ranges, and scientific notation are not fully protected.

**Important notes:**

-   `〜` is a punctuation character and is removed by default. `～` is
    converted by NFKC into the symbol `~`, which is retained by default.
    These two characters may therefore produce different results.
-   Removing symbols may remove currency units. A combined emoji
    sequence may contain components from other Unicode categories, so
    the entire sequence is not guaranteed to be removed.
-   Removing punctuation such as hyphens may join text that was
    previously separated.

If exact numeric formatting or range notation matters, consider
disabling punctuation/symbol removal or using `rules/raw.yaml`.

### 6.3 Consistent Number Representation

**The tool does not convert between Kanji numerals, Arabic numerals, or
kana readings. Establish a consistent number representation for
reference and hypothesis text during data preparation.**

The following expressions have equivalent numeric meanings but are
scored as different character sequences:

``` text
二十三     != 23
三万五千   != 35000
二〇二六   != 2026
二十三点五 != 23.5
```

The tool does not use number-conversion libraries to infer meaning. This
avoids unintended conversions such as changing `一般` into `1般`.
Leading zeros, readings, units, and numeric meanings are not rewritten.

With NFKC enabled, `２３` and `23` are normalized to the same string.
This is character-width normalization, not number-expression conversion.

### 6.4 Disable All Normalization

Use `rules/raw.yaml` to disable all normalization:

``` bash
python compute_cer.py \
  --ref examples/cer_test/ref.tsv \
  --hyp examples/cer_test/hyp.tsv \
  --rules rules/raw.yaml \
  --output result_raw.cer
```

In raw mode, differences in whitespace, punctuation, letter case, and
full-width/half-width characters are included in scoring. Fillers are
never specifically removed under any configuration.

## 7. CER Calculation

``` text
CER = (S + D + I) / N
N   = C + S + D
```

| Symbol | Meaning |
| --- | --- |
| `C` | Correctly matched reference characters |
| `S` | Substitutions: a reference character is recognized as a different character |
| `D` | Deletions: a reference character is missing from the hypothesis |
| `I` | Insertions: the hypothesis contains a character absent from the reference |
| `N` | Number of normalized reference characters |

A character is a Python Unicode code point. It is not a byte, word,
visual grapheme, or Japanese morpheme. English is scored character by
character, and Arabic numerals are scored digit by digit. Normalization
may change text length, so `N` may differ from the original reference
length.

Each utterance is aligned independently; alignment is never performed
across UIDs. Overall CER is calculated by dividing the total number of
errors by the total number of reference characters. **It is not the
average of per-utterance CER values.** CER may exceed 100% when there
are many insertions.

If multiple optimal alignment paths exist, the specific allocation among
`S`, `D`, and `I` depends on jiwer and its underlying implementation.

Empty-text behavior follows the jiwer 4.0 convention:

-   Both reference and hypothesis are empty: CER = 0.
-   Reference is non-empty and hypothesis is empty: all reference
    characters are counted as deletions.
-   Reference is empty and hypothesis is non-empty: all hypothesis
    characters are counted as insertions. CER equals the number of
    inserted characters; two inserted characters are displayed as 200%.
-   If the total reference character count is zero, overall CER equals
    the total number of insertions.

Whitespace is removed by default. Therefore, `ai model` and `aimodel`
have a CER of zero, while `model` and `modal` have one substitution.
This is character-level scoring and does not evaluate word-boundary
correctness.

## 8. Output Formats and Report Interpretation

### Choosing an Output Format

| Use case | Recommended format | Reason |
| --- | --- | --- |
| Manually inspecting substitutions, deletions, and insertions | `.cer` | Side-by-side `lab`/`rec` alignment is easy to read. |
| Sorting or filtering error utterances in Excel or LibreOffice | `.tsv` | One utterance per row, with metrics and text in separate columns. |
| Analysis in Python or integration with another program | `.jsonl` | One JSON object per line; numeric values retain numeric types. |

All three formats use the same normalization and scoring logic. They
differ only in presentation. The output extension selects the format; no
additional option is required. Each run generates exactly one file.

The input and output formats do not need to match. For example, TSV
input can produce JSONL output.

The commands below should be run from the project directory. Replace
`reference.tsv` and `hypothesis.jsonl` with your actual file paths.
Existing output files cannot be overwritten. To change only the
presentation format, keep the input files and `--rules` setting
unchanged.

### 8.1 `.cer`: Character Alignment Report

Generate a report:

``` bash
python compute_cer.py \
  --ref reference.tsv \
  --hyp hypothesis.jsonl \
  --rules rules/ja.yaml \
  --output outputs/result.cer
```

Open `outputs/result.cer` in a text editor, or use
`less outputs/result.cer` in a terminal. Avoid rich-text viewers that
automatically collapse consecutive spaces.

The following example shows a single deletion: `学校へ行く` →
`学校行く`.

``` text
utt: deletion
CER: 20.00 % N=5 C=4 S=0 D=1 I=0
lab: 学 校 へ 行 く
rec: 学 校    行 く

Overall
CER: 20.00 % N=5 C=4 S=0 D=1 I=0
```

`lab` is the normalized reference, and `rec` is the normalized
hypothesis. A deletion appears as a blank position in `rec`; an
insertion appears as a blank position in `lab`. A substitution appears
as different characters in the same column. Display spacing does not
affect scoring. The `Overall` section at the end contains corpus-level
statistics.

A monospace font is recommended. Display width is estimated using
Unicode East Asian Width, but combining characters, emoji, and terminal
fonts may affect visual alignment.

In raw mode, actual whitespace is displayed using visible markers:

-   Space: `␠`
-   Tab: `⇥`
-   Newline: `↵`
-   Carriage return: `␍`

These markers affect display only; the text passed to jiwer is
unchanged.

Percentages in this format are displayed to two decimal places. The
report contains normalized alignment and statistics only; it does not
include original text or rule metadata.

### 8.2 TSV: Spreadsheet Analysis

``` bash
python compute_cer.py \
  --ref reference.tsv \
  --hyp hypothesis.jsonl \
  --rules rules/ja.yaml \
  --output outputs/result.tsv
```

Import the file into Excel or LibreOffice as UTF-8 text with tab
delimiters. It is recommended to set UID and text columns to the Text
type to prevent automatic conversion of identifiers, leading zeros, or
text. Do not split the file by commas.

Suggested analysis workflow:

1.  Filter `type=utterance` to exclude the overall statistics row.
2.  Sort by `cer_percent` in descending order and inspect high-error
    utterances first.
3.  Compare `ref` and `hyp` to review the original text differences.
    Compare `normalized_ref` and `normalized_hyp` to confirm the actual
    text used for scoring.
4.  Inspect `lab` and `rec` to locate insertions, deletions, and
    substitutions. Use a monospace font when viewing alignment.
5.  Use `type=total` to obtain overall results. Do not calculate overall
    CER by directly averaging per-utterance percentages.

TSV includes a header. Tabs, newlines, and quotation marks in fields are
escaped using standard quoting rules. Read the file with a TSV parser
rather than calling `split()` on each line.

Example:

``` python
import csv

with open('outputs/result.tsv', encoding='utf-8', newline='') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

total = next(row for row in rows if row['type'] == 'total')
print('Total CER:', total['cer_percent'], '%')

errors = [
    row for row in rows
    if row['type'] == 'utterance' and float(row['cer_percent']) > 0
]
print('Number of utterances containing errors:', len(errors))
```

Note that values read by `csv.DictReader` are strings. Convert them
explicitly to `int` or `float` before performing calculations.

### 8.3 JSONL: Programmatic Analysis

``` bash
python compute_cer.py \
  --ref reference.tsv \
  --hyp hypothesis.jsonl \
  --rules rules/ja.yaml \
  --output outputs/result.jsonl
```

JSONL is not a single JSON array and has no outer square brackets. Each
line is an independent JSON object. The following complete records
correspond to the single-utterance example above:

``` jsonl
{"type":"utterance","uid":"deletion","cer_percent":20.0,"cer_s":0,"cer_d":1,"cer_i":0,"cer_n":5,"cer_c":4,"ref":"学校へ行く","hyp":"学校行く","normalized_ref":"学校へ行く","normalized_hyp":"学校行く","lab":"学 校 へ 行 く","rec":"学 校    行 く"}
{"type":"total","uid":"","cer_percent":20.0,"cer_s":0,"cer_d":1,"cer_i":0,"cer_n":5,"cer_c":4,"ref":"","hyp":"","normalized_ref":"","normalized_hyp":"","lab":"","rec":""}
```

Python example:

``` python
import json

with open('outputs/result.jsonl', encoding='utf-8') as f:
    for line in f:
        row = json.loads(line)
        if row['type'] == 'total':
            print('Total CER:', row['cer_percent'], '%')
        elif row['cer_percent'] > 0:
            print(row['uid'], row['cer_percent'])
```

Do not use `json.load()` on the entire JSONL file. Call `json.loads()`
once for each line. Counts are integers and percentages are numeric
values. Newlines and other special characters in the original text are
escaped according to JSON rules.

### 8.4 TSV and JSONL Field Definitions

Each utterance has one record. The final record contains overall
statistics. Both formats use the same fields.

| Field | Description |
| --- | --- |
| `type` | `utterance` for an individual utterance; `total` for overall statistics. |
| `uid` | Utterance identifier. Empty for the overall statistics record. |
| `cer_percent` | CER percentage, with up to four decimal places. `25` means 25%, not `0.25`. |
| `cer_s` / `cer_d` / `cer_i` | Number of substitutions, deletions, and insertions. |
| `cer_n` / `cer_c` | Number of reference characters and correctly matched characters. |
| `ref` / `hyp` | Original reference and hypothesis text. |
| `normalized_ref` / `normalized_hyp` | Text actually used for scoring. |
| `lab` / `rec` | Character-alignment rows. |

Text and alignment fields in the overall statistics record are empty. No
`cer_errors` field is output. TSV includes a header; JSONL contains one
complete JSON object per line. Output encoding is UTF-8.

Output files are evaluation results, not valid input files for `--ref`
or `--hyp`. To run another evaluation, prepare input files containing
only `uid` and `text`.

## 9. Command-Line Options and Resource Limits

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| `--ref` | Yes | None | Reference TSV/JSONL file. |
| `--hyp` | Yes | None | Hypothesis TSV/JSONL file. |
| `--output` | Yes | None | New `.cer`, `.tsv`, or `.jsonl` output file. |
| `--rules` | No | `rules/ja.yaml` in the project | Normalization configuration. |
| `--missing` | No | `error` | `error` rejects missing hypotheses; `empty` treats them as empty text. |
| `--max-cells` | No | `10000000` | Maximum alignment input size per utterance. |

View command-line help:

``` bash
python compute_cer.py --help
```

The size guard checks:

``` text
(normalized_reference_length + 1) * (normalized_hypothesis_length + 1)
```

If the value exceeds the limit, the tool reports an error. This
threshold is not the actual memory allocation size used by jiwer. Long
recordings should be prepared with consistent boundaries on both sides.
Evaluate time and memory requirements before increasing the threshold.

The current implementation keeps input data and results in memory; it is
not a streaming processor. For very large datasets, run the evaluation
in batches. When combining batches, sum `S`, `D`, `I`, and `N`, then
calculate overall CER. Do not average batch-level CER values directly.

## 10. Tests and Troubleshooting

Run the automated tests:

``` bash
python test_compute_cer.py -v
```

The tests cover normalization, number-expression handling, `S`/`D`/`I`
counts, empty text, edit-distance validation, character alignment,
command-line output, UID validation, and output-file protection.

Manual functional-test data is located in `examples/cer_test/`.

| Symptom | Suggested action |
| --- | --- |
| `Output already exists` | Specify a new output filename. |
| `UID mismatch` | Check identifier conventions. Use `--missing empty` only when missing hypotheses should be treated as empty text. |
| `duplicate uid` | Remove duplicate identifiers before evaluation. |
| Invalid TSV header | Check the column order and ensure actual tab delimiters are used. |
| YAML validation error | Keep all eight configuration fields and use Boolean values rather than strings. |
| `Alignment too large` | Check whether an entire batch was accidentally combined into one utterance, or adjust the limit after assessing resource requirements. |
| Non-zero CER for semantically equivalent text | Check number representation, kana, and normalization settings. Semantic equivalence does not imply character identity. |
| Misaligned display | Use a monospace font and consider combining characters and emoji width differences. |

## 11. Evaluation Recommendations

CER measures character-level similarity. It cannot replace evaluations
of semantic accuracy, proper-noun accuracy, speaker distinction, or
punctuation quality.

For example, when punctuation is removed, sentence-boundary errors may
not affect CER. Important entities and ordinary particles have the same
character-level weight.

When comparing multiple recognition systems, use the same reference
data, number-representation conventions, and normalization
configuration. Review both overall statistics and per-utterance
alignments to avoid mistaking differences in evaluation methodology for
differences in model accuracy.

## 12. How Normalization Affects CER: Synthetic Example

This section uses a manually constructed Japanese text pair to
demonstrate how normalization changes the score. The values were
calculated using the tool's current Normalizer and jiwer 4.0.0.

**This is a functional demonstration using synthetic text. It is not a
result from a real evaluation dataset and does not represent the
accuracy of any recognition engine or a typical improvement range.**

### 12.1 Example Text

``` text
REF: ＡＩの予測では、東京都の気温は２３．５度でした。
HYP: aiの予測では東京都の気温わ23.5度でした
```

The example includes full-width/half-width differences, English letter
case, punctuation differences, and one actual character substitution:
`は` → `わ`.

Both sides use Arabic numerals. The example does not involve conversion
from Kanji numerals.

### 12.2 Results with Cumulative Normalization

| Cumulative settings | N | S | D | I | CER | Difference from raw baseline (pp) |
| --- | --- | --- | --- | --- | --- | --- |
| Raw | 24 | 7 | 2 | 0 | 37.5000% | — |
| + NFKC | 24 | 3 | 2 | 0 | 20.8333% | −16.6667 |
| + punctuation removal and numeric-symbol preservation | 22 | 3 | 0 | 0 | 13.6364% | −23.8636 |
| All default rules | 22 | 1 | 0 | 0 | 4.5455% | −32.9545 |

The settings in each row are cumulative:

1.  **Raw:** All eight options are disabled.
2.  **+ NFKC:** Only `unicode_nfkc` is enabled. Full-width English
    letters and digits are converted to half-width forms.
3.  **+ punctuation removal and numeric-symbol preservation:** Also
    enable `remove_punctuation` and `preserve_numeric_symbols`. The
    punctuation marks `、` and `。` are removed, while the decimal point
    in the number is preserved.
4.  **All default rules:** Use the complete default configuration in
    `rules/ja.yaml`. Lowercasing, format-character removal, and
    whitespace removal are also enabled. Kana conversion and symbol
    removal remain disabled. "All default rules" means the complete
    default configuration; it does not mean setting every option to
    `True`.

### 12.3 Interpreting the Differences

-   The raw result contains seven substitutions: two English-letter
    substitutions, four numeric-character substitutions, and one `は` →
    `わ` substitution. It also contains two deletion errors caused by
    punctuation.
-   NFKC removes the four numeric-character substitutions. The `AI` →
    `ai` case difference and `は` → `わ` substitution remain.
-   Punctuation removal eliminates the two deletion errors. The
    reference denominator `N` also decreases from 24 to 22, so the
    change cannot be interpreted by looking only at the number of
    errors.
-   Lowercasing under the default rules removes the two remaining
    English-letter substitutions. Only `は` → `わ` remains, giving a CER
    of `1 / 22 × 100% = 4.5455%`. This example contains no whitespace or
    format characters, so those options do not cause additional changes.

The difference from the baseline is calculated as the CER in the current
row minus the raw CER. The unit is **percentage points (pp)**, not
relative percentage change and not the difference from the previous row.
Differences are calculated using unrounded values and displayed to four
decimal places.

Normalization absorbs differences in written form; it does not improve
the recognition output itself. These reductions must not be interpreted
as an increase in recognition-engine accuracy. Results may change in a
different direction or by a different amount on other text.

If real evaluation results are added in the future, report them
separately with the measurement conditions and results. Include the
dataset and its license, number of samples and speakers, engine version
and region, evaluation date, and configuration version. Do not present
the changes in this synthetic example as measured results.

## 13. License

The project code and accompanying documentation are licensed under the [MIT License](LICENSE).
Copyright (c) 2026 DolphinAI, K.K.

Dependencies and third-party data remain subject to their own licenses and terms.
This project's MIT License does not grant additional rights to use or redistribute third-party data.
