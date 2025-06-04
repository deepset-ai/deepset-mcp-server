# Deepset MCP Benchmark System

A comprehensive benchmarking and testing framework for the Deepset Cloud Platform that enables automated testing of AI agents against predefined test cases.

## Getting Started

### Prerequisites

- Python 3.11+
- Access to Deepset Cloud Platform
- Required environment variables:
  - `DEEPSET_API_KEY`: Your Deepset Cloud API key
  - `DEEPSET_WORKSPACE`: Your workspace name

### Installation

Install the benchmark dependencies:

```bash
pip install -e .[benchmark]
```

For agent testing, also install:

```bash
pip install -e .[agents]
```

### Quick Start

1. **Check your environment**:
   ```bash
   deepset agent check-env agent_configs/generalist_agent.yml
   ```

2. **List available test cases**:
   ```bash
   deepset test list
   ```

3. **Run a single test**:
   ```bash
   deepset agent run agent_configs/generalist_agent.yml chat_rag_answers_wrong_format
   ```

## Core Concepts

### Test Cases

Test cases define specific scenarios for testing agents. Each test case includes:

- **Pipeline configuration**: YAML files defining Haystack pipelines
- **Index configuration**: YAML files for document indexing
- **Test prompt**: The input message sent to the agent
- **Validation criteria**: Expected behavior and outputs

Test cases are stored as YAML files in `tasks/` directory.

### Agent Configurations

Agent configurations define how to instantiate and run AI agents. They specify:

- **Agent factory function**: Python function that creates the agent
- **Environment variables**: Required API keys and settings
- **Display name**: Human-readable identifier

### Pipelines and Indexes

- **Pipelines**: Define the processing workflow for queries and documents
- **Indexes**: Configure document storage and retrieval systems
- Both are managed as YAML configurations on the Deepset platform

## Tutorials

### Running Your First Benchmark

1. **Prepare your environment**:
   ```bash
   export DEEPSET_API_KEY="your_api_key"
   export DEEPSET_WORKSPACE="your_workspace"
   export ANTHROPIC_API_KEY="your_anthropic_key"
   ```

2. **Validate your agent configuration**:
   ```bash
   deepset agent validate-config agent_configs/generalist_agent.yml
   ```

3. **Run a single test case**:
   ```bash
   deepset agent run agent_configs/generalist_agent.yml chat_rag_answers_wrong_format
   ```

   This will:
   - Create necessary pipelines and indexes
   - Run the agent against the test case
   - Validate the results
   - Clean up resources
   - Save detailed results to disk

4. **View the results**:
   Results are saved in `agent_runs/` directory with:
   - Full message transcripts (`messages.json`)
   - Performance metrics (`test_results.csv`)
   - Pipeline configurations (`post_run_pipeline.yml`)

### Running Multiple Test Cases

Run all available test cases:

```bash
deepset agent run-all agent_configs/generalist_agent.yml
```

With parallel execution:

```bash
deepset agent run-all agent_configs/generalist_agent.yml --concurrency 3
```

### Creating Test Cases

1. **Create a test case YAML file** in `tasks/`:

   ```yaml
   name: "my_test_case"
   objective: "Test pipeline validation"
   prompt: "Please check my pipeline configuration"
   query_yaml: "pipelines/my_pipeline.yml"
   query_name: "test-pipeline"
   index_yaml: "pipelines/my_index.yml"
   index_name: "test-index"
   tags:
     - "validation"
     - "debugging"
   ```

2. **Create the referenced pipeline files** in `tasks/pipelines/`

3. **Test your new case**:
   ```bash
   deepset agent run agent_configs/generalist_agent.yml my_test_case
   ```

## How-To Guides

### Managing Test Resources

#### Setup Test Cases Manually

Create all test case resources on the platform:

```bash
deepset test setup-all --workspace your-workspace --concurrency 5
```

Setup a specific test case:

```bash
deepset test setup my_test_case --workspace your-workspace
```

#### Cleanup Test Resources

Remove all test case resources:

```bash
deepset test teardown-all --workspace your-workspace
```

Remove a specific test case:

```bash
deepset test teardown my_test_case --workspace your-workspace
```

### Managing Pipelines and Indexes

#### Create Individual Resources

Create a pipeline from YAML file:

```bash
deepset pipeline create --path pipeline.yml --name my-pipeline --workspace your-workspace
```

Create an index from YAML content:

```bash
deepset index create --content "$(cat index.yml)" --name my-index --workspace your-workspace
```

#### Delete Resources

Delete a pipeline:

```bash
deepset pipeline delete --name my-pipeline --workspace your-workspace
```

Delete an index:

```bash
deepset index delete --name my-index --workspace your-workspace
```

### Environment Configuration

#### Using Environment Files

Create a `.env` file:

```bash
DEEPSET_API_KEY=your_api_key
DEEPSET_WORKSPACE=your_workspace
ANTHROPIC_API_KEY=your_anthropic_key
```

