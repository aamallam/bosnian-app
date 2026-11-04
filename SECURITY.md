# Security policy

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's private
"Report a vulnerability" button on this repository (Security tab).
We aim to acknowledge reports within 3 working days and to share a fix
timeline within 10.

## Scope

The backend API, the mobile apps, and the content-ingestion workers.

## How we work

The security baseline, threat model and data-handling rules are in
[docs/security/](docs/security/). Every change runs static analysis,
dependency auditing and secret scanning in CI before it can merge.
