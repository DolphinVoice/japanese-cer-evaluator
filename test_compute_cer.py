import csv
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from compute_cer import score, load_records
from normalization import Normalizer
from pipeline import aligned_lines


def normalize(text, profile='ja', kana='keep'):
    normalizer = Normalizer(Path(__file__).parent / 'rules' / ('raw.yaml' if profile == 'raw' else 'ja.yaml'))
    normalizer.config['kana_to_hiragana'] = kana == 'hiragana'
    return normalizer.apply(text)[0]


class CerTests(unittest.TestCase):
    def test_display_alignment(self):
        lab, rec = aligned_lines(score('学校へ行く', '学校行く')['alignment'])
        self.assertEqual(lab, '学 校 へ 行 く')
        self.assertEqual(rec, '学 校    行 く')
        lab, rec = aligned_lines(score('猫', '猫犬')['alignment'])
        self.assertEqual(lab, '猫   ')
        self.assertEqual(rec, '猫 犬')
    def test_normalization(self):
        self.assertEqual(normalize('「猫」【犬】、。！？…—・'), '猫犬')
        self.assertEqual(normalize('-23.5%。'), '-23.5%')
        n = Normalizer(Path(__file__).parent/'rules/ja.yaml')
        n.config['remove_symbols'] = True
        self.assertEqual(n.apply('￥100+猫★')[0], '100猫')
        self.assertEqual(normalize('ＡＢＣ １２３、ｶﾞｯｺｳ。\u200b'), 'abc123ガッコウ')
        self.assertEqual(normalize('スーパー・キャット'), 'スーパーキャット')
        self.assertEqual(normalize('カタカナ', kana='hiragana'), 'かたかな')
        self.assertNotEqual(normalize('学校'), normalize('がっこう'))
        self.assertNotEqual(normalize('二十'), normalize('20'))
        self.assertEqual(normalize('A 。', profile='raw'), 'A 。')
        self.assertEqual(normalize('50%+￥'), '50%+¥')

    def test_numbers_unchanged(self):
        for text in ['二十三点五', '三万五千', '二〇二六', '0012', '-23.5%', '一般の話']:
            self.assertEqual(normalize(text), text)
        self.assertGreater(score(normalize('二十三'), normalize('23'))['cer'], 0)

    def test_edits(self):
        for ref, hyp, expected in [('猫です', '犬です', (1, 0, 0)), ('猫です', '猫す', (0, 1, 0)),
                                   ('猫です', '猫ですね', (0, 0, 1)), ('', '猫', (0, 0, 1)),
                                   ('猫', '', (0, 1, 0)), ('', '', (0, 0, 0))]:
            r = score(ref, hyp)
            self.assertEqual(tuple(r[k] for k in ['substitutions', 'deletions', 'insertions']), expected)
            self.assertEqual(''.join(o['ref'] for o in r['alignment']), ref)
            self.assertEqual(''.join(o['hyp'] for o in r['alignment']), hyp)
        self.assertEqual(score('', '猫')['cer'], 1)
        self.assertEqual(score('', '猫犬')['cer'], 2)
        self.assertEqual(score(' 猫 ', '猫')['deletions'], 2)
        self.assertEqual(score('', '')['cer'], 0)
        self.assertEqual(score('猫', '猫犬鳥')['cer'], 2)
        with self.assertRaises(ValueError):
            score('abc', 'abc', max_cells=2)

    def test_exhaustive_distance(self):
        strings = [''.join(x) for n in range(4) for x in itertools.product('ab', repeat=n)]
        for ref in strings:
            for hyp in strings:
                dp = list(range(len(hyp) + 1))
                for i, a in enumerate(ref, 1):
                    nxt = [i]
                    for j, b in enumerate(hyp, 1):
                        nxt.append(min(dp[j]+1, nxt[-1]+1, dp[j-1]+(a != b)))
                    dp = nxt
                self.assertEqual(score(ref, hyp)['errors'], dp[-1])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'ref.tsv').write_text('uid\ttext\na\t猫です。\nb\t犬\n', encoding='utf-8')
            hyp = root / 'hyp.jsonl'
            hyp.write_text(json.dumps({'uid': 'a', 'text': '猫です'})+'\n'+json.dumps({'uid': 'b', 'text': '鳥'})+'\n')
            cmd = [sys.executable, str(Path(__file__).with_name('compute_cer.py')), '--ref', str(root/'ref.tsv'),
                   '--hyp', str(hyp), '--output', str(root/'out.jsonl')]
            subprocess.run(cmd, check=True, capture_output=True)
            summary = json.loads((root/'out.jsonl').read_text().splitlines()[-1])
            self.assertEqual(summary['cer_percent'], 25)
            self.assertEqual(summary['cer_n'], 4)
            self.assertFalse(any(k.startswith('mer') for k in summary))
            self.assertNotIn('cer_errors', summary)
            self.assertIn('lab', summary)
            cmd[-1] = str(root/'out.cer')
            subprocess.run(cmd, check=True, capture_output=True)
            report = (root/'out.cer').read_text()
            self.assertIn('utt: a\nCER: 0.00 % N=3 C=3 S=0 D=0 I=0', report)
            self.assertIn('Overall\nCER: 25.00 % N=4 C=3 S=1 D=0 I=0', report)
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            hyp.write_text(json.dumps({'uid': 'a', 'text': '猫です'})+'\n')
            cmd[-1] = str(root/'missing.tsv')
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            subprocess.run(cmd + ['--missing', 'empty'], check=True, capture_output=True)
            (root/'duplicate.tsv').write_text('uid\ttext\na\tx\na\ty\n')
            with self.assertRaises(ValueError):
                load_records(root/'duplicate.tsv')


if __name__ == '__main__':
    unittest.main()