Use it with any command:

```bash
deepset agent run --env-file .env agent_configs/generalist_agent.yml test_case
```

#### Override Settings

Override workspace and API key:

```bash
deepset agent run agent_configs/generalist_agent.yml test_case \
  --workspace different-workspace \
  --api-key different-key
```

### Custom Output Directories

Specify where to save results:

```bash
deepset agent run agent_configs/generalist_agent.yml test_case \
  --output-dir ./my_results
```

Specify test case directory:

```bash
deepset agent run agent_configs/generalist_agent.yml test_case \
  --test-base-dir ./my_test_cases
```

### Debugging and Monitoring

#### Check Environment Variables

Verify all required environment variables are set:

```bash
deepset agent check-env agent_configs/generalist_agent.yml
```

#### Validate Configurations

Check agent configuration syntax:

```bash
deepset agent validate-config agent_configs/generalist_agent.yml
```

#### View Test Case Lists

List available test cases:

```bash
deepset test list --test-dir ./my_test_cases
```

## Command Reference

### Agent Commands

- `deepset agent run` - Run agent against single test case
- `deepset agent run-all` - Run agent against all test cases
- `deepset agent check-env` - Verify environment configuration
- `deepset agent validate-config` - Validate agent configuration

### Test Management Commands

- `deepset test list` - List available test cases
- `deepset test setup` - Setup single test case resources
- `deepset test setup-all` - Setup all test case resources
- `deepset test teardown` - Remove single test case resources
- `deepset test teardown-all` - Remove all test case resources

### Pipeline Management Commands

- `deepset pipeline create` - Create new pipeline
- `deepset pipeline delete` - Delete existing pipeline

### Index Management Commands

- `deepset index create` - Create new index
- `deepset index delete` - Delete existing index

## Configuration Files

### Agent Configuration Format

```yaml
agent_factory_function: "module.path.to.get_agent"
display_name: "My Agent"
required_env_vars:
  - DEEPSET_API_KEY
  - DEEPSET_WORKSPACE
  - ANTHROPIC_API_KEY
```

### Test Case Configuration Format

```yaml
name: "test_case_name"
objective: "Description of what this test validates"
prompt: "The message sent to the agent"
query_yaml: "relative/path/to/pipeline.yml"  # Optional
query_name: "pipeline-name"                   # Required if query_yaml present
index_yaml: "relative/path/to/index.yml"     # Optional
index_name: "index-name"                      # Required if index_yaml present
expected_query: "path/to/expected.yml"        # Optional validation reference
tags:
  - "category"
  - "type"
judge_prompt: "Optional prompt for LLM validation"  # Optional
```

## Result Analysis

### Understanding Output Files

Each test run produces:

1. **`messages.json`**: Complete conversation transcript with the agent
2. **`test_results.csv`**: Performance metrics and validation results
3. **`post_run_pipeline.yml`**: Final pipeline configuration after agent modifications

### Performance Metrics

The system tracks:

- **Token usage**: Prompt and completion tokens consumed
- **Tool calls**: Number of API calls made by the agent
- **Validation status**: Pre and post-run pipeline validation results
- **Model information**: Which AI model was used

### Aggregate Analysis

When running multiple test cases, the system provides:

- Success/failure counts
- Total resource consumption
- Per-test case breakdowns
- Cleanup status reports

## Troubleshooting

### Common Issues

**Environment variable errors**:
- Ensure all required variables are set
- Use `deepset agent check-env` to verify configuration

**Test case not found**:
- Check test case directory path
- Verify YAML file exists and is properly named
- Use `deepset test list` to see available cases

**Validation failures**:
- Review pipeline YAML syntax
- Check component type names and parameters
- Use Deepset Cloud UI to validate manually

**Resource conflicts**:
- Ensure unique names for pipelines and indexes
- Clean up existing resources before running tests
- Use different workspace for testing

**Permission errors**:
- Verify API key has sufficient permissions
- Check workspace access rights
- Confirm network connectivity to Deepset Cloud

### Getting Help

1. **Check logs**: Review detailed error messages in command output
2. **Validate configs**: Use validation commands before running tests
3. **Test incrementally**: Start with single test cases before batch runs
4. **Clean environment**: Remove conflicting resources and retry

## Best Practices

### Test Organization

- Use descriptive test case names with underscores
- Group related tests with consistent tag names
- Keep pipeline files organized in subdirectories
- Document test objectives clearly

### Resource Management

- Always clean up test resources after experiments
- Use unique names to avoid conflicts
- Prefer automated setup/teardown over manual management
- Monitor resource usage in your workspace

### Performance Optimization

- Use appropriate concurrency levels (start with 1-3)
- Set reasonable token limits for cost control
- Cache common pipeline configurations
- Run expensive tests separately from quick validation tests

### Environment Management

- Use environment files for consistent configuration
- Never commit API keys to version control
- Use different workspaces for development and testing
- Validate environment before important test runs