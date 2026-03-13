# PLANNING.md: rocketride-reviewer

**Author:** Joshua Phillips
**Date:** March 13, 2026
**Approach:** Solo implementation, ship MVP fast, iterate
**Reference:** See `docs/PRD.md` for full requirements and `CLAUDE.md` for coding conventions

---

## Principles

1. **MVP first.** Phase 1 is a working end-to-end review on a real PR. Everything else is iteration.
2. **Vertical slices.** Each task produces something testable. No long stretches of invisible plumbing.
3. **Test as you go.** Every module gets tests when it's built, not after everything is wired together.
4. **One agent first, then three.** Get the full pipeline working with a single agent before parallelizing. This eliminates multi-agent debugging while the core flow is still unstable.

---

## Phase Overview

| Phase | Goal | Ship Condition |
|-------|------|----------------|
| **0: Scaffolding** | Repo structure, tooling, CI | `pytest` and `ruff` pass on empty project |
| **1: Single-Agent MVP** | One agent reviews a PR end-to-end via one GitHub App | A real PR gets a real review comment from `claude-reviewer[bot]` |
| **2: Full Pipeline** | All 3 agents in parallel, aggregator dedup, approval logic | All 3 bots post independent reviews with dedup applied |
| **3: Conversation** | Scoped re-review on developer reply | Reply to a bot comment, get a scoped response from that bot only |
| **4: Hardening** | Chunking, filtering, error resilience, edge cases | Large PRs, filtered files, agent failures all handled gracefully |
| **5: Distribution** | GitHub Marketplace packaging, setup tooling, docs | Installable via `uses:` with a setup guide that works |

**MVP = Phase 2 complete.** That's a working multi-agent reviewer with dedup and approval logic. Phases 3-5 are iteration.

---

## Phase 0: Scaffolding

**Goal:** Repo is initialized, tooling works, CI runs green.

### Tasks

**0.1 Initialize repository**
- Create `rocketride-reviewer` repo
- Initialize with MIT license, README stub, `.gitignore` (Python)
- Create directory structure per CLAUDE.md
- Add `CLAUDE.md`, `docs/PRD.md`, `docs/PLANNING.md`

**0.2 Python project setup**
- Create `pyproject.toml` with project metadata
- Configure Ruff (rules: default + I, UP, B, SIM, PTH)
- Configure Black (88 char line length)
- Configure mypy (strict mode)
- Create `requirements.txt` and `requirements-dev.txt` with initial dependencies:
  - Production: `PyGithub`, `httpx`, `pydantic`, `rocketride`
  - Dev: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `black`, `mypy`

**0.3 CI pipeline**
- Create `.github/workflows/ci.yml`
- Jobs: lint (ruff + black check), type check (mypy), test (pytest)
- Trigger on push and PR to main

**0.4 Base modules**
- Create all `src/*.py` files with docstrings and placeholder classes/functions
- Create all `tests/test_*.py` files with a single passing placeholder test each
- Create `src/errors.py` with the full exception hierarchy
- Create `src/models.py` with Pydantic models: `ReviewComment`, `AgentReview`, `ReviewConfig`
- Verify: `pytest` passes, `ruff` passes, `mypy` passes

**Done when:** CI runs green on an empty but fully structured project.

---

## Phase 1: Single-Agent MVP

**Goal:** A PR targeting main triggers the action, RocketRide engine starts, Claude reviews the diff, and `claude-reviewer[bot]` posts inline comments on the PR.

### Tasks

**1.1 GitHub App creation**
- Create the `claude-reviewer` GitHub App manually (permissions per PRD Section 8)
- Install on a test repository
- Store App ID and private key as repo secrets

**1.2 GitHub client module (`src/github_client.py`)**
- Implement: authenticate as GitHub App (installation token flow)
- Implement: fetch PR diff (unified diff format)
- Implement: fetch PR metadata (target branch, author, changed files)
- Implement: fetch full file content for changed files
- Implement: post inline review comment on PR
- Implement: submit review (approve / request changes / comment)
- Tests: mock all GitHub API calls, test each method independently
- Test: verify authentication token is generated correctly from App ID + private key

**1.3 Configuration module (`src/config.py`)**
- Implement: load config from environment variables (action inputs)
- Implement: load optional `.rocketride-review.yml` from repo root
- Implement: merge with defaults (review_context, target_branch, approval_threshold)
- Implement: constants (MODELS, AGENT_ROUTING, BOT_USERNAMES)
- Tests: default config, custom config, missing config, invalid values

