"""Label a chore video with a free local vision model, 4-second windows, fixed vocabulary.

Usage: python label.py qwen2.5vl:7b
Writes labels_<model>.json. Runs on the local GPU through Ollama. No paid API.
"""
import base64, json, sys, time, urllib.request
from pathlib import Path

MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5vl:7b"
HERE = Path(__file__).parent
FRAMES = sorted((HERE / "frames").glob("f_*.jpg"))  # f_001 = second 0
WIN = 4

ACTIONS = ["rinse", "scrub", "apply_soap", "pick_up", "put_down", "idle", "camera_off"]
OBJECTS = ["bowl", "plate", "glass", "utensil", "sponge", "none"]

PROMPT = f"""These {WIN} images are consecutive frames, one per second, from a camera looking down at a kitchen sink.
Say what the person's hands are doing in this window.

Answer with JSON only:
{{"action": one of {ACTIONS},
 "object": one of {OBJECTS},
 "hands": one of ["left", "right", "both", "none"],
 "label": "one short sentence describing the step",
 "qc": {{"sink_in_view": true or false, "view_blocked": true or false, "blurry": true or false}}}}

Rules: "idle" = no dish is being handled. "camera_off" = the sink is not in view.
"glass" covers cups and drinking glasses. Use "none" for object when nothing is handled."""


def ask(images):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT,
                      "images": [base64.b64encode(p.read_bytes()).decode() for p in images]}],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0, "seed": 7},
    }
    req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(json.loads(r.read())["message"]["content"])


out, t0 = [], time.time()
for i in range(0, len(FRAMES), WIN):
    imgs = FRAMES[i:i + WIN]
    try:
        ans = ask(imgs)
    except Exception as e:  # keep going; a failed window is scored as a miss
        ans = {"error": str(e)}
    out.append({"start": i, "end": i + len(imgs), **ans})
    print(f"{i:>3}s {ans.get('action')!s:>11} {ans.get('object')!s:>8}  {ans.get('label', ans.get('error'))}", flush=True)

name = MODEL.replace(":", "_").replace("/", "_")
(HERE / f"labels_{name}.json").write_text(json.dumps({"model": MODEL, "window_s": WIN,
                                                      "seconds": round(time.time() - t0, 1),
                                                      "windows": out}, indent=1))
print(f"done in {time.time() - t0:.0f}s")
