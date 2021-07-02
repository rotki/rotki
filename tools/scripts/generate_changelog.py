"""
Generate changelog for github release from the changelog.rst file
Example of execution:

python tools/scripts/generate_changelog.py -v 1.15.0 -f docs/changelog.rst

It outputs the result to the stdout
"""

import argparse
from typing import Dict, List
import re

NEW_ASSETS_MSG = 'Added support for the following tokens'
NEW_VERSION_FORMAT = '* :release:`{}'


def generate_changelog(version: str, path: str) -> str:
    change_regex = r'\*\ :(feature|bug):`(\d*|-)`\ (.+)'

    changes: Dict[str, List[str]] = {'features': [], 'bugs': []}
    github_link = '- #{number} {text}'
    not_listed_change = '- {text}'

    with open(path) as f:
        lines = f.readlines()
        start = False
        for line in lines:
            if NEW_VERSION_FORMAT.format(version) in line:
                start = True
                continue
            if start:
                r = re.search(change_regex, line)
                if r is not None:
                    groups = r.groups()
                    # Check if the change is related to a commit
                    if groups[1].isdigit():
                        text = github_link.format(number=groups[1], text=groups[2])
                    else:
                        text = not_listed_change.format(text=groups[2])

                    if NEW_ASSETS_MSG in text:
                        # Skip new assets feature
                        continue

                    if groups[0] == 'feature':
                        changes['features'].append(text)
                    else:
                        changes['bugs'].append(text)

            if start and '* :release:' in line:
                break

    result = [
        '# New Features\n',
        '\n'.join(changes['features']),
        '\n# Bug Fixes\n',
        '\n'.join(changes['bugs']),
    ]
    return '\n'.join(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get changes for release notes from the changelog')  # noqa: E501
    parser.add_argument('-f', '--file', type=str, help='File to use for the extraction of changes')
    parser.add_argument('-v', '--version', type=str, help='Version to generate the changelog for')

    args = parser.parse_args()

    print(generate_changelog(args.version, args.file))
