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

"""Pre-flight check of an entry's layout, runnable without Docker.

`kit check` needs a Linux host with Docker. This script checks the parts that
are pure file work — the fields `submission.yaml` must carry, the license, the
presence and shape of `artifacts/manifest.json`, and that every harness file the
manifest names still exists — so the remaining failures are the ones only the
kit can find.

Usage: python submit_check.py [--root .]
"""

import argparse
import collections
import json
import pathlib
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}$")
REQUIRED = ("name", "model_api", "serve")
LICENSES = ("Apache License", "MIT License")


def parse_yaml_lite(text):
  """Parses the flat `key: value` subset `submission.yaml` uses.

  Args:
    text: File contents.

  Returns:
    A dict of top-level keys to strings (nested blocks are kept as text).
  """
  out, key = {}, None
  for raw in text.splitlines():
    line = raw.rstrip()
    if not line or line.lstrip().startswith("#"):
      continue
    m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
    if m:
      key, value = m.group(1), m.group(2).strip()
      out[key] = value
    elif key and line.startswith((" ", "\t")):
      out[key] = (out.get(key, "") + " " + line.strip()).strip()
  return out


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", default=".")
  args = ap.parse_args()
  root = pathlib.Path(args.root).resolve()

  errors, notes = [], []

  yaml_path = root / "submission.yaml"
  if not yaml_path.exists():
    errors.append("submission.yaml is missing")
    meta = {}
  else:
    meta = parse_yaml_lite(yaml_path.read_text(encoding="utf-8"))
    for key in REQUIRED:
      if not meta.get(key):
        errors.append(f"submission.yaml has no `{key}`")
    name = meta.get("name", "")
    if name and not NAME_RE.match(name):
      errors.append(f"name `{name}` must be 2-39 chars of a-z, 0-9, '-'")
    api = meta.get("model_api", "")
    if api and not api.startswith("google-cloud/"):
      errors.append(f"model_api `{api}` is not one of the google-cloud models")

  serve = meta.get("serve", "")
  if serve:
    first = serve.split()[0] if serve.split() else ""
    script = [tok for tok in serve.split() if tok.endswith(".py")]
    if script and not (root / pathlib.Path(script[-1]).name).exists():
      errors.append(f"serve names {script[-1]}, which is not in the entry")

  license_text = ""
  for candidate in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
    p = root / candidate
    if p.exists():
      license_text = p.read_text(encoding="utf-8", errors="replace")[:4000]
      break
  if not any(tag in license_text for tag in LICENSES):
    errors.append("no LICENSE file with an Apache-2.0 or MIT text")

  manifest_path = root / "artifacts" / "manifest.json"
  if not manifest_path.exists():
    errors.append("artifacts/manifest.json is missing (run eval/run.py)")
  else:
    try:
      manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
      errors.append(f"artifacts/manifest.json does not parse: {exc}")
      manifest = {}
    tasks = manifest.get("tasks") or {}
    if not tasks:
      errors.append("manifest lists no tasks")
    status = collections.Counter(t.get("ended") or "?" for t in tasks.values())
    notes.append(f"tasks in manifest: {len(tasks)} ({dict(status)})")
    missing = [name for name in (manifest.get("harness", {}).get("files") or {})
               if not (root / name).exists()]
    if missing:
      errors.append(f"manifest names {len(missing)} harness file(s) that are gone"
                    f": {', '.join(missing[:5])}")
    scored = sum(1 for t in tasks.values() if float(t.get("reward") or 0) > 0)
    notes.append(f"tasks with reward > 0: {scored}")

  size = sum(p.stat().st_size for p in (root / "artifacts").rglob("*")
             if p.is_file()) if (root / "artifacts").exists() else 0
  notes.append(f"artifacts size: {size / 1024 / 1024:.1f} MiB (limit 512)")

  for note in notes:
    print("note:", note)
  if errors:
    print(f"NOT READY — {len(errors)} problem(s):")
    for err in errors:
      print("  ✗", err)
    return 1
  print("READY (file layout); run `uv run python -m kit check` next")
  return 0


if __name__ == "__main__":
  sys.exit(main())
