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

"""Builds the three required write-up figures from a dev-set run.

Figure 1 is drawn from constants (the harness architecture). Figures 2 and 3
read `runs/<run>/results.json` (per-task reward, status and token usage) and
`artifacts/manifest.json` when present. Everything is plain matplotlib so the
figures can be regenerated offline.

Usage:
  python make_figures.py --run runs/plan-verify-mcp-20261201-120000 --out figs
"""

import argparse
import json
import pathlib
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

INK = "#1b1b1b"
ACCENT = "#1f5fa8"
MUTED = "#8a8a8a"
WARN = "#b3651f"


def _read(path):
  p = pathlib.Path(path)
  if not p.exists():
    return None
  try:
    return json.loads(p.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def disciplines(root):
  """Maps task id -> discipline, parsed from eval/README.md's dev-set table."""
  table = pathlib.Path(root) / "eval" / "README.md"
  mapping = {}
  if not table.exists():
    return mapping
  for line in table.read_text(encoding="utf-8").splitlines():
    m = re.match(r"\|\s*`([a-z0-9-]+)`\s*\|\s*([A-Za-z ]+?)\s*\|", line)
    if m:
      mapping[m.group(1)] = m.group(2).strip()
  return mapping


def _as_tokens(value):
  """A run may record tokens as a number or as a per-kind dict."""
  if isinstance(value, dict):
    return sum(float(v or 0.0) for v in value.values())
  return float(value or 0.0)


def tasks_from_run(run_dir):
  """Returns {task: {"reward", "status", "tokens"}} from a run directory."""
  data = _read(pathlib.Path(run_dir) / "results.json")
  if not data:
    return {}
  out = {}
  rows = data.get("tasks") or data.get("results") or []
  if isinstance(rows, dict):
    rows = [{"task": k, **(v if isinstance(v, dict) else {"reward": v})}
            for k, v in rows.items()]
  for row in rows:
    name = row.get("task") or row.get("id") or row.get("name")
    if not name:
      continue
    usage = row.get("usage") or {}
    tokens = row.get("tokens") or usage.get("total_tokens") or (
        (usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0))
    out[name] = {
        "reward": float(row.get("reward") or row.get("score") or 0.0),
        "status": str(row.get("status") or row.get("ended") or "ok"),
        "tokens": _as_tokens(tokens),
    }
  return out


def tasks_from_manifest(root):
  """Falls back to artifacts/manifest.json when no run directory survives."""
  data = _read(pathlib.Path(root) / "artifacts" / "manifest.json")
  if not data:
    return {}
  return {
      name: {"reward": float(t.get("reward") or 0.0),
             "status": str(t.get("ended") or "ok"), "tokens": 0.0}
      for name, t in (data.get("tasks") or {}).items()
  }


def figure_architecture(out):
  fig, ax = plt.subplots(figsize=(11, 5.2), dpi=200)
  ax.set_axis_off()
  ax.set_xlim(0, 11)
  ax.set_ylim(0, 5.2)

  def box(x, y, w, h, text, color=INK, fill="#ffffff", fs=9.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                                linewidth=1.2, edgecolor=color, facecolor=fill))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=color, linespacing=1.35)

  def arrow(x1, y1, x2, y2, color=MUTED, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=12, linewidth=1.1, color=color,
                                 linestyle=ls, shrinkA=2, shrinkB=2))

  box(0.2, 3.1, 2.2, 1.2, "task prompt\n(project folder)", fs=9)
  ax.add_patch(FancyBboxPatch((2.7, 0.35), 5.6, 4.5, boxstyle="round,pad=0.08,rounding_size=0.15",
                              linewidth=1.6, edgecolor=ACCENT, facecolor="#f6f9fe"))
  ax.text(5.5, 4.62, "serve.py  (WebSocket harness)", ha="center", fontsize=11, color=ACCENT)
  steps = [
      ("1  discover\nmcp_servers → initialize → tools/list\n→ mcp__<server>__<tool>", 3.55),
      ("2  plan   planner: bash + read_file → deliverable plan", 2.55),
      ("3  work   worker: bash + files + every MCP tool", 1.55),
      ("4  verify  fresh-context verifier → PASS | numbered gaps", 0.55),
  ]
  for text, y in steps:
    box(3.0, y, 5.0, 0.78, text, fs=8.4)
  arrow(2.45, 3.7, 2.95, 3.9)
  for y1, y2 in ((3.5, 3.35), (2.5, 2.35), (1.5, 1.35)):
    arrow(5.5, y1, 5.5, y2)

  box(8.7, 3.0, 2.1, 1.1, "task container\n(no network)", fs=9)
  box(8.7, 1.1, 2.1, 1.1, "google-cloud/<model>\n(egress proxy)", fs=9)
  arrow(8.0, 3.9, 8.68, 3.7, color=ACCENT)
  arrow(8.0, 1.6, 8.68, 1.5, color=ACCENT)
  ax.text(8.62, 2.55, "MCP tools\n(sheets, docs,\nmail, CAD)", ha="center", fontsize=7.2,
          color=MUTED, linespacing=1.3)
  ax.text(0.2, 0.12, "Figure 1 — the entry: MCP discovery feeds the worker's tool list; "
                      "three roles never share context.", fontsize=8, color=MUTED)
  fig.savefig(out / "fig1_architecture.png", bbox_inches="tight", facecolor="white")
  plt.close(fig)


