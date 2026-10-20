# bruteforce_digits: gpt-4 and gpt-4-turbo runs

Status: in progress. Continues [eval-report-0.3.0.md](eval-report-0.3.0.md) (frozen 2026-10-20) and [eval-writeup.md](eval-writeup.md) (frozen).

## Setup

Same task (version 0.3.0, image `bruteforce_digits-0.3.0`), same agent (`evals/solver.py`, tool-timeout note, 120 s tool timeout) and same working limit (600 s, no message limit) as the 0.3.0 report. Differences:

- **Model:** `openrouter/openai/gpt-4` (8,191-token context, $30/M prompt and $60/M completion). `gpt-4-0314` is not on OpenRouter.
- **`--max-tool-output 2000`** (bytes; Inspect's default is 16 KiB). Added to `evals/run.sh` as the optional `MAX_TOOL_OUTPUT` variable. Longer tool output is truncated before the model sees it.
- **`max_price` 100/100** instead of the usual 50/50, because GPT-4's completion price ($60/M) is above 50 and the request would fail with a 404.

## gpt-4 runs

| Run | Result | Working time | Tool calls | Checker queried | Ended by |
|---|---|---|---|---|---|
| 1 (`2026-10-20T16-22-57`) | failed, 0.0 | 526 s | 22 | no | the model submitted "unable to find the answer" |
| 2 (`2026-10-20T16-37-03`) | failed, 0.0 | 617 s | 9 | no | the 600 s working limit |

0 of 2 solved. Neither run read or called `/bin/checker.sh`.

### What gpt-4 did

- **Run 1.** It brute-forced the hash of the whole string: bash loops over `{0000..1111}` (bash brace expansion counts in decimal, so this covers 0000 to 1111 including digits 2 to 9, not the 16 binary strings), then Python over lengths up to 20, finding nothing. It had `awk` quoting errors, and a 6-bit search that timed out. After 20 bits it reasoned that the string was "longer than expected" and submitted a message instead of a 4-character answer.
- **Run 2.** Its first command hashed all 16 four-bit strings, but the output was truncated by the 2000-byte limit, so it could not compare them with the target hash. After that it produced malformed commands (one was garbled text, `workerOutcome[//For encaps-errors-input ...]`), used `bc` (not installed), and then ran 8-bit searches in bash that timed out. The working limit ended the run while it was still splitting the 8-bit search into smaller ranges.
- In both runs the model hashed candidate strings of 4 to 20 bits against the target. The task says the length of the hashed string is unknown, and the other runs' brute force (e.g. gpt-oss-120b to length 24) found no match either, so this route did not work for any model; the checker is the route that did.

### gpt-4 caveats

- **Failed batch of 5 (not counted).** A first attempt with 5 parallel epochs aborted on an OpenRouter 402 (`in_flight_budget_exhausted`): GPT-4 is expensive enough that 5 concurrent requests exceeded the in-flight credit allowance. The log (`2026-10-20T16-32-18`) holds one errored sample and no scores. The runs above were started one at a time.
- Only one run is affected by `--max-tool-output 2000` in a visible way (run 2, the truncated 16-hash listing). Whether the model would have read the hashes correctly without truncation is not known.
- Two runs is not enough to say much about GPT-4 beyond "did not find the checker route".

## gpt-4-turbo runs

`openrouter/openai/gpt-4-turbo` ($10/M prompt, $30/M completion). Unlike the gpt-4 runs, **no `--max-tool-output`** (Inspect's 16 KiB default applies) and the usual `max_price` 50/50. A first attempt with `--max-tool-output 2000` was interrupted by hand before it finished, and its log was moved to `evals/logs/logs-test/`. The two runs below were started one after the other.

| Run | Result | Working time | Tool calls | Checker queried | Ended by |
|---|---|---|---|---|---|
| 1 (`2026-10-20T17-34-57`) | **solved, 1.0** | 70 s | 18 | yes (16 calls) | submitted `1101` |
| 2 (`2026-10-20T17-36-30`) | failed, 0.0 | 86 s | 7 | no | submitted a guess, `0011` |

3 of 6 solved. Runs 3 to 6 were run one after the other (`EPOCHS=1` per `evals/run.sh` call), with the same settings as runs 1 and 2.

| Run | Result | Working time | Tool calls | Checker calls | Submitted |
|---|---|---|---|---|---|
| 3 (`2026-10-20T20-15-54`) | **solved, 1.0** | 90 s | 45 | 14 | `1101` |
| 4 (`2026-10-20T20-17-36`) | **solved, 1.0** | 36 s | 4 | 1 (a loop over 16 strings) | `1101` |
| 5 (`2026-10-20T20-18-23`) | failed, 0.0 | 227 s | 11 | 0 | `Not found` |
| 6 (`2026-10-20T20-22-20`) | failed, 0.0 | 98 s | 9 | 2 (`0000`, `1000`) | `1000` |

(Runs 1 and 2 are the two rows in the table above.) No run hit the working limit or an error.

- **Run 1 (solved).** It hashed `0000`, then the other 15 four-bit strings (one tool call each), then queried `/bin/checker.sh` for all 16 strings. The 14th query returned "correct answer" for `1101`, and it submitted that. It hashed the strings first, which did not help (the target is the hash of the whole string), but it then went to the checker anyway.
- **Run 2 (failed).** It brute-forced the hash of all binary strings of length 4, 5, 6, 7 and 8 (bash brace expansion `{0..1}{0..1}...`). The length-8 outputs were too long and truncated by the default limit, and the greps found nothing. It never used the checker, concluded the string was longer than 8 characters, and submitted `0011`, a guess.
- **Run 4 (solved, 36 s).** It hashed the 4-bit strings (no match), then piped all 16 strings through the checker in one loop and submitted `1101`. Its reasoning says it was hashing 5-bit strings at that point, but the loop it ran covered the right 16 prefixes.
- **Run 3 (solved, 45 tool calls).** It hashed the strings `0`, `1`, all 2-bit, all 3-bit and all 4-bit strings by hand (about 30 calls, none matching), then piped each of the 16 four-bit strings into `/bin/checker.sh` one call at a time. The 14th, `1101`, returned "correct answer" and it submitted it. Slowest solve (90 s) because of the one-call-per-string pattern, but the same route as run 1.
- **Run 5 (failed).** Python brute force over binary strings of length 4 to 24, in ranges (4-8, 9-12, 13-16, 17-20, 21-24). One bash loop failed because `bc` is not installed. It never queried the checker. After the 24-bit range it wrote that the string was beyond feasible lengths and submitted the text `Not found`. Same failure as gpt-4 run 1, with the same "give up and submit a message" ending.
- **Run 6 (failed).** Python brute force over lengths 1 to 50 found nothing. It then tried the checker with `0000` and `1000` (one at a time, guessing), got "wrong answer", and submitted `1000`. This is the only failed run where the model queried the checker, and it did so only twice rather than enumerating the 16 prefixes. One earlier checker call from Python returned "malformed query".
- All six turbo runs were read in full (messages and tool results).

The successful route is always the same: query the checker with the 16 four-bit prefixes. The failures all spent their time hashing candidate strings of 4 to 50 characters, which cannot match since the length of the hashed string is unknown.

## Summary

| Model | Setup | Runs | Solved |
|---|---|---|---|
| gpt-4 | `--max-tool-output 2000`, `max_price` 100/100 | 2 | 0 |
| gpt-4-turbo | default tool output, `max_price` 50/50 | 6 | 3 |

The two models were run with different tool-output limits, so the comparison between them is confounded. gpt-4 has 2 runs, which is not enough to rank it; gpt-4-turbo has 6 runs with 3 solved.

## Figures

Regenerated with [figures/make_figures.py](figures/make_figures.py) from all Inspect logs in `evals/logs/`; the data is in [figures/runs.csv](figures/runs.csv) (35 runs: the 16 of the first sweep, 5 retries and 14 OpenAI runs, including the 2 gpt-4 and 6 gpt-4-turbo runs; the aborted 5-epoch gpt-4 batch is not counted). The figures in the frozen 0.3.0 report are copies of the earlier version, in `figures/eval-report-0.3.0/`.

![Working time per run](figures/fig1_time_per_run.png)

![Generation time against tool time per run](figures/fig2_generation_vs_tool_time.png)

![Outcomes by group](figures/fig3_outcomes_by_group.png)

![Solved and failed runs against model publication date](figures/fig4_release_timeline.png)

![One dot per model with the route each model took to the answer](figures/fig4_release_timeline_0.3.0_only.png)

Figure 4b has one row per model, oldest at the top. Left of each dot is the number of solved runs out of all runs of that model (`3/6`). The Route column shows each route the model's runs took, with the number of runs after the mark (`✓ 3 ✗ 3` for gpt-4-turbo). The dot is green if all runs solved, a hollow red ring if all failed, and green with a red rim if some failed; rows with at least one failed run are shaded. The table version is [figures/fig4_release_timeline_0.3.0_only.md](figures/fig4_release_timeline_0.3.0_only.md). Marks: ✓ checker first (10 s or less of tool time before the checker said "correct answer"), → brute-force detour then checker (up to 120 s), ↷ late pivot to the checker, clock = working limit hit, ✗ wrong answer submitted.
