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

"""Offline unit checks for `mcp_tools` using a stub MCP server."""

import asyncio
import sys

import taskbridge


class _StubSession:
  mcp_servers = [{"name": "apps", "url": "http://127.0.0.1:8000/mcp/"}]
  workdir = "/workspace"

  def __init__(self):
    self.logged = []

  async def log(self, message):
    self.logged.append(message)


class _StubClient:
  VERSION = "2025-06-18"

  def __init__(self, session, url, **kwargs):
    self.session, self.url = session, url
    self.calls = []

  async def rpc(self, method, params=None, notify=False):
    self.calls.append((method, params))
    if method == "tools/list":
      return {
          "tools": [
              {
                  "name": "sheet.read",
                  "description": "Read a range from a workbook.",
                  "inputSchema": {
                      "type": "object",
                      "properties": {"path": {"type": "string"}},
                      "required": ["path"],
                  },
              },
              {
                  "name": "doc.write",
                  "description": "Write a document.",
                  "inputSchema": {"type": "object", "properties": {}},
              },
          ]
      }
    if method == "tools/call":
      return {"content": [{"type": "text", "text": "A1: 42"}]}
    return {}


def main():
  original = taskbridge.MCPClient
  taskbridge.MCPClient = _StubClient
  try:
    import mcp_tools

    session = _StubSession()
    registry = asyncio.run(mcp_tools.discover(session))

    assert registry.servers == ["apps(2)"], registry.servers
    names = [d["function"]["name"] for d in registry.defs]
    assert names == ["mcp__apps__sheet_read", "mcp__apps__doc_write"], names
    # the dot in the remote name is sanitized in the function name but kept in
    # the route
    client, remote = registry.routes["mcp__apps__sheet_read"]
    assert remote == "sheet.read", remote

    out = asyncio.run(registry.call("mcp__apps__sheet_read", {"path": "a.xlsx"}))
    assert out == "A1: 42", out
    assert client.calls[-1][0] == "tools/call"

    # unknown tool name falls through to the bash/read_file/write_file branch
    print("PASS mcp_tools")
  finally:
    taskbridge.MCPClient = original


if __name__ == "__main__":
  sys.exit(main())