def _steps_from_artifacts(root):
  """Maps task -> agent steps, from the committed trajectories."""
  out = {}
  base = pathlib.Path(root) / "artifacts"
  if not base.exists():
    return out
  for task in base.iterdir():
    traj = task / "trajectory.json"
    if not traj.exists():
      continue
    data = _read(traj)
    metrics = (data or {}).get("final_metrics") or {}
    steps = metrics.get("total_steps") or len((data or {}).get("steps") or [])
    if steps:
      out[task.name] = float(steps)
  return out


def figure_score_cost(tasks, out, steps=None):
  """Reward against the two things a run actually spends: steps and tokens.

  The five measured tasks split cleanly by step count - the one that scored
  1.000 finished in 117 steps, the two zeros ran 397 and 393 - so the left
  panel plots the mechanism and the right one the bill. Tasks the evaluator
  could not grade are marked separately, so a "0" that is the environment's
  fault does not read as the harness's.
  """
  steps = steps or {}
  graded = [(t["tokens"], t["reward"], name) for name, t in tasks.items()
            if t["tokens"] > 0 and t["status"] == "ok"]
  ungraded = [(t["tokens"], t["reward"], name) for name, t in tasks.items()
              if t["tokens"] > 0 and t["status"] != "ok"]
  fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2), dpi=200)
  panels = (
      (axes[0], "agent steps on the task", "steps"),
      (axes[1], "tokens spent on the task (millions)", "tokens"),
  )
  for ax, label, key in panels:
    if key == "steps":
      gx = [(steps.get(name, 0.0), reward) for _, reward, name in graded]
      ux = [(steps.get(name, 0.0), reward) for _, reward, name in ungraded]
      gx = [p for p in gx if p[0] > 0]
      ux = [p for p in ux if p[0] > 0]
    else:
      gx = [(tokens / 1e6, reward) for tokens, reward, _ in graded]
      ux = [(tokens / 1e6, reward) for tokens, reward, _ in ungraded]
    if gx:
      ax.scatter([p[0] for p in gx], [p[1] for p in gx], s=46, color=ACCENT,
                 edgecolor="white", linewidth=0.7, zorder=3,
                 label=f"graded ({len(gx)})")
      for x, y in gx:
        if y <= 0:      # the two zeros sit on top of each other; the panels' x
          continue      # axis already separates them
        ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points",
                    xytext=(6, 5), fontsize=7, color=MUTED)
    if ux:
      ax.scatter([p[0] for p in ux], [p[1] for p in ux], s=46, color="#b0b7c3",
                 marker="s", edgecolor="white", linewidth=0.7, zorder=3,
                 label=f"grader failed ({len(ux)})")
    ax.set_xlabel(label, fontsize=9)
    ax.set_ylim(-0.06, 1.08)
    ax.set_ylabel("task reward (0-1)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.18, linewidth=0.6)
    ax.tick_params(labelsize=8)
    if gx or ux:
      ax.legend(frameon=False, fontsize=8, loc="best")
  fig.suptitle("Figure 2 - the zeros are long loops, not hard tasks: "
               "117 steps scored 1.000, 397 and 393 scored 0.000",
               fontsize=9.5, color=INK)
  fig.tight_layout(rect=(0, 0, 1, 0.94))
  fig.savefig(out / "fig2_score_cost.png", bbox_inches="tight", facecolor="white")
  plt.close(fig)


def figure_failures(tasks, out):
  cats = {"reward ≥ 0.8": 0, "0 < reward < 0.8": 0, "reward = 0": 0,
          "timeout": 0, "error": 0}
  for t in tasks.values():
    status = t["status"].lower()
    if "timeout" in status or "limit" in status:
      cats["timeout"] += 1
    elif status not in ("ok", "completed", "success", ""):
      cats["error"] += 1
    elif t["reward"] >= 0.8:
      cats["reward ≥ 0.8"] += 1
    elif t["reward"] > 0:
      cats["0 < reward < 0.8"] += 1
    else:
      cats["reward = 0"] += 1
  fig, ax = plt.subplots(figsize=(7.6, 4.2), dpi=200)
  names, values = list(cats), list(cats.values())
  colors = ["#2f7d4f", ACCENT, WARN, "#b03a2e", "#7d3c98"]
  bars = ax.bar(names, values, color=colors, width=0.62)
  for b, v in zip(bars, values):
    if v:
      ax.text(b.get_x() + b.get_width() / 2, v + 0.12, str(v), ha="center", fontsize=9, color=INK)
  ax.set_ylabel("tasks")
  ax.set_title("Figure 3 — dev-set failure breakdown", fontsize=10, color=INK)
  ax.spines[["top", "right"]].set_visible(False)
  ax.grid(axis="y", alpha=0.18, linewidth=0.6)
  fig.savefig(out / "fig3_failures.png", bbox_inches="tight", facecolor="white")
  plt.close(fig)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", default="../repo", help="PLE repo (for eval/README.md)")
  ap.add_argument("--run", default=None, help="runs/<run> directory")
  ap.add_argument("--artifacts", default=".", help="entry root holding artifacts/")
  ap.add_argument("--out", default="figs")
  args = ap.parse_args()

  out = pathlib.Path(args.out)
  out.mkdir(parents=True, exist_ok=True)
  tasks = tasks_from_run(args.run) if args.run else {}
  if not tasks:
    tasks = tasks_from_manifest(args.artifacts)
  print(f"tasks with data: {len(tasks)}")
  figure_architecture(out)
  figure_score_cost(tasks, out, _steps_from_artifacts(args.artifacts or args.root))
  figure_failures(tasks, out)
  print("wrote", *sorted(p.name for p in out.glob("fig*.png")))


if __name__ == "__main__":
  main()
