# Capital Weekly market-data instructions

## Read before work

The cross-repository product documents in the adjacent frontend checkout are
authoritative. Set `CAPITAL_WEEKLY_FRONTEND_ROOT` to that repository root, then
read:

1. `$CAPITAL_WEEKLY_FRONTEND_ROOT/docs/superpowers/specs/2026-08-11-capital-weekly-terminal-redesign.md`
2. `$CAPITAL_WEEKLY_FRONTEND_ROOT/docs/superpowers/plans/2026-08-11-capital-weekly-terminal-redesign.md`
3. `$CAPITAL_WEEKLY_FRONTEND_ROOT/docs/PARALLEL_EXECUTION.md`

Also read the existing data-domain design and tests for the files assigned to the current task.

## Task ownership

- Work only on the assigned implementation-plan task.
- Task 1 owns shared history cutoff plus indices, equity sectors, GICS fetchers/CLIs/tests.
- Task 2 owns weekly-context empty-table schemas and its tests.
- Task 3 owns the coordinated weekly release, manifest, status, CLI, tests, and its README section.
- Preserve every unrelated dirty or untracked file included in the worktree baseline.
- Do not modify the Next.js repository from a backend execution task.

## Data and publication rules

- Apply `as_of_date` before calculating any snapshot return.
- Never publish a formal week containing observations after the target Sunday.
- Empty optional context tables retain their standard headers.
- A new week becomes visible only after all five pipelines and release validation succeed.
- Tests must use deterministic fake histories or runners; do not trigger a real network refresh unless the user explicitly requests it.

## Development workflow

- Follow TDD for behavior changes and show the expected RED before implementation.
- Run the focused unittest modules named by the task, followed by `python3 -m unittest -v`.
- Do not switch branches, rebase, reset, or merge other work inside an execution chat.
- Commit only the assigned task files using the plan's commit message.

## Handoff

Report task number, commit SHA, files changed, RED/GREEN evidence, full unittest result, and remaining risks. Stop and report when the baseline is broken or the task needs a file owned by another active chat.
