# 日本語音声認識 CER 評価ツール

日本語 | [English](README_en.md)

日本語音声認識の正解テキスト（label）と認識結果を比較し、文字誤り率（Character Error Rate、CER）を計算するツールです。文ごとの文字アラインメントを出力し、置換、削除、挿入の位置を確認できます。

**jiwer 4.0.0** で編集距離と最適アラインメントを計算し、YAML の真偽値で正規化を切り替えます。入力は TSV／JSONL、出力は人が読むための `.cer` レポートと分析用の TSV／JSONL に対応します。1 回の実行で、指定した結果ファイルを一つだけ作成します。

## 1. 機能と対象範囲

- 文ごとの CER と、正解文字数の合計を分母とする全体 CER を計算します。
- 正解文字数 N、一致数 C、置換数 S、削除数 D、挿入数 I を出力します。
- 正解と認識結果に同じ正規化を適用します。
- 全角・半角、小文字化、仮名変換、書式制御文字、句読点類、記号、空白を設定できます。
- `lab`／`rec` のアラインメントで誤りを表示し、挿入・削除は対応する位置の空欄で表します。
- フィールド、UID の重複・欠落・余分な UID を検証し、既存の結果の上書きを防止します。

計算する指標は CER のみです。WER／MER、音声認識、音声分割、日本語の分かち書き、数字表現の変換、フィラー削除には対応しません。測定条件や正規化履歴のファイルも別途出力しません。

## 2. 実行環境とインストール

実行環境は Python 3 です。依存関係は次のとおりです。

```text
jiwer==4.0.0
PyYAML==6.0.3
```

以下のコマンドはすべてリポジトリのルートで実行します。スクリプトを実行する Python と同じ環境にインストールしてください。

```bash
python -m pip install -r requirements.txt
```

日本語の分割用辞書、`kanjize`、`num2words` は不要です。

## 3. クイックスタート

テキストの評価に音声は不要です。`examples/cer_test` の入力を使用できます。現在のサンプルには欠落した UID があるため、デフォルトの厳密な照合ではエラーになります。対応する認識結果を補ってから実行してください。

```bash
python compute_cer.py \
  --ref examples/cer_test/ref.tsv \
  --hyp examples/cer_test/hyp.tsv \
  --rules rules/ja.yaml \
  --output result.cer
```

出力形式は拡張子で選びます。

```bash
# TSV：表計算での表示・分析用
python compute_cer.py --ref examples/cer_test/ref.tsv --hyp examples/cer_test/hyp.tsv --output result.tsv

# JSONL：プログラムでの読み込み用
python compute_cer.py --ref examples/cer_test/ref.tsv --hyp examples/cer_test/hyp.tsv --output result.jsonl
```

指定した結果ファイルだけを作成し、レポート用ディレクトリは追加しません。既存ファイルは上書きしないため、再実行時には別のファイル名を指定してください。存在しない親ディレクトリは自動作成します。

## 4. プロジェクト構成

```text
japanese-cer-evaluator/
├── LICENSE                 # MIT License
├── README.md               # Japanese documentation
├── README_en.md            # English documentation
├── compute_cer.py          # Command line entry
├── pipeline.py             # Input validation, scoring, alignment and output
├── normalization.py        # Configuration verification and normalization
├── requirements.txt        # Dependency Version
├── test_compute_cer.py     # Automated Testing
├── rules/
│   ├── ja.yaml             # Default Normalization Rules
│   └── raw.yaml            # Disable All Normalization
└── examples/
    └── cer_test/
        ├── ref.tsv        # Current Reference Text
        └── hyp.tsv        # Current Recognition Result
```

## 5. 入力形式

正解を `--ref`、認識結果を `--hyp` で指定します。両者の形式は異なっていても構いません。通常の `.tsv`／`.jsonl` ファイルのみを受け付け、音声、ディレクトリ、単独の JSON、各社独自の結果形式は直接読み込みません。

### 5.1 TSV

