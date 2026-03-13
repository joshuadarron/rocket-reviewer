# PRD: RocketRide Multi-Agent PR Review Tool

**Author:** Joshua Phillips
**Date:** March 13, 2026
**Status:** Draft
**Version:** 0.1.0

---

## 1. Overview

This product is a GitHub Action that uses RocketRide's agentic pipeline platform to perform automated, multi-agent code reviews on pull requests. Three independent AI agents (Claude, GPT, Gemini) review PRs in parallel, each posting feedback under its own GitHub App identity. A final Claude-based aggregator deduplicates overlapping comments before results are posted. The tool supports recursive, conversational reviews where developers can reply to agent comments and receive scoped follow-up responses from the originating agent.

The tool is distributed as a marketplace-ready composite GitHub Action designed for minimal-configuration integration into any repository's CI/CD pipeline.

---

## 2. Problem Statement

Code review is one of the most time-consuming bottlenecks in the software development lifecycle. Human reviewers are inconsistent, subject to availability constraints, and often miss issues outside their area of expertise. Existing AI review tools typically rely on a single model, producing a single perspective with that model's blind spots.

There is no widely available tool that coordinates multiple AI agents as independent reviewers, each with its own identity and review style, while also supporting ongoing conversation between the developer and each agent. Engineers also lack a way to evaluate which AI models produce the most useful review feedback in the context of their own codebase.

---

## 3. Solution

A GitHub Action powered by RocketRide's pipeline orchestration that:

- Runs three AI reviewer agents in parallel on every qualifying PR
- Gives each agent a distinct GitHub App identity so reviews are natively integrated into the PR experience
- Supports conversational follow-up where developers reply to a specific agent and only that agent responds
- Auto-approves PRs that receive no critical or high severity feedback
- Is installable from the GitHub Actions Marketplace with minimal configuration

---

## 4. Architecture

### 4.1 High-Level Flow

```
PR Event (opened/updated/comment)
        |
        v
GitHub Action Trigger
        |
        v
Gate Check (target branch, event type, comment author)
        |
        v
   +----+----+
   |         |
   v         v
Full Review  Scoped Re-review
(3 agents    (1 agent,
parallel)    scoped context)
   |         |
   v         v
Claude Aggregator (deduplicate)
        |
        v
Post Reviews via GitHub Apps
        |
        v
Approval Logic (auto-approve or request changes)
```

### 4.2 Component Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| CI/CD Trigger | GitHub Actions (composite action) | Event detection, gating, orchestration |
| Pipeline Engine | RocketRide (Docker in runner) | Agentic review pipeline execution |
| Reviewer Agents | OpenAI, Claude, Gemini (via RocketRide nodes) | Independent parallel code review |
| Aggregator Agent | Claude (via RocketRide node) | Deduplication and output normalization |
| GitHub Integration | Python + PyGithub | PR comment posting, review submission, diff retrieval |
| Configuration | YAML config file | File filters, context scope, severity thresholds |

### 4.3 Model Versions

| Agent | Model | Provider |
|-------|-------|----------|
| Claude Reviewer | `claude-sonnet-4-20250514` | Anthropic |
| GPT Reviewer | `gpt-4o` | OpenAI |
| Gemini Reviewer | `gemini-2.0-flash` | Google |
| Aggregator | `claude-sonnet-4-20250514` | Anthropic |

Model identifiers are defined as constants in `src/config.py` and are not user-configurable in v1. Future versions may expose model selection via `.rocketride-review.yml`.

### 4.4 RocketRide Pipeline Design

The pipeline operates in two modes, defined as separate pipeline JSON files.

**Mode 1: Full Review Pipeline**

Triggered on PR creation or update targeting the main branch. All three reviewer agents execute in parallel. Each receives:

- The full PR diff
- Full file context for each changed file (configurable, on by default)
- Any existing PR comments for conversational awareness
- The review comment struct schema (enforced output format)

The outputs from all three agents feed into the Claude aggregator node, which deduplicates identical or near-identical comments and produces a final per-agent JSON payload.

**Mode 2: Conversation Reply Pipeline**

Triggered when a developer replies to an agent comment. Only the originating agent runs. It receives:

- The specific comment thread (original agent comment + developer reply)
- The relevant file context surrounding the commented lines
- The original review context for continuity

The output bypasses the aggregator and routes directly to the posting layer for the originating agent's GitHub App.

**Agent-to-Pipeline Routing**

