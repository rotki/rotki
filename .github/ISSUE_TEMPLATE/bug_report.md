---
name: Bug Report
about: Submit bug reports about rotki
---


## Problem Definition

Provide a description of what is the current problem and why you are raising this issue.
If it's a bug please describe what was the unexpected thing that occured and what was the
expected behaviour.

Rotki also logs debug information to the `rotkehlchen.log` file. Please attach it to the
issue as it may help us find the source of the issue faster.

### System Description

Here add a detailed description of your system, e.g. output of the following script:

```
uname -a
command -v geth && geth version
command -v parity && parity --version
command -v rotki && rotki version
[ -d .git ] && git rev-parse HEAD
```
