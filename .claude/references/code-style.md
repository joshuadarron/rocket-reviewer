# Code Style Guide

This document defines the coding standards for the Aparavi File Investigator project.

---

## Core Philosophy

- Code should read like English
- Prioritize clarity over cleverness
- Small, focused functions
- Avoid repetition (DRY)
- Fail fast — validate early
- Logic should be explicit, descriptive, and intention-revealing

---

## Formatting

| Rule | Standard |
|------|----------|
| Semicolons | Required |
| Indentation | Tabs |
| Trailing commas | None |
| Quotes | Single quotes preferred |
| Line length | Reasonable (no strict limit) |

### Imports
- Alphabetize imports
- Group by: external packages, then internal modules
- Default export for primary file function, named exports otherwise

---

## Naming Conventions

### Variables
```ts
// Values: descriptive nouns
const userId = '123';
const authToken = 'abc';
const webhookResponse = await fetch(...);

// Booleans: prefix with is/isNot
const isAuthenticated = true;
const isNotEmpty = arr.length > 0;

// Avoid abbreviations
const config = {};      // Good
const cfg = {};         // Bad
```

### Functions
```ts
// Use verbs describing the action
function fetchUser() {}
function extractPayload() {}
function validateRequest() {}
function buildWebhookConfig() {}

// Describe exactly what they do
function getUserById() {}           // Good
function getUser() {}               // Too vague
```

### Files
```ts
// camelCase for all files
userService.ts
errorHandler.ts
chatController.ts
webhookUtils.ts
```

---

## Error Handling

### Never Use try/catch

Always use the `Callout` wrapper:

```ts
// Good
const [err, data] = await Callout.call(somePromise);
if (err) {
	logger.error(err.message);
	throw new AppError('Operation failed', 500);
}

// Bad
try {
	const data = await somePromise;
} catch (err) {
	// ...
}
```

### Always Use AppError

```ts
// Good
throw new AppError('User not found', 404);
throw new AppError('Validation failed', 400, { field: 'email' });

// Bad
throw new Error('Something went wrong');
```

---

## Logging

### Never Use console.log

```ts
// Good
logger.info('Processing request', { userId });
logger.error('Failed to fetch user', { error: err.message });
logger.debug('Webhook response', { status, body });

// Bad
console.log('Processing request');
console.error(err);
```

### What to Log
- Function entry/exit for important operations
- Important decision branches
- External API calls (request and response)
- All errors with context

---

## Async Patterns

### Prefer async/await
```ts
// Good
async function fetchData() {
	const [err, response] = await Callout.call(api.get('/data'));
	if (err) return handleError(err);
	return response.data;
}

// Bad
function fetchData() {
	return api.get('/data')
		.then(response => response.data)
		.catch(handleError);
}
```

### Use Promise.all When Appropriate
```ts
// Good - parallel independent operations
const [users, posts] = await Promise.all([
	fetchUsers(),
	fetchPosts()
]);
```

### Avoid Unnecessary async
```ts
// Bad - unnecessary async
async function getValue() {
	return 42;
}

// Good - just return the value
function getValue() {
	return 42;
}
```

---

## TypeScript

### Always Define Object Types
```ts
// Good
type UserPayload = {
	id: string;
	email: string;
	name: string;
};

function createUser(payload: UserPayload): User {}

// Bad
function createUser(payload: any): any {}
```

### Prefer type Over interface
```ts
// Good - use type by default
type Config = {
	port: number;
	env: string;
};

// Use interface only when extending
interface BaseService {
	init(): void;
}

interface UserService extends BaseService {
	getUser(id: string): User;
}
```

### Avoid any
```ts
// Good
function parseResponse(data: WebhookResponse): ChatResult {}

// Bad
function parseResponse(data: any): any {}
```

### Use Generics Sparingly
Only when truly necessary for reusability:
```ts
// Good use of generics
async function callout<T>(promise: Promise<T>): Promise<[Error | null, T?]> {}

// Unnecessary generic
function getId<T extends { id: string }>(obj: T): string {
	return obj.id;  // Just use a simple type instead
}
```

---

## Helper Functions

### Placement Rules

**Cross-file usage → `/utils`**
```ts
// utils/validation.ts
export function isValidEmail(email: string): boolean {}
```

**Single-file usage → top of file**
```ts
// userController.ts

// Helper at top of file
function formatUserResponse(user: User): UserResponse {
	return { id: user.id, name: user.name };
}

// Main exports below
export function getUser(req: Request, res: Response) {}
```

---

## Documentation

### JSDoc Required for Exported Functions

```ts
/**
 * Processes a chat message through the webhook pipeline
 *
 * @param {ChatRequestBody} request - The chat request containing message or data
 * @param {WebhookConfig} config - Webhook configuration with auth credentials
 * @return {Promise<ChatServiceResult>} The processed chat response
 *
 * @example
 *     const result = await ChatService.processChat(
 *         { message: 'Hello' },
 *         { baseUrl: '...', token: '...' }
 *     );
 */
export async function processChat(
	request: ChatRequestBody,
	config: WebhookConfig
): Promise<ChatServiceResult> {}
```

### Comments Only for Complex Logic

Clear naming should minimize comment needs:
```ts
// Good - self-documenting
const isUserAuthenticated = token && !isTokenExpired(token);

// Bad - unnecessary comment
// Check if user is authenticated
const auth = t && !exp(t);
```

---

## Testing

### Structure: describe → context → it

```ts
describe('ChatService', () => {
	context('when message is provided', () => {
		it('should process the message successfully', async () => {
			// test
		});

		it('should handle webhook errors', async () => {
			// test
		});
	});

	context('when message is missing', () => {
		it('should return validation error', async () => {
			// test
		});
	});
});
```

### Stub External Calls

```ts
import sinon from 'sinon';
import axios from 'axios';

describe('ChatService', () => {
	let axiosStub: sinon.SinonStub;

	beforeEach(() => {
		axiosStub = sinon.stub(axios, 'post');
	});

	afterEach(() => {
		sinon.restore();
	});

	it('should call webhook with correct payload', async () => {
		axiosStub.resolves({ data: { answers: ['response'] } });
		// test
	});
});
```

### Test Both Paths

Always test success and error scenarios:
```ts
describe('fetchUser', () => {
	it('should return user on success', async () => {});
	it('should throw AppError on not found', async () => {});
	it('should throw AppError on network error', async () => {});
});
```
