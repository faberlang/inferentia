# Runs a command, timestamps each stderr line relative to launch, writes the
# stderr log to argv[2] and stdout to argv[3], prints per-family timings.
import subprocess, sys, time, threading, re
timeout = float(sys.argv[1]); log = sys.argv[2]; out = sys.argv[3]; cmd = sys.argv[4:]
t0 = time.time()
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
lines = []
def pump_err():
    for ln in p.stderr:
        lines.append((time.time() - t0, ln.rstrip("\n")))
def pump_out():
    with open(out, "w") as f:
        for ln in p.stdout:
            f.write(ln); f.flush()
ths = [threading.Thread(target=pump_err), threading.Thread(target=pump_out)]
[t.start() for t in ths]
try:
    p.wait(timeout=timeout)
except subprocess.TimeoutExpired:
    p.kill(); lines.append((time.time() - t0, "TIMEOUT after %ss" % timeout))
[t.join() for t in ths]
total = time.time() - t0
with open(log, "w") as f:
    for t, ln in lines:
        f.write("%9.2f %s\n" % (t, ln))
marks = {ln: t for t, ln in lines if ln.startswith("driver:")}
def mark(k): return marks.get("driver: " + k)
print("exit=%s total_wall=%.2fs" % (p.returncode, total))
for k in ["start", "admit-done", "inspect-done", "digest-done", "load-done", "cells-done"]:
    if mark(k) is not None: print("  %-13s t=%.2fs" % (k, mark(k)))
# per-family load seconds: delta between consecutive 'port: loaded' lines,
# the first measured from digest-done
fam = {}
prev = mark("digest-done")
for t, ln in lines:
    m = re.match(r"port: loaded (\S+)", ln)
    if not m or prev is None: continue
    name = m.group(1)
    key = re.sub(r"^blk\.\d+\.", "", name)
    if key == "token_embd.weight": key = "embed"
    elif key in ("attn_norm.weight", "ffn_norm.weight", "output_norm.weight"): key = "norms"
    elif key.startswith("attn_"): key = "attention"
    elif key.startswith("ffn_"): key = "ffn"
    fam[key] = fam.get(key, 0.0) + (t - prev)
    prev = t
for k, v in fam.items(): print("  family %-10s %.2fs" % (k, v))
if mark("digest-done") is not None and mark("load-done") is not None:
    print("  TOTAL LOAD (digest-done -> load-done) = %.2fs" % (mark("load-done") - mark("digest-done")))
for t, ln in lines:
    if "maximum resident set size" in ln or "real" in ln.split() or "peak memory footprint" in ln:
        print("  " + ln.strip())
print("  loaded tensors: %d" % sum(1 for t, ln in lines if ln.startswith("port: loaded")))
sys.exit(0 if p.returncode == 0 else 1)