The Python orchestration layer maps GitHub App identities to RocketRide pipeline node IDs using a static routing table:

```python
AGENT_ROUTING = {
    "claude-reviewer[bot]": "claude-reviewer",
    "gpt-reviewer[bot]":    "gpt-reviewer",
    "gemini-reviewer[bot]": "gemini-reviewer",
}
```

When a comment event is received, `src/main.py` extracts the bot username from the parent comment, looks up the corresponding node ID, and passes it to `conversation_reply.json` as an input parameter. The pipeline JSON uses this parameter to activate only the matching reviewer node.

### 4.5 RocketRide Engine Provisioning

The RocketRide engine spins up fresh in the GitHub Actions runner via Docker on each invocation. The pipeline JSON files and node configurations are bundled within the action's repository. The engine starts, executes the pipeline, and terminates within the same job.

```
docker build -f docker/Dockerfile.engine -t rocketride-engine .
docker run -p 5565:5565 rocketride-engine
```

The Python orchestration layer connects to the engine via the RocketRide Python SDK on `localhost:5565`.

**Health Check**: After starting the Docker container, the orchestration layer polls `localhost:5565` every 2 seconds for up to 30 seconds. If the engine does not respond within this window, the run is aborted with a graceful failure (PR comment posted, CI exits with code 0). See Section 7.2 for failure handling details.

---

## 5. Functional Requirements

### 5.1 Trigger Conditions

| Event | Action |
|-------|--------|
| PR opened targeting `main` | Full review pipeline |
| PR updated (new commits) targeting `main` | Full review pipeline |
| Developer replies to an agent comment | Scoped re-review (originating agent only) |
| PR opened targeting non-`main` branch | No action (return) |
| PR updated targeting non-`main` branch | No action (return) |
| Agent replies to its own comment | No action (prevent loops) |

### 5.2 Review Comment Struct

Each reviewer agent must return a list of comments conforming to the following schema:

```json
{
  "reviewer": "string",
  "comments": [
    {
      "file": "string",
      "line": "integer",
      "severity": "critical | high | medium | low | nitpick",
      "status": "add | resolve",
      "body": "string"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `reviewer` | Name of the LLM agent (e.g., `claude-reviewer`, `gpt-reviewer`, `gemini-reviewer`) |
| `file` | Relative file path within the repository |
| `line` | Line number in the diff where the comment applies |
| `severity` | One of: `critical`, `high`, `medium`, `low`, `nitpick` |
| `status` | `add` to post a new comment, `resolve` to mark a previous comment as resolved |
| `body` | The full text of the review comment |

### 5.3 Aggregator Behavior

The Claude aggregator agent receives the combined output of all three reviewer agents and performs the following:

1. **Deduplication**: Identifies duplicate comments across agents using the following criteria. Two comments are considered duplicates when they target the same file AND the same line (or within a 3-line window) AND the semantic intent is the same. The aggregator uses the following heuristic: if two comments from different agents reference the same code location and both suggest the same type of change (e.g., both suggest renaming a variable, both flag a missing null check, both recommend extracting a function), they are duplicates. When duplicates are found, the aggregator keeps the version with the most specific or actionable phrasing and attributes it to that agent. The other agent's duplicate is removed from its payload.
2. **Passthrough**: All non-duplicate comments are passed through without modification.
3. **Output**: Produces three separate JSON payloads, one per agent, each containing only that agent's final comments (with duplicates removed where the other agent's version was preferred).

The aggregator does NOT have authority to:

- Drop comments it considers low quality
- Reconcile contradictory feedback between agents
- Modify the content of any comment

### 5.4 Approval Logic

After all reviews are posted:

| Condition | Result |
|-----------|--------|
| Zero `critical` or `high` severity comments across all 3 agents | Each GitHub App submits an **approval** review |
| Any `critical` or `high` severity comment from any agent | Each GitHub App submits a **comment** review (not request changes), the agent(s) with critical/high findings submit **request changes** |

### 5.5 Recursive Conversation

When a developer replies to an agent comment:

1. The action identifies which agent authored the comment (via the GitHub App identity)
2. Only that agent's pipeline mode is invoked
3. The agent receives the full comment thread plus the relevant file context
4. The agent responds in the same thread under its own GitHub App identity
5. The other two agents remain silent

Loop prevention: if the comment author is any of the three GitHub Apps, the action exits without running.

### 5.6 File Filtering

A configurable ignore list excludes files from review. Default ignore patterns:

```yaml
ignore_patterns:
  - "*.lock"
  - "*.min.js"
  - "*.min.css"
  - "package-lock.json"
  - "pnpm-lock.yaml"
  - "yarn.lock"
  - "*.generated.*"
  - "*.g.dart"
  - "*.pb.go"
  - "dist/**"
  - "build/**"
  - "vendor/**"
  - "node_modules/**"
  - "*.svg"
  - "*.png"
  - "*.jpg"
  - "*.gif"
  - "*.ico"
  - "*.woff"
  - "*.woff2"
  - "*.ttf"
  - "*.eot"
