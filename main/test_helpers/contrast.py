"""Calculate contrast from recorded computed colors, retaining axe's review flags.

Flat ancestor backgrounds are alpha-composited. Gradients and ancestor opacity are
explicitly unresolved. Glass labels use bounds over both black and white substrates,
since a blurred underlying window is not necessarily the DOM parent's background.
This is sampled color evidence, not a WCAG certification or screen-reader test.
"""
import argparse
import json
import re
from pathlib import Path


def rgba(value):
    # color-mix() is serialized as normalized color(srgb ...) by Chromium.
    # Unknown spaces must fail explicitly rather than yield a misleading ratio.
    value = value.strip().lower()
    if value == 'transparent':
        return [0, 0, 0, 0]
    if value.startswith('color(srgb '):
        channels = value.removeprefix('color(srgb ').removesuffix(')').replace('/', ' ').split()
        rgb = [float(n) * 255 for n in channels[:3]]
    elif value.startswith(('rgb(', 'rgba(')):
        channels = value[value.index('(') + 1:-1].replace(',', ' ').replace('/', ' ').split()
        rgb = [float(n[:-1]) * 2.55 if n.endswith('%') else float(n) for n in channels[:3]]
    else:
        raise ValueError(f'Unsupported computed color: {value}')
    alpha = channels[3] if len(channels) > 3 else '1'
    alpha = float(alpha[:-1]) / 100 if alpha.endswith('%') else float(alpha)
    return rgb + [alpha]


def luminance(rgb):
    linear = [v / 255 / 12.92 if v / 255 <= .04045 else ((v / 255 + .055) / 1.055) ** 2.4 for v in rgb]
    return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(foreground, background):
    values = sorted((luminance(foreground), luminance(background)))
    return (values[1] + .05) / (values[0] + .05)


def calculate(node):
    background = [255, 255, 255]
    unresolved = []
    for surface in reversed(node['surfaces']):
        if surface['image'] != 'none' or surface['opacity'] != '1':
            unresolved.append(surface)
        color = rgba(surface['background'])
        background = [color[i] * color[3] + background[i] * (1 - color[3]) for i in range(3)]
    foreground = rgba(node['color'])[:3]
    result = {'foreground': foreground, 'background': background,
              'contrast': round(contrast(foreground, background), 3), 'unresolved': unresolved}
    if node.get('placeholder') and node.get('placeholderColor'):
        result['placeholder_contrast'] = round(contrast(rgba(node['placeholderColor'])[:3], background), 3)
    glass = next((s for s in node['surfaces'] if s['class'] == 'desktop-dock'), None)
    if glass:
        color = rgba(glass['background'])
        bounds = [[color[i] * color[3] + substrate * (1 - color[3]) for i in range(3)] for substrate in (0, 255)]
        result['glass_minimum'] = round(min(contrast(foreground, bg) for bg in bounds), 3)
    return result


def review(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    result = []
    for row in data['reviews']:
        for node in row['historical_nodes']:
            if 'after' not in node:
                continue
            result.append({**{key: row[key] for key in ('route', 'width', 'theme')},
                           'target': node['target'], **calculate(node['after'])})
    output = path.with_name(path.stem.replace('contrast-review', 'contrast-calculated') + '.json')
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    failed = [r for r in result if min(r['contrast'], r.get('placeholder_contrast', 99), r.get('glass_minimum', 99)) < 4.5]
    print(f'{path.name}: {len(result)} sampled nodes; {len(failed)} below 4.5:1; '
          f'{sum(bool(r["unresolved"]) for r in result)} unresolved surfaces')
    return failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', nargs='+', type=Path)
    args = parser.parse_args()
    failures = [failure for path in args.reports for failure in review(path)]
    if failures:
        print(json.dumps(failures, indent=2))
        raise SystemExit(1)
