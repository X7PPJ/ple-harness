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

"""Fetches the dev-set artifacts of a GitHub Actions run into the entry.

The workflow uploads `harness/artifacts` and `ple/runs` as one artifact zip.
This script finds the newest successful run (or the run id given), downloads
that zip, unpacks the artifacts into `harness/artifacts/` and the run output
into `runs/`, then prints what arrived.

Usage:
  python scripts/fetch_artifacts.py --repo X7PPJ/ple-harness --root ..
"""

import argparse
import io
import json
import pathlib
import subprocess
import sys
import zipfile


def api(token, url, method="GET", payload=None, binary=False):
  cmd = ["curl", "-sS", "-X", method, url,
         "-H", f"Authorization: Bearer {token}",
         "-H", "Accept: application/vnd.github+json",
         "-H", "X-GitHub-Api-Version: 2022-11-28",
         "-H", "User-Agent: dsh-ple"]
  if payload is not None:
      cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(payload)]
  if binary:
      cmd += ["-L", "-o", "-"]
  out = subprocess.run(cmd, capture_output=True, timeout=600)
  if binary:
      return out.stdout
  return json.loads(out.stdout.decode("utf-8", "replace") or "{}")


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--repo", default="X7PPJ/ple-harness")
  ap.add_argument("--token-file", default=r"E:\kaggledeepseek\ple\.gh_token")
  ap.add_argument("--root", default=".", help="entry root (holds artifacts/ and runs/)")
  ap.add_argument("--run-id", type=int, default=None)
  ap.add_argument("--workflow", default="dev-run.yml")
  args = ap.parse_args()

  token = pathlib.Path(args.token_file).read_text(encoding="utf-8").strip()
  root = pathlib.Path(args.root).resolve()

  run_id = args.run_id
  if run_id is None:
    runs = api(token, f"https://api.github.com/repos/{args.repo}/actions/runs?per_page=30")
    for run in runs.get("workflow_runs", []):
      if run["path"].endswith(args.workflow) and run["conclusion"] == "success":
        run_id = run["id"]
        break
    if run_id is None:
      print("no successful run of", args.workflow)
      return 1
  print("run:", run_id)

  arts = api(token, f"https://api.github.com/repos/{args.repo}/actions/runs/{run_id}/artifacts")
  names = [a["name"] for a in arts.get("artifacts", [])]
  print("artifacts:", names)
  if not names:
    return 1
  art = arts["artifacts"][0]
  blob = api(token, art["archive_download_url"], binary=True)
  if not blob[:2] == b"PK":
    print("download failed:", blob[:120])
    return 1
  with zipfile.ZipFile(io.BytesIO(blob)) as zf:
    names = zf.namelist()
    print("zip entries:", len(names))
    out_art = root / "artifacts"
    out_runs = root / "runs"
    for name in names:
      if name.startswith("harness/artifacts/"):
        target = out_art / name[len("harness/artifacts/"):]
      elif name.startswith("ple/runs/"):
        target = out_runs / name[len("ple/runs/"):]
      else:
        continue
      if name.endswith("/"):
        target.mkdir(parents=True, exist_ok=True)
        continue
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_bytes(zf.read(name))
  manifest = out_art / "manifest.json"
  if manifest.exists():
    data = json.loads(manifest.read_text(encoding="utf-8"))
    tasks = data.get("tasks") or {}
    print("manifest tasks:", len(tasks),
          "| mean reward:",
          round(sum(float(t.get("reward") or 0) for t in tasks.values()) / max(1, len(tasks)), 4))
  else:
    print("no manifest.json in the artifact")
  return 0


if __name__ == "__main__":
  sys.exit(main())