```

Users can override or extend this list via a `.rocketride-review.yml` configuration file in their repository root.

### 5.7 Large PR Handling

When a PR diff exceeds the effective context window for any agent, the diff is split into chunks and each chunk is reviewed independently. The chunking strategy operates as follows:

**Chunking rules:**

1. The diff is split at file boundaries first. Each file's diff is a natural chunk.
2. If a single file's diff exceeds 500 lines, it is split into segments at function or class boundaries where detectable, otherwise at the nearest blank line boundary. Each segment includes 20 lines of overlap context with the previous segment to preserve continuity.
3. Each chunk is sent through the review pipeline independently. Agent responses are collected across all chunks and merged before aggregation.
4. The merge step concatenates comment lists and adjusts line numbers to map back to the original diff coordinates.

**Configuration:**

```yaml
# .rocketride-review.yml
max_chunk_lines: 500       # Max lines per chunk (default: 500)
chunk_overlap_lines: 20    # Overlap context between segments (default: 20)
```

**Limits:** If a PR contains more than 50 changed files after filtering, or more than 5,000 total changed lines, the action posts a summary comment noting the PR is too large for automated review and exits without reviewing. These thresholds are configurable.

---

## 6. Configuration

### 6.1 GitHub Action Usage

```yaml
name: RocketRide PR Review

on:
  pull_request:
    types: [opened, synchronize]
    branches: [main]
  issue_comment:
    types: [created]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: rocketride-org/rocketride-reviewer@v1
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          google_api_key: ${{ secrets.GOOGLE_API_KEY }}
          claude_app_id: ${{ secrets.CLAUDE_APP_ID }}
          claude_app_private_key: ${{ secrets.CLAUDE_APP_PRIVATE_KEY }}
          gpt_app_id: ${{ secrets.GPT_APP_ID }}
          gpt_app_private_key: ${{ secrets.GPT_APP_PRIVATE_KEY }}
          gemini_app_id: ${{ secrets.GEMINI_APP_ID }}
          gemini_app_private_key: ${{ secrets.GEMINI_APP_PRIVATE_KEY }}
          review_context: "full"       # "full" or "diff"
          config_path: ".rocketride-review.yml"  # optional
```

### 6.2 Required Secrets

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT reviewer agent |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude reviewer and aggregator |
| `GOOGLE_API_KEY` | Google AI API key for Gemini reviewer agent |
| `CLAUDE_APP_ID` | GitHub App ID for claude-reviewer[bot] |
| `CLAUDE_APP_PRIVATE_KEY` | GitHub App private key for claude-reviewer[bot] |
| `GPT_APP_ID` | GitHub App ID for gpt-reviewer[bot] |
| `GPT_APP_PRIVATE_KEY` | GitHub App private key for gpt-reviewer[bot] |
| `GEMINI_APP_ID` | GitHub App ID for gemini-reviewer[bot] |
| `GEMINI_APP_PRIVATE_KEY` | GitHub App private key for gemini-reviewer[bot] |

### 6.3 Repository Configuration File

Optional `.rocketride-review.yml` in the repository root:

```yaml
# Review scope
review_context: full  # "full" or "diff"

# Target branch (default: main)
target_branch: main

# File ignore patterns (extends defaults)
ignore_patterns_extra:
  - "migrations/**"
  - "*.sql"

# Override default ignore patterns entirely
# ignore_patterns_override:
#   - "*.lock"

# Severity threshold for auto-approval
# PR is auto-approved if no comments at or above this severity
approval_threshold: high  # "critical" or "high" (default: high)

