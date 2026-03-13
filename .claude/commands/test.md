# Test Commands

## Run All Tests

```bash
pnpm test
```

Runs tests for all packages in sequence: chat-core → express-app → client

---

## Package-Specific Tests

### Shared Library (chat-core)
```bash
pnpm test:chat-core

# Or from package directory
cd packages/chat-core && pnpm test
```

**Framework:** Mocha + Chai + Sinon

**Test files:**
- `src/utils/callout.test.ts`
- `src/utils/webhook.test.ts`
- `src/utils/pipelineOutput.test.ts`
- `src/service/chatService.test.ts`

### Backend (express-app)
```bash
pnpm test:app

# Or from package directory
cd packages/express-app && pnpm test
```

**Framework:** Mocha + Chai + Sinon

**Test files:**
- `src/api/components/chat/controller.test.ts`

### Frontend (client)
```bash
pnpm test:client

# Or from package directory
cd packages/client && pnpm test
```

**Framework:** Vitest + React Testing Library

---

## Watch Mode

Run tests continuously during development:

```bash
# All packages (concurrent)
pnpm test:watch

# Single package
cd packages/chat-core && pnpm test:watch
cd packages/express-app && pnpm test:watch
```

---

## Test Structure

Follow the `describe → context → it` pattern:

```ts
describe('ChatService', () => {
	context('when processing a valid message', () => {
		it('should return success response', async () => {
			// Arrange
			const request = { message: 'test query' };

			// Act
			const result = await ChatService.processChat(request, config);

			// Assert
			expect(result.success).to.be.true;
		});
	});

	context('when message is missing', () => {
		it('should return validation error', async () => {
			// test
		});
	});
});
```

---

## Mocking and Stubbing

### Sinon (Backend)
```ts
import sinon from 'sinon';
import axios from 'axios';

describe('Webhook', () => {
	let axiosStub: sinon.SinonStub;

	beforeEach(() => {
		axiosStub = sinon.stub(axios, 'post');
	});

	afterEach(() => {
		sinon.restore();
	});

	it('should call webhook with payload', async () => {
		axiosStub.resolves({ data: { answers: ['response'] } });
		// test
	});

	it('should handle timeout', async () => {
		axiosStub.rejects({ code: 'ECONNABORTED' });
		// test
	});
});
```

### Vitest (Frontend)
```ts
import { vi } from 'vitest';
import * as api from '../services/api';

describe('FilesChatbot', () => {
	beforeEach(() => {
		vi.spyOn(api, 'sendChatMessage').mockResolvedValue({
			success: true,
			message: 'response'
		});
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});
});
```

---

## Testing Checklist

Before completing any code change:

- [ ] All existing tests pass (`pnpm test`)
- [ ] New functionality has tests
- [ ] Success paths tested
- [ ] Error paths tested
- [ ] Edge cases considered
- [ ] Mocks/stubs properly restored

---

## Type Checking

Run TypeScript validation without running tests:

```bash
cd packages/express-app && pnpm type-check
```

---

## Debugging Tests

### Run Single Test File
```bash
# Backend
cd packages/express-app
npx mocha --require tsx src/api/components/chat/controller.test.ts

# Chat-core
cd packages/chat-core
npx mocha --require tsx src/service/chatService.test.ts
```

### Run Tests Matching Pattern
```bash
# Backend - tests matching "validation"
cd packages/express-app
npx mocha --require tsx --grep "validation" src/**/*.test.ts
```

### Verbose Output
```bash
cd packages/express-app
pnpm test -- --reporter spec
```

---

## Coverage (if configured)

```bash
# Generate coverage report
pnpm test -- --coverage

# View HTML report
open coverage/index.html
```

---

## Common Test Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot find module` | Missing dependency or path alias | Run `pnpm install`, check tsconfig paths |
| `Timeout exceeded` | Async test not completing | Increase timeout or fix hanging promise |
| `stub not restored` | Sinon stub leaking | Add `sinon.restore()` in afterEach |
| `ECONNREFUSED` | Test hitting real API | Stub external calls |
