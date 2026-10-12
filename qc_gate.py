"""The fix: a one-frame quality gate that runs BEFORE labeling. Asks only whether the work area is usable.
Usage: python qc_gate.py qwen2.5vl:7b   -> qc_<model>.json, scored against gt.json qc_events.
"""
import base64, json, sys, time, urllib.request
from pathlib import Path

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5vl:7b"
HERE = Path(__file__).parent
FRAMES = sorted((HERE / "frames").glob("f_*.jpg"))

PROMPT_V1 = """This frame should show a kitchen sink from above, with a person's hands washing dishes.
Do not describe the activity. Only check the camera view. Answer with JSON only:
{"sink_visible": true or false, "view_blocked_by_person": true or false}
sink_visible = false if the sink is mostly out of the frame.
view_blocked_by_person = true if a head, hair or body covers a large part of the sink."""

PROMPT_V2 = """Look at this photo taken from above a kitchen counter.
Question 1: Is a stainless steel sink basin visible? Answer true even if hands, dishes, the faucet or a sponge are in or over it. Answer false only if the photo mostly shows the countertop, a fruit bowl, or something other than the sink.
Question 2: Does a person's head or hair cover part of the photo? Hands and arms do not count.
Answer with JSON only: {"sink_visible": true or false, "view_blocked_by_person": true or false}"""
VER = sys.argv[2] if len(sys.argv) > 2 else "v1"
PROMPT = PROMPT_V2 if VER == "v2" else PROMPT_V1


def ask(img):
    body = {"model": MODEL, "stream": False, "format": "json", "options": {"temperature": 0, "seed": 7},
            "messages": [{"role": "user", "content": PROMPT, "images": [base64.b64encode(img.read_bytes()).decode()]}]}
    req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(json.loads(r.read())["message"]["content"])


t0, flags = time.time(), []
for sec, f in enumerate(FRAMES):
    a = ask(f)
    bad = a.get("sink_visible") is False or bool(a.get("view_blocked_by_person"))
    flags.append({"second": sec, "bad": bad, **a})

gt = json.loads((HERE / "gt.json").read_text())["qc_events"]
bad_secs = {x["second"] for x in flags if x["bad"]}
caught = [e for e in gt if any(e["start"] <= s < e["end"] for s in bad_secs)]
key_secs = {s for e in gt for s in range(e["start"], e["end"])}
false_alarms = sorted(bad_secs - key_secs)
summary = {"model": MODEL, "prompt": VER, "seconds": round(time.time() - t0, 1), "frames": len(FRAMES),
           "events_in_key": len(gt), "events_caught": len(caught),
           "flagged_seconds": sorted(bad_secs), "false_alarm_seconds": false_alarms}
name = MODEL.replace(":", "_")
(HERE / f"qc_{name}_{VER}.json").write_text(json.dumps({"summary": summary, "frames": flags}, indent=1))
print(json.dumps(summary, indent=1))
