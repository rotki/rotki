import os

# Find the branch name here!
github_head_ref = os.getenv('GITHUB_HEAD_REF')
github_head_ref2 = os.environ.get('GITHUB_HEAD_REF')
print(f'{github_head_ref=}')
print(f'{github_head_ref2=}')
