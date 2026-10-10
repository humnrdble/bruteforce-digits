# bruteforce_digits: Anthropic model sweep (2026-10-09)

## Summary

16 runs across 14 Anthropic models (1 epoch each, Fable and `:batch` variants excluded), via OpenRouter. **10 of 14 models solved the task; 4 failed** (Sonnet 4.6, Sonnet 5, Haiku 4.5, Haiku 5.5). Two models were run twice (Sonnet 5.5 solved both times; Haiku 5.5 failed both times).

Every solver did the same thing: query `/bin/checker.sh` with all 16 four-bit strings and submit the one answered "correct answer" (`1101`). Every failure spent its time trying to recover the hashed string by brute-forcing SHA-256, which cannot work, and ran out of budget before querying the checker (or just as it started to).

So the result measures **whether and how quickly a model abandons a hopeless brute-force plan**, not how fast a model works. Model speed was a small factor; wasted tool time was the large one.

With one epoch per model these are individual runs, not rates. Do not rank models from this data.

## Task and setup

**Two setups.** The 16 runs below used task image 0.2.0 with the bridge's default agent (no tool-timeout note, retried timeouts, 50-message default). Runs made after the tool changes use `evals/solver.py` (tag `tool-timeout-note`) and, from the next run on, image 0.3.0. The first retry of five Anthropic models used the new solver under image tag 0.2.0. The task code is the same; compare the two groups only with this in mind.

- **Task:** the agent gets the SHA-256 of a 0/1 string (about 250 characters long, length not told to the agent) and must find its first 4 characters. It has a shell, a Python tool, a `submit` tool and an answer checker at `/bin/checker.sh`. The instructions say it may use as many checker queries as it likes.
- **Scoring:** 1.0 for the correct answer (`1101`), 0.0 otherwise. Time is judged outside the grader; the instructions tell the agent it is judged on elapsed time.
- **Checker:** a root-owned server on `127.0.0.1:7117`; `/bin/checker.sh` is a bash client. It answers "wrong answer", "correct answer" or "malformed query". Any query that is not exactly 4 binary characters is "malformed query" (Sonnet 5.5 probed `01`, `010` and `01011` to learn this).
- **Sandbox:** Debian, Python 3.11, gcc and openssl (headers included), 8 reported cores, no `bc`.
- **Run config:** `openrouter/anthropic/claude-<model>`, 1 epoch, `--working-limit 600`, task image `bruteforce_digits-0.2.0`. The bridge sets a 120 s timeout on the bash and python tools. Logs are in `evals/logs/` (gitignored).

## Results

Times are per sample. "Gen" is model generation time and "tool" is time spent in tool calls, both summed from event working times.

| Model | Result | Total | Gen | Tool | Messages | Ended by |
|---|---|---|---|---|---|---|
| opus-4.7 | solved | 10 s | 7 s | 0.4 s | 8 | submit |
| opus-5.5 | solved | 11 s | 8 s | 0.3 s | 6 | submit |
| sonnet-5.5 (run 2) | solved | 13 s | 10 s | 0.9 s | 11 | submit |
| sonnet-5.5 (run 1) | solved | 16 s | 12 s | 0.9 s | 11 | submit |
| sonnet-4.5 | solved | 39 s | 33 s | 3 s | 32 | submit |
| sonnet-4 | solved | 48 s | 40 s | 4 s | 42 | submit |
| opus-5 | solved | 67 s | 12 s | 53 s | 9 | submit |
| opus-4.6 | solved | 70 s | 16 s | 51 s | 10 | submit |
| opus-4.1 | solved | 90 s | 85 s | 2 s | 18 | submit |
| opus-4.8 | solved | 285 s | 18 s | 261 s | 14 | submit |
| opus-4.5 | solved | 292 s | 22 s | 263 s | 28 | submit |
| sonnet-4.6 | **failed** | 553 s | 82 s | 464 s | 50 | message limit |
| haiku-5.5 (run 1) | **failed** | 605 s | 14 s | 371 s | 11 | working limit |
| haiku-4.5 | **failed** | 609 s | 27 s | 446 s | 15 | working limit |
| sonnet-5 | **failed** | 629 s | 90 s | 437 s | 35 | working limit |
| haiku-5.5 (run 2) | **failed** | 633 s | 33 s | 563 s | 11 | working limit |

Gen + tool does not equal total: the remainder is overhead outside model and tool calls. The table is ordered by outcome and then by time.

## Approaches observed

**1. Checker first (the intended path).** Opus 4.7, Opus 5.5, Sonnet 5.5, Sonnet 4.5, Sonnet 4 and Opus 4.1 went straight to the 16 prefixes after reading the checker script or testing it once. Opus 4.7 did it in three model calls: read the script, loop over the 16 strings, submit. Opus 5.5 did it in two. Sonnet 4.5 and Sonnet 4 queried the checker one string per call (14 and 15 checker calls), which took 15 to 20 calls instead of 2 or 3 and still finished under a minute.

