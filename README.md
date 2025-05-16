# MCP Server for the deepset AI platform

The deepset MCP server exposes tools that MCP clients like Claude or Cursor can use to interact with the deepset AI platform.
Use these tools to develop pipelines, or to get information about components and how they are defined.




## Usage

### Claude Desktop App
Prerequisites:
- [Claude Desktop App](https://claude.ai/download) needs to be installed
- You need to be on the Claude Pro, Team, Max, or Enterprise plan
- You need an installation of [Docker](https://docs.docker.com/desktop/) (scroll down to step 4 if you want to use `uv` instead of Docker)

1. Go to: `/Users/your_user/Library/Application Support/Claude` (Mac)
2. Either open or create `claude_desktop_config.json`
3. Add the following json as your config (or update your existing config if you are already using other MCP servers)

```json
{
  "mcpServers": {
    "deepset": {
      "command": "/usr/local/bin/docker",
      "args": [
        "run",
        "-i",
        "-e",
        "DEEPSET_WORKSPACE",
        "-e",
        "DEEPSET_API_KEY",
        "deepset/deepset-mcp-server"
      ],
      "env": {
       "DEEPSET_WORKSPACE":"<WORKSPACE>",
       "DEEPSET_API_KEY":"<API_KEY>"
     }

    }
  }
}
```

4. (Optional) Use the following config if you want to use `uv` instead of docker


## Further improvements ideas

- remove hardcoded workspace
- fix the tool description for fetching pipeline (it’s relying on id instead of names)
- expose standard prompts via MCP e.g., for debugging, fixing pipelines, reading logs etc
- fix the docker run command to clear cache
- the ability to dump the conversation of improving the copilot
- test with different models not just Claude Sonnet 3.7
- test with different clients other than Claude Desktop app


## Todo

### Haystack Knowledge
- list_component_families
- get_component_family
- get_component_definition


