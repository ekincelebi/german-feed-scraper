# Security Guide

This document defines practical security standards for the German Feed Scraper project.

## Threat Model (What We Protect)

- API credentials: `SUPABASE_KEY` (service role), `GROQ_API_KEY`
- Database contents and metadata in Supabase
- Any potentially sensitive text found in scraped content
- Infrastructure reputation (avoid abuse, over-scraping, accidental exposure)

## Authentication and Authorization

### Supabase Keys

- Use `SUPABASE_KEY` (service role) only in trusted backend scripts/processes.
- Never expose service role keys in browser or client-side apps.
- If you add a frontend, use Supabase `anon` key there with strict RLS.
- Use separate Supabase projects/keys for `dev`, `staging`, and `prod`.

### Principle of Least Privilege

- Keep write operations restricted to backend jobs using service role.
- Grant read access to `anon` only for truly public datasets.
- Prefer read-only views for frontend access over direct table access.
- Regularly audit policies and grants for drift.

## Sensitive Data Handling

### Secrets

- Store secrets in environment variables, not in code.
- Keep `.env` local only (`.gitignore` already includes it).
- Use a secret manager in hosted environments (GitHub Actions secrets, cloud secret manager).
- Rotate API keys regularly and immediately on suspected exposure.

### Logging and Error Handling

- Never log raw credentials or authorization headers.
- Avoid logging full request/response payloads from external APIs when not required.
- Sanitize error logs if third-party SDK errors might include sensitive context.
- Use `INFO` level in production; reserve `DEBUG` for temporary troubleshooting.

### Data Minimization and Retention

- Store only fields required by product needs.
- Do not persist unnecessary raw payloads indefinitely.
- Define retention windows for intermediate processing data.
- Ensure exports/backups are encrypted and access-controlled.

## Network and Runtime Hardening

- Use HTTPS for all outbound API and feed calls.
- Keep dependency versions patched and current.
- Run scheduled jobs with least-privileged runtime identities.
- Set resource limits/timeouts to reduce blast radius from hangs or abuse.

## Supabase RLS Checklist

Use this checklist before exposing data to a frontend:

- [ ] RLS enabled on all user-facing tables
- [ ] `anon` has only required `SELECT` access
- [ ] No unintended `INSERT`/`UPDATE`/`DELETE` access for `anon`
- [ ] Views expose only safe columns
- [ ] Policies tested with both `anon` and `authenticated` roles

## Local Security Checks

Run these before shipping changes:

```bash
# 1) Python dependency vulnerability scan
python -m pip install pip-audit
pip-audit

# 2) Secret scanning (requires gitleaks installed)
gitleaks detect --source . --verbose
```

## Pre-commit Protection (Recommended)

This repository includes a `.pre-commit-config.yaml` with a `gitleaks` hook.

Enable it once per clone:

```bash
python -m pip install pre-commit
pre-commit install
```

Run manually across all files:

```bash
pre-commit run --all-files
```

## CI Security Checks (GitHub Actions Example)

Create `.github/workflows/security.yml` with:

```yaml
name: security

on:
  pull_request:
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"

      - name: Install deps
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pip-audit

      - name: Dependency audit
      run: pip-audit

      - name: Secret scan
      uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Incident Response (Credential Leak or Suspected Compromise)

1. Revoke/rotate leaked keys immediately (`SUPABASE_KEY`, `GROQ_API_KEY`).
2. Redeploy all environments with new secrets.
3. Review logs for unusual API/database access.
4. Audit recent commits and pull requests for leaked material.
5. Remove leaked secrets from history if needed (coordinate carefully).
6. Document incident, timeline, impact, and preventive controls.

## Secure Development Defaults

- Never commit `.env` files or credentials.
- Never paste service role keys into issues, PRs, or chat.
- Prefer fail-closed behavior when configuration is missing.
- Validate and sanitize external content before downstream processing.

