# Project Architecture Guide

This document defines architectural principles and decision heuristics for project structure, applicable across languages and ecosystems.

---

## Core Philosophy

- Follow the ecosystem's standard layout for the language in use
- Start minimal and add structure as complexity grows
- Never scaffold empty folders or boilerplate "just in case"
- Every file and folder should exist because current code requires it
- Structure should be discoverable: a new contributor should be able to guess where things live

---

## Language-Specific Conventions

Do not invent custom folder structures when the ecosystem already has an established one.

| Language | Follow Standard |
|----------|----------------|
| Go | `cmd/`, `internal/`, `pkg/` conventions |
| TypeScript/Node | `src/` with layered organization |
| Python | Package-based layout with `__init__.py`, `src/` layout for libraries |

When in doubt, look at well-maintained open-source projects in the same ecosystem and mirror their conventions.

---

## Separation of Concerns

### Business Logic

- Business logic lives in dedicated service files/modules
- Services must be framework-agnostic: a service should not know whether it is being called from an HTTP handler, a CLI command, a Lambda, or a test
- Services receive data, operate on it, and return results. They do not read headers, set status codes, or interact with request/response objects

### Transport / HTTP Layer

- Route definitions and handler/controller logic live in separate locations
- Routes define endpoints and map them to handlers
- Handlers are thin: parse the request, call the appropriate service, format the response
- All framework-specific concerns (middleware, request parsing, response formatting) stay in the transport layer

### Data Access

- Use an abstracted data layer (repository pattern or equivalent)
- Services call the data access layer, never the ORM or database client directly
- This keeps business logic testable and decoupled from the specific database or storage mechanism
- The data access layer is the only code that knows how data is persisted

### Example Layering (conceptual, not a prescribed folder tree)

```
Routes/Endpoints
  → Handlers/Controllers (thin, transport-aware)
    → Services (business logic, framework-agnostic)
      → Repositories/Data Access (database-aware)
```

---

## Monorepo Tooling

### When to Use a Monorepo

- Multiple packages or apps that share code
- Projects with both a frontend and backend
- SDKs, plugins, or extensions alongside a core project

### Tool Selection

| Scenario | Tool |
|----------|------|
| TypeScript-heavy multi-package project | pnpm workspaces |
| Cross-language or complex build orchestration | Nx |
| Go multi-module | Go workspaces (`go.work`) |

Follow the monorepo tool's recommended folder structure. Do not fight the tool's conventions.

---

## Configuration and Environment Variables

### Config Module Structure

- Centralize all environment variable access through dedicated config files
- Nothing outside the config layer should read environment variables directly (no `process.env`, `os.environ`, or `os.Getenv` scattered through business logic)
- Split config files by concern:

```
config/
  db.config.ts
  auth.config.ts
  api.config.ts
  server.config.ts
```

- Each config file reads the relevant env vars, applies defaults, and exports a typed configuration object
- Import config where needed rather than reading env vars inline

### Environment Files

- Use multiple `.env` files per environment:

```
.env              # Shared defaults / local development
.env.development  # Development-specific overrides
.env.staging      # Staging-specific values
.env.production   # Production-specific values
.env.test         # Test environment values
```

- Never commit secrets to version control
- Include a `.env.example` with all required variable names (no real values) so new contributors can get started

---

## Test Structure

### Placement

- Tests live in a dedicated top-level `tests/` (or equivalent) directory, separate from source code
- Separate directories for each test type:

```
tests/
  unit/
  integration/
  e2e/
```

### Mirror the Source Tree

- The test directory structure mirrors the source tree so any file's tests are immediately locatable:

```
src/
  services/
    user.service.ts
  controllers/
    user.controller.ts

tests/
  unit/
    services/
      user.service.test.ts
    controllers/
      user.controller.test.ts
  integration/
    ...
  e2e/
    ...
```

- Given a source file, its tests should be findable by navigating to the same relative path under the appropriate test type directory
- Given a test file, the source it covers should be immediately obvious from its path

### Coverage Expectations

- Always test both success and error paths
- External dependencies (APIs, databases) should be stubbed in unit tests
- Integration tests may use real dependencies where appropriate

---

## Scaffolding Rules

When starting a new project or adding new functionality:

1. **Do not create structure preemptively.** If there is only one route, one service, and one repository, they do not need separate directories yet.
2. **Extract to a new file or folder when there is a concrete reason:** a second service, a shared utility, a new test type.
3. **Name things for what they contain now**, not what they might contain later.
4. **A flat structure is fine when the project is small.** Nesting should emerge from actual complexity, not anticipated complexity.
