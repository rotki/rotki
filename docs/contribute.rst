Rotkehlchen Contribution Guide
##############################

Rotkehlchen is an opensource project so help is really appreciated.

Bug Reporting
=============

Use the `proper template <https://github.com/rotkehlchenio/rotkehlchen/issues/new?template=bug_report.md>`_ to create bug report issues.

Make sure to check the issue tracker for similar issues before reporting. If this is a new issue then provide a detailed description of the problem, what happened and what you were expecting to happen instead.

Also provide a detailed description of your system and of the rotkehlchen version used as the issue template explains.

Feature Requests
================

Use the `feature request <https://github.com/rotkehlchenio/rotkehlchen/issues/new?template=feature_request.md>`_ template.

Describe exactly what it is that you would like to see added to rotkehlchen and why that would provide additional value.

Please note that feature requests are just that. Requests. There is no guarantee that they will be worked on in the near future.

Contributing as a Developer
===========================

Being an opensource project, we welcome contributions in the form of source code. To do that you will have to work on an issue and open a Pull Request for it.

In order for your Pull Request to be considered it will need to pass the automated CI tests and you will also need to sign the CLA (Contributor's license agreement).

Committing Rules
****************

Please follow these rules for commits:
1. Commits should be just to the point, not too long and not too short.
2. Commits should do one thing, if two commits both do the same thing, that's a good sign they should be combined.
3. Commits should follow a simple format. A max 80 columns title, optionally followed by an empty line separator and then the subject.
4. More info on commit messages `here <https://who-t.blogspot.com/2009/12/on-commit-messages.html>`_.
5. **Never** merge master on the branch, always rebase on master. To delete/amend/edit/combine commits follow `this tutorial <https://robots.thoughtbot.com/git-interactive-rebase-squash-amend-rewriting-history>`_.
