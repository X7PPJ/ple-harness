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

"""Deterministic deliverable inventory for the verification step.

The verifier is an LLM: it can miss a deliverable that was never written, and
reading a 40 MB workbook costs tokens. This module runs one small Python
program inside the task container that lists the files created or changed since
the task started, with their size and a cheap validity flag (empty file,
unreadable JSON). The inventory is handed to the verifier as facts, so it
starts from what exists instead of exploring.

The script is embedded here (and duplicated in `_probe.py` for the offline
test) so it can run with the container's own interpreter.
"""

import json
import os
import stat
import subprocess
import sys
import tempfile

MARKER = "/tmp/.ple_task_start"

PROBE = r'''
import json, os, sys
marker = sys.argv[1]
root = os.getcwd()
skip = {".git", "__pycache__", ".ipynb_checkpoints", "node_modules", ".venv"}
marker_mtime = os.path.getmtime(marker) if os.path.exists(marker) else None
rows = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in skip]
    for name in filenames:
        path = os.path.join(dirpath, name)
        try:
            st = os.stat(path)
        except OSError:
            continue
        if marker_mtime is not None and st.st_mtime < marker_mtime:
            continue
        ext = os.path.splitext(name)[1].lower()
        status = "empty" if st.st_size == 0 else "ok"
        if ext == ".json" and 0 < st.st_size < 5_000_000:
            try:
                json.load(open(path, encoding="utf-8", errors="replace"))
            except Exception:
                status = "invalid-json"
        rows.append({"path": os.path.relpath(path, root), "bytes": st.st_size,
                     "status": status})
rows.sort(key=lambda r: r["path"])
print(json.dumps({"files": rows[:400], "truncated": len(rows) > 400}))
'''


async def start(session):
  """Drops the start marker the inventory compares against."""
  try:
    await session.exec(f"touch {MARKER}")
  except Exception:  # noqa: BLE001 - a missing marker only widens the inventory
    pass


async def report(session, limit=40):
  """Returns a compact text inventory of deliverables, or "" when unavailable.

  Args:
    session: Active `taskbridge.Session` for the task.
    limit: Maximum number of files named in the text report.

  Returns:
    A newline-separated inventory suitable for a model message.
  """
  script = "python3 - <<'PROBE_EOF'\n" + PROBE + "\nPROBE_EOF"
  try:
    result = await session.exec(f"{script} {MARKER}")
  except Exception:  # noqa: BLE001 - the inventory is an optimization, not a gate
    return ""
  output = (result.get("output") or "").strip()
  line = output.splitlines()[-1] if output else ""
  try:
    data = json.loads(line)
  except (ValueError, IndexError):
    return ""
  files = data.get("files") or []
  if not files:
    return "No file was created or changed in the working directory."
  lines = [f"{len(files)} file(s) created or changed since the task started:"]
  for row in files[:limit]:
    flag = "" if row["status"] == "ok" else f"  [{row['status']}]"
    lines.append(f"- {row['path']} ({row['bytes']} bytes){flag}")
  if len(files) > limit:
    lines.append(f"- … and {len(files) - limit} more")
  if data.get("truncated"):
    lines.append("(inventory truncated at 400 files)")
  return "\n".join(lines)


def main():
  """Offline self-test: runs PROBE against a temporary directory."""
  import shutil

  origin = os.getcwd()
  tmp = tempfile.mkdtemp(prefix="ple-check-")
  try:
    os.chdir(tmp)
    marker = ".task_start"
    open("old.txt", "w").close()
    os.utime("old.txt", (1, 1))
    with open(marker, "w") as handle:
      handle.write("")
    with open("deliverable.json", "w") as handle:
      handle.write('{"ok": true}')
    with open("broken.json", "w") as handle:
      handle.write("{oops")
    with open("empty.csv", "w") as handle:
      handle.write("")
    proc = subprocess.run([sys.executable, "-c", PROBE, marker],
                          capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout)
    paths = {row["path"]: row["status"] for row in data["files"]}
    assert "old.txt" not in paths, paths
    assert paths.get("deliverable.json") == "ok", paths
    assert paths.get("broken.json") == "invalid-json", paths
    assert paths.get("empty.csv") == "empty", paths
  finally:
    os.chdir(origin)
    shutil.rmtree(tmp, ignore_errors=True)
  print("PASS deliverable_check")


if __name__ == "__main__":
  main()
