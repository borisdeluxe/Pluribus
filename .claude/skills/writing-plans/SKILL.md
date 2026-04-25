---
name: writing-plans
description: Use when you have a tk-draft for a feature, before touching code
---

# Writing Implementation Plans

Write comprehensive implementation plans assuming the implementer has zero context. Document everything: which files to touch, exact code, how to test.

<HARD-GATE>
Do NOT write code outside of plan examples. The plan is the deliverable, not code.
</HARD-GATE>

## Input

Read `.pipeline/<feature>/tk-draft.md` from concept_clarifier.

## Output

Write `.pipeline/<feature>/plan.md` with bite-sized tasks.

## Scope Check

If the tk-draft covers multiple independent subsystems:
1. Flag that it should have been broken up during brainstorming
2. Suggest separate plans — one per subsystem
3. Each plan should produce working, testable software on its own

## File Structure

Before defining tasks, map out files:

```markdown
## Files

### New Files
- `src/api/feature.py` — Main feature logic
- `tests/test_feature.py` — Feature tests

### Modified Files
- `src/api/routes.py:45-60` — Add new endpoint
- `src/models/schemas.py:20-30` — Add new schema
```

Design units with clear boundaries:
- Each file has one responsibility
- Prefer smaller, focused files
- Files that change together live together

## Task Granularity

Each step is one action (2-5 minutes):
- "Write the failing test" — step
- "Run it to verify failure" — step
- "Implement minimal code" — step
- "Run tests to verify pass" — step
- "Commit" — step

## Plan Document Format

```markdown
# <Feature> Implementation Plan

**Goal:** <One sentence>

**Architecture:** <2-3 sentences>

**Tech Stack:** <Key technologies>

---

## Files

### New Files
- `path/to/file.py` — Purpose

### Modified Files
- `path/to/existing.py:lines` — What changes

---

## Task 1: <Component Name>

**Files:**
- Create: `exact/path/to/file.py`
- Test: `tests/exact/path/test.py`

- [ ] **Step 1: Write failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```

---

## Task 2: ...

---

STATUS: READY_FOR_TEST_DESIGNER
```

## No Placeholders

These are plan failures — never write them:
- "TBD", "TODO", "implement later"
- "Add appropriate error handling"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code)
- Steps without code blocks

## Self-Review

After writing the plan:

1. **Spec coverage:** Check each requirement in tk-draft. Can you point to a task?
2. **Placeholder scan:** Search for red flags from "No Placeholders" section
3. **Type consistency:** Do names match between tasks?

Fix issues inline.

## Red Flags - STOP

- Writing implementation code outside examples
- Skipping test steps
- Vague "add error handling" steps
- References to undefined functions

## Output

Last line MUST be one of:
- `STATUS: READY_FOR_TEST_DESIGNER` — Plan complete, proceed to tests
- `STATUS: RETURN_TO_CONCEPT_CLARIFIER` — tk-draft has gaps, needs clarification
