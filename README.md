# Prometheus MCP Server
[![smithery badge](https://smithery.ai/badge/@kakao-yanoo-kim/prometheus-mcp-server-py)](https://smithery.ai/server/@kakao-yanoo-kim/prometheus-mcp-server-py)

A tool that allows access to Prometheus data through a Model Context Protocol server.

## Installation

### Installing via Smithery

To install Prometheus Data Access Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@kakao-yanoo-kim/prometheus-mcp-server-py):

```bash
npx -y @smithery/cli install @kakao-yanoo-kim/prometheus-mcp-server-py --client claude
```

### Manual Installation
```bash
pipx install git+https://github.com/kakao-yanoo-kim/prometheus-mcp-server-py.git
```

### Run Without Installation

You can also run the package directly without installing it using `pipx run`:

```bash
pipx run --spec git+https://github.com/kakao-yanoo-kim/prometheus-mcp-server-py.git prometheus-mcp --url http://your-prometheus-server:9090
```

This is useful for testing or one-time usage scenarios.

## Usage

```bash
# Command line arguments
prometheus-mcp --url http://your-prometheus-server:9090 \
  --username username \
  --password password
# Or
prometheus-mcp --url http://your-prometheus-server:9090 \
  --token your-token
```

## Command Line Arguments

- `--url`: Prometheus server URL (required)
- `--username`: Username for basic authentication (optional)
- `--password`: Password for basic authentication (optional)
- `--token`: Token for authentication (optional)
- `--org-id`: Organization ID for multi-tenant setups (optional)
- `--timeout`: Evaluation timeout in seconds (default: 30)
- `--limit`: Maximum number of returned series (default: 1000)
