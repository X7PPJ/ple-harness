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

"""Prepares the committed entry: declares a google-cloud model and checks it.

The dev artifacts are produced locally on a model of our own (documented in the
write-up). The rules accept that as long as the committed `submission.yaml`
declares one of the Google-sponsored `google-cloud/<id>` models, so this script
does the switch and then runs the parts of the pre-flight check that do not need
Docker.

Usage:
  python scripts/finalize_submission.py [--model google-cloud/claude-opus-5-5]
"""

import argparse
import pathlib
import re
import subprocess
import sys

MODELS = (
    "google-cloud/claude-opus-5-5",
    "google-cloud/gemini-3.8-flash",
    "google-cloud/gemini-3.8-pro",
)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--root", default=".")
  ap.add_argument("--model", default=MODELS[0], choices=MODELS)
  args = ap.parse_args()
  root = pathlib.Path(args.root).resolve()
  yaml_path = root / "submission.yaml"

  text = yaml_path.read_text(encoding="utf-8")
  if "model_api:" not in text:
    print("submission.yaml has no model_api line")
    return 1
  text = re.sub(r"(?m)^model_api:.*$", f"model_api: {args.model}", text)
  # a model_base_url only makes sense for openai-compatible entries
  text = re.sub(r"(?m)^model_base_url:.*\n?", "", text)
  yaml_path.write_text(text, encoding="utf-8", newline="\n")
  print("model_api ->", args.model)

  check = root / "submit_check.py"
  if check.exists():
    proc = subprocess.run([sys.executable, str(check), "--root", str(root)],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    print((proc.stdout or "").strip()[-1200:])
    if proc.returncode != 0:
      return proc.returncode

  print("\nnext: uv run python -m kit check .   (needs Linux + Docker)")
  return 0


if __name__ == "__main__":
  sys.exit(main())
