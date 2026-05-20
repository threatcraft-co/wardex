# wardex

**Warden for your VS Code extensions.**

Wardex is a macOS daemon that prevents unverified VS Code extensions from installing on developer machines. It operates at the OS layer, outside the IDE, and stops the install before the extension's code ever executes.

Built for security teams managing developer fleets.

---

## Why wardex exists

On May 20, 2026, GitHub confirmed that ~3,800 internal repositories were exfiltrated after one of its employees installed a poisoned VS Code extension. One day earlier, the Nx Console extension (2.2M installs, verified publisher) was briefly backdoored and reached every user with auto-update enabled.

The developer IDE is now a primary supply chain attack surface. Existing tooling either watches behavior after install (IDE-SHEPHERD), scans the marketplace after publish (Microsoft's pipeline), or relies on the developer to choose carefully. None of them enforce a publisher-trust policy at the install boundary on the endpoint.

That's what wardex does.

## What wardex does

- Watches `~/.vscode/extensions/` for new installs in real time using macOS FSEvents
- Queries the Visual Studio Marketplace API to check the publisher's verified status
- Blocks and quarantines the install if the publisher is not verified
- Cross-references every install against Microsoft's RemovedPackages blocklist
- Flags verified extensions updated within a configurable recency window (defense against the Nx Console vector)
- Ships alerts to Slack, webhooks, syslog, or macOS Notification Center
- Runs silently as a `launchd` user agent — deployable via Jamf, Ansible, or any MDM

## What wardex does NOT do

- Replace an EDR or behavioral runtime monitor (use IDE-SHEPHERD for that layer)
- Guarantee verified publishers are safe — verification is a necessary but not sufficient signal
- Catch extensions installed before wardex was deployed (use `wardex audit` for that)

## Architecture

Wardex runs as a user-space `launchd` daemon. It uses FSEvents to watch the extensions directory, the Marketplace REST API to verify publishers, and a pluggable alert dispatcher for security team integrations. No kernel extensions, no Apple entitlements required.

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the full threat model and known limitations.

## Quick start

```bash
git clone https://github.com/threatcraft-co/wardex.git
cd wardex
./install.sh
```

That installs the daemon, registers the launchd agent, and starts wardex in alert-only mode. To switch to enforcement mode, edit `~/.config/wardex/wardex.yaml` and set `mode: enforce`.

## Fleet deployment

See [docs/policy-authoring.md](docs/policy-authoring.md) for org policy distribution via MDM, and `deploy/` for Ansible roles and Jamf scripts.

## Status

Wardex is in early development. Phase 1 (core daemon + Marketplace verification) is the current focus. See [issues](https://github.com/threatcraft-co/wardex/issues) and the roadmap in `docs/`.

## License

MIT. See [LICENSE](LICENSE).