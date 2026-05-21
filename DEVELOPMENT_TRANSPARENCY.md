# Development Disclosure

## How this project was built

Wardex was designed, directed, and tested by a non-developer with a background in cybersecurity. The implementation was produced with substantial assistance from AI-based code generation tools.

This document exists to be transparent about that process and what it means for anyone using, auditing, or contributing to this project.

---

## What that means in practice

Every line of code in this repository was written with AI assistance. The author is not a software developer and did not write the implementation independently. The conceptual design, threat model, security requirements, architecture decisions, testing approach, and final judgments on what shipped were made by the author — but the translation of those decisions into working code was AI-assisted.

This is disclosed because:

- Security tools carry a higher standard of transparency than most software
- Users of wardex should be able to make an informed decision about how much trust to place in the code
- The open source community deserves honesty about how a project came to exist

---

## What was done to mitigate the risks of AI-assisted code

AI-generated code can contain subtle bugs, logical errors, or security issues that are not immediately obvious. The following steps were taken to reduce that risk:

**Security requirements were defined before implementation.** The threat model, privilege model (user-space only, no root), network boundaries (one external host), trust signals (`isDomainVerified` not `flags`), and failure mode defaults (`fail_closed`) were specified explicitly before code was written, and the implementation was verified against them.

**The code was reviewed line by line.** Every function was read, understood at a conceptual level, and verified to do what it claims before being committed.

**Real-world testing caught a real bug.** During end-to-end testing, wardex initially allowed an unverified extension (`vscodevim.vim`, 8.5M installs, no blue checkmark) because the first implementation was checking the wrong trust signal — the API's `flags = "verified"` field, which only indicates account-in-good-standing — instead of `isDomainVerified`, which is the actual blue-checkmark badge. This was discovered, diagnosed, and fixed before Phase 1 was marked complete. The fact that this slipped past initial review is exactly why testing against real extensions matters more than testing against mocks, and why the trust model section of `SECURITY.md` is explicit about which field wardex relies on.

**Security hardening was applied deliberately.** Identifier validation against `^[A-Za-z0-9_-]+$` before any Marketplace API call, `fail_closed` as the default `api_failure_policy`, quarantine via move (not delete) so false positives are reversible, and user-only file permissions on the launchd plist were each explicitly requested, implemented, and confirmed in the running daemon.

**The codebase was kept readable.** Wardex is ~1500 lines of Python across about a dozen modules. Each module has a single responsibility (Marketplace API client, policy engine, FSEvents watcher, quarantine, alerts). The trust-sensitive logic lives in two files (`wardex/marketplace.py` and `wardex/policy.py`) that together total under 300 lines. Anyone reviewing wardex's verification behavior can read those two files in a few minutes.

**Dependencies were chosen conservatively.** Five runtime dependencies, all widely-used, all listed in `pyproject.toml`: `watchdog` (FSEvents wrapper), `requests` (HTTP), `pyyaml` (config), `click` (CLI), `rich` (terminal output). No analytics SDKs, no telemetry libraries, no closed-source binaries beyond `watchdog`'s native FSEvents binding (which is the canonical PyPI build).

**Tests were written for the security-critical path.** The policy engine has unit tests covering verified-publisher allow, unverified-publisher block, allowlist override, and blocklist override. All pass.

---

## What this does not mean

This disclosure is not an apology. The security properties documented in `SECURITY.md` are real and were implemented intentionally. The identifier validation runs. The `fail_closed` default applies. The `isDomainVerified` field is what gets checked. The end-to-end test against `vscodevim.vim` was real, and the 221-millisecond detection-to-quarantine timing in the README is from an actual log capture, not an aspirational claim.

This disclosure also does not mean the code is untrustworthy by default. It means you should read it — which you should do with any security tool regardless of how it was written.

---

## For security researchers and contributors

If you find a vulnerability, please follow the responsible disclosure process in [SECURITY.md](SECURITY.md). The fact that this project used AI assistance in development does not change the seriousness with which security reports will be treated — if anything, it raises the priority.

If you are a developer who wants to contribute, your review and improvement of the codebase is genuinely welcome. Contributions from people with stronger implementation experience than the original author are not just accepted — they are encouraged. Specific areas where deeper expertise would help:

- The FSEvents handler's race-condition properties between extension extraction and the rename-into-place event
- The `package.json` parsing path's robustness against edge cases (BOMs, encoding declarations, deeply nested JSON, etc.)
- The launchd plist's posture for fleet deployment via Jamf, Kandji, and Intune
- Test coverage for the daemon module (currently only the policy engine is unit-tested)

---

## Honest assessment of risk

Anyone using wardex should understand:

- The code has not been independently audited by a third party
- The author cannot rule out bugs or issues that were not caught during development and testing
- AI-assisted code generation, while powerful, is not equivalent to expert human engineering reviewed over time
- Wardex is at version 0.1.0 — early. The verification logic was tested against real extensions on real macOS, but the surface area is small and so is the test history

The recommendation is the same as for any open source security tool: read the source before trusting it with anything sensitive, deploy in alert mode before enforce mode, and report anything that looks wrong.

---

*This file will be updated if the development process changes significantly — for example, if a formal third-party audit is conducted or if maintainership expands to include developers contributing independent implementation work.*