UTF-8（BOM 付きも可）で保存します。ヘッダーは `uid`、`text` の 2 列のみで、順序は固定です。実際の Tab で区切ってください。

```tsv
uid	text
utt_0001	今日は晴れです。
utt_0002	気温は23.5度でした。
```

本文に Tab、引用符、改行を含める場合は、標準的な TSV の引用規則に従ってください。`csv.writer(..., delimiter='\t')` での生成を勧めます。

### 5.2 JSONL

空行以外の各行に、文字列フィールド二つだけを持つ JSON オブジェクトを置きます。

```jsonl
{"uid":"utt_0001","text":"今日は晴れです。"}
{"uid":"utt_0002","text":"気温は23.5度でした。"}
```

空のテキストは `"text":""` とし、`null` は使用しません。空行は無視します。

### 5.3 UID の照合と欠落の扱い

- UID は空でなく、Tab・改行を含まず、各ファイル内で一意である必要があります。
- 完全一致で照合します。拡張子や前後の空白の除去、大文字・小文字の変換はしません。
- 行順は異なっていても構いません。結果は正解ファイルの順序に従います。
- UID の重複や、正解にない UID が認識結果にある場合はエラーになります。
- 対応する認識結果がない場合もデフォルトではエラーです。`--missing empty` で空のテキストとして扱えます。
- ファイルには 1 件以上のレコードが必要ですが、個々のテキストは空でも構いません。

```bash
python compute_cer.py --ref reference.tsv --hyp hypothesis.jsonl --missing empty --output result.cer
```

## 6. YAML 正規化ルール

デフォルトではスクリプトのあるディレクトリの `rules/ja.yaml` を使用します。コピーして設定を変更し、`--rules` で指定できます。8 項目すべてを残し、値は引用符なしの真偽値にしてください。未知・欠落の項目や、文字列の `"True"` は受け付けません。

```yaml
unicode_nfkc: True
lowercase: True
kana_to_hiragana: False
remove_format_characters: True
remove_whitespace: True
remove_punctuation: True
remove_symbols: False
preserve_numeric_symbols: True
```

| 設定項目 | 既定値 | 処理 |
| --- | --- | --- |
| `unicode_nfkc` | True | NFKC で文字幅と互換文字を正規化 |
| `lowercase` | True | `lower()` で小文字化 |
| `kana_to_hiragana` | False | `ァ`～`ヶ` を対応するひらがなに変換 |
| `remove_format_characters` | True | Unicode Cf 類の書式制御文字を削除 |
| `remove_whitespace` | True | `isspace()` が真となる文字を削除 |
| `remove_punctuation` | True | Unicode P 類の句読点類を削除 |
| `remove_symbols` | False | Unicode S 類の記号を削除 |
| `preserve_numeric_symbols` | True | 句読点類・記号を削除するときに、数値に一致する範囲を保護 |

処理順は **NFKC → 小文字化 → 仮名変換 → 書式制御文字 → 句読点類 → 記号 → 空白** で固定です。YAML の項目の並び順では変わりません。

### 6.1 主な処理例

| 正解 | 認識結果 | デフォルト設定での比較 |
| --- | --- | --- |
| `ＡＢＣ１２３` | `abc123` | 一致 |
| `ｶﾞｯｺｳ` | `ガッコウ` | 一致 |
| `こんにちは、世界！` | `こんにちは世界` | 一致 |
| `東京 大阪` | `東京大阪` | 一致 |
| `カタカナ` | `かたかな` | 不一致。仮名変換で統一可能 |
| `スーパー` | `スパー` | 不一致。長音符は保持 |
| `二十三` | `23` | 不一致。数字表現は変換しない |

NFKC は幅だけでなく、`①→1`、`㍿→株式会社` のように互換文字を展開する場合もあります。仮名変換は上記範囲のみが対象で、読みへの変換ではなく、漢字を仮名にはしません。

### 6.2 句読点類・記号と数値書式

句読点類は Unicode 分類に従って削除します。句読点、中点、引用符、括弧、ダッシュなどが対象です。数学記号、通貨記号、一部の emoji を含む記号の削除は、別の設定で制御します。

