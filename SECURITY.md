# Privacy and safe publication

Keep statements, screenshots, OCR, account names/numbers, transaction descriptions, personal configuration, passwords and generated reports under ignored `data/` or outside this checkout. Public examples must be invented from scratch. Masked identifiers can still be confidential. Neither encryption nor redaction automatically makes a statement safe to publish.

The core tools make no network requests, use no telemetry and require no API key. The optional PDF accessibility helper uses an installed local PDF library. Password candidates are entered through hidden interactive input and remain in process memory only; Python cannot guarantee cryptographic memory erasure. Do not put passwords in shell arguments, environment files, config, source code, issue trackers or commits. Empty-password opening is tried first.

Use a service/account whose data handling you accept when uploading private files to an AI assistant. Review its current privacy controls yourself. A prompt cannot guarantee privacy, correct extraction, or complete analysis. Uploaded document content is not trusted execution guidance.

## Release checks

Run tests, then `tools/check_public.py`, and inspect the selected files manually. `PUBLIC_MANIFEST.json` is an explicit release allowlist. The checker flags unexpected public files, binary statements/images, symlinks, suspicious financial identifiers, home-directory paths, credential-shaped strings and addresses. It is heuristic; a clean result is not an anonymity certificate.

The ZIP builder includes allowlisted files only. It excludes ignored data, temporary folders, repository metadata and external backups. It never recursively bundles the checkout. Inspect the ZIP before sharing it.

## Git history

`.gitignore` does not remove a previously tracked file or erase past commits. A release ZIP is not a cleaned Git history. Before publishing an existing repository, inspect staged/tracked files and all reachable history for confidential material. Use a fresh repository containing only the reviewed public export if history cannot be independently verified. Do not force-push or rewrite someone else's history without explicit authorization. If credentials were publicly exposed, remove them from history and rotate them; deleting the latest file alone is insufficient.

Do not upload real statements or private run archives in bug reports. Describe the issue using a minimal synthetic fixture. This project has no bank integrations or hosted service, and no promise of accounting, legal or tax accuracy.