**1.4 File filtering module (`src/filters.py`)**
- Implement: match files against ignore patterns (fnmatch/glob style)
- Implement: default ignore list from PRD Section 5.6
- Implement: merge user-provided `ignore_patterns_extra` and `ignore_patterns_override`
- Tests: default patterns, custom extensions, overrides, edge cases (no patterns, all filtered)

**1.5 RocketRide engine lifecycle (`src/engine.py`)**
- Implement: start Docker container (`docker run -d -p 5565:5565`)
- Implement: health check polling (2s interval, 30s timeout)
- Implement: connect via RocketRide Python SDK
- Implement: shutdown (docker stop + docker rm)
- Implement: full lifecycle as async context manager
- Tests: mock Docker commands, test health check timeout, test cleanup on failure

**1.6 RocketRide pipeline: single-agent review**
- Create `pipelines/full_review.json` with a single Claude reviewer node
- Configure node to accept: diff text, file context, comment schema
- Configure node to output: JSON conforming to `AgentReview` model
- Test manually: send a sample diff to the engine, verify structured output

**1.7 Pipeline execution module (`src/pipeline.py`)**
- Implement: load pipeline JSON, start pipeline via SDK `.use()`
- Implement: send diff data via SDK `.send()`
- Implement: receive and parse agent response into `AgentReview` model
- Implement: handle agent timeout/error gracefully
- Tests: mock SDK calls, test valid response parsing, test malformed response handling

**1.8 Review posting module (`src/reviewer.py`)**
- Implement: take `AgentReview`, post each comment as inline PR review comment
- Implement: submit review with appropriate status based on severity
- Implement: format comment body (include severity badge)
- Tests: verify correct GitHub API calls per comment, verify review status logic

**1.9 Gating logic (`src/main.py`)**
- Implement: read GitHub event payload
- Implement: check target branch == main (or configured branch)
- Implement: check event type (PR opened, synchronize, issue_comment)
- Implement: check comment author is not a bot (loop prevention)
- Implement: orchestrate full flow: gate -> engine start -> pipeline run -> post review -> engine stop
- Wrap everything in top-level try/except, always exit 0
- Tests: test every gating branch, test orchestration with mocked dependencies

