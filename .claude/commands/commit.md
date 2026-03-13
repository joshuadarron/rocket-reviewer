# Git Commit Commands

## Before Committing

Always run tests and linting before committing:
```bash
pnpm test && pnpm lint
```

## Commit Workflow

### 1. Check Status
```bash
git status
git diff
```

### 2. Stage Files
```bash
# Stage specific files (preferred)
git add packages/express-app/src/api/components/chat/controller.ts
git add packages/client/src/pages/FilesChatbot/index.tsx

# Stage all changes in a package
git add packages/express-app/

# Stage all (use sparingly)
git add -A
```

### 3. Create Commit
```bash
git commit -m "Add feature description"
```

## Commit Message Format

### Structure
```
<type>: <short description>

[optional body with more details]
```

### Types
| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks, dependencies |
| `style` | Formatting, whitespace (no code change) |

### Examples
```bash
# Feature
git commit -m "feat: Add message editing to chat interface"

# Bug fix
git commit -m "fix: Resolve rate limiter bypass with fingerprint fallback"

# Refactor
git commit -m "refactor: Extract webhook utilities to chat-core package"

# Multiple lines
git commit -m "feat: Add conversation persistence

- Save messages to LocalStorage per dataset
- Load previous conversation on page mount
- Add clear conversation button"
```

## Common Scenarios

### Amend Last Commit (unpushed only)
```bash
git add <files>
git commit --amend -m "Updated commit message"
```

### Undo Last Commit (keep changes)
```bash
git reset --soft HEAD~1
```

### View Commit History
```bash
git log --oneline -10
git log --oneline --all --graph
```

### Stash Changes
```bash
git stash                    # Stash changes
git stash pop                # Restore stashed changes
git stash list               # View stash list
```

## Branch Workflow

### Create Feature Branch
```bash
git checkout -b feature/add-export-conversation
git checkout -b fix/rate-limiter-bug
```

### Push Branch
```bash
git push -u origin feature/add-export-conversation
```

### Merge to Main
```bash
git checkout main
git pull origin main
git merge feature/add-export-conversation
git push origin main
```

## Files to Never Commit

- `.env` files (contain secrets)
- `node_modules/`
- `dist/` build outputs
- `.DS_Store`, `Thumbs.db`
- IDE config (`.idea/`, `.vscode/` unless shared)

These are already in `.gitignore` but always verify with `git status`.
