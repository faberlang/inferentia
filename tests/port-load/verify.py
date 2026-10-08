# Reads the GGUF directly (tensor table, numpy) and compares the driver's
# printed cells bit-exactly (the printed shortest-repr decimal is parsed back
# to float32 and compared as raw bits).
import struct, sys
import numpy as np
model, outp = sys.argv[1], sys.argv[2]
f = open(model, "rb")
def rd(fmt):
    n = struct.calcsize(fmt); return struct.unpack(fmt, f.read(n))
def rstr():
    (n,) = rd("<Q"); return f.read(n).decode()
assert f.read(4) == b"GGUF"
ver, nt, nkv = rd("<IQQ")
SC = {0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
def skip(t):
    if t in SC: f.read(SC[t])
    elif t == 8: rstr()
    elif t == 9:
        et, = rd("<I"); n, = rd("<Q")
        for _ in range(n): skip(et)
    else: raise SystemExit("bad kv type %d" % t)
align = 32
for _ in range(nkv):
    k = rstr(); t, = rd("<I")
    if k == "general.alignment" and t == 4: align, = rd("<I"); continue
    skip(t)
tab = {}
for _ in range(nt):
    name = rstr(); nd, = rd("<I"); ne = rd("<%dQ" % nd); ty, = rd("<I"); off, = rd("<Q")
    tab[name] = (ne, ty, off)
pos = f.tell(); data_start = (pos + align - 1) // align * align
assert data_start == 1786560, data_start
def tensor(name):
    ne, ty, off = tab[name]; assert ty == 0
    n = int(np.prod(ne))
    a = np.memmap(model, dtype="<f4", mode="r", offset=data_start + off, shape=(n,))
    return a.reshape(tuple(reversed(ne)))   # row-major shape = reversed ne
cells = [
 ("token_embd[30000,17]", "token_embd.weight", (30000, 17)),
 ("token_embd[49151,959]", "token_embd.weight", (49151, 959)),
 ("blk0.attn_q[123,456]", "blk.0.attn_q.weight", (123, 456)),
 ("blk0.attn_k[319,959]", "blk.0.attn_k.weight", (319, 959)),
 ("blk31.ffn_down[900,2000]", "blk.31.ffn_down.weight", (900, 2000)),
 ("blk15.ffn_gate[2559,0]", "blk.15.ffn_gate.weight", (2559, 0)),
 ("blk7.attn_norm[500]", "blk.7.attn_norm.weight", (500,)),
 ("output_norm[959]", "output_norm.weight", (959,)),
]
got = {}
for ln in open(outp):
    if ln.startswith("cell "):
        _, label, val = ln.split()
        got[label] = val
ok = True
print("%-26s %-14s %-14s %s" % ("cell", "file bits", "driver bits", "match"))
for label, name, idx in cells:
    want = np.float32(tensor(name)[idx])
    wb = want.view(np.uint32).item()
    if label not in got:
        print("%-26s %08x %-14s NO"  % (label, wb, "missing")); ok = False; continue
    gv = np.float32(got[label]); gb = gv.view(np.uint32).item()
    m = wb == gb; ok &= m
    print("%-26s %08x       %08x       %s  (%s)" % (label, wb, gb, "yes" if m else "NO", got[label]))
print("sha.bound=true" if "sha.bound=true" in open(outp).read() else "SHA BINDING MISSING")
sys.exit(0 if ok else 1)
