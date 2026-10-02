import json
from pathlib import Path

from app.main import app

target = Path(__file__).parents[2] / "web/src/lib/api/openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(target)
