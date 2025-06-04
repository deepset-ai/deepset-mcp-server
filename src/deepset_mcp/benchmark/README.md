# Benchmark System

The benchmark system evaluates how well AI agents perform on real-world deepset tasks. It runs agents against test cases that involve creating and modifying pipelines and indexes in deepset workspaces.

## Getting Started

### Prerequisites

Before running benchmarks, you need:

- **Environment variables**: `DEEPSET_WORKSPACE` and `DEEPSET_API_KEY` 
- **Agent configuration**: A YAML file defining your agent
- **Test cases**: YAML files describing the tasks to evaluate

### Quick Start

1. **Set up environment**:
   ```bash
   export DEEPSET_WORKSPACE="your-workspace" 
   export DEEPSET_API_KEY="your-api-key"
   ```

2. **Run a single test**:
   ```bash
   deepset agent run agent_configs/generalist_agent.yml chat_rag_answers_wrong_format
   ```

3. **Run all tests**:
   ```bash
   deepset agent run-all agent_configs/generalist_agent.yml
   ```

### Installation

Install with benchmark dependencies:
```bash
uv sync --extra benchmark
```

## Tutorials

### Creating Your First Agent Configuration

Agent configurations define how to load and run your AI agent:

```yaml
# agent_configs/my_agent.yml
agent_factory_function: "my_module.agents.get_agent"
display_name: "my-agent"
required_env_vars:
  - DEEPSET_API_KEY
  - DEEPSET_WORKSPACE
  - ANTHROPIC_API_KEY
```

### Writing a Test Case

Test cases define tasks for agents to complete:

```yaml
# tasks/my_test.yml
name: "my_test_case"
objective: "Fix a broken pipeline by adding missing components"
prompt: "Can you check why my RAG pipeline doesn't work?"
query_yaml: "pipelines/broken_rag.yml"
query_name: "test-pipeline"
index_yaml: "pipelines/standard_index.yml"
index_name: "test-index"
tags:
  - "debug"
  - "pipeline-fixes"
judge_prompt: |
  The agent successfully:
  - Identified the missing component
  - Added the correct component with proper configuration
  - Connected all inputs and outputs correctly
```

### Running Your First Benchmark

1. **Validate your agent config**:
   ```bash
   deepset agent validate-config agent_configs/my_agent.yml
   ```

2. **Check environment setup**:
   ```bash
   deepset agent check-env agent_configs/my_agent.yml
   ```

3. **List available test cases**:
   ```bash
   deepset test list
   ```

4. **Set up test resources**:
   ```bash
   deepset test setup my_test_case
   ```

5. **Run the benchmark**:
   ```bash
   deepset agent run agent_configs/my_agent.yml my_test_case
   ```

6. **Clean up resources**:
   ```bash
   deepset test teardown my_test_case
   ```

## How-to Guides

### Managing Test Resources

**Set up all test cases at once**:
```bash
deepset test setup-all --workspace my-workspace --concurrency 3
```

**Clean up all test resources**:
```bash
deepset test teardown-all --workspace my-workspace
```

### Working with Pipelines and Indexes

**Create a standalone pipeline**:
```bash
deepset pipeline create --path my_pipeline.yml --name test-pipeline
```

**Create an index from YAML content**:
```bash
deepset index create --content "$(cat my_index.yml)" --name test-index
```

**Delete resources**:
```bash
deepset pipeline delete --name test-pipeline
deepset index delete --name test-index
```

### Running Benchmarks at Scale

**Run with custom output directory**:
```bash
deepset agent run-all my_agent.yml --output-dir ./results/experiment_1
```

**Run with controlled concurrency**:
```bash
deepset agent run-all my_agent.yml --concurrency 2
```

**Override workspace for testing**:
```bash
deepset agent run my_agent.yml test_case --workspace sandbox
```

### Environment Management

**Use custom environment file**:
```bash
deepset agent run my_agent.yml test_case --env-file .env.staging
```

