#!/usr/bin/env python
import hashlib
import json
import re
import sys
from pathlib import Path

src_dir = Path(__file__).parent.parent.parent / 'rotkehlchen'
ASSETS_JSON = src_dir / 'data/all_assets.json'
ASSETS_META = src_dir / 'data/all_assets.meta'
ASSETS_TEST = src_dir / 'tests/unit/test_assets.py'

with open(ASSETS_META, 'r') as assets_meta:
    old_meta = json.load(assets_meta)

with open(ASSETS_JSON, 'rb') as assets_json:
    new_md5 = hashlib.new('md5')
    new_md5.update(assets_json.read())

if new_md5.hexdigest() == old_meta['md5']:
    print('Assets meta file is up-to-date.')
    sys.exit(0)

new_meta = json.dumps({
    'md5': new_md5.hexdigest(),
    'version': old_meta['version'] + 1,
})

with open(ASSETS_META, 'w') as assets_meta:
    assets_meta.write(new_meta + '\n')

with open(ASSETS_TEST, 'r+') as assets_test:
    test = assets_test.read()
    assets_test.seek(0)
    needle = r'last_meta = {.md5.: .*.version.: .*}'
    replacement = 'last_meta = ' + new_meta.replace('"', '\'')
    assets_test.write(re.sub(needle, replacement, test))
