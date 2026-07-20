# Security Policy

## Reporting a vulnerability

Use GitHub's **[private vulnerability reporting](https://github.com/vrvlab/amphibious-aircraft-ontology/security/advisories/new)** — the Security tab → "Report a vulnerability." That opens a private channel visible only to maintainers.

Please do **not** open a public issue for a security problem.

We aim to acknowledge reports within 7 days. This is a small volunteer project, so please be patient; we would rather respond carefully than quickly.

## Scope

This repository contains data (YAML constraint definitions), documentation, and — over time — tooling that reads them. Relevant security concerns include:

- vulnerabilities in any tooling or CI we ship
- supply-chain issues in dependencies
- anything that would let a contributor's PR execute code in our CI or exfiltrate secrets

## Data integrity is also a security concern here

This project publishes machine-readable regulatory constraints. **A silently incorrect constant is a safety issue, not just a bug**, because the entire purpose of the artifact is to be trusted by automated tooling.

If you find a constraint that misstates the underlying regulation, please report it — as a normal issue is fine, no need for the private channel. Include:

- the constraint `id`
- what the repository says
- what the primary source says, with a citation and the edition date

We treat these as high priority and will correct them promptly. See [`docs/verification-log.md`](docs/verification-log.md) for the corrections we have already made to our own source material.

## What this project is not

Nothing here has regulatory standing. A `verified` status means "a maintainer read the primary source carefully and it matched," **not** that any authority has reviewed or approved it. Anyone doing actual certification work must work from the regulation itself and their certification authority.

Using this repository as a substitute for regulatory review is a misuse of it, and no verification status we assign changes that.
