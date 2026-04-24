---
name: code-review
description: Review code changes against project standards, check coverage, identify regressions. Used by QA Validator agent. Produces gate decision for pipeline progression. Autonomous, no user interaction.
type: rigid
---

# Code Review

Review implementation code against standards, verify test coverage, check for regressions.

## When to Use

- QA Validator reviewing Implementer's code changes
- Final gate before deploy handoff
- Any code artifact that needs validation before merge/deploy

## Workflow

### Step 1: Gather Inputs

Collect from `.pipeline/<feature>/` and worktree:
- `plan.md` (what was supposed to be implemented)
- `test-plan.md` (what tests were specified)
- `security-report.md` (security review findings)
- Git diff of implementation (from worktree)
- Test results (pytest output)
- Coverage report (if available)

### Step 2: Extract Standards Context

Read from CLAUDE.md and `.claude/agents/qa_validator.md`:
- Code style requirements
- Required patterns (error handling, logging, etc.)
- Forbidden patterns (anti-patterns to flag)
- Coverage thresholds
- Performance baselines

### Step 3: Run Parallel Reviews

Call Claude API with three review perspectives:

1. **Reviewer A (Correctness)**: Does code match plan? Are tests comprehensive?
2. **Reviewer B (Standards)**: Does code follow project conventions?
3. **Reviewer C (Regression)**: Could this break existing functionality?

Use prompts from `prompts/` directory.

Model: `claude-sonnet-4-5`
Timeout: 120 seconds per reviewer (code review takes longer)
Retry: 1 retry on failure

If 2+ reviewers fail, output `STATUS: BLOCKED_REVIEW_FAILED` and stop.

### Step 4: Check Automated Metrics

Verify:
- [ ] All tests pass (exit code 0)
- [ ] Coverage >= threshold (default: 80% for new code)
- [ ] No new linting errors
- [ ] No TODO/FIXME without ticket reference

Flag violations as HIGH priority issues.

### Step 5: Evaluate Reviews

Read `prompts/evaluator.md` and consolidate:

- Group issues by category
- Evaluate each: AGREE / REJECT / PARTIALLY
- Cross-reference with security-report.md findings
- Verify plan.md requirements are met
- Produce prioritized issue list

### Step 6: Gate Decision

| Condition | Decision |
|-----------|----------|
| All tests pass + no HIGH issues | **PASS** |
| Tests pass + 1-2 HIGH issues (minor fixes) | **FIX_AND_PASS** |
| Tests fail OR 3+ HIGH issues | **FAIL** |
| Security findings unaddressed | **FAIL** |
| Plan requirements not met | **FAIL** |

### Step 7: Write Output

Write `qa-report.md` to `.pipeline/<feature>/`:

```markdown
# QA Report: <feature>

## Summary
[1-2 sentence outcome]

## Checklist
- [x] All tests pass
- [x] Coverage: 87% (threshold: 80%)
- [x] No linting errors
- [ ] Security findings addressed (1 open)

## Plan Compliance
| Requirement | Status |
|-------------|--------|
| [req from plan] | DONE / PARTIAL / MISSING |

## Code Review Issues

### High Priority
- [issue]: [file:line] [reasoning] → [action]

### Medium Priority
...

### Low Priority
...

## Gate Decision
[PASS | FIX_AND_PASS | FAIL]: [reasoning]

STATUS: READY_FOR_DEPLOY_RUNNER
```

## Cost Estimate

~$0.12-0.20 per review (3x Sonnet calls + evaluation + metrics check)

## Integration with Security Reviewer

If `security-report.md` contains unresolved HIGH findings:
- Cross-reference with implementation
- If finding is addressed in code → mark resolved
- If finding is NOT addressed → automatic FAIL

Do not duplicate security review work — trust the Security Reviewer's findings.
