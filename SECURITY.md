# ️ Security Policy

**A clear, coordinated process for protecting users of terminal-odds-ticker.**

![Security](https://img.shields.io/badge/Security-Responsible%20Disclosure-2ea44f?style=for-the-badge&logo=shield)
![Supported](https://img.shields.io/badge/Supported-v2.x-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)

## Supported versions

| Release | Support status |
|:--|:--|
| `v2.x` | Supported |
| `v1.x` | End-of-Life |

Security fixes are developed for the supported release line. Upgrade to the latest `v2.x` release before reporting an issue where practical.

## Reporting a vulnerability

Please report suspected vulnerabilities privately. Do not open a public issue or disclose exploit details before maintainers have had an opportunity to investigate.

Use GitHub's **Security** tab to create a [private security advisory](https://github.com/imardagokce/terminal-odds-ticker/security/advisories/new). Include the affected version, impact, reproduction steps, and any relevant logs with secrets removed. For suspected API-key exposure, describe where the key may have appeared and revoke or rotate it with the provider immediately.

If private advisories are unavailable, contact the repository maintainer through the contact details shown on their GitHub profile. Never include a live API key, token, or other credential in a report.

## Response and disclosure

- **Acknowledgement:** within 48 hours of receipt.
- **Initial triage:** within 5 business days.
- **Coordinated disclosure:** we will work with the reporter on a reasonable remediation and disclosure date. Please allow maintainers time to validate and release a fix before public disclosure.

These are response targets. Complex reports may take longer to resolve; we will keep the reporter informed as the investigation proceeds.

## Credential and API-key handling

The Odds API key is a secret. Prefer the `ODDS_API_KEY` environment variable and avoid placing it in source code, screenshots, terminal recordings, issue reports, or shell history. Treat process environments and diagnostic logs as sensitive, and remove keys before sharing logs.

When using the application's saved configuration, restrict access to the per-user configuration directory: `%APPDATA%` on Windows and `~/.config` on Linux. Ensure the configuration file is readable only by your user (for example, directory mode `0700` and file mode `0600` on Linux), and do not sync it to a public or shared location. On Windows, use an account-protected profile and review inherited permissions if the device is shared.

If a key is exposed, revoke it with the API provider, create a replacement, update the local configuration or environment, and review relevant logs and repository history for further exposure.

## Scope

This policy covers security issues in this repository and its released application. API-provider account issues should also be reported to the provider. The application displays third-party odds and does not process bets or payments.