`preserve_numeric_symbols` が有効な場合、「任意の ASCII 正負符号＋連続する ASCII 数字＋任意の小数部分＋任意の百分率記号」に一致する範囲を保護します。例は `23.5`、`-23.5%`、`100%` です。デフォルトでは NFKC を先に適用するため、全角数字も通常は変換後に保護されます。

数値中の小数点は残し、文末のピリオドは削除します。意味解析ではないため、日付、時刻、桁区切り、区間、指数表記を完全には保護しません。

- `〜` は句読点類のためデフォルトで削除します。`～` は NFKC で記号 `~` となり、デフォルトでは残ります。
- 記号削除は通貨単位を消す可能性があります。複合 emoji には別分類の構成要素もあり、全体を削除できるとは限りません。
- ダッシュなどを削除すると、区切られていた内容が連結される場合があります。

数値書式や区間表現を厳密に比較する場合は、句読点類・記号の削除を無効にするか、`rules/raw.yaml` を使用してください。

### 6.3 数字表現の方針

**漢数字、算用数字、仮名の読みの相互変換はしません。データ準備の段階で、正解と認識結果の数字表記方針をそろえてください。**

次の表現は数値の意味が同じでも、文字の差として誤りになります。

```text
二十三     ≠ 23
三万五千   ≠ 35000
二〇二六   ≠ 2026
二十三点五 ≠ 23.5
```

数字変換ライブラリによる推定は行わず、「一般」を「1般」にするような変換を避けています。先頭のゼロ、読み、単位、意味は書き換えません。NFKC が有効なら `２３` と `23` は統一しますが、これは文字幅の正規化です。

### 6.4 正規化をすべて無効にする

```bash
python compute_cer.py \
  --ref examples/cer_test/ref.tsv \
  --hyp examples/cer_test/hyp.tsv \
  --rules rules/raw.yaml \
  --output result_raw.cer
```

空白、句読点、大文字・小文字、全角・半角の差も採点します。フィラーはどの設定でも専用の削除処理を行いません。

## 7. CER の計算方法

```text
CER = (S + D + I) / N
N   = C + S + D
```

| 記号 | 意味 |
| --- | --- |
| C | 正しく一致した正解文字数 |
| S | 置換：正解の文字が別の文字になった数 |
| D | 削除：正解の文字が欠落した数 |
| I | 挿入：正解にない文字が追加された数 |
| N | 正規化後の正解文字数 |

文字は Python の Unicode code point を指し、バイト、単語、見た目の字形、形態素とは異なります。英字は一文字ずつ、数字は一桁ずつ採点します。正規化で長さが変わるため、N は元の label の長さと一致しない場合があります。

UID ごとに独立してアラインメントを計算します。全体 CER は総誤り数を総正解文字数で割った値で、**文ごとの CER の平均ではありません**。挿入が多ければ 100% を超えます。最適経路が複数ある場合、S/D/I の内訳は jiwer と下位の実装に依存します。

空のテキストは jiwer 4.0 の定義に従います。

- 両方が空：CER=0。
- 正解が空でなく、認識結果が空：正解の全文字を削除として計上。
- 正解が空で、認識結果が空でない：全文字を挿入とし、CER は挿入文字数。2 文字なら 200% と表示。
- 全体の正解文字数がゼロ：全体 CER は総挿入数。

デフォルトでは空白を削除するため、`ai model` と `aimodel` の CER は 0 です。`model` と `modal` は 1 文字の置換です。文字単位の指標なので、単語境界の正しさは表しません。

## 8. 出力形式とレポートの読み方

### 出力形式の選択

| 用途 | 推奨形式 | 理由 |
| --- | --- | --- |
| 置換・削除・挿入を文ごとに確認 | `.cer` | lab/rec の上下のアラインメントを読みやすい |
| Excel／LibreOffice で誤りのある文を並べ替え・抽出 | `.tsv` | 文ごとの行に指標とテキストを別列で保存 |
| Python での分析やシステム連携 | `.jsonl` | 行ごとの JSON オブジェクトで数値型を保持 |

