import hashlib
import json
import re
from pathlib import Path
import tempfile
import unittest
import generate_resources
import update_rules

ROOT = Path(__file__).parent

class ResourcesTest(unittest.TestCase):
    def test_snapshot_integrity(self):
        data = (ROOT / 'easylist.txt').read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), json.loads((ROOT / 'snapshot.json').read_text(encoding='utf-8'))['sha256'])
        update_rules.validate(data)

    def test_invalid_download(self):
        for data in (b'<html>Error</html>', b'[Adblock Plus 2.0]\n', b'\0' * 100001):
            with self.assertRaises(ValueError):
                update_rules.validate(data)

    def test_cosmetic_exceptions(self):
        self.assertEqual(generate_resources.cosmetics('a.com,~b.com##.ad\na.com#@#.ad\nx##+js(test)'),
                         [[['a.com', '~b.com'], '.ad', False], [['a.com'], '.ad', True]])

    def test_document_exceptions(self):
        rules = generate_resources.cosmetic_exceptions(
            '@@||google.*/search?$generichide\n'
            '@@$elemhide,domain=example.com|~ads.example.com')
        self.assertRegex('https://www.google.com/search?q=test', rules[0][0])
        concrete = generate_resources.cosmetic_exceptions('@@||example.com^$generichide')[0][0]
        self.assertIsNone(re.search(concrete, 'https://example.com.evil.test/'))
        self.assertEqual(rules[1][1], ['example.com', '~ads.example.com'])
        self.assertFalse(rules[1][2])
        with self.assertRaises(ValueError):
            generate_resources.cosmetic_exceptions('@@||example.com^$generichide,unknown')

    def test_deterministic_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / 'a.h', Path(directory) / 'b.h'
            generate_resources.generate(ROOT, first)
            generate_resources.generate(ROOT, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertIn('kYoutubeScript', first.read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()
