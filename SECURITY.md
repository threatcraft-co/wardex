# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in wardex, **please do not file a public GitHub issue.** Instead:

- **Preferred:** Open a [private security advisory](https://github.com/threatcraft-co/wardex/security/advisories/new) on GitHub.
- **Alternative:** Email `security@threatcraft.co`.

Please include:
- A description of the issue and its impact
- Steps to reproduce
- The version of wardex, macOS, and VS Code you tested against
- Any proof-of-concept code (encrypted attachment is fine if sensitive)

We aim to acknowledge reports within 72 hours and provide a fix or mitigation timeline within 7 days.

Wardex is open-source and maintained by [Threatcraft](https://github.com/threatcraft-co). We do not currently offer a bug bounty.

---

## Security model

Wardex is itself a security tool. This section documents what wardex does that is security-sensitive, what it trusts, and what it explicitly does not protect against. We are deliberately specific here so that security teams reviewing wardex for fleet deployment can verify our claims.

### Privilege model

Wardex runs **as the user**, not as root. The macOS launchd integration installs a user agent (`~/Library/LaunchAgents/com.threatcraft.wardex.plist`), not a system daemon. No `sudo`, no setuid binaries, no kernel extensions, no Apple entitlements.

This is intentional. Running as the user means:
- Smaller attack surface if wardex itself is compromised
- No risk of wardex's bugs cascading into system-level damage
- Easy uninstall (a single `launchctl unload`)

The trade-off: a sufficiently privileged process (or the user themselves) can disable wardex. For stronger guarantees, deploy via MDM with the extensions directory permission-locked and wardex's launchd plist managed by your endpoint management tool.

### Network behavior

Wardex makes outbound HTTPS connections to exactly **one** external host:

- `marketplace.visualstudio.com` — to query the public extension query API for publisher verification status

That is the only network call wardex makes. No telemetry. No analytics. No phone-home. No third-party services. No upload of installed extension lists. No CDN beacons.

You can verify this with a packet capture or by reviewing `wardex/marketplace.py`, which contains the only HTTP code in the project.

The URL is constructed from a hardcoded base path and the validated `publisher.name` identifier. We do not follow any URL supplied by an extension's manifest.

### File system behavior

Wardex reads from:
- `~/.vscode/extensions/` — to enumerate installed extensions and read their `package.json` files
- `~/.config/wardex/wardex.yaml` — its configuration

Wardex writes to:
- `~/.wardex/quarantine/` — where blocked extensions are moved
- Log files configured in `wardex.yaml` (default: `~/Library/Logs/wardex.log`)

Wardex does **not** write outside these locations. Quarantined extensions are **moved** (not deleted) with a timestamped suffix, so a false positive can be restored.

### Input validation

The trust boundary between wardex and the outside world consists of two inputs:

**Extension `package.json`.** Parsed with Python's stdlib `json.load()`, which has no code execution path. Only the `publisher` and `name` fields are used. Both are validated against `^[A-Za-z0-9_-]+$` before being interpolated into any URL — this matches the Marketplace's own publisher/extension naming policy and rejects any value containing characters that could break URL semantics or cause encoding ambiguity.

**Marketplace API response.** Parsed with `requests`' JSON decoder. We extract specific typed fields (`isDomainVerified`, `domain`, `publisherName`, etc.) with sensible defaults when missing. A malformed or hostile response will raise `MarketplaceError`, at which point wardex applies its `api_failure_policy` (default: `fail_closed` — block the install).

### Trust assumptions

Wardex trusts:

- The Visual Studio Marketplace API response (`marketplace.visualstudio.com` over HTTPS, using the system trust store)
- Microsoft's `RemovedPackages` list when Phase 2 ships
- The org policy file signature (HMAC-SHA256) when Phase 5 ships
- The macOS file system semantics — specifically that FSEvents accurately reports directory creation and rename events

Wardex does **not** trust:

- The contents of `~/.vscode/extensions/` itself (we cross-reference with the API)
- The `.vsix` payload (we never execute or unpack it)
- The extension's own claims about its publisher beyond the identifier match

### What wardex does not protect against

Be explicit about this. Wardex is one layer.

1. **A malicious extension from a verified publisher whose update has not yet been flagged.** The Nx Console scenario (May 2026) involved a legitimate verified publisher whose maintainer's token was stolen and a malicious version was published. Wardex would allow that update through until Microsoft retroactively pulls it. Phase 2 (blocklist sync) and Phase 3 (update monitoring) address this.

2. **An attacker with root or sudo on the developer's machine.** Wardex runs as the user. Root can disable it, modify the allowlist, or replace the binary.

3. **Social engineering.** If a developer is convinced to add an unverified publisher to their allowlist, wardex will respect that allowlist entry.

4. **Display name impersonation.** Wardex checks publisher identity (the immutable `publisherName`), not the human-readable `displayName`. An attacker who legitimately gains verified status under an unrelated `publisherName` can still set their displayName to mimic a popular extension. Wardex does not detect this; runtime monitoring tools like IDE-SHEPHERD are better positioned to catch downstream behavior.

5. **Side-loaded `.vsix` files that were placed in the extensions directory before wardex was deployed.** Wardex's baseline captures existing extensions and does not evaluate them. The planned `wardex audit` command (Phase 2) addresses this.

6. **Wardex itself being compromised.** If an attacker can replace `wardex/marketplace.py` or `wardex/policy.py`, they can change the verdict. Standard mitigations apply: code review, repository signing, MDM-managed deployment of a pinned version.

### Cryptography

Wardex does not implement custom cryptography. It uses:
- TLS via Python's `requests` library (which uses the system trust store)
- HMAC-SHA256 for org policy file signatures (planned, Phase 5) — via Python's stdlib `hmac` module

We do not generate keys, certificates, or signatures ourselves at runtime.

### Dependencies

Wardex's runtime dependencies are listed in `pyproject.toml`. As of writing:

- `watchdog` — FSEvents wrapper, the OS event source
- `requests` — HTTP client for the Marketplace API
- `pyyaml` — config file parser
- `click` — CLI framework
- `rich` — terminal output formatting

We pin major versions and audit transitive dependencies as part of release. To check the dependency tree:

```bash
pip install -e ".[dev]"
pip list
```

### Reproducible builds

Wardex is pure Python — no compiled binaries, no native modules in our own code (`watchdog` does ship a native FSEvents binding, but it's the canonical published version from PyPI). You can audit every line of wardex by reading the source.

---

## What we ask of users

- Run wardex with `--enforce` mode in production. Alert mode is for initial rollout only.
- Pin wardex to a tagged release rather than `main` once we publish releases.
- Review your allowlist regularly. Allowlisted publishers are exempt from verification — treat additions as a significant trust decision.
- Update wardex. We will document significant security-relevant changes in release notes.

---

## Acknowledgments

Vulnerability reports and security improvements are credited (with permission) in release notes.