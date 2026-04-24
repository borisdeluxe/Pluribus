---
name: review-runner
description: Review design documents, implementation plans, or specs for completeness and correctness. Sends document to multiple Claude instances for independent review, then evaluates feedback as author-judge. Used by Architect/Planner agent. Autonomous gate decision, no user interaction.
type: rigid
---

# Review Runner

Send a design document to multiple Claude reviewers for independent review, then evaluate and produce gate decision.

## When to Use

- Architect/Planner reviewing a `tk-draft.md` before creating `plan.md`
- Reviewing `plan.md` before handoff to Test Designer
- Any design artifact that needs validation before next pipeline stage

## Workflow

### Step 1: Determine Input

Read the artifact from `.pipeline/<feature>/` as specified by orchestrator handoff.

### Step 2: Extract Codebase Context

Before sending for review, extract relevant context so reviewers don't flag non-issues.

Gather and prepend to review request:
- **DB Schema** relevant to the feature (table names, key columns, RLS policies)
- **Auth Patterns** used in the codebase (JWT flow, permission checks)
- **Existing Similar Code** (endpoints, functions the plan builds on)
- **Intentional Constraints** (documented tech debt, scale assumptions, explicit trade-offs from CLAUDE.md)

Format:
```markdown
## Existing Codebase Context

### DB Schema
[relevant tables and columns]

### Auth/Security Pattern
[how auth works in this codebase]

### Existing Similar Code
[relevant endpoints or functions the plan extends]

### Intentional Constraints
[documented tech debt, scale limits, explicit trade-offs]
```

Skip sections with no relevant information. For greenfield features, minimize context.

### Step 3: Run Parallel Reviews

Call Claude API twice with different temperatures/perspectives:

1. **Reviewer A (Conservative)**: Focus on correctness, edge cases, failure modes
2. **Reviewer B (Pragmatic)**: Focus on complexity, over-engineering, simpler alternatives

Use the prompt from `prompts/reviewer.md` for both, with perspective parameter.

Model: `claude-sonnet-4-5` (or as configured in agent role)
Timeout: 90 seconds per reviewer
Retry: 1 retry on failure

If both reviewers fail, output `STATUS: BLOCKED_REVIEW_FAILED` and stop.

### Step 4: Evaluate Reviews

Read `prompts/evaluator.md` and follow its instructions:

- Group points by topic
- Evaluate each: AGREE / REJECT / PARTIALLY with reasoning
- Flag cross-reviewer agreement (strong signal)
- Flag contradictions (resolve with own assessment)
- Produce prioritized issue list

### Step 5: Gate Decision

Based on evaluation, decide:

| Condition | Decision | Output |
|-----------|----------|--------|
| No AGREE points with priority HIGH | **PASS** | `STATUS: READY_FOR_<next_agent>` |
| 1-2 HIGH issues, all fixable in-place | **FIX_AND_PASS** | Apply fixes, then PASS |
| 3+ HIGH issues OR architectural concerns | **FAIL** | `STATUS: RETURN_TO_<author_agent>` |

### Step 6: Write Output

Write `review-report.md` to `.pipeline/<feature>/` containing:
- Summary (1-2 sentences)
- Issues found (grouped by priority)
- Gate decision with reasoning
- Status line (last line)

## Output Format

```markdown
# Review Report: <feature>

## Summary
[1-2 sentence summary of review outcome]

## Issues

### High Priority
- [issue]: [reasoning] → [action]

### Medium Priority
- [issue]: [reasoning] → [action]

### Low Priority
- [issue]: [reasoning] → [action]

## Gate Decision
[PASS | FIX_AND_PASS | FAIL]: [reasoning]

STATUS: READY_FOR_TEST_DESIGNER
```

## Cost Estimate

~$0.08-0.15 per review (2x Sonnet calls + evaluation)
