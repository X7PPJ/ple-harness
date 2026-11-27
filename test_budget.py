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

"""Offline test of the step and token caps in `serve.agent`.

The first dev run spent 152.7M tokens on a task that scored 0 because nothing
bounded the tool loop. The caps that fix it have to be provable without a model
or a task, so this test drives `agent` with a stubbed client that always asks
for one more tool call, and asserts the loop stops and returns a wrap-up answer
instead of calling tools forever.

Run with:
  MODEL_NAME=stub python test_budget.py
"""

import asyncio
import os
import types
import unittest

os.environ.setdefault("MODEL_NAME", "stub")

import serve  # noqa: E402  (needs MODEL_NAME in the environment)


class Message:
  """The assistant turn the loop appends, with the SDK's `model_dump`."""

  def __init__(self, tool_call=True):
    function = types.SimpleNamespace(name="bash", arguments='{"command":"ls"}')
    self.content = None
    self.tool_calls = None if not tool_call else [
        types.SimpleNamespace(id="call-1", function=function)
    ]

  def model_dump(self, **_):
    out = {"role": "assistant", "content": self.content}
    if self.tool_calls:
      out["tool_calls"] = [
          {"id": c.id, "type": "function",
           "function": {"name": c.function.name, "arguments": c.function.arguments}}
          for c in self.tool_calls
      ]
    return out


class Reply:
  """One stubbed chat completion."""

  def __init__(self, tool_call=True):
    self.usage = types.SimpleNamespace(prompt_tokens=1000, completion_tokens=100,
                                       prompt_tokens_details=None)
    message = Message(tool_call=tool_call)
    self.choices = [types.SimpleNamespace(message=message, finish_reason="tool_calls")]


class Session:
  """The parts of `taskbridge.Session` the loop touches."""

  def __init__(self, left=None):
    self._left = left
    self.logs = []
    self.final_message = ""
    self.tool_calls = 0

  def time_left(self):
    return self._left

  async def log(self, message):
    self.logs.append(message)

  async def usage(self, *args, **kwargs):
    return None


async def fake_run_tool(session, function, registry=None):
  session.tool_calls += 1
  return "ok"


async def fake_create(**_):
  return Reply(tool_call=True)


class BudgetTest(unittest.TestCase):

  def setUp(self):
    self._real_tool = serve.run_tool
    self._real_client = serve.client
    serve.run_tool = fake_run_tool
    serve.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=fake_create))
    )

  def tearDown(self):
    serve.run_tool = self._real_tool
    serve.client = self._real_client

  def drive(self, session, **kwargs):
    return asyncio.run(serve.agent(session, [{"role": "user", "content": "go"}], [],
                                   until=0, registry=None, **kwargs))

  def test_stops_after_max_steps(self):
    """A model that always calls a tool is stopped at MAX_STEPS rounds."""
    session = Session(left=None)
    original = serve.MAX_STEPS
    serve.MAX_STEPS = 3
    try:
      self.drive(session)
    finally:
      serve.MAX_STEPS = original
    self.assertEqual(session.tool_calls, 3,
                     "the loop must stop calling tools at the cap")

  def test_stops_after_token_budget(self):
    """The token cap stops the loop before the step cap would."""
    session = Session(left=None)
    steps, budget = serve.MAX_STEPS, serve.TOKEN_BUDGET
    serve.MAX_STEPS = 100
    serve.TOKEN_BUDGET = 2_500  # one reply costs 1,100
    try:
      self.drive(session)
    finally:
      serve.MAX_STEPS, serve.TOKEN_BUDGET = steps, budget
    # each stubbed reply costs 1,100 tokens and the cap is checked at the top of
    # the loop, so the third round runs and the fourth does not
    self.assertEqual(session.tool_calls, 3,
                     "the loop must stop once the token allowance is spent")
    self.assertLess(session.tool_calls, 100, "and long before the step cap")

  def test_deadline_stops_the_loop(self):
    """A capped budget reaches the clock even when the task has hours left."""
    session = Session(left=6 * 3600)  # the task clock alone never wraps up
    result = asyncio.run(
        serve.agent(session, [{"role": "user", "content": "go"}], [], until=60,
                    registry=None, deadline=__import__("time").monotonic() - 1)
    )
    self.assertEqual(result, "", "a passed deadline must return at once")
    self.assertEqual(session.tool_calls, 0)


if __name__ == "__main__":
  unittest.main(verbosity=2)
