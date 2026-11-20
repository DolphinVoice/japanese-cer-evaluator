"""Strict inputs, jiwer scoring, reproducible reports and CLI."""
import argparse
import csv
import json
import unicodedata
from pathlib import Path

import jiwer
import yaml
from normalization import Normalizer


def aligned_lines(ops):
    """Display jiwer character alignment; missing characters leave blank cells."""
    def visible(text):
        return text.replace(' ', '␠').replace('\t', '⇥').replace('\n', '↵').replace('\r', '␍')
    def width(text):
        return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)
    lab, rec = [], []
    for op in ops:
        a, b = visible(op['ref']), visible(op['hyp'])
        size = max(width(a), width(b), 1)
        lab.append(a + ' ' * (size-width(a)))
        rec.append(b + ' ' * (size-width(b)))
    return ' '.join(lab), ' '.join(rec)


def load_records(path):
    path = Path(path)
    records = {}
    if path.suffix.lower() not in {'.tsv', '.jsonl'} or not path.is_file():
        raise ValueError(f'Only TSV/JSONL files accepted: {path}')
    with path.open(encoding='utf-8-sig', newline='') as f:
        if path.suffix.lower() == '.tsv':
            reader = csv.DictReader(f, delimiter='\t')
            if reader.fieldnames != ['uid', 'text']:
                raise ValueError(f'{path}: TSV header must be uid<TAB>text')
        else:
            reader = (json.loads(line) for line in f if line.strip())
        for line, row in enumerate(reader, 2 if path.suffix.lower() == '.tsv' else 1):
            if not isinstance(row, dict) or set(row) != {'uid', 'text'}:
                raise ValueError(f'{path}:{line}: expected uid/text fields only')
            uid, text = row['uid'], row['text']
            if not isinstance(uid, str) or not uid.strip() or any(c in uid for c in '\r\n\t') or not isinstance(text, str):
                raise ValueError(f'{path}:{line}: invalid uid or text')
            if uid in records:
                raise ValueError(f'{path}:{line}: duplicate uid {uid}')
            records[uid] = text
    if not records:
        raise ValueError(f'No records: {path}')
    return records


def score(ref, hyp, max_cells=10000000):
    if (len(ref)+1)*(len(hyp)+1) > max_cells:
        raise ValueError('Alignment too large; split utterance or increase --max-cells')
    transform = jiwer.ReduceToListOfListOfChars()
    result = jiwer.process_characters(ref, hyp, reference_transform=transform, hypothesis_transform=transform)
    ops = []
    for chunk in result.alignments[0]:
        nr = chunk.ref_end_idx - chunk.ref_start_idx
        nh = chunk.hyp_end_idx - chunk.hyp_start_idx
        for offset in range(max(nr, nh)):
            i = chunk.ref_start_idx + offset if offset < nr else None
            j = chunk.hyp_start_idx + offset if offset < nh else None
            ops.append({'op': 'I' if i is None else 'D' if j is None else '=' if chunk.type == 'equal' else 'S',
                        'ref': ref[i] if i is not None else '', 'hyp': hyp[j] if j is not None else '',
                        'ref_pos': i+1 if i is not None else None, 'hyp_pos': j+1 if j is not None else None})
    counts = {k: getattr(result, k) for k in ['hits', 'substitutions', 'deletions', 'insertions']}
    return dict(counts, cer=result.cer, errors=result.substitutions+result.deletions+result.insertions,
                reference_chars=len(ref), hypothesis_chars=len(hyp), alignment=ops)


def run(args):
    normalizer = Normalizer(args.rules)
    refs, hyps = load_records(args.ref), load_records(args.hyp)
    missing, extra = sorted(refs.keys()-hyps.keys()), sorted(hyps.keys()-refs.keys())
    if extra or (missing and args.missing == 'error'):
        raise ValueError(f'UID mismatch: missing={missing[:10]} ({len(missing)}), extra={extra[:10]} ({len(extra)})')
    out = Path(args.output)
    if out.suffix.lower() not in {'.tsv', '.jsonl', '.cer'}:
        raise ValueError('--output must be a .tsv, .jsonl or .cer file')
    if out.exists():
        raise ValueError(f'Output already exists: {out}')
    results = []
    for uid, ref in refs.items():
        hyp = hyps.get(uid, '')
        nr, rt = normalizer.apply(ref)
        nh, ht = normalizer.apply(hyp)
        result = score(nr, nh, args.max_cells)
        result.update(uid=uid, reference=ref, hypothesis=hyp, normalized_reference=nr, normalized_hypothesis=nh,
                      normalization_trace={'reference': rt, 'hypothesis': ht}, missing_hypothesis=uid in missing)
        results.append(result)
    totals = {k: sum(r[k] for r in results) for k in
              ['reference_chars', 'hypothesis_chars', 'errors', 'hits', 'substitutions', 'deletions', 'insertions']}
    totals.update(cer=totals['errors']/totals['reference_chars'] if totals['reference_chars'] else float(totals['insertions']),
                  utterances=len(results), exact_matches=sum(r['errors'] == 0 for r in results), missing_uids=missing,
                  extra_uids=extra)
    def row(uid, r, kind='utterance'):
        lab, rec = aligned_lines(r.get('alignment', []))
        return dict(type=kind, uid=uid, cer_percent=round(r['cer']*100, 4),
                    cer_s=r['substitutions'], cer_d=r['deletions'], cer_i=r['insertions'], cer_n=r['reference_chars'], cer_c=r['hits'],
                    ref=r.get('reference', ''), hyp=r.get('hypothesis', ''),
                    normalized_ref=r.get('normalized_reference', ''), normalized_hyp=r.get('normalized_hypothesis', ''),
                    lab=lab, rec=rec)
    rows = [row(r['uid'], r) for r in results]
    rows.append(row('', totals, 'total'))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8', newline='') as f:
        if out.suffix.lower() == '.cer':
            for item in rows:
                f.write(('utt: ' + item['uid'] if item['type'] == 'utterance' else 'Overall') + '\n')
                f.write(f'CER: {item["cer_percent"]:.2f} % N={item["cer_n"]} C={item["cer_c"]} S={item["cer_s"]} D={item["cer_d"]} I={item["cer_i"]}\n')
                if item['type'] == 'utterance':
                    f.write('lab: ' + item['lab'] + '\nrec: ' + item['rec'] + '\n')
                f.write('\n')
        elif out.suffix.lower() == '.jsonl':
            for item in rows:
                f.write(json.dumps(item, ensure_ascii=False)+'\n')
        else:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)
    print(f'Completed: {len(results)} utterances, CER={totals["cer"]*100:.4f}%, result: {out.resolve()}')


def main():
    parser = argparse.ArgumentParser(description='YAML-driven Japanese CER using jiwer')
    parser.add_argument('--ref', required=True, help='TSV/JSONL with uid and text')
    parser.add_argument('--hyp', required=True, help='TSV/JSONL with uid and text')
    parser.add_argument('--rules', default=str(Path(__file__).parent/'rules/ja.yaml'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--missing', choices=['error', 'empty'], default='error')
    parser.add_argument('--max-cells', type=int, default=10000000)
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, OSError, KeyError, csv.Error, yaml.YAMLError) as exc:
        parser.exit(1, f'Error: {exc}\n')
