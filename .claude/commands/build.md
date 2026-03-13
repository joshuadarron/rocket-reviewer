# Build Commands

## Before Building

Ensure dependencies are installed:
```bash
pnpm install
```

## Build Workflow

### 1. Check Current State
```bash
git status
pnpm lint
```

### 2. Build All Packages
```bash
pnpm build
```

This builds packages in dependency order:
1. `chat-core` — Shared library (must build first)
2. `express-app` — Backend server
3. `client` — Frontend application

### 3. Verify Build
```bash
pnpm test
```

## Package-Specific Builds

### Shared Library Only
```bash
pnpm build:chat-core
```
Use when making changes only to `packages/chat-core/`.

### Backend Only
```bash
cd packages/express-app
pnpm build
```
Outputs to `packages/express-app/dist/`.

### Frontend Only
```bash
cd packages/client
pnpm build
```
Outputs to `packages/client/dist/`.

## Build Output Locations

| Package | Output Directory | Contents |
|---------|------------------|----------|
| `chat-core` | `packages/chat-core/dist/` | Compiled JS + type declarations |
| `express-app` | `packages/express-app/dist/` | Compiled Node.js server |
| `client` | `packages/client/dist/` | Static SPA files |

## Common Build Issues

### TypeScript Errors
```bash
cd packages/express-app
pnpm type-check
```
Fix type errors before building.

### Dependency Issues
```bash
# Clean and reinstall
rm -rf node_modules packages/*/node_modules
pnpm install
```

### Stale Build Cache
```bash
# Remove build outputs
rm -rf packages/*/dist
pnpm build
```

## Production Build

For production deployment:
```bash
NODE_ENV=production pnpm build
```

### Run Production Server
```bash
pnpm start
```
This builds all packages and starts the production servers.

## CI/CD Build Sequence

Recommended order for CI pipelines:
```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm build
pnpm test
```
