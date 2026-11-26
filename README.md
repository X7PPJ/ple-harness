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
   must deliver, or query the CAD model.
4. **Verify**: a fresh-context verifier re-opens each deliverable and replies
   `PASS` or a numbered list of gaps; up to two fix rounds are fed back to the
   worker while time remains.

Time budgeting is inherited from `plan-verify`: the planner gets 10% of the
task clock, the worker wraps up with 25% left, and verification/fix rounds use
what remains, with a 4-minute wrap-up per step.

## Files

| File | Purpose |
|---|---|
| `serve.py` | Planner/worker/verifier loop, time budgeting, MCP wiring |
| `mcp_tools.py` | MCP discovery, tool-definition synthesis, call routing |
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

## License

Apache 2.0. `serve.py`, `taskbridge.py` and the role prompts are derived from
the PLE sample submissions, © 2026 Google LLC.
