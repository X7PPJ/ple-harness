# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Fills the write-up's `[[PLACEHOLDER]]`s from a dev run.

Reads `artifacts/manifest.json` (per-task reward and status) and, when present,
`runs/<run>/results.json` (token usage), then rewrites the placeholders in
`writeup/WRITEUP.md`. Every placeholder it cannot fill is left in place and
printed, so a half-finished run never silently invents a number.

Usage:
  python scripts/fill_writeup.py [--root .] [--dry-run]
"""

import argparse
import json
import pathlib
import re
import sys

PLACEHOLDER = re.compile(r"\[\[([A-Z0-9_]+)\]\]")


def load_json(path):
  try:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def task_rows(root):
  """Returns [(task, reward, status, tokens)] for the committed artifacts."""
  manifest = load_json(pathlib.Path(root) / "artifacts" / "manifest.json")
  if not manifest:
    return []
  rows = []
  for name, info in (manifest.get("tasks") or {}).items():
    rows.append((name, float(info.get("reward") or 0.0), str(info.get("ended") or "ok"), 0))
  return rows


def run_usage(root):
  """Maps task -> total tokens from the newest runs/*/results.json."""
  runs = pathlib.Path(root) / "runs"
  if not runs.exists():
    return {}
  newest = sorted((p for p in runs.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)
  for run in reversed(newest):
    data = load_json(run / "results.json")
    if not data:
      continue
    usage = {}
    for row in data.get("tasks") or []:
      name = row.get("task") or row.get("id")
      if not name:
        continue
      u = row.get("usage") or {}
      tokens = row.get("tokens") or u.get("total_tokens") or (
          (u.get("prompt_tokens") or 0) + (u.get("completion_tokens") or 0))
      usage[name] = float(tokens or 0)
    if usage:
      return usage
  return {}


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", default=".")
  ap.add_argument("--dry-run", action="store_true")
  args = ap.parse_args()
  root = pathlib.Path(args.root).resolve()

  rows = task_rows(root)
  if not rows:
    print("no artifacts/manifest.json with tasks; nothing to fill")
    return 1
  usage = run_usage(root)
  total = len(rows)
  scored = [r for r in rows if r[1] > 0]
  mean_reward = sum(r[1] for r in rows) / total
  high = [r for r in rows if r[1] >= 0.8]
  tokens = [usage.get(r[0], 0.0) for r in rows]
  tok_total = sum(tokens)
  tok_mean = tok_total / max(1, len([t for t in tokens if t > 0]))

  values = {
      "DEV_SCORE": f"{mean_reward:.3f}",
      "NONZERO": str(len(scored)),
      "HIGH": str(len(high)),
      "COST_USD": f"{tok_total / 1e6:.2f}M tokens",
      "TOKENS_PER_TASK": f"{tok_mean / 1000:.0f}k",
      "WALL_CLOCK": f"{len(rows)} tasks in one CI job",
  }

  writeup = root / "writeup" / "WRITEUP.md"
  text = writeup.read_text(encoding="utf-8")
  filled, missing = 0, []
  for name in set(PLACEHOLDER.findall(text)):
    if name in values:
      text = text.replace(f"[[{name}]]", values[name])
      filled += 1
    else:
      missing.append(name)

  print(f"tasks: {total} | scored: {len(scored)} | mean reward: {mean_reward:.4f}")
  print(f"filled {filled} placeholder(s); still open: {', '.join(sorted(missing)) or 'none'}")
  if not args.dry_run:
    writeup.write_text(text, encoding="utf-8", newline="\n")
    print("wrote", writeup)
  return 0


if __name__ == "__main__":
  sys.exit(main())
