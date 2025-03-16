# MCP Standard Bots Server

This is an MCP server implementation for Standard Bots that provides tools for controlling and managing routines through the Standard Bots API.

## Features

- Play, pause, and stop routines
- List available routines
- Get routine details and state
- Get step variables
- Full integration with Standard Bots API

## Installation

1. Make sure you have Python 3.9 or higher installed
2. Install uv (if not already installed):
   ```bash
   pip install uv
   ```
3. Clone this repository:
   ```bash
   git clone https://github.com/sub-arjun/mcp-standard-bots.git
   cd mcp-standard-bots
   ```
4. Create a virtual environment and install dependencies:
   ```bash
   uv venv
   uv pip install -e .
   ```
5. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your Standard Bots URL and API key.

## Usage

Run the MCP server:

```bash
python mcp_server.py
```

The server provides the following MCP tools:

- `play_routine`: Play a routine with optional initial variable states
- `pause_routine`: Pause a running routine
- `stop_routine`: Stop running routine and all ongoing motions
- `list_routines`: List routines defined in Routine Editor UI
- `get_routine`: Get routine data by ID
- `get_routine_state`: Get the state from a running routine
- `get_step_variables`: Get all step variables from a running routine

## Configuration

The server requires the following environment variables:

- `STANDARD_BOTS_URL`: The URL of your Standard Bots instance (e.g., https://mybot.sb.app)
- `STANDARD_BOTS_API_KEY`: Your Standard Bots API key

These can also be provided directly when instantiating the server:

```python
server = MCPStandardBotsServer(
    url="https://mybot.sb.app",
    api_key="your_api_key_here"
)
```

## Directory Structure

- `mcp_server.py`: Main MCP server implementation with Standard Bots integration
- `pyproject.toml`: Project configuration and dependencies
- `.env.example`: Example environment variables file

## License

MIT License - see LICENSE file for details