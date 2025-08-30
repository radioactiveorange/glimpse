# Contributing to Glimpse

## Commit Message Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automatic semantic versioning and changelog generation.

### Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- **feat**: A new feature (triggers minor version bump)
- **fix**: A bug fix (triggers patch version bump)
- **perf**: A performance improvement (triggers patch version bump)
- **refactor**: Code refactoring (triggers patch version bump)
- **docs**: Documentation changes (no version bump)
- **style**: Code style changes (no version bump)
- **test**: Adding or updating tests (no version bump)
- **chore**: Maintenance tasks (no version bump)
- **ci**: CI/CD changes (no version bump)
- **build**: Build system changes (no version bump)

### Breaking Changes
Add `BREAKING CHANGE:` in the footer or `!` after the type to trigger a major version bump.

### Examples
```
feat: add spacebar binding for play/pause timer
fix: resolve icon loading issue on Linux
feat!: redesign startup dialog (breaking change)
docs: update installation instructions
chore: update dependencies
```

## Release Process

Releases are automated using GitHub Actions:

1. **Push to main**: Commits are analyzed for semantic versioning
2. **Version bump**: Automatic version increment based on commit types
3. **Changelog**: Auto-generated from commit messages
4. **Cross-platform builds**: Windows, Linux, and macOS binaries created
5. **GitHub release**: Automatic release with downloadable assets

## Development Workflow

1. Create feature branch: `git checkout -b feat/my-feature`
2. Make changes with conventional commits
3. Push branch: `git push origin feat/my-feature`
4. Create Pull Request
5. CI tests run automatically
6. After merge to main, release is automatically created if needed

## Building Locally

```bash
# Install dependencies
uv pip install pyside6 pyinstaller

# Build executable
pyinstaller glimpse.spec

# Output in dist/ folder
```