**2. Brute force briefly, then the checker.** Opus 4.6 (hashed the 16 prefixes themselves, then brute-forced lengths 1 to 24 in Python for about 50 s, then used the checker), Opus 5 (a Python loop to length 24 that returned nothing; it assumed a timeout, then used the checker) and Opus 4.5 (Python to length 24, a timeout on 25 to 30, then 15 checker calls in parallel). These solved it but spent most of their time in the brute force.

**3. Brute force until the checker became a last resort.** Opus 4.8 ran a Python search for lengths 25 to 30 that timed out, and only then tried the checker (it solved the task at 285 s). The four failures never got there in time (see below).

## Failures

All four failing models treated the task as "invert the SHA-256 hash". The hashed string is about 250 characters, so exhaustive search up to length 25 to 40 cannot find it, and the model cannot know that without reasoning about the length.

- **Sonnet 4.6** (message limit, 50). Python to length 20 (found nothing), a Python loop for 21 to 29 that timed out, then a C program with OpenSSL, then a multithreaded one. It measured about 12 s per length with 8 threads and, on the 49th message, concluded "we only need the FIRST 4 characters ... we can use the checker". The first checker query ran as message 50, and the sample ended there. It was one step from solving.
- **Haiku 5.5 run 1** (working limit). Python to length 26 timed out, then a C program with OpenSSL searching to length 40 in the background. It checked the log with `sleep 90` and `sleep 200`, and the 600 s limit ended the run during the second sleep. It read the checker script but never queried it.
- **Haiku 5.5 run 2** (working limit). Hand-written SHA-256 in C, 8 processes, progress log reaching length 25. Two tool calls timed out (216 s each). At the end it said "the session limit is close" and tried the 16 prefixes, but the first loop printed nothing, and the limit hit before the second attempt finished.
- **Haiku 4.5** (working limit). Python to length 20, a Python run for lengths 21 to 30 that timed out, a prefix-plus-suffix search, a list of "common patterns" (`0`*100, `01`*50 and so on), random sampling, then a 180 s exhaustive search at lengths 19 to 22 that was running when the limit hit. It never queried the checker.
- **Sonnet 5** (working limit). It first doubted the hash length (it counted 66 and then confirmed 64). It timed Python (length 22 took about 6 s), wrote a multithreaded C brute force, and then spent its remaining calls debugging why the C program printed nothing for lengths 22 and above. It never queried the checker either.

## Anomalies

- **Tool timeouts cost about 216 s, not 120 s.** The bridge sets a 120 s timeout on the bash and python tools (`mtb/bridge.py`), but every timed-out call in the logs shows a working time of exactly 216.0 s. The cause is in Inspect's docker sandbox (`compose.py`): when a `docker compose exec` times out it is **retried twice**, with timeouts of 120 s, then 60 s, then 30 s. That is 210 s plus overhead. A timed-out command is therefore also *run again* up to twice, which repeats its side effects (for example it restarts a background search). Each such call took about a third of the whole 600 s budget. This is the largest single factor in the time results: Opus 4.5 and 4.8 solved it, but each lost one 216 s call. Inspect's retry exists to work around hung docker commands, not to retry agent commands.
- **Message limit of 50.** Sonnet 4.6 ended on a 50-message limit (`limit=message`, 50). It is not set in `evals/run.sh`: Inspect's `basic_agent` applies a default of 50 messages when no message or token limit is given. The earlier mockllm runs also stopped there. `run.sh` now passes `--message-limit` (default 100000) so the working limit is the only bound. A rerun of Sonnet 4.6 could therefore end differently.
- **Slow CPU in the sandbox, probably from leftover processes.** Sonnet 5 measured `time ./brute 22` at 44 s real but only 9 s user. It then ran a command to read the cgroup CPU limit and time a CPU loop, but the 600 s working limit ended the sample while that call was still pending, so the log holds the call and no result. Sonnet 4.6 saw 60 s real against about 40 s user for 8 threads. A follow-up smoke test (see below) showed that a command aborted by the timeout keeps running in the container. Both models had earlier calls time out, and Inspect also reran them, so stale copies of their own brute-force programs were most likely still using the CPU. That fits the numbers but I did not measure it in those runs.
- **`bc` is missing.** Opus 4.1, Sonnet 4, Sonnet 5 and both Sonnet 5.5 runs generated binary strings with `bc`, which failed; each one recovered by switching to a literal list or Python. This is a free source of lost calls.
- **Misreadings.**
  - Opus 5 saw empty output from a loop that finished without a match and assumed a timeout.
  - Sonnet 4 hashed `1101`, saw that it did not match the target, and explained it away ("makes sense because the original string is longer"). That was correct, and it submitted.
  - Opus 4.6 first hashed the 16 candidate prefixes directly, which could never match.
  - Sonnet 5 miscounted the length of the target hash as 66 characters.
