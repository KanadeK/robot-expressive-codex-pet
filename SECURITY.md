# Security policy

## Supported version

Security fixes are provided for the latest tagged release.

## Reporting

Please do not attach secrets, private Codex configuration, or personal paths to
a public issue. Report a vulnerability through GitHub's private vulnerability
reporting page:

https://github.com/KanadeK/robot-expressive-codex-pet/security/advisories/new

If private reporting is unavailable, open a minimal issue asking the maintainer
for a private contact channel without including exploit details.

## Installer guarantees

The installer rejects archive traversal, validates the complete pet before
changing the destination, stages into a temporary directory, backs up an
existing installation, and restores it if replacement fails. Uninstall moves
the pet to a recoverable backup instead of deleting it.
