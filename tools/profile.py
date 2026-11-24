#!/usr/bin/env python3
"""Structural profile of an enwik file: where the bytes are."""
import sys, re, collections
path = sys.argv[1]
data = open(path, 'rb').read()
n = len(data)
pages = data.count(b'<page>')
redir = len(re.findall(rb'<text xml:space="preserve">#REDIRECT', data, flags=re.I))
# bytes inside <text ...>...</text>
text_bytes = 0; meta_bytes = 0
pos = 0
tb = re.compile(rb'<text xml:space="preserve">')
sizes = []
while True:
    m = tb.search(data, pos)
    if not m: break
    e = data.find(b'</text>', m.end())
    if e < 0: e = n
    text_bytes += e - m.end(); sizes.append(e - m.end())
    pos = e
meta_bytes = n - text_bytes
print(f"file bytes         {n:>13,}")
print(f"pages              {pages:>13,}")
print(f"redirect pages     {redir:>13,}")
print(f"text bytes         {text_bytes:>13,}  ({100*text_bytes/n:.1f}%)")
print(f"xml/meta bytes     {meta_bytes:>13,}  ({100*meta_bytes/n:.1f}%)")
sizes.sort()
print("page text size percentiles:", [sizes[int(len(sizes)*q)] for q in (0.1,0.25,0.5,0.75,0.9,0.99)])
links = len(re.findall(rb'\[\[', data))
print(f"[[ links           {links:>13,}")
print(f"{{{{ templates       {data.count(b'{{'):>13,}")
print(f"&lt; / &gt; / &amp;quot; {data.count(b'&lt;'):,} / {data.count(b'&gt;'):,} / {data.count(b'&quot;'):,}")
print(f"newlines           {data.count(10):>13,}")
hi = sum(1 for b in data[:20_000_000] if b >= 128)
print(f"bytes >=128 (first 20MB) {hi:,} ({100*hi/20e6:.2f}%)")
words = re.findall(rb'[A-Za-z]+', data[:200_000_000] if n > 200_000_000 else data)
c = collections.Counter(words)
tot = sum(c.values())
print(f"word tokens (first {min(n,200_000_000)//10**6}MB) {tot:,}; distinct {len(c):,}; letter bytes {sum(len(w)*k for w,k in c.items()):,}")
cum = 0
for i,(w,k) in enumerate(c.most_common()):
    cum += k
    if i+1 in (256, 4096, 16384, 65536, 262144): print(f"  top {i+1:>7,} words cover {100*cum/tot:.2f}% of tokens")
