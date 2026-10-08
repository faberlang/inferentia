#!/usr/bin/env python3.13
"""A1 oracle: `inferentia live --backend metal` against the captured llama.cpp references.

For each case (eog, continuation) of radix/docs/factory/gpu-reset/references/a1/
the script runs

    faber run --device metal <inferentia> -- inferentia live --backend metal
        --model <F32 gguf> --prompt <text> --max-tokens <n> --trace

with a RELEASE faber, parses the output and compares

    our prompt ids      vs  prompt_token_ids
    our generated ids   vs  generated_token_ids
    our finish reason   vs  finish_reason

At the first generated-id mismatch k the NEAR-TIE RULE of
s1-s2-acceptance-inputs-delivery.md section 3 applies: the reference gap
g = logprob1 - logprob2 at step k (per_step_top2_logprobs), M = the larger
absolute logit magnitude of OUR two top logits at step k (from the --trace line);
if g <= 1e-5 + 1e-4 * M the comparison ENDS SUCCESSFULLY at k ("near-tie at
step k"), otherwise it FAILS with the full context. Exit status is non-zero on
any FAIL.

    FABER_LIBRARY_HOME=<container root> a1_oracle.py --faber <release faber> \
        [--package <inferentia dir>] [--model <F32 gguf>] [--cases eog,continuation] \
        [--timeout 400] [--out results.json] [--refs <references/a1 dir>]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_MODEL = "/Users/ianzepp/ai/models/SmolLM2-360M-Instruct-f32.gguf"
DEFAULT_REFS = "/Users/ianzepp/work/faberlang/radix/docs/factory/gpu-reset/references/a1"
CASES = {"eog": "eog-reference.json", "continuation": "continuation-reference.json"}

TRACE_RE = re.compile(
    r"^trace step=(\d+) id=(-?\d+) top1=(-?\d+):(\S+) top2=(-?\d+):(\S+)$"
)


# ---------------------------------------------------------------------------
# Pure comparison logic (unit-testable)
# ---------------------------------------------------------------------------

def near_tie_bound(m):
    """The campaign F32 bound evaluated at logit magnitude m."""
    return 1e-5 + 1e-4 * m


def compare(ref, prompt_ids, ids, finish, traces):
    """Compare one live run with its reference.

    traces: {step: (chosen, id1, v1, id2, v2)}.
    Returns (verdict, detail) with verdict in PASS | PASS (near-tie) | FAIL.
    """
    if prompt_ids != ref["prompt_token_ids"]:
        return "FAIL", "prompt ids differ: ours=%s reference=%s" % (prompt_ids, ref["prompt_token_ids"])
    want = ref["generated_token_ids"]
    n = min(len(ids), len(want))
    for k in range(n):
        if ids[k] == want[k]:
            continue
        top2 = ref["per_step_top2_logprobs"][k]
        g = top2[0]["logprob"] - top2[1]["logprob"]
        t = traces.get(k)
        if t is None:
            return "FAIL", "mismatch at step %d (ours=%d reference=%d) and no trace line for the step" % (k, ids[k], want[k])
        m = max(abs(t[2]), abs(t[4]))
        bound = near_tie_bound(m)
        ctx = "step=%d ours=(id %d, top1 %d:%s, top2 %d:%s) reference=(id %d, top2 %d) g=%.3e M=%.4f bound=%.3e" % (
            k, ids[k], t[1], t[2], t[3], t[4], want[k], top2[1]["id"], g, m, bound)
        if g <= bound:
            return "PASS (near-tie)", "near-tie at step %d: %s" % (k, ctx)
        return "FAIL", "first mismatch: " + ctx
    if len(ids) != len(want):
        return "FAIL", "length differs: ours=%d reference=%d (first %d ids equal)" % (len(ids), len(want), n)
    if finish != ref["finish_reason"]:
        return "FAIL", "finish reason differs: ours=%s reference=%s" % (finish, ref["finish_reason"])
    return "PASS", "all %d ids equal, finish=%s" % (len(ids), finish)


def parse_output(out_lines, err_lines):
    """-> (prompt_ids, ids, finish, traces) from the run's stdout/stderr lines."""
    prompt_ids, ids, finish = None, None, None
    for ln in out_lines:
        if ln.startswith("prompt.ids="):
            prompt_ids = [int(x) for x in re.findall(r"-?\d+", ln[len("prompt.ids="):])]
        elif ln.startswith("ids="):
            ids = [int(x) for x in ln[len("ids="):].split()]
        elif ln.startswith("finish="):
            finish = ln[len("finish="):].strip()
    traces = {}
    for ln in err_lines:
        m = TRACE_RE.match(ln)
        if m:
            traces[int(m.group(1))] = (
                int(m.group(2)), int(m.group(3)), float(m.group(4)), int(m.group(5)), float(m.group(6)))
    return prompt_ids, ids, finish, traces


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def run_live(faber, package, model, prompt, max_tokens, timeout):
    cmd = ["/usr/bin/time", "-l", faber, "run", "--device", "metal", package, "--",
           "inferentia", "live", "--backend", "metal", "--model", model,
           "--prompt", prompt, "--max-tokens", str(max_tokens), "--trace"]
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    out, err = [], []

    def pump(stream, sink):
        for ln in stream:
            sink.append((time.time() - t0, ln.rstrip("\n")))

    ths = [threading.Thread(target=pump, args=(p.stdout, out)),
           threading.Thread(target=pump, args=(p.stderr, err))]
    for t in ths:
        t.start()
    timed_out = False
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        timed_out = True
    for t in ths:
        t.join()
    return p.returncode, timed_out, time.time() - t0, out, err


