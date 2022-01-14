#!/usr/bin/env bash
#
# The script has to be called with either "force" or "noforce" as
# arguments. If force is called then no matter the current branch we
# perform the check. Otherwise we only do it if the current branch is master.
unmerged_commits=$(git rev-list  HEAD..bugfixes --no-merges | wc -l | xargs echo -n)
current_branch=$(git branch --show-current)

should_check=false
if [[ $1 == "force" ]] || [[ "$current_branch" == "master" ]]; then
    should_check=true
fi

if [[ "$unmerged_commits" != "0" ]] && [[ "$should_check" == true ]]; then
    echo "There is $unmerged_commits commits in bugfixes that have not been merged for release"
    exit 1
else
    echo "Up to date with bugfixes or not on master"
fi
