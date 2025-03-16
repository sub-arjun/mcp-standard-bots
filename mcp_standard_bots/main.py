"""Main entry point for MCP Standard Bots server"""

import os
import sys
import argparse
from dotenv import load_dotenv
import uvicorn

from mcp_standard_bots.server import MCPStandardBotsServer

def main():
    """Main entry point for the MCP Standard Bots server"""
    parser = argparse.ArgumentParser(description="MCP Standard Bots Server")
    parser.add_argument("--mode", choices=["http", "stdio", "sse"], default="stdio",
                       help="Server mode: 'http' for HTTP/FastAPI, 'stdio' for MCP stdio transport, or 'sse' for Server-Sent Events")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (HTTP mode only)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (HTTP mode only)")
    parser.add_argument("--url", help="Standard Bots URL (can also be set via STANDARD_BOTS_URL env var)")
    parser.add_argument("--api-key", help="Standard Bots API key (can also be set via STANDARD_BOTS_API_KEY env var)")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    
    args = parser.parse_args()
    
    # Load environment variables
    if os.path.exists(args.env_file):
        load_dotenv(args.env_file)
    
    # Get configuration from args or environment
    url = args.url or os.getenv("STANDARD_BOTS_URL")
    api_key = args.api_key or os.getenv("STANDARD_BOTS_API_KEY")
    
    if not url or not api_key:
        print("Error: Standard Bots URL and API key must be provided either through arguments or environment variables")
        sys.exit(1)
    
    # Create server
    server = MCPStandardBotsServer(url=url, api_key=api_key)
    
    # Run in appropriate mode
    if args.mode == "http":
        uvicorn.run(server.app, host=args.host, port=args.port)
    elif args.mode == "sse":
        server.run_sse()  # SSE mode uses FastMCP's built-in server
    else:  # stdio mode
        server.run_stdio()

if __name__ == "__main__":
    main() 