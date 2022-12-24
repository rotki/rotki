"""
This script runs pylint on the rotki codebase with the useless-suppression check on.
Then reads all the output, finds the files and lines and removes the useless suppressions.

There is a few problems with this and it's all due to pylint.
1. This does not find all useless suppressions.
2. It has false positives. Which means that it may flag as useless suppressions that are needed.

In general when the codebase has too many useless suppressions like the first time
I ran this, it's usefull. Removed ~500 occurences.  20 of them were false positives,
which I manually entered again later.

We should probably open bug reports to pylint for all of these at some point.
"""
import io
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

OCCURENCE_RE = re.compile(r'(.*\.py):(\d+):(\d+): I0021: Useless suppression of \'(.*)\'.*')


root_path = Path(__file__).resolve().parent.parent.parent


pylint_call = subprocess.Popen(
    ['pylint', '--rcfile', '.pylint.rc', 'rotkehlchen/', 'setup.py', 'package.py', 'tools/', '--enable', 'useless-suppression'],  # noqa: E501
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False,
)
pylint_call.wait()


class Suppression(NamedTuple):
    filename: str
    line: int
    error: str


files = defaultdict(dict)
for line in io.TextIOWrapper(pylint_call.stdout, encoding='utf-8'):
    print(line)
    match = OCCURENCE_RE.search(line)
    if match is None:
        continue

    matched_file = match.group(1)
    matched_line = int(match.group(2))
    files[matched_file][matched_line] = Suppression(
        filename=matched_file,
        line=matched_line - 1,  # 0 based indexing for file reading but 1 based for pylint
        error=match.group(4),
    )

for filename, occurences in files.items():
    with open(filename) as file:
        line_data = file.readlines()

    count = 0
    for idx, line in enumerate(line_data):
        suppression = occurences.get(idx)
        if suppression is None:
            continue

        line_data[idx] = line.replace(f'  # pylint: disable={suppression.error}', '')
        count += 1

    with open(filename, 'w') as file:
        file.writelines(line_data)
    print(f'Replaced {count} lines in {filename}')

print('DONE!')