# Large PR chunking
max_chunk_lines: 500          # Max lines per diff chunk (default: 500)
chunk_overlap_lines: 20       # Overlap between segments (default: 20)
max_files: 50                 # Max changed files before skipping review (default: 50)
max_total_lines: 5000         # Max total changed lines before skipping (default: 5000)
```

---

## 7. Non-Functional Requirements

### 7.1 Performance

- Full review pipeline should complete within 5 minutes for a typical PR (under 500 changed lines)
- Docker engine startup should add no more than 60 seconds of overhead
- Parallel agent execution should keep total review time close to the slowest single agent, not the sum of all three

### 7.2 Reliability

- If one agent fails (API timeout, rate limit), the other two should still complete and post their reviews
- Agent failures should be logged as a comment on the PR noting which agent was unavailable
- The action should never crash the CI pipeline; all errors are caught and reported gracefully

### 7.3 Security

- No API keys are logged or exposed in action output
- GitHub App private keys are handled in memory only, never written to disk in the runner
- The RocketRide Docker container runs with no network access beyond the LLM API endpoints and localhost

### 7.4 Modularity

- The action must be installable from the GitHub Marketplace with a single `uses:` line
- All configuration is optional with sensible defaults
- The action should work on any repository regardless of language or framework
- No dependencies on the host repository's build system or toolchain

---

## 8. GitHub App Setup

Users must create three GitHub Apps (one per reviewer agent). Each app requires:

**Permissions:**

- Pull requests: Read & Write
- Issues: Read & Write (for comment events)
- Contents: Read (for file context)

**Events:**

- Pull request
- Issue comment
- Pull request review comment

A setup guide and optional CLI setup script will be provided to streamline the creation of all three apps. The script will:

1. Walk through creating each GitHub App via the GitHub API
2. Generate and download private keys
3. Output the required secrets for the user to add to their repository

---

## 9. Future Considerations

These are explicitly out of scope for v1 but documented for future planning:

- **Performance analytics dashboard**: Structured tracking of which agent's comments get resolved, pushed back on, or lead to code changes
- **Custom agent prompts**: Allow users to provide per-agent system prompts for domain-specific review guidance
- **Persistent RocketRide instance**: Option to connect to a remote RocketRide engine instead of spinning up Docker each time
- **Additional LLM agents**: Support for adding more agents (Grok, Llama, Mistral) via configuration
- **Review memory**: Cross-PR context where agents learn the team's coding patterns and preferences over time
- **Self-hosted model support**: Route agent reviews through locally hosted models for air-gapped environments

---

## 10. Success Metrics

Since formal performance tracking is deferred, v1 success is measured by:

- **Adoption**: Number of repositories installing the GitHub Action
- **Completion rate**: Percentage of triggered reviews that complete without errors
- **Developer engagement**: Whether developers reply to agent comments (indicating the feedback is worth engaging with)
- **Time to review**: Wall clock time from PR creation to all reviews posted

All of these are observable through GitHub's native data and the action's workflow run logs.

---

## 11. Open Source and Licensing

This tool will be released under the MIT license, consistent with RocketRide's own licensing. The repository will include:

- The composite GitHub Action definition
- RocketRide pipeline JSON files (full review and conversation reply modes)
- Python orchestration scripts
- Documentation (setup guide, configuration reference, contributing guide)
- Example workflow files for quick integration

---

## Appendix A: Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent execution model | Parallel | Faster reviews; independent perspectives |
| Distribution format | GitHub Action (composite) | Marketplace-ready, minimal integration effort |
| Re-review behavior | Scoped to replied-to agent | Avoids noise, keeps conversation focused |
| Agent identity | 3 separate GitHub Apps | Each agent is a distinct reviewer with its own identity |
| RocketRide provisioning | Docker in runner | Self-contained, no external dependencies |
| Review scope | Configurable, full context default | Better review quality with opt-out for cost savings |
| Approval logic | Auto-approve on zero critical/high | Balances automation with safety |
| Aggregator authority | Deduplicate only | Preserves each agent's voice; avoids silent comment drops |
| Severity tiers | critical/high/medium/low/nitpick | Granular enough for approval logic and developer triage |
| File filtering | Configurable ignore list with defaults | Avoids wasting tokens on lockfiles and generated code |
| Performance tracking | GitHub history only | Lightweight; no infrastructure overhead for v1 |
| Model versions | Claude Sonnet, GPT-4o, Gemini 2.0 Flash | Fast and cost-effective for high-frequency CI usage |
| Large PR handling | Chunking at file/function boundaries | Preserves review quality within context window limits |
| Dedup criteria | Same file + 3-line window + same semantic intent | Concrete enough for implementation, flexible enough for LLM judgment |
| Engine health check | 30s timeout, 2s polling interval | Balances fast failure detection with Docker startup variance |
