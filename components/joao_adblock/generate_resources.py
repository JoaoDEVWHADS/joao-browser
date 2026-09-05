#!/usr/bin/env python3
"""Generate compiled native filtering resources from the reviewed EasyList snapshot."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def cosmetics(text):
    rules = []
    for line in text.splitlines():
        exception = '#@#' in line
        delimiter = '#@#' if exception else '##'
        if delimiter not in line or line.startswith('!'):
            continue
        domains, selector = line.split(delimiter, 1)
        if not selector or selector.startswith('+js(') or ':style(' in selector:
            continue
        rules.append([domains.split(',') if domains else [], selector, exception])
    return rules


def cosmetic_exceptions(text):
    result = []
    for line in text.splitlines():
        if not line.startswith('@@') or '$' not in line:
            continue
        pattern, options = line[2:].split('$', 1)
        options = options.split(',')
        if not {'generichide', 'elemhide'}.intersection(options):
            continue
        domains = []
        for option in options:
            if option.startswith('domain='):
                domains = option[7:].split('|')
            elif option not in ('generichide', 'elemhide', 'match-case'):
                raise ValueError('Unsupported cosmetic exception: ' + line)
        prefix = ''
        if pattern.startswith('||'):
            prefix, pattern = r'^https?://(?:[^/?#]*\.)?', pattern[2:]
        elif pattern.startswith('|'):
            prefix, pattern = '^', pattern[1:]
        suffix = ''
        if pattern.endswith('|'):
            pattern, suffix = pattern[:-1], '$'
        converted = ''.join('.*' if c == '*' else
                            r'(?:[^A-Za-z0-9_.%-]|$)' if c == '^' else
                            re.escape(c) for c in pattern)
        result.append([prefix + converted + suffix, domains,
                       'elemhide' not in options, 'match-case' in options])
    return result


def literal(value):
    # Small adjacent literals avoid MSVC's per-literal size limit.
    return '\n'.join(json.dumps(value[i:i + 2048], ensure_ascii=False)
                     for i in range(0, len(value), 2048))


def generate(source, output):
    text = (source / 'easylist.txt').read_text(encoding='utf-8')
    expected = json.loads((source / 'snapshot.json').read_text(encoding='utf-8'))['sha256']
    if hashlib.sha256(text.encode()).hexdigest() != expected:
        raise ValueError('EasyList snapshot hash mismatch')
    script = (source / 'cosmetic.js').read_text(encoding='utf-8').replace(
        '/* RULES */ []', json.dumps(cosmetics(text), ensure_ascii=True)).replace(
        '/* EXCEPTIONS */ []', json.dumps(cosmetic_exceptions(text)))
    youtube = (source / 'youtube.js').read_text(encoding='utf-8')
    output.write_text('#ifndef COMPONENTS_JOAO_ADBLOCK_RESOURCES_H_\n'
                      '#define COMPONENTS_JOAO_ADBLOCK_RESOURCES_H_\n'
                      'namespace joao_adblock {\n'
                      'inline constexpr char kRules[] =\n' + literal(text) + ';\n'
                      'inline constexpr char kVersion[] = "joao-' + hashlib.sha256(text.encode()).hexdigest()[:24] + '";\n'
                      'inline constexpr char kCosmeticScript[] =\n' + literal(script) + ';\n'
                      'inline constexpr char kYoutubeScript[] =\n' + literal(youtube) + ';\n'
                      '}\n#endif\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    generate(Path(__file__).parent, args.output)
