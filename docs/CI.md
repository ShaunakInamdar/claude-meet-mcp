# CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on pushes and PRs to `main`/`master`.

## Jobs

| Job | Runs On | Purpose |
|-----|---------|---------|
| **test** | Ubuntu, Windows, macOS × Python 3.9-3.12 | Runs `pytest tests/` across all platform/version combos |
| **lint** | Ubuntu (Python 3.11) | Runs `ruff check` and `ruff format --check` on `claude_meet/` and `tests/` |
| **install-check** | Ubuntu, Windows, macOS | Verifies package installs and CLI commands work (`--version`, `--help`, subcommands) |
| **security** | Ubuntu (Python 3.11) | Runs `safety check` to scan dependencies for known vulnerabilities |

## Key Details

- **Caching**: Pip packages cached using `requirements.txt` hash
- **Fail-fast**: Disabled for test matrix (all combinations run even if one fails)
- **Soft failures**: Format check and security scan use `continue-on-error: true`

## Maintenance

- Update Python versions in `matrix.python-version` as needed
- Add new CLI subcommands to install-check's "Verify commands exist" step
- If adding new source directories, update ruff paths in lint job