三形式の正規化と採点は同じで、表示方法だけが異なります。**`--output` の拡張子で選択し、追加オプションは不要です。1 回の実行で一ファイルだけを生成します。** TSV 入力から JSONL 出力など、入出力形式を別々に選べます。

以下はプロジェクトのルートで実行します。`reference.tsv` と `hypothesis.jsonl` は実際のパスに置き換えてください。出力先に既存ファイルは指定できません。表示形式だけを変える場合は、入力と `--rules` を変更しないでください。

### 8.1 `.cer` アラインメントレポート

```bash
python compute_cer.py \
  --ref reference.tsv \
  --hyp hypothesis.jsonl \
  --rules rules/ja.yaml \
  --output outputs/result.cer
```

`outputs/result.cer` をテキストエディタまたは `less outputs/result.cer` で開きます。連続する空白をまとめてしまう表示方法は避けてください。

`学校へ行く→学校行く` の一文だけを採点した例です。

```text
utt: deletion
CER: 20.00 % N=5 C=4 S=0 D=1 I=0
lab: 学 校 へ 行 く
rec: 学 校    行 く

Overall
CER: 20.00 % N=5 C=4 S=0 D=1 I=0
```

`lab` は正規化後の正解、`rec` は認識結果です。削除は rec、挿入は lab の空欄で示し、置換は同じ列の異なる文字で示します。表示の間隔は採点に含みません。末尾の `Overall` が全体集計です。

等幅フォントを使用してください。表示幅は Unicode East Asian Width で見積もるため、結合文字、emoji、フォントによってはずれる場合があります。raw の空白は、スペース `␠`、Tab `⇥`、改行 `↵`、復帰 `␍` で可視化します。表示だけの処理で、jiwer への入力は変えません。

百分率は小数点以下 2 桁で表示します。正規化後のアラインメントと集計のみを含み、元のテキストやルールのメタデータは付けません。

### 8.2 TSV：表計算での分析

```bash
python compute_cer.py \
  --ref reference.tsv \
  --hyp hypothesis.jsonl \
  --rules rules/ja.yaml \
  --output outputs/result.tsv
```

Excel／LibreOffice では UTF-8、Tab 区切りとして読み込みます。UID とテキスト列は文字列に指定し、識別子、先頭のゼロ、本文の自動変換を防いでください。カンマでは区切りません。

1. `type=utterance` に絞り、全体集計行を除外します。
2. `cer_percent` の降順で、誤り率の高い文を確認します。
3. `ref/hyp` で元の差を、`normalized_ref/normalized_hyp` で採点対象を確認します。
4. `lab/rec` で位置を確認します。等幅フォントを勧めます。
5. 全体の値は `type=total` を使い、文ごとの百分率を平均しません。

TSV にはヘッダーがあり、フィールド内の Tab、改行、引用符は標準の引用規則で保存します。単純な `split()` ではなく TSV パーサーを使ってください。

```python
import csv

with open('outputs/result.tsv', encoding='utf-8', newline='') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

total = next(row for row in rows if row['type'] == 'total')
print('Total CER：', total['cer_percent'], '%')
errors = [row for row in rows
          if row['type'] == 'utterance' and float(row['cer_percent']) > 0]
print('Number of sentences containing errors ', len(errors))
```

`csv.DictReader` で取得した数値も文字列です。計算前に `int`／`float` に変換してください。

### 8.3 JSONL：プログラムでの分析

```bash
python compute_cer.py \
  --ref reference.tsv \
  --hyp hypothesis.jsonl \
  --rules rules/ja.yaml \
  --output outputs/result.jsonl
```

JSONL は一つの JSON 配列ではなく、外側の角括弧もありません。各行が独立したオブジェクトです。前述の一文に対応する完全な出力例を示します。