def first(lines, pred):
    for t, ln in lines:
        if pred(ln):
            return t
    return None


def timing_split(wall, out, err):
    """Front end / admit+digest / load / prefill / decode seconds."""
    t_out0 = first(out, lambda s: s.startswith("inferentia live"))   # the program's first line: front end done
    t_sha = first(out, lambda s: s.startswith("admit.sha256="))
    t_tok = first(out, lambda s: s.startswith("tokenizer.vocab="))
    t_ld0 = first(err, lambda s: s.startswith("port: load-start"))
    t_ld1 = first(err, lambda s: s.startswith("port: load-done"))
    t_pf0 = first(err, lambda s: s.startswith("port: prefill-start"))
    t_dc0 = first(err, lambda s: s.startswith("port: decode-start"))
    t_dc1 = first(err, lambda s: s.startswith("port: decode-done"))

    def d(a, b):
        return None if a is None or b is None else b - a

    return {
        "front_end_s": t_out0,
        "admit_digest_s": d(t_out0, t_tok),
        "load_s": d(t_ld0, t_ld1),
        "prefill_s": d(t_pf0, t_dc0),
        "decode_s": d(t_dc0, t_dc1),
        "wall_s": wall,
    }


def step_times(err):
    """Per generated-step wall times from the trace lines' arrival."""
    ts = [t for t, ln in err if TRACE_RE.match(ln)]
    return ts


def rss_bytes(err):
    for _, ln in err:
        m = re.match(r"\s*(\d+)\s+maximum resident set size", ln)
        if m:
            return int(m.group(1))
    return None


def fmt(x, nd=1):
    return "n/a" if x is None else ("%.*f" % (nd, x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faber", required=True, help="RELEASE faber binary")
    ap.add_argument("--package", default=PACKAGE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--refs", default=DEFAULT_REFS)
    ap.add_argument("--cases", default="eog,continuation")
    ap.add_argument("--timeout", type=float, default=400.0)
    ap.add_argument("--out", default=None, help="write results JSON here")
    a = ap.parse_args()
    if "FABER_LIBRARY_HOME" not in os.environ:
        sys.exit("set FABER_LIBRARY_HOME to the container root")

    rows, results = [], {}
    for name in a.cases.split(","):
        ref = json.load(open(os.path.join(a.refs, CASES[name])))
        max_tokens = len(ref["generated_token_ids"]) if ref["finish_reason"] == "length" else 32
        rc, timed_out, wall, out, err = run_live(
            a.faber, a.package, a.model, ref["prompt"], max_tokens, a.timeout)
        out_lines = [ln for _, ln in out]
        err_lines = [ln for _, ln in err]
        prompt_ids, ids, finish, traces = parse_output(out_lines, err_lines)
        if timed_out:
            verdict, detail = "FAIL", "timeout after %.0fs" % a.timeout
        elif rc != 0 or ids is None:
            tail = "\n".join(err_lines[-8:])
            verdict, detail = "FAIL", "run failed rc=%s; stderr tail:\n%s" % (rc, tail)
        else:
            verdict, detail = compare(ref, prompt_ids, ids, finish, traces)
        split = timing_split(wall, out, err)
        st = step_times(err)
        tps = None
        if len(st) >= 2:
            tps = (len(st) - 1) / (st[-1] - st[0])
        rss = rss_bytes(err)
        results[name] = {
            "verdict": verdict, "detail": detail, "ids": ids, "finish": finish,
            "prompt_ids": prompt_ids, "traces": {str(k): v for k, v in traces.items()},
            "split": split, "tokens_per_s_after_first": tps, "peak_rss_bytes": rss,
        }
        rows.append((name, verdict, len(ids) if ids else 0, finish, detail, split, tps, rss))

    print()
    print("%-13s %-16s %-5s %-7s %s" % ("case", "verdict", "ids", "finish", "detail"))
    for name, verdict, n, finish, detail, split, tps, rss in rows:
        print("%-13s %-16s %-5s %-7s %s" % (name, verdict, n, finish, detail))
    print()
    print("%-13s %9s %9s %9s %9s %9s %9s %10s %9s" % (
        "case", "front", "admit", "load", "prefill", "decode", "wall", "tok/s>1st", "RSS GB"))
    for name, verdict, n, finish, detail, split, tps, rss in rows:
        print("%-13s %9s %9s %9s %9s %9s %9s %10s %9s" % (
            name, fmt(split["front_end_s"]), fmt(split["admit_digest_s"]), fmt(split["load_s"]),
            fmt(split["prefill_s"]), fmt(split["decode_s"]), fmt(split["wall_s"]),
            fmt(tps, 2), fmt(None if rss is None else rss / 1e9, 2)))
    if a.out:
        json.dump(results, open(a.out, "w"), indent=1)
    sys.exit(0 if all(r[1].startswith("PASS") for r in rows) else 1)


if __name__ == "__main__":
    main()
