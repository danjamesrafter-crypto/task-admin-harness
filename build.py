#!/usr/bin/env python3
"""Inline src/index.html's vendor CSS, JS, fonts and images into one self-contained index.html.
GitHub's web upload flattens folders, and one file keeps the extension-app frame free of extra requests."""
import base64, os, re
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
MIME = {'.woff2': 'font/woff2', '.woff': 'font/woff', '.svg': 'image/svg+xml'}
def data_uri(path):
    return 'data:%s;base64,%s' % (MIME[os.path.splitext(path)[1]], base64.b64encode(open(path, 'rb').read()).decode())
def css(rel):
    path = os.path.join(SRC, rel); base = os.path.dirname(path); text = open(path, encoding='utf-8').read()
    return re.sub(r"url\('([^')]+\.(?:woff2?|svg))'\)", lambda m: "url('%s')" % data_uri(os.path.normpath(os.path.join(base, m.group(1)))), text)
h = open(os.path.join(SRC, 'index.html'), encoding='utf-8').read()
h = re.sub(r'<link rel="stylesheet" href="(vendor/[^"]+)">', lambda m: '<style data-src="%s">\n%s\n</style>' % (m.group(1), css(m.group(1))), h)
h = re.sub(r'<script src="(vendor/[^"]+)"></script>', lambda m: '<script data-src="%s">\n%s\n</script>' % (m.group(1), open(os.path.join(SRC, m.group(1)), encoding='utf-8').read().replace('</script', '<\\/script')), h)
for svg in set(re.findall(r"vendor/vision/[\w.-]+\.svg", h)):
    h = h.replace(svg, data_uri(os.path.join(SRC, svg)))
assert not re.search(r'[ (](src|href)="vendor/|url\(.vendor/', h), 'unresolved vendor reference'
out = os.path.join(os.path.dirname(SRC), 'index.html'); open(out, 'w', encoding='utf-8').write(h)
print(out, round(len(h) / 1024), 'KB')
