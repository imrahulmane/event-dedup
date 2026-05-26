import base64
import json
import random
import uuid
from datetime import datetime, timezone

URL = "http://localhost:8000/events"
NUM_UNIQUE = 1      # number of distinct events
REPEATS = 10000            # each one sent this many times
OUTPUT = "targets.json"

targets = []
for _ in range(NUM_UNIQUE):
    event = {
        "source": "loadtest",
        "event_type": "stress.run",
        "entity_id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": {"test": True},
    }
    body_bytes = json.dumps(event, separators=(",", ":")).encode("utf-8")
    body_b64 = base64.b64encode(body_bytes).decode("ascii")

    target = {
        "method": "POST",
        "url": URL,
        "header": {"Content-Type": ["application/json"]},
        "body": body_b64,
    }
    targets.extend([target] * REPEATS)

random.shuffle(targets)

with open(OUTPUT, "w") as f:
    for t in targets:
        f.write(json.dumps(t, separators=(",", ":")) + "\n")

print(f"Wrote {len(targets)} targets ({NUM_UNIQUE} unique × {REPEATS}) to {OUTPUT}")
