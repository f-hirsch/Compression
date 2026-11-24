#!/usr/bin/env python3
"""Round-trip benchmark harness.

Contract for a compressor binary BIN:
    BIN c <input> <archive>     compress
    BIN d <archive> <output>    decompress
Both must be deterministic and single-threaded.

Prints one JSON line (and appends it to --out if given):
  in_bytes, out_bytes, bpc (bits per input byte), c_cpu_s / d_cpu_s (user+sys),
  c_rss_mb / d_rss_mb (peak RSS), ns_per_byte, roundtrip_ok, exe_bytes.
CPU time (not wall time) is reported so results stay comparable on a busy machine.
"""
import argparse, json, os, subprocess, sys, tempfile, time, filecmp

def run(cmd):
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    err = p.stderr.read()
    _, status, ru = os.wait4(p.pid, 0)
    p.returncode = os.waitstatus_to_exitcode(status)
    return dict(rc=p.returncode, cpu=ru.ru_utime + ru.ru_stime, wall=time.time() - t0,
                rss_mb=ru.ru_maxrss / 1024.0, err=err.decode('utf8', 'replace')[-2000:])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bin', required=True)
    ap.add_argument('--file', required=True)
    ap.add_argument('--tag', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--no-decomp', action='store_true', help='skip decompression (NOT a valid result)')
    ap.add_argument('--keep', default='', help='keep the archive at this path')
    ap.add_argument('extra', nargs='*', help='extra args appended to the compress command only')
    a = ap.parse_args()
    tmpdir = tempfile.mkdtemp(prefix='bench_', dir=os.environ.get('BENCH_TMP', '/tmp'))
    arc = a.keep or os.path.join(tmpdir, 'arc')
    rec = os.path.join(tmpdir, 'rec')
    res = dict(tag=a.tag, bin=a.bin, file=os.path.basename(a.file), in_bytes=os.path.getsize(a.file),
               exe_bytes=os.path.getsize(a.bin))
    c = run([a.bin, 'c', a.file, arc] + a.extra)
    res.update(c_rc=c['rc'], c_cpu_s=round(c['cpu'], 2), c_wall_s=round(c['wall'], 2), c_rss_mb=round(c['rss_mb'], 1))
    if c['rc'] != 0:
        res.update(error='compress failed', stderr=c['err'])
    else:
        res['out_bytes'] = os.path.getsize(arc)
        res['bpc'] = round(8.0 * res['out_bytes'] / res['in_bytes'], 5)
        res['ns_per_byte'] = round(1e9 * c['cpu'] / res['in_bytes'], 1)
        if a.no_decomp:
            res['roundtrip_ok'] = None
        else:
            d = run([a.bin, 'd', arc, rec])
            res.update(d_rc=d['rc'], d_cpu_s=round(d['cpu'], 2), d_rss_mb=round(d['rss_mb'], 1))
            res['roundtrip_ok'] = (d['rc'] == 0 and os.path.exists(rec) and filecmp.cmp(a.file, rec, shallow=False))
            if d['rc'] != 0:
                res['stderr'] = d['err']
    for f in (rec, None if a.keep else arc):
        if f and os.path.exists(f):
            os.remove(f)
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass
    line = json.dumps(res)
    print(line)
    if a.out:
        with open(a.out, 'a') as f:
            f.write(line + '\n')
    sys.exit(0 if res.get('roundtrip_ok', False) or a.no_decomp and res.get('c_rc') == 0 else 1)

if __name__ == '__main__':
    main()
