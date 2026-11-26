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

"""Discovers and calls the task's MCP servers (documents, spreadsheets, CAD).

The starter harnesses only expose `bash`, `read_file`, and `write_file`, so the
agent never touches the project applications a task serves over MCP. This
module turns every MCP tool into an ordinary OpenAI function tool named
`mcp__<server>__<tool>` and routes its calls back through `taskbridge`.
"""

import json
import re

import taskbridge

PREFIX = "mcp__"
MAX_TOOLS = 48  # keep the tool list small enough for long tasks
# A verifier must not change the project, so it only sees tools that look like
# readers. The heuristic is name-based because MCP schemas do not say whether a
# tool writes.
WRITE_WORDS = re.compile(
    r"write|create|update|delete|remove|set_|_set|put|post|insert|append|edit"
    r"|send|move|rename|add|upload|apply|commit|run|exec",
    re.I,
)
READ_WORDS = re.compile(
    r"get|list|read|search|query|find|describe|view|show|fetch|lookup|open"
    r"|inspect|resolve|calc|compute|check|validate",
    re.I,
)


def _sanitize(text):
  """Maps arbitrary server/tool names onto function-name characters."""
  return "".join(c if c.isalnum() or c in "_-" else "_" for c in str(text))


class Registry:
  """OpenAI tool definitions plus the client each one calls."""

  def __init__(self):
    self.defs = []
    self.readonly_defs = []
    self.routes = {}
    self.servers = []
    self.notes = []

  async def call(self, name, arguments):
    """Runs one MCP tool call and returns its output as text.

    Args:
      name: Function name exposed to the model.
      arguments: Parsed JSON arguments object.

    Returns:
      The tool output (JSON text) or an error string.
    """
    client, remote = self.routes[name]
    try:
      result = await client.rpc(
          "tools/call", {"name": remote, "arguments": arguments or {}}
      )
    except (taskbridge.TaskError, taskbridge.MCPError) as exc:
      return f"error: {type(exc).__name__}: {exc}"
    parts = []
    for block in (result or {}).get("content", []) or []:
      if block.get("type") == "text":
        parts.append(block.get("text", ""))
      else:
        parts.append(json.dumps(block)[:2000])
    if (result or {}).get("isError"):
      return "error: " + ("\n".join(parts) or "tool reported an error")
    return "\n".join(parts) or "(no output)"


async def discover(session):
  """Builds a `Registry` from `session.mcp_servers`.

  Args:
    session: Active `taskbridge.Session` for the task.

  Returns:
    A `Registry` (empty when the task serves no MCP servers).
  """
  registry = Registry()
  for server in getattr(session, "mcp_servers", None) or []:
    label = _sanitize(server.get("name") or f"mcp{len(registry.servers) + 1}")
    url = server.get("url")
    if not url:
      continue
    client = taskbridge.MCPClient(session, url)
    try:
      await client.rpc(
          "initialize",
          {
              "protocolVersion": taskbridge.MCPClient.VERSION,
              "capabilities": {},
              "clientInfo": {"name": "ple-mcp-harness", "version": "1.0"},
          },
      )
      await client.rpc("notifications/initialized", notify=True)
      listing = await client.rpc("tools/list", {})
    except (taskbridge.TaskError, taskbridge.MCPError) as exc:
      registry.notes.append(f"{label}: unavailable ({type(exc).__name__})")
      continue
    tools = (listing or {}).get("tools", []) or []
    registry.servers.append(f"{label}({len(tools)})")
    for spec in tools:
      if len(registry.defs) >= MAX_TOOLS:
        break
      remote = spec.get("name")
      if not remote:
        continue
      name = f"{PREFIX}{label}__{_sanitize(remote)}"
      schema = spec.get("inputSchema") or {"type": "object", "properties": {}}
      if schema.get("type") != "object":
        schema = {"type": "object", "properties": {}}
      definition = {
          "type": "function",
          "function": {
              "name": name,
              "description": (spec.get("description") or remote)[:900],
              "parameters": schema,
          },
      }
      registry.defs.append(definition)
      if READ_WORDS.search(remote) and not WRITE_WORDS.search(remote):
        registry.readonly_defs.append(definition)
      registry.routes[name] = (client, remote)
  return registry
