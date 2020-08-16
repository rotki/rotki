import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
ASSETS_FILE = Path(f'{root_dir}/rotkehlchen/data/all_assets.json')
with open(ASSETS_FILE, 'r') as f:
    assets = json.loads(f.read())


new_assets = {}
for key, entry in assets.items():
    new_assets[key] = entry
    # Under here do entry specific editing


with open(ASSETS_FILE, 'w') as f:
    f.write(
        json.dumps(
            new_assets, sort_keys=True, indent=4,
        ),
    )