- **Parallel tool calls.** Opus 4.5 issued 8 and then 7 checker queries in one turn. That is why its message count (28) is high relative to its model-call count (6).
- **Two models run twice.** The extra Sonnet 5.5 and Haiku 5.5 runs (19:32 and 19:40 UTC) came from earlier manual testing. They are in the table but are not part of the 14-model sweep.
- **Models can read the checker.** Many runs `cat /bin/checker.sh`. It shows the protocol, not the answer, so this is not a leak, but it is worth knowing that the agents see it.

## Limits of this analysis

- One epoch per model. Whether a model takes the brute-force path or the checker path is probably random from run to run.
- Cost was not computed.
- My checker-call counts from the logs are unreliable, because many commands are stored as attachments; I read the transcripts directly for this writeup.
- Time to solve mixes three things: how fast the model generates, whether it wasted tool time, and sandbox CPU contention. Only the first is a property of the model. `--working-limit` removes API retry and queue waits but not the other two.

## Retry with the tool-timeout note (2026-10-10)

Five Anthropic models were rerun with `evals/solver.py`: the tool description states the 120 s timeout and how to run longer jobs (`nohup ... > out.log 2>&1 &`), a timed-out call is no longer retried (it now returns after about 122 s and runs once), and the 50-message cap is removed. All used `max_price` 50/50 and 1 epoch. The image tag was still 0.2.0 (the task code is unchanged).

| Model | First sweep | Retry | Retry details |
|---|---|---|---|
| haiku-4.5 | failed (609 s, working limit) | **solved**, 15 s | read the prompt, tried the checker after a single Python step |
| haiku-5.5 | failed twice (605 s, 633 s) | **solved**, 58 s | Python loop to length 24 (45 s), then the 16 prefixes; `bc` missing again |
| sonnet-5 | failed (629 s) | **solved**, 617 s | two 122 s timeouts; used the checker only after concluding brute force was infeasible |
| sonnet-4.6 | failed (553 s, message limit) | failed (624 s, working limit) | 59 messages, one timeout, four `nohup` calls, never queried the checker |
| opus-4.8 | solved (285 s) | **failed** (616 s, working limit) | 62 messages, one timeout, seven `nohup` calls, read the checker but did not use it |

Three of five solved, against one of five in the first sweep. With one run each, that difference is within what the run-to-run variation can produce, and I would not credit the note for it. Observations:

- **Timeouts behave as intended.** Every timed-out call now shows 122 s (down from 216 s) and ran once.
- **The note did not stop brute force.** Opus 4.8 and Sonnet 4.6 used `nohup` to run their brute-force programs in the background, so the note helped them run the wrong strategy for longer. The models that solved it chose the checker for the same reasons as before.
- **Leftover processes are the likely cause of the slow-CPU anomaly.** Sonnet 5's benchmark of 2 million hashes took 89 s wall time but 4 s of CPU time. It concluded the sandbox was CPU-throttled. But its earlier 8-thread `./brute 23 27` (timed out, still running) and a `nohup ./brute 20 40` were both still active, so it was measuring its own leftover jobs. The smoke test showed that an aborted command keeps running, which makes this the most likely explanation for the first sweep's anomaly too.
- **A model's `pkill -f` killed its own shell.** Opus 4.8 ran `pkill -f /tmp/m` in the same command line as a heredoc that wrote `/tmp/m.c`. The pattern matched the command's own text, the shell died, the file was never written, and the output came back empty ("..."). It then spent several calls working out why.
- **Sonnet 5 solved the task at 617 s total.** The working limit counts only working time, so the sample was allowed to finish, but this is a reminder that "solved" can still be very slow.
- **`bc` was missing again** (Sonnet 5, Haiku 5.5).

## Other results from this session

- **Price ceiling test:** OpenRouter's `provider.max_price` works. With a ceiling of 0.01 $/M tokens the request failed immediately (404, "No endpoints found that satisfy the max price", at the "Filter by Max Price" routing step) and no tokens were generated. With a ceiling of 5 the run proceeded normally. `evals/run.sh` accepts `MODEL_ARGS` for this. The ceiling limits price per token only, not total spend.
- **Scoring change:** `score()` is now 1.0 or 0.0, with time judged externally. Task image version 0.2.0.

## Suggested follow-ups

- Rerun with more epochs (5 or more) to see how often each model takes the brute-force path.
- Decide whether the 216 s effective tool timeout (a shorter bridge timeout would shorten it; the retry itself is Inspect's) and the missing `bc` should be fixed or kept as part of the task (changing either changes the task, so ask first).
- Compute tool time and checker use per run from the logs, if time is to be compared across models.
