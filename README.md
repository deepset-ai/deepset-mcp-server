# Local MCP Server for deepset platform

It provides tools that can list pipelines, fetch YAML, fetch component schemas, validate YAML, and update YAML.


## Usage
To use it with Claude Desktop app, use the following config:

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
        "deepset/deepset-mcp-server:main"
      ],
      "env": {
       "DEEPSET_WORKSPACE":"<WORKSPACE>",
       "DEEPSET_API_KEY":"<API_KEY>"
     }

    }
  }
}
```


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


