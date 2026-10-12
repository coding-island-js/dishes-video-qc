"""Score model labels against the answer key. 0-3 per 4-second window:
+1 action right, +1 object right, +1 quality check right (sink out of view / view blocked).
Window boundaries are 4 s and the key is drawn at ~2 s, so a label counts as right if it matches
any key segment inside the window. Usage: python score.py labels_qwen2.5vl_7b.json
"""
import json, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
gt = json.loads((HERE / "gt.json").read_text())
run = json.loads((HERE / sys.argv[1]).read_text())


def in_window(items, s, e):
    return [x for x in items if x["start"] < e and x["end"] > s]


rows, fails = [], Counter()
for w in run["windows"]:
    s, e = w["start"], w["end"]
    key = in_window(gt["segments"], s, e)
    key_qc = in_window(gt["qc_events"], s, e)
    act_ok = any(k["action"] == w.get("action") for k in key)
    obj_ok = any(w.get("object") in [k["object"], *k.get("alt_objects", [])] for k in key)
    qc = w.get("qc") or {}
    flagged = (qc.get("sink_in_view") is False) or bool(qc.get("view_blocked")) or w.get("action") == "camera_off"
    qc_ok = flagged == bool(key_qc)
    score = act_ok + obj_ok + qc_ok
    want = " / ".join(sorted({f'{k["action"]} {k["object"]}' for k in key}))
    if not act_ok:
        fails[f'action: said {w.get("action")}, was {want}'] += 1
    if not obj_ok and act_ok:
        fails[f'object: said {w.get("object")}, was {want}'] += 1
    if not qc_ok:
        fails["missed a camera/view problem" if key_qc else "flagged a problem that wasn't there"] += 1
    rows.append({"start": s, "end": e, "score": score, "model": f'{w.get("action")} {w.get("object")}',
                 "key": want, "label": w.get("label"), "qc_flagged": flagged, "qc_key": bool(key_qc)})

n = len(rows)
summary = {
    "model": run["model"], "seconds_to_label": run["seconds"], "windows": n,
    "points": sum(r["score"] for r in rows), "max_points": 3 * n,
    "perfect_windows": sum(r["score"] == 3 for r in rows),
    "score_counts": {str(k): sum(r["score"] == k for r in rows) for k in (3, 2, 1, 0)},
    "qc_events_caught": sum(1 for r in rows if r["qc_key"] and r["qc_flagged"]),
    "qc_windows_in_key": sum(1 for r in rows if r["qc_key"]),
    "false_alarms": sum(1 for r in rows if r["qc_flagged"] and not r["qc_key"]),
    "failure_modes": fails.most_common(),
}
out = HERE / sys.argv[1].replace("labels_", "score_")
out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
print(json.dumps(summary, indent=1))
