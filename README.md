# wardex

**Warden for your VS Code extensions.**

Wardex is a macOS daemon that prevents unverified VS Code extensions from running on developer machines. It watches the extensions directory in real time and quarantines any extension whose publisher does not hold the blue-checkmark domain verification — before the extension's code activates.

Built for security teams managing developer fleets. Open source, MIT licensed, local-only (no telemetry, no cloud).

---

## Why wardex exists

On May 20, 2026, GitHub confirmed that roughly 3,800 internal repositories were exfiltrated after one of its employees installed a poisoned VS Code extension. One day earlier, the Nx Console extension (2.2M installs, verified publisher) was briefly backdoored and reached every user with auto-update enabled before maintainers caught it.

The developer IDE is now a primary supply chain attack surface. Existing tooling watches behavior at runtime (IDE-SHEPHERD), scans the marketplace after publication (Microsoft's pipeline), runs periodic inventories from the cloud (StepSecurity Dev Machine Guard), or relies on the developer to choose carefully. **None of them enforce a publisher-trust policy at the install boundary on the endpoint, in real time, locally, before activation.**

That's what wardex does.

---

## How it works

Wardex is a local FSEvents-based daemon. When a new directory appears under `~/.vscode/extensions/`:

1. Wardex reads the extension's `package.json` to identify the publisher
2. Queries the Visual Studio Marketplace API for the publisher's `isDomainVerified` status
3. Evaluates against an allowlist, a blocklist, and the verification status
4. In **alert mode**: logs a warning if the extension would be blocked
5. In **enforce mode**: moves the extension directory into a quarantine folder before VS Code can activate it

No kernel extensions, no Apple entitlements, no telemetry. Pure user-space Python.

---

## Demo

$ wardex start --enforce

Starting wardex in ENFORCE mode

Watching: /Users/you/.vscode/extensions

2026-05-20 17:47:40 [INFO] Baseline: 71 existing extensions recorded

2026-05-20 17:47:40 [INFO] Wardex started in ENFORCE mode


**In another terminal — install an unverified extension:**

$ code --install-extension vscodevim.vim

Installing extension 'vscodevim.vim'...

Extension 'vscodevim.vim' v1.32.4 was successfully installed.


**Back in the wardex terminal:**

17:47:56,253 [INFO]    New extension directory detected: vscodevim.vim-1.32.4

17:47:56,253 [INFO]    Checking extension: vscodevim.vim

17:47:56,474 [INFO]    Policy decision: block (publisher is not verified)

17:47:56,474 [WARNING] Quarantined: vscodevim.vim-1.32.4 -> ~/.wardex/quarantine/...

17:47:56,474 [WARNING] BLOCKED vscodevim.vim — publisher is not verified


**221 milliseconds** from FSEvents detection to quarantine. VS Code thinks the install succeeded; the extension's code is sitting in a quarantine directory it cannot execute from.

`vscodevim.vim` has 8.5 million installs and no blue checkmark. Install count is not trust. Wardex enforces that distinction.

---

## Quick start

```bash
git clone https://github.com/threatcraft-co/wardex.git
cd wardex
./install.sh
```

That installs the daemon, registers the launchd agent, and starts wardex in alert mode. To switch to enforcement mode, edit `~/.config/wardex/wardex.yaml` and set `mode: enforce`, or pass `--enforce` to `wardex start`.

Requires Python 3.11 or newer, macOS, and VS Code with the `code` CLI installed.

---

## The trust model

Wardex relies on the Visual Studio Marketplace's `isDomainVerified` field as its primary trust signal. This is the same signal that renders the blue checkmark on the Marketplace web page and inside the VS Code GUI.

A publisher gets `isDomainVerified: true` when they have:

1. Proved DNS ownership of an identifying domain (e.g., `microsoft.com`, `github.com`)
2. Maintained their domain and extensions in good standing on the Marketplace for at least 6 months

**Why this and not `publisher.flags = "verified"`?** The Marketplace API exposes two different "verified" signals. `flags = "verified"` only means the publisher account is in good standing — not the blue checkmark. Long-standing indie publishers like `vscodevim` carry this flag without having a verified domain. Early versions of wardex (and most casual readings of the API) check the wrong field; we explicitly fixed that.

### What this trust model does NOT guarantee

We're deliberately honest about this:

- **Domain verification is not safety.** A motivated attacker can buy a domain, verify it, wait six months publishing benign extensions, then push a malicious update. Wardex would allow that update through. This is the Nx Console scenario, and addressing it requires the blocklist sync and update monitoring planned for Phase 2.
- **Display-name impersonation is still possible.** An attacker who acquires verified status can rename their publisher displayName to mimic a popular extension. Wardex checks publisher identity, not visual similarity.
- **Wardex runs as the user**, so a sufficiently privileged process (or the user themselves) can disable it. It is detective + fast-reactive, not kernel-enforced. For stronger guarantees, deploy via MDM with the extensions directory permission-locked.

For the full threat model, see [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

---

## Compared to other tools

Wardex is one layer in a defense-in-depth strategy. It is not a replacement for any of the tools below — and we use a few of them ourselves.

| Tool | What it does | Where it sits | Open source |
|------|-------------|--------------|-------------|
| **wardex** | Real-time pre-install enforcement based on publisher domain verification | OS layer, local daemon | ✅ MIT |
| **IDE-SHEPHERD** (Datadog) | Runtime behavioral monitoring of extension code execution | Inside VS Code as an extension | ✅ |
| **StepSecurity Dev Machine Guard** | Periodic inventory + risk scoring sent to cloud platform | Script + SaaS dashboard | Agent open source; platform closed |
| **Socket** | Marketplace-side scanning of npm/PyPI packages, PR gating | Build pipeline | ✅ Free tier |
| **Microsoft Marketplace** | Malware scanning, signature verification, retroactive takedowns | Server-side at publish time | N/A |

The fundamental architectural distinction: **wardex stops the extension before its code runs.** IDE-SHEPHERD catches malicious behavior after activation. StepSecurity reports on what's already installed at the next scan interval. Microsoft pulls compromised extensions after detection. These are all valid layers, but only wardex enforces at the install boundary in real time. A complete posture pairs wardex with at least one runtime monitor (IDE-SHEPHERD) and one CI-side scanner (Socket).

---

## Status

**Phase 1 complete** as of May 2026: real-time FSEvents-based daemon, Marketplace API verification, allowlist/blocklist policy engine, alert and enforce modes, quarantine directory, launchd integration, tested end-to-end on macOS 26.5 with VS Code 1.121.

**In progress / planned:**

- **Phase 2 — Blocklist sync.** Pull Microsoft's `RemovedPackages` list every 15 minutes and re-evaluate currently installed extensions. Closes the compromised-verified-publisher gap.
- **Phase 2 — `wardex audit` command.** One-shot scan of every installed extension against policy. For onboarding and compliance reports.
- **Phase 3 — Update monitoring.** Flag verified extensions updated within a configurable recency window (default 24 hours) and hold them for review. Directly addresses the Nx Console 18-minute backdoor pattern.
- **Phase 3 — HTML cross-verification.** Defense-in-depth check against the Marketplace product page HTML to catch API/UI drift.
- **Phase 4 — Fleet deployment kits.** Tested Jamf, Kandji, Ansible roles for security teams managing 50+ machines.

See [issues](https://github.com/threatcraft-co/wardex/issues) for the full roadmap.

---

## Contributing

Bug reports, false-positive reports (a legitimate extension was blocked), and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

Security issues should not be filed publicly. Open a private security advisory or email `security@threatcraft.co` (advisory channel preferred).

---

## License

MIT. See [LICENSE](LICENSE).

Built by [Threatcraft](https://github.com/threatcraft-co).