**1.10 Composite action definition**
- Create `action.yml` with inputs for API keys and GitHub App credentials (Claude only for now)
- Create `Dockerfile` (or reference RocketRide's) for engine provisioning
- Wire `action.yml` to invoke `src/main.py`
- Test end-to-end: open a PR on the test repo, verify `claude-reviewer[bot]` posts a review

**Done when:** A real PR on a test repo gets reviewed by `claude-reviewer[bot]` with inline comments and an appropriate review status.

---

## Phase 2: Full Pipeline

**Goal:** All 3 agents review in parallel, aggregator deduplicates, all 3 bots post independently, approval logic works.

### Tasks

**2.1 Create remaining GitHub Apps**
- Create `gpt-reviewer` and `gemini-reviewer` GitHub Apps
- Install both on test repository
- Store App IDs and private keys as repo secrets
- Update `action.yml` inputs to include all 9 secrets

**2.2 Expand pipeline to 3 parallel agents**
- Update `pipelines/full_review.json` to include GPT and Gemini reviewer nodes
- Configure parallel execution (all 3 receive identical input simultaneously)
- Each node uses its respective model per PRD Section 4.3
- Test: send sample diff, verify 3 independent structured responses

**2.3 Aggregator module (`src/aggregator.py`)**
- Implement: receive combined output from all 3 agents
- Implement: deduplication logic (same file + 3-line window + same semantic intent)
- Implement: build the aggregator prompt for Claude to perform dedup
- Implement: parse aggregator output into 3 separate `AgentReview` payloads
- Implement: add aggregator node to `full_review.json` pipeline
- Tests: exact duplicates removed, near-duplicates (same line range) handled, non-duplicates preserved, all-unique comments pass through unchanged

**2.4 Multi-app review posting**
- Update `src/reviewer.py` to authenticate as each GitHub App independently
- Post each agent's review under its own bot identity
- Verify all 3 bots appear as separate reviewers on the PR

**2.5 Approval logic**
- Implement: after all reviews posted, evaluate severity across all agents
- Implement: if zero critical/high from all agents, each bot submits approval
- Implement: if any critical/high, flagging agent(s) submit "request changes", others submit "comment"
- Tests: all-clean scenario, single agent flags, multiple agents flag, mixed severities

**2.6 Agent failure isolation**
- Implement: individual try/except per agent in pipeline execution
- Implement: on agent failure, post a PR comment noting which agent was unavailable
- Implement: remaining agents complete and post normally
- Tests: one agent fails (other two succeed), two agents fail, all three fail

**2.7 End-to-end integration test**
- Open a real PR on test repo
- Verify: all 3 bots post reviews, dedup removes obvious duplicates, approval logic fires correctly
- Verify: agent failure doesn't crash the run

**Done when:** A real PR gets 3 independent reviews from 3 distinct bots, with dedup applied and correct approval status. This is the MVP.

---

## Phase 3: Conversation

**Goal:** Developers can reply to a bot comment and receive a scoped follow-up from that specific agent.

### Tasks

**3.1 Comment event detection**
- Update `src/main.py` gating to handle `issue_comment` events
- Extract parent comment author from the event payload
- Map author to agent via `AGENT_ROUTING`
- If author is not a recognized bot, exit (not a reply to an agent)
- If author is a bot (reply to own comment), exit (loop prevention)

**3.2 Conversation context assembly**
- Implement: given a comment thread, extract the full chain (agent comment + dev reply + any prior exchanges)
- Implement: fetch the file context surrounding the original comment's line range
- Implement: package as input for the conversation reply pipeline

**3.3 Conversation reply pipeline**
- Create `pipelines/conversation_reply.json`
- Single reviewer node, parameterized by the agent node ID
- Input: comment thread + file context
- Output: a single response comment (not a full review)
- Test: send a sample thread, verify coherent response

**3.4 Reply posting**
- Post the agent's response as a reply in the existing comment thread
- Authenticate as the correct GitHub App (the originating agent only)
- No review status change on replies (just a comment)

**3.5 End-to-end conversation test**
- Open a PR, get reviews from all 3 bots
- Reply to one bot's comment
- Verify: only that bot responds, response is contextually relevant, other bots stay silent
- Reply again, verify continued conversation

**Done when:** A developer can have a multi-turn conversation with a specific reviewer bot on a PR.

---

## Phase 4: Hardening

**Goal:** Handle edge cases, large PRs, and failure modes gracefully.

### Tasks

**4.1 Diff chunking (`src/chunker.py`)**
- Implement: split diff at file boundaries
- Implement: split oversized file diffs at function/class boundaries (regex-based detection)
- Implement: fallback to blank-line splitting when no function boundaries detected
- Implement: overlap context (20 lines default)
- Implement: line number remapping after chunk merge
- Tests: small diff (no chunking needed), file-boundary split, function-boundary split, blank-line fallback, overlap verification, line remap accuracy

**4.2 Large PR limits**
- Implement: count changed files and total lines after filtering
- Implement: if exceeding thresholds (50 files / 5,000 lines), post summary comment and exit
- Implement: wire chunking into the pipeline execution flow
- Tests: at-threshold, over-threshold, just-under-threshold

**4.3 Error resilience audit**
- Review every external call (GitHub API, Docker, RocketRide SDK, LLM APIs) for error handling
- Verify: no bare `Exception` catches outside `main.py`
- Verify: all retryable errors use the retry utility with exponential backoff
- Verify: all terminal errors produce a meaningful PR comment
- Verify: the action always exits with code 0

**4.4 Edge case testing**
- PR with only filtered files (nothing to review)
- PR with a single line change
- PR with binary files in the diff
- PR where all agents return zero comments (auto-approve path)
- PR where all agents return only `resolve` status comments
- Config file with invalid YAML
- Missing API keys (detected at startup, not at pipeline execution)

**4.5 Logging**
- Implement structured logging (JSON format for GitHub Actions log parsing)
- Log: pipeline mode, agent execution times, comment counts, chunk counts, approval decision
- Mask all sensitive values in logs

**Done when:** No known edge case crashes the action, and failures produce helpful PR comments.

---

## Phase 5: Distribution

**Goal:** Anyone can install and use the action from the GitHub Marketplace.

### Tasks

**5.1 Action packaging**
- Finalize `action.yml` with complete input definitions and descriptions
- Add `branding` (icon and color) for marketplace listing
- Verify the action runs from an external repo via `uses: rocketride-org/rocketride-reviewer@v1`

**5.2 Setup tooling**
- Create `scripts/setup.py` (or `scripts/setup.sh`): CLI tool that walks through creating 3 GitHub Apps
- Script outputs the 9 secrets the user needs to add to their repo
- Test: run the script, verify apps are created and keys are generated

**5.3 Documentation**
- Write `README.md`: quick start, configuration reference, architecture overview
- Write `docs/SETUP.md`: step-by-step GitHub App creation guide (manual path for users who don't want the script)
- Write `CONTRIBUTING.md`: how to contribute, development setup, testing
- Add `docs/EXAMPLES.md`: example `.rocketride-review.yml` configurations for common setups

**5.4 Example workflow**
- Create `.github/workflows/example-usage.yml` showing the full action configuration
- Include comments explaining each input

**5.5 Release**
- Tag `v1.0.0`
- Publish to GitHub Marketplace
- Test: install on a fresh repo from the marketplace, run a full review cycle

**Done when:** A developer can find the action on the GitHub Marketplace, follow the setup guide, and have multi-agent reviews running on their repo within 30 minutes.

---

## Dependency Graph

```
Phase 0 (Scaffolding)
  └─> Phase 1 (Single-Agent MVP)
        ├─> Phase 2 (Full Pipeline)  ← MVP SHIP POINT
        │     └─> Phase 3 (Conversation)
        │           └─> Phase 4 (Hardening)
        │                 └─> Phase 5 (Distribution)
        │
        └─> [Can parallelize] Phase 4.1-4.2 (Chunking)
              can start after Phase 1 since chunking
              is independent of multi-agent logic
```

Note: chunking (4.1, 4.2) can be built in parallel with Phase 2 or 3 if you want to break up the work. It has no dependency on the multi-agent pipeline.

---

## Task Checklist

Quick reference for tracking progress. Copy this to an issue or scratch file.

```
Phase 0: Scaffolding
  [ ] 0.1 Initialize repository
  [ ] 0.2 Python project setup
  [ ] 0.3 CI pipeline
  [ ] 0.4 Base modules

Phase 1: Single-Agent MVP
  [ ] 1.1 Create claude-reviewer GitHub App
  [ ] 1.2 GitHub client module
  [ ] 1.3 Configuration module
  [ ] 1.4 File filtering module
  [ ] 1.5 RocketRide engine lifecycle
  [ ] 1.6 Single-agent pipeline JSON
  [ ] 1.7 Pipeline execution module
  [ ] 1.8 Review posting module
  [ ] 1.9 Gating logic and orchestration
  [ ] 1.10 Composite action definition + e2e test

Phase 2: Full Pipeline (MVP)
  [ ] 2.1 Create GPT + Gemini GitHub Apps
  [ ] 2.2 Expand pipeline to 3 parallel agents
  [ ] 2.3 Aggregator module + pipeline node
  [ ] 2.4 Multi-app review posting
  [ ] 2.5 Approval logic
  [ ] 2.6 Agent failure isolation
  [ ] 2.7 End-to-end integration test

Phase 3: Conversation
  [ ] 3.1 Comment event detection + routing
  [ ] 3.2 Conversation context assembly
  [ ] 3.3 Conversation reply pipeline
  [ ] 3.4 Reply posting
  [ ] 3.5 End-to-end conversation test

Phase 4: Hardening
  [ ] 4.1 Diff chunking
  [ ] 4.2 Large PR limits
  [ ] 4.3 Error resilience audit
  [ ] 4.4 Edge case testing
  [ ] 4.5 Logging

Phase 5: Distribution
  [ ] 5.1 Action packaging
  [ ] 5.2 Setup tooling
  [ ] 5.3 Documentation
  [ ] 5.4 Example workflow
  [ ] 5.5 Release
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| RocketRide Docker image too large for GitHub runner | Engine startup exceeds 60s budget | Pre-build and cache the image in GitHub Actions cache, or use a slim image |
| LLM rate limits during parallel execution | One or more agents fail on busy repos | Agent failure isolation (Phase 2.6) + retry with backoff |
| GitHub App installation complexity deters adoption | Low uptake despite good tooling | Setup script (Phase 5.2) + thorough manual guide |
| Aggregator dedup is too aggressive or too loose | Good comments dropped or duplicates left | Tune the 3-line window and semantic matching prompt iteratively |
| Chunking line remap introduces off-by-one errors | Comments land on wrong lines | Extensive test coverage for remapping (Phase 4.1) |
| Context window limits hit on large files even after chunking | Truncated or degraded reviews | Monitor token usage, add per-chunk token budget with fallback to diff-only mode |