**Override specific settings**:
```bash
deepset agent run my_agent.yml test_case \
  --workspace different-workspace \
  --api-key different-key
```

### Debugging Failed Tests

**Check what went wrong**:
```bash
# Validate your agent configuration
deepset agent validate-config agent_configs/my_agent.yml

# Check environment variables
deepset agent check-env agent_configs/my_agent.yml

# List available test cases
deepset test list
```

**Examine results**:
Results are saved to `./agent_runs/[run-id]/[test-case]/`:
- `messages.json` - Full conversation history
- `test_results.csv` - Summary statistics
- `post_run_pipeline.yml` - Final pipeline state

## Concepts

### Test Cases

Test cases define realistic scenarios where agents interact with deepset resources:

- **Pipeline tasks**: Creating, modifying, or debugging pipelines
- **Index tasks**: Setting up document indexes 
- **Integration tasks**: Connecting pipelines and indexes

### Agent Configurations

Agent configs specify how to load your AI agent:

- **Function-based**: Load via a Python factory function
- **JSON-based**: Load from a JSON configuration file
- **Environment requirements**: Declare needed environment variables

### Validation

The system validates pipeline configurations:

- **Pre-validation**: Checks initial pipeline state
- **Post-validation**: Confirms agent modifications are valid
- **Judge prompts**: Optional LLM-based correctness evaluation

### Resource Management

Benchmarks automatically handle deepset resources:

- **Setup**: Creates pipelines and indexes before agent runs
- **Isolation**: Each test gets clean resources
- **Cleanup**: Removes resources after testing

### Results and Metrics

Benchmark runs produce comprehensive data:

- **Conversation logs**: Complete agent interaction history
- **Token usage**: Prompt and completion token counts  
- **Tool calls**: Number of deepset API interactions
- **Validation results**: Pipeline correctness before/after
- **Performance metrics**: Runtime and resource usage

### CLI Structure

The CLI is organized into logical command groups:

```
deepset
├── agent     # Run agents against test cases
│   ├── run           # Single test case
│   ├── run-all       # All test cases  
│   ├── check-env     # Validate environment
│   └── validate-config # Validate agent config
├── test      # Manage test case resources
│   ├── list          # Show available tests
│   ├── setup         # Create test resources
│   ├── teardown      # Clean up resources
│   ├── setup-all     # Batch setup
│   └── teardown-all  # Batch cleanup
├── pipeline  # Direct pipeline management
│   ├── create        # Create pipeline
│   └── delete        # Delete pipeline
└── index     # Direct index management
    ├── create        # Create index  
    └── delete        # Delete index
```

### Configuration Files

**Agent Config Structure**:
```yaml
agent_factory_function: "module.path.to.factory"  # OR
agent_json: "path/to/agent.json"                   # Exactly one required
display_name: "human-readable-name"                # Required
required_env_vars:                                   # Optional
  - DEEPSET_API_KEY
  - ANTHROPIC_API_KEY
```

**Test Case Structure**:
```yaml
name: "unique_test_name"           # Required
objective: "What this test evaluates"  # Required  
prompt: "Instructions for the agent"   # Required
query_yaml: "path/to/pipeline.yml"     # Optional
query_name: "pipeline-name"            # Required if query_yaml
index_yaml: "path/to/index.yml"        # Optional
index_name: "index-name"               # Required if index_yaml
expected_query: "path/to/gold.yml"     # Optional
tags: ["category", "type"]            # Optional
judge_prompt: "Evaluation criteria"    # Optional
```

### Environment Variables

**Required**:
- `DEEPSET_WORKSPACE` - Your deepset workspace name
- `DEEPSET_API_KEY` - Your deepset API key

**Agent-specific** (depends on your agent):
- `ANTHROPIC_API_KEY` - For Claude-based agents
- `OPENAI_API_KEY` - For OpenAI-based agents
- `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY` - For tracing

**Optional**:
- Any environment variables your agent needs

