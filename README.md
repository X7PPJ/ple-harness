# plan-verify-mcp: a planner/worker/verifier harness that actually uses the task's MCP servers

An entry for [Physical-Engineering's Last Exam](https://www.kaggle.com/competitions/physical-engineerings-last-exam)
built on the official `plan-verify` starter. The change that matters: the
harness **discovers the task's MCP servers at start-up and exposes every one of
their tools to the model**, so the agent can drive the project's spreadsheet,
document, email and CAD applications instead of only running shell commands.

The stock starters ship `bash`, `read_file` and `write_file` only; `kit check`
prints an `mcp` warning for them because the agent never opens the applications
that a task serves. This entry closes that gap.

## What it does per task

1. **Discover** (`mcp_tools.discover`): for every `mcp_servers` entry in the task
   message, open a Streamable-HTTP JSON-RPC client through
   `taskbridge.MCPClient`, send `initialize` and `tools/list`, and turn each
   remote tool into an OpenAI function tool named `mcp__<server>__<tool>`.
   Names are sanitized to function-name characters; the original remote name is
   kept for the call.
2. **Plan**: the planner explores the project with `bash` and `read_file` and
   writes a deliverable-by-deliverable plan.
3. **Work**: the worker runs with `bash`, `read_file`, `write_file` **and every
   MCP tool**, so it can read the workbook it must fill, write the document it
   must deliver, or query the CAD model. The planner and the verifier get only
   the MCP tools whose names read like readers (`get/list/read/query/...`) and
   not like writers, so verification cannot modify the project.
4. **Verify**: a fresh-context verifier receives the task, the plan, the
   worker's summary **and a deterministic inventory** of every file created or
   changed since the task started (path, size, and a cheap empty/invalid-JSON
   flag), so it starts from what exists instead of exploring. It replies `PASS`
   or a numbered list of gaps; up to two fix rounds go back to the worker while
   time remains.

Time budgeting is inherited from `plan-verify`: the planner gets 10% of the
task clock, the worker wraps up with 25% left, and verification/fix rounds use
what remains, with a 4-minute wrap-up per step.

## Files

| File | Purpose |
|---|---|
| `serve.py` | Planner/worker/verifier loop, time budgeting, MCP wiring |
| `mcp_tools.py` | MCP discovery, tool-definition synthesis, call routing |
| `deliverable_check.py` | Deterministic inventory of files written, fed to the verifier |
| `taskbridge.py` | Serve protocol implementation (from the official kit) |
| `test_mcp_tools.py` | Offline unit test of discovery and routing (stub server) |
| `requirements.txt` | Pinned `openai` and `websockets` |
| `submission.yaml` | Model declaration, build command, server start-up |
| `artifacts/` | Dev-set run of this harness (`eval/run.py` output) |

## Local checks

```bash
python test_mcp_tools.py          # offline: discovery + routing
uv run python -m kit check ../harness
uv run python eval/run.py ../harness
```

## How `artifacts/` was produced

`artifacts/` is the output of one `eval/run.py` dev run, not hand-written and
never read by the harness. Because the development machine had no Docker, that
run happened on a GitHub-hosted Ubuntu runner
(`.github/workflows/dev-run.yml`), which reproduces the two commands above and
adds three environment fixes the runner needs: it deletes preinstalled
toolchains to free disk, adds swap, and passes keys through repository secrets
so the entry itself holds none.

Two facts about that run matter when reading the numbers:

- **Model.** The dev run used a model of our own,
  `openai-compatible/deepseek-chat`, because the sponsored models are only
  reachable from the organizer's rerun. `submission.yaml` in this repository
  therefore declares `google-cloud/claude-opus-5-5`, the model the rerun will
  use; the switch is allowed as long as it is disclosed, which the write-up
  does in §3 and §5. To reproduce the dev numbers yourself, put your own model
  back in `submission.yaml` (`model_api:` + `model_base_url:`) and pass the key
  in `MODEL_API_KEY`.
- **Coverage.** 5 of the 29 dev tasks produced artifacts. 12 more were attempted
  and never started — the kit reported `evaluator: RuntimeError` with 0 s and 0
  tokens, i.e. the task container never came up on the runner — and the 12
  heaviest task images were not attempted there. Longer jobs on the same runner
  were killed about an hour in (`exit code 143`, "runner has received a
  shutdown signal"), so the dev set has to be run in small batches; that is a
  property of the free CI runner, not of the harness. A task without artifacts
  scores 0, so treat the per-task numbers in `artifacts/manifest.json` as "what
  the harness did on the tasks it got to start", not as a dev score.

## Cost controls

Three environment variables bound a task, because the first dev run showed a
task can spend a hundred million tokens re-reading files if nothing stops it:

| variable | default | effect |
|---|---|---|
| `PLE_TASK_BUDGET_SEC` | unset (task limit) | wall clock the harness may use inside the task |
| `PLE_MAX_STEPS` | 45 | tool rounds one agent step may take before it must wrap up |
| `PLE_TOKEN_BUDGET` | 12000000 | tokens one agent step may spend before it must wrap up |

A step that hits a cap takes the same wrap-up path the clock uses, so it still
writes its deliverable. `RESULT_CHARS` (12,000) bounds a single tool result,
since the history is resent on every round.

## License

Apache 2.0. `serve.py`, `taskbridge.py` and the role prompts are derived from
the PLE sample submissions, © 2026 Google LLC.
