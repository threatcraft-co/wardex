# Wardex threat model

## Attacker capabilities

Wardex is designed to defend against an attacker who can:

1. Publish a malicious extension to the Visual Studio Marketplace under an unverified publisher account
2. Compromise a verified publisher account and push a malicious update (the Nx Console scenario)
3. Distribute a malicious `.vsix` file outside the Marketplace for sideload installation

## What wardex protects against

| Vector | Protection |
|---|---|
| Unverified publisher install | Blocked at install time via Marketplace API check |
| Sideloaded `.vsix` from unverified publisher | Blocked — wardex doesn't care about install source |
| Known malicious extension (on RemovedPackages list) | Blocked on install, flagged retroactively for already-installed extensions |
| Compromised verified publisher pushing a fast update | Flagged for review via update_monitor; alert-only by default |

## What wardex does NOT protect against

- A malicious extension from a verified publisher whose update has been live longer than the recency threshold and not yet on the RemovedPackages list
- An attacker with root or sudo on the developer's machine (wardex runs as the user)
- Social engineering that convinces a developer to add an unverified publisher to their allowlist
- Malicious behavior in legitimately verified extensions that have not yet been reported (this is IDE-SHEPHERD's domain)

## Trust boundaries

- Wardex trusts: the Visual Studio Marketplace API response, the Microsoft RemovedPackages list, the org policy file signature (when used)
- Wardex does NOT trust: the contents of `~/.vscode/extensions/`, the `.vsix` payload, the extension's `package.json` claims about itself (it cross-references with the API)

## Complementary tooling

Wardex is one layer. A complete IDE security posture also includes:

- **IDE-SHEPHERD** (Datadog) for runtime behavioral monitoring of extensions that did pass verification
- **Endpoint EDR** for host-level threat detection
- **SIEM** to correlate wardex events with other signals