```jsonl
{"type":"utterance","uid":"deletion","cer_percent":20.0,"cer_s":0,"cer_d":1,"cer_i":0,"cer_n":5,"cer_c":4,"ref":"学校へ行く","hyp":"学校行く","normalized_ref":"学校へ行く","normalized_hyp":"学校行く","lab":"学 校 へ 行 く","rec":"学 校    行 く"}
{"type":"total","uid":"","cer_percent":20.0,"cer_s":0,"cer_d":1,"cer_i":0,"cer_n":5,"cer_c":4,"ref":"","hyp":"","normalized_ref":"","normalized_hyp":"","lab":"","rec":""}
```

Python での読み込み例です。

```python
import json

with open('outputs/result.jsonl', encoding='utf-8') as f:
    for line in f:
        row = json.loads(line)
        if row['type'] == 'total':
            print('Total CER：', row['cer_percent'], '%')
        elif row['cer_percent'] > 0:
            print(row['uid'], row['cer_percent'])
```

ファイル全体に `json.load()` を使わず、行ごとに `json.loads()` を呼びます。件数は整数、百分率は数値です。本文の改行などは JSON の規則に従ってエスケープします。

### 8.4 TSV／JSONL のフィールド

文ごとに 1 レコード、末尾に全体集計を置き、同じフィールドを使用します。

| フィールド | 説明 |
| --- | --- |
| `type` | 文は `utterance`、全体は `total` |
| `uid` | 文の識別子。全体集計では空文字列 |
| `cer_percent` | 小数点以下最大 4 桁の CER 百分率。25 は 25% で、0.25 ではない |
| `cer_s` / `cer_d` / `cer_i` | 置換・削除・挿入数 |
| `cer_n` / `cer_c` | 正解文字数・一致数 |
| `ref` / `hyp` | 元の正解・認識結果 |
| `normalized_ref` / `normalized_hyp` | 実際に採点したテキスト |
| `lab` / `rec` | 二行のアラインメント表示 |

全体集計のテキスト・アラインメントは空です。`cer_errors` は出力しません。TSV はヘッダー付き、JSONL は各行に一つのオブジェクトを保存します。文字コードは UTF-8 です。

出力は本ツールの入力形式ではなく、そのまま `--ref`／`--hyp` に指定できません。再評価時は `uid` と `text` のみを持つ入力を準備してください。

## 9. CLI オプションと規模制限

| オプション | 必須 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `--ref` | はい | なし | 正解 TSV／JSONL |
| `--hyp` | はい | なし | 認識結果 TSV／JSONL |
| `--output` | はい | なし | 新規の .cer／.tsv／.jsonl |
| `--rules` | いいえ | プロジェクト内 rules/ja.yaml | 正規化設定 |
| `--missing` | いいえ | error | error は欠落を拒否、empty は空の認識結果として処理 |
| `--max-cells` | いいえ | 10000000 | 一文のアラインメント入力規模の上限 |

ヘルプ：`python compute_cer.py --help`。

正規化後の `(正解文字数+1) × (認識結果文字数+1)` が上限を超えるとエラーにします。この値は jiwer の実際のメモリ割り当て量ではありません。長い音声は共通の境界で分割し、上限を上げる際は時間・メモリを考慮してください。

入力と結果をメモリに保持し、ストリーミング処理は行いません。大規模データを分割評価する場合は、S/D/I/N を合計して全体 CER を求め、バッチごとの CER を平均しないでください。

## 10. テストとトラブルシューティング

```bash
python test_compute_cer.py -v
```

正規化、数字を変換しないこと、S/D/I、空文字列、編集距離、アラインメント、CLI 出力、UID 検証、上書き防止をテストします。手動の機能確認用データは `examples/cer_test/` にあります。

| 症状 | 対処 |
| --- | --- |
| `Output already exists` | 新しい出力ファイル名を指定 |
| `UID mismatch` | 識別子を確認。必要に応じて --missing empty を使用 |
| `duplicate uid` | 重複を解消してから評価 |
| TSV ヘッダーエラー | 列順と実際の Tab を確認 |
| YAML 検証エラー | 8 項目を残し、文字列ではなく真偽値を指定 |
| `Alignment too large` | バッチ全体を一文にしていないか確認、または上限を調整 |
| 意味が同じでも CER がゼロにならない | 数字表記、仮名、設定を確認。意味と文字の一致は別 |
| 表示がずれる | 等幅フォントを使い、結合文字や emoji の幅を確認 |

