# Development Commands

## Root Level
| Command | Description |
|---------|-------------|
| `pnpm install` | Install all workspace dependencies |
| `pnpm dev` | Run backend + frontend concurrently |
| `pnpm dev:app` | Run backend only |
| `pnpm dev:client` | Run frontend only |
| `pnpm build` | Build all packages (chat-core → express-app → client) |
| `pnpm build:chat-core` | Build shared library only |
| `pnpm start` | Build and run production servers |
| `pnpm test` | Run all package tests |
| `pnpm test:chat-core` | Test shared library |
| `pnpm test:app` | Test backend |
| `pnpm test:client` | Test frontend |
| `pnpm test:watch` | Run tests in watch mode |
| `pnpm lint` | Lint all TypeScript/TSX files |
| `pnpm lint:fix` | Auto-fix lint issues |

## Backend (`packages/express-app/`)
| Command | Description |
|---------|-------------|
| `pnpm dev` | Start dev server with auto-restart |
| `pnpm build` | Compile TypeScript to dist/ |
| `pnpm start` | Run compiled production server |
| `pnpm test` | Run Mocha tests |
| `pnpm test:watch` | Run tests in watch mode |
| `pnpm type-check` | TypeScript validation without emit |

## Frontend (`packages/client/`)
| Command | Description |
|---------|-------------|
| `pnpm dev` | Start Vite dev server (port 3000) |
| `pnpm build` | Build for production |
| `pnpm preview` | Preview production build |
| `pnpm test` | Run Vitest tests |

## Shared Library (`packages/chat-core/`)
| Command | Description |
|---------|-------------|
| `pnpm build` | Compile TypeScript with declarations |
| `pnpm test` | Run Mocha tests |
| `pnpm test:watch` | Run tests in watch mode |
