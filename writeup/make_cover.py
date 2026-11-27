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

"""Draws the write-up's cover image (Kaggle Media Gallery).

The cover states the entry's one-line claim and the two numbers a reader needs:
how the harness is built and what it scored on the dev set. Numbers come from
`artifacts/manifest.json` when present; without it the cover shows the design
facts only, so it can be regenerated at any time without inventing results.

Usage:
  python make_cover.py [--root .] [--out figs/cover.png]
"""

import argparse
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

INK = "#14213d"
ACCENT = "#1f5fa8"
MUTED = "#6b7280"


def dev_numbers(root):
  """Returns (scored, total, mean_reward) from the committed artifacts."""
  manifest = pathlib.Path(root) / "artifacts" / "manifest.json"
  if not manifest.exists():
    return None
  try:
    data = json.loads(manifest.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None
  tasks = data.get("tasks") or {}
  if not tasks:
    return None
  scored = sum(1 for t in tasks.values() if float(t.get("reward") or 0) > 0)
  total = len(tasks)
  mean = sum(float(t.get("reward") or 0) for t in tasks.values()) / max(1, total)
  return scored, total, mean


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", default=".")
  ap.add_argument("--out", default="writeup/figs/cover.png")
  args = ap.parse_args()
  out = pathlib.Path(args.out)
  out.parent.mkdir(parents=True, exist_ok=True)

  fig, ax = plt.subplots(figsize=(12, 6.4), dpi=200)
  ax.set_axis_off()
  ax.set_xlim(0, 12)
  ax.set_ylim(0, 6.4)

  ax.add_patch(FancyBboxPatch((0.35, 0.35), 11.3, 5.7,
                              boxstyle="round,pad=0.02,rounding_size=0.25",
                              linewidth=0, facecolor="#f7f9fc"))

  ax.text(0.9, 5.30, "plan-verify-mcp", fontsize=28, color=INK, weight="bold", va="center")
  ax.text(0.9, 4.80, "a planner / worker / verifier harness that drives the project's own tools",
          fontsize=11.5, color=ACCENT, va="center")
  ax.text(0.9, 4.05,
          "Discovers every MCP server a PLE task serves (spreadsheets, documents, mail, CAD),\n"
          "hands those tools to the worker and a read-only subset to the checker, and gives\n"
          "the verifier a deterministic inventory of every file the run wrote.",
          fontsize=9.2, color=INK, linespacing=1.6, va="top")

  boxes = [
      ("1  discover", "mcp_servers -> initialize\n-> tools/list\n-> mcp__<server>__<tool>"),
      ("2  plan", "deliverables,\nmethod,\nchecks"),
      ("3  work", "bash + files +\nevery MCP tool"),
      ("4  verify", "PASS | gaps\n-> fix rounds"),
  ]
  x, width, gap = 0.9, 2.55, 0.15
  for title, body in boxes:
    ax.add_patch(FancyBboxPatch((x, 1.35), width, 1.5,
                                boxstyle="round,pad=0.03,rounding_size=0.12",
                                linewidth=1.1, edgecolor=ACCENT, facecolor="white"))
    ax.text(x + width / 2, 2.50, title, ha="center", va="center", fontsize=9.5,
            color=ACCENT, weight="bold")
    ax.text(x + width / 2, 1.92, body, ha="center", va="center", fontsize=6.8,
            color=MUTED, linespacing=1.45)
    x += width + gap

  nums = dev_numbers(args.root)
  if nums:
    scored, total, mean = nums
    ax.text(0.9, 0.80, f"dev set: {scored}/{total} tasks scored, mean reward {mean:.3f}",
            fontsize=10, color=INK)
  else:
    ax.text(0.9, 0.80, "dev-set artifacts pending: entry files complete, kit check clean",
            fontsize=10, color=MUTED)

  fig.savefig(out, bbox_inches="tight", facecolor="white")
  plt.close(fig)
  print("wrote", out)


if __name__ == "__main__":
  main()
