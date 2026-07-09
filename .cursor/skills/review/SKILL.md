---
name: review
description: Review pull requests, diffs, and local changes in the Yoink repository before merge — for correctness, regressions, safety, test coverage, and maintainability. Use whenever the user asks to "review this PR/diff/patch", "check this change", "is this safe to merge", "find what's wrong with this", or pastes a code diff from this project. Also use for self-review before opening a PR. This is a pre-merge risk reviewer: its job is to catch what will bite in production or in six months, not to restate what the code obviously does.
---

# Code Review — Yoink

A good review finds the 2-3 things that actually matter and says them clearly. It does not produce a uniform pass over every possible axis of code quality — that produces noise, and noise trains people to skim reviews instead of reading them.

## Step 1 — Understand what changed and why

Before reading a single line of diff, answer:
- What problem is this change solving? (Read the PR description/commit message/user's framing — don't infer from the diff alone if a stated intent exists.)
- What's the smallest version of "done" for that problem? You'll use this to judge scope, not just correctness.

If there's no stated intent and it's not inferable from the diff with confidence, ask rather than guess — a review built on a wrong assumption about intent is worse than no review.

## Step 2 — Read the diff in context, not in isolation

Open the changed files, not just the diff hunks. A diff shows *what* changed; the surrounding file shows whether it's *consistent* with what's already there and whether it interacts badly with code just outside the changed lines.

For each changed file, check:
- **Does the change do what it claims?** Trace the actual logic, don't pattern-match on variable names. If there's a described bug being fixed, confirm the fix addresses the root cause, not just the reported symptom.
- **Regressions**: does this change behavior anywhere it shouldn't? Check call sites of changed functions/methods if they're not obvious from the diff.
- **Edge cases and invalid input**: empty collections, nulls, boundary values, concurrent access, partial failures. Only raise ones that are plausible given how this code is actually called — not a generic "what if input is null" for a private method with one caller that never passes null.
- **State and error handling**: are errors caught at the right level, or swallowed/logged-and-ignored where they should propagate? Do state transitions (e.g. start → running → done/failed) have all their transitions covered?
- **Tests**: do they exist for the new/changed behavior, and do they actually exercise the change (not just re-assert the mock did what the mock was told to do)? A change with no test isn't automatically wrong, but it needs a stated reason.

## Step 3 — Triage before writing anything

Sort what you found into exactly these buckets — this is the actual deliverable, not an afterthought:

- **Blocking** — will cause incorrect behavior, data loss, a crash, or a regression a user will hit. Must be fixed before merge.
- **Should fix** — real problem, but not merge-blocking: a maintainability trap, a missing test for a non-trivial path, an inconsistency that will confuse the next person touching this code.
- **Worth mentioning** — genuinely optional: a nitpick, a style preference, a "consider this for later." Keep this bucket small; if it's more than a couple items, most of them probably aren't worth saying.

If a bucket is empty, don't force content into it. An empty "Blocking" section is a real and useful signal — say so plainly ("nothing blocking") rather than omitting the heading.

## Step 4 — Write the review

```markdown
## Summary
<1-2 sentences: what this change does and whether it's ready to merge as-is>

## Blocking
- [file:line] <issue> — <why it matters, concretely: what breaks and when>

## Should fix
- [file:line] <issue> — <why>

## Worth mentioning
- [file:line] <suggestion>

## Tests
<is coverage adequate for what changed? specific gaps if not>
```

Omit any section with nothing in it except Summary. For every issue, name the file and line, and say *why* it matters in terms of actual consequence ("this will throw on an empty list, which happens whenever a search returns no results" — not "this could be an issue"). A reviewer comment without a mechanism is an opinion; one with a mechanism is a fact the author can check.

Always call out what's good, briefly, if something is — a review that's 100% negative reads as adversarial even when accurate, and it's genuinely useful signal for the author to know what not to change.

## Calibration

- Don't flag style choices that are already consistent with the rest of the file/module just because you'd have written it differently.
- Don't repeat what a linter or type-checker would already catch, unless none appears to be configured — in that case, say so once, briefly, rather than manually itemizing every formatting nit.
- If you're unsure whether something is a real bug vs. intentional, say what you observed and ask, rather than asserting it's wrong.
- Security and performance issues get raised when you actually see one (e.g. unsanitized input reaching a query, an obviously blocking call on a UI thread) — don't pad the review with a generic "consider security implications" when nothing specific was found.