## 11. 評価時の推奨事項

CER は文字の一致を測る指標で、意味、固有名詞、話者、句読点の品質の評価を代替しません。句読点を消せば区切りの誤りが見えなくなり、重要なエンティティも助詞も同じ重みになります。

複数のシステムを比較する際は、正解、数字表記方針、正規化設定を統一し、全体集計と文ごとのアラインメントを併せて確認してください。

## 12. 正規化による CER の変化：合成テキスト例

同じ自作の日本語テキストを、異なる正規化設定で比較します。値は本ツールの Normalizer と jiwer 4.0.0 で計算したものです。**機能の説明用で、実際の評価セットの成績、エンジンの精度、一般的な改善幅を示すものではありません。**

### 12.1 テキスト例

```text
REF: ＡＩの予測では、東京都の気温は２３．５度でした。
HYP: aiの予測では東京都の気温わ23.5度でした
```

全角・半角、英字の大文字・小文字、句読点の差に加え、`は→わ` の置換を含みます。両方とも算用数字で、幅だけが異なり、漢数字変換は行いません。

### 12.2 ルールを累積した結果

| 条件（累積） | N | S | D | I | CER | raw 基準との差（pt） |
| --- | --- | --- | --- | --- | --- | --- |
| raw | 24 | 7 | 2 | 0 | 37.5000% | — |
| ＋ NFKC | 24 | 3 | 2 | 0 | 20.8333% | −16.6667 |
| ＋句読点類の削除と数値保護 | 22 | 3 | 0 | 0 | 13.6364% | −23.8636 |
| デフォルトの全ルール | 22 | 1 | 0 | 0 | 4.5455% | −32.9545 |

1. **raw**：8 項目すべてを無効化します。
2. **＋ NFKC**：`unicode_nfkc` のみを有効にし、全角英数字を半角にします。
3. **＋句読点類の削除と数値保護**：`remove_punctuation` と `preserve_numeric_symbols` も有効にし、`、。` を削除して小数点を残します。
4. **デフォルトの全ルール**：`rules/ja.yaml` 全体を使用し、小文字化、書式制御文字削除、空白削除も有効にします。仮名変換と記号削除は無効のままです。「全ルール」はすべてを True にする意味ではありません。

### 12.3 差の読み方

- raw は英字 2、数値の文字 4、`は→わ` の 1、計 7 置換と、句読点 2 削除です。
- NFKC は数値の 4 置換を解消し、`AI→ai` と `は→わ` は残ります。
- 句読点類の削除で 2 削除がなくなり、分母 N も 24 から 22 に変わります。
- 小文字化で英字の 2 置換を解消し、残るのは `は→わ` のみです。CER は `1 / 22 × 100% = 4.5455%` です。この例に空白や書式制御文字はなく、その設定は結果を変えません。

差は各行の CER から raw の CER を引いた値で、単位は**パーセントポイント（pt）**です。相対変化率や前行との差ではありません。丸める前の値から差を計算し、小数点以下 4 桁で表示しています。

正規化は表記差を吸収しますが、認識結果自体を改善しません。エンジンの精度向上と解釈しないでください。別のテキストでは変化の方向や幅が異なる場合があります。

実データの結果を追加する場合は、データセットと利用条件、サンプル数・話者数、モデルのバージョン・リージョン、日付、設定のバージョンを別に示してください。合成例の変化量を実測結果として扱わないでください。

## 13. ライセンス

コードと付属ドキュメントは [MIT License](LICENSE) で提供します。著作権は DolphinAI, K.K. に帰属します。

依存関係と第三者データには、それぞれのライセンス・利用条件が適用されます。本プロジェクトの MIT License は、第三者データの利用・再配布の権利を追加するものではありません。
