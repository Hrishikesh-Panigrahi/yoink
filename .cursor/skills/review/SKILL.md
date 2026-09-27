---
name: review
description: Review pull requests, diffs and local changes in the Yoink repository before they're merged, looking for bugs, regressions, safety problems, missing tests and code that will be hard to maintain. Use whenever the user asks to "review this PR/diff/patch", "check this change", "is this safe to merge", "find what's wrong with this", or pastes a diff from this project. Also use for a self-review before opening a PR. The job is to catch what will cause trouble in production or in six months, not to describe what the code obviously does.
---

# Code review for Yoink

A good review finds the two or three things that really matter and says them
clearly. It doesn't go over every possible aspect of code quality. That just
creates noise, and people learn to skim reviews full of noise.

## Step 1: Understand what changed and why

Before reading the diff, answer two questions:
- What problem is this change solving? Read the PR description, the commit
  message or what the user said. If they stated an intent, go by that rather
  than guessing from the diff.
- What's the smallest change that would solve it? You'll use this to judge
  scope as well as correctness.

If there's no stated intent and you can't work it out from the diff with
confidence, ask. A review based on the wrong idea of what the change is for is
worse than no review.

## Step 2: Read the diff in context

Open the changed files, not just the diff hunks. The diff shows what changed;
the rest of the file shows whether the change fits with what's already there,
and whether it clashes with code just outside the lines that changed.

For each changed file, check:
- **Does it do what it claims?** Follow the actual logic instead of trusting
  variable names. If it fixes a bug, make sure it fixes the cause and not just
  the symptom that was reported.
- **Regressions.** Does it change behaviour anywhere it shouldn't? Look at the
  callers of changed functions if they aren't obvious from the diff.
- **Edge cases and bad input.** Empty lists, `None`, boundary values, two
  things happening at once, partial failures. Only raise the ones that can
  actually happen given how the code is called. A generic "what if this is
  None" on a private function whose only caller never passes None is noise.
- **Errors and state.** Are errors caught at the right level, or swallowed
  where they should be passed up? If there's a state machine (start, running,
  done or failed), is every transition handled?
- **Tests.** Is the new or changed behaviour tested, and do the tests really
  exercise it rather than just checking that a mock did what it was told? A
  change without a test isn't automatically wrong, but it needs a reason.

## Step 3: Sort what you found before writing anything

Put each finding in one of these three groups. This sorting is the real result
of the review, not an afterthought.

- **Blocking.** It will cause wrong behaviour, lost data, a crash, or a
  regression a user will run into. It has to be fixed before merging.
- **Should fix.** A real problem that doesn't block the merge: something that
  will trip up the next person, a missing test for a path that matters, or an
  inconsistency that will confuse people.
- **Worth mentioning.** Optional: a small nitpick, a style preference, an idea
  for later. Keep this group small. If it grows past a couple of items, most of
  them probably aren't worth saying.

If a group is empty, don't pad it. "Nothing blocking" is useful to hear, so say
it plainly instead of leaving the heading out.

## Step 4: Write the review

```markdown
## Summary
<1-2 sentences: what this change does and whether it's ready to merge as it is>

## Blocking
- [file:line] <issue>: <why it matters, concretely: what breaks and when>

## Should fix
- [file:line] <issue>: <why>

## Worth mentioning
- [file:line] <suggestion>

## Tests
<is the coverage enough for what changed? name the specific gaps if not>
```

Leave out any section that has nothing in it, except Summary. For every issue,
give the file and line, and explain the real consequence. "This throws on an
empty list, which happens whenever a search returns no results" is something
the author can check. "This could be an issue" is just an opinion.

If something is good, say so briefly. A review that's entirely negative reads
as hostile even when it's right, and it helps the author to know what not to
change.

## Calibration

- Don't flag style choices that match the rest of the file just because you'd
  have done it differently.
- Don't repeat what a linter or type checker would catch. If none seems to be
  set up, say that once instead of listing every formatting issue.
- If you're not sure whether something is a bug or intended, say what you saw
  and ask, rather than calling it wrong.
- Raise security and performance problems when you actually see one (for
  example unchecked input reaching a query, or a blocking call on the UI
  thread). Don't add a generic "consider security" line when you haven't found
  anything specific.
