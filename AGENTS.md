# Capital Weekly data-pipeline instructions

## Repository boundary

- `pipeline/` contains all tracked implementation, configuration, tests, and engineering documents.
- `output/` contains only the latest complete successful JSON release and is not committed to Git.
- The only visible top-level product directories are `pipeline/` and `output/`.
- The frontend is a separate future repository. Do not modify the adjacent Next.js checkout from this backend repository.

## Data and publication rules

- Apply `as_of_date` before calculating any snapshot return or derived value.
- Keep the existing five data domains: indices, cross-market sectors, GICS, macro assets, and weekly context.
- A release becomes visible only after all five pipelines and cross-file validation succeed.
- Refresh replaces the stable files in `output/`; it must not create dated or historical week directories.
- Keep one successful raw-cache generation under `pipeline/.cache/`.
- Empty optional context collections remain present as empty arrays.
- Never use zero, an empty string, `NaN`, or `Infinity` to represent missing JSON data; use `null`.
- Every published business record retains its source URL, observation date, and QC or source status.
- Tests use deterministic fake histories or runners. Do not run a real network refresh unless the user explicitly requests it.

## Development workflow

- Follow TDD for behavior changes and show the expected RED before implementation.
- Run focused unittest modules followed by `python3 -m unittest -v`.
- Run `node --test pipeline/tests/test_verify_weekly_workbooks.mjs` while the workbook compatibility tests remain present.
- Do not switch branches, rebase, reset, or merge other work inside an execution chat.
- Preserve unrelated dirty or untracked files and archive them recoverably before cleanup.
- Commit only the files owned by the active implementation-plan task.

## Handoff

Report commit SHAs, moved/created/deleted files, RED/GREEN evidence, full test results, the source release used for offline conversion, the stable output identity, the recoverable cleanup archive, and remaining compatibility risks.
