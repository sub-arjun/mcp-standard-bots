"""
MCP Standard Bots Server

This module implements a FastMCP server that provides a bridge between the Model Context Protocol (MCP)
and the Standard Bots Routine Editor API. It supports three transport modes:
1. stdio: For command-line integration with MCP clients
2. HTTP: For REST API access with OpenAPI documentation
3. SSE: For real-time updates via Server-Sent Events

The server provides tools for:
- Playing, pausing, and stopping routines
- Listing available routines
- Getting routine details and state
- Managing step variables
"""

from typing import Dict, List, Optional, Any
import os
from pathlib import Path
import json
import httpx
from enum import Enum
from datetime import datetime

from fastmcp import FastMCP
from pydantic import BaseModel, Field

class RobotStatusEnum(str, Enum):
    """
    Enumeration of possible robot status states.
    These states represent the different operational modes and conditions of the robot.
    """
    IDLE = "Idle"  # Robot is powered on but not executing any commands
    RUNNING_AD_HOC_COMMAND = "RunningAdHocCommand"  # Executing a one-off command
    ROUTINE_RUNNING = "RoutineRunning"  # Executing a routine
    ANTIGRAVITY = "Antigravity"  # In anti-gravity/freedrive mode
    ANTIGRAVITY_SLOW = "AntigravitySlow"  # In slow anti-gravity mode
    FAILURE = "Failure"  # Robot has encountered an error
    RECOVERING = "Recovering"  # Robot is attempting to recover from an error

class StandardBotsClient:
    """
    Async HTTP client for interacting with the Standard Bots API.
    Handles authentication and provides methods for all supported API endpoints.
    """
    def __init__(self, url: str, api_key: str):
        """
        Initialize the client with base URL and authentication.
        
        Args:
            url: Base URL of the Standard Bots API
            api_key: API key for authentication
        """
        self.url = url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "robot_kind": "live"  # Indicates we're controlling a real robot, not simulation
        }
        self.client = httpx.AsyncClient(base_url=self.url, headers=self.headers)
    
    async def play_routine(self, routine_id: str, variables: Dict[str, str] = None) -> Dict:
        """
        Start executing a routine with optional initial variable values.
        
        Args:
            routine_id: ID of the routine to play
            variables: Optional dictionary of variable name-value pairs to initialize
        
        Returns:
            API response containing the routine execution status
        """
        endpoint = f"/api/v1/routine-editor/routines/{routine_id}/play"
        data = {"variables": variables} if variables else {}
        response = await self.client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()
    
    async def pause_routine(self, routine_id: str) -> Dict:
        """
        Pause a currently running routine.
        
        Args:
            routine_id: ID of the routine to pause
        
        Returns:
            API response confirming the pause action
        """
        endpoint = f"/api/v1/routine-editor/routines/{routine_id}/pause"
        response = await self.client.post(endpoint)
        response.raise_for_status()
        return response.json()
    
    async def stop_routine(self) -> Dict:
        """
        Stop the currently running routine and halt all robot motion.
        
        Returns:
            API response confirming the stop action
        """
        endpoint = "/api/v1/routine-editor/stop"
        response = await self.client.post(endpoint)
        response.raise_for_status()
        return response.json()
    
    async def list_routines(self, limit: int = 10, offset: int = 0) -> Dict:
        """
        Get a paginated list of available routines.
        
        Args:
            limit: Maximum number of routines to return
            offset: Number of routines to skip for pagination
        
        Returns:
            API response containing the list of routines
        """
        endpoint = f"/api/v1/routine-editor/routines?limit={limit}&offset={offset}"
        response = await self.client.get(endpoint)
        response.raise_for_status()
        return response.json()
    
    async def get_routine(self, routine_id: str) -> Dict:
        """
        Get detailed information about a specific routine.
        
        Args:
            routine_id: ID of the routine to fetch
        
        Returns:
            API response containing the routine details
        """
        endpoint = f"/api/v1/routine-editor/routines/{routine_id}"
        response = await self.client.get(endpoint)
        response.raise_for_status()
        return response.json()
    
    async def get_routine_state(self, routine_id: str) -> Dict:
        """
        Get the current execution state of a running routine.
        
        Args:
            routine_id: ID of the routine to check
        
        Returns:
            API response containing the routine's current state
        """
        endpoint = f"/api/v1/routine-editor/routines/{routine_id}/state"
        response = await self.client.get(endpoint)
        response.raise_for_status()
        return response.json()
    
    async def get_step_variables(self, routine_id: str, step_id_map: bool = False) -> Dict:
        """
        Get the current values of all variables in a running routine.
        
        Args:
            routine_id: ID of the routine
            step_id_map: Whether to include mapping of variables to step IDs
        
        Returns:
            API response containing the variable values
        """
        endpoint = f"/api/v1/routine-editor/routines/{routine_id}/step-variables?step_id_map={str(step_id_map).lower()}"
        response = await self.client.get(endpoint)
        response.raise_for_status()
        return response.json()

class PlayRoutineRequest(BaseModel):
    """
    Pydantic model for routine play requests.
    Validates the input parameters for starting a routine.
    """
    routine_id: str
    variables: Optional[Dict[str, str]] = None

class RoutineResponse(BaseModel):
    """
    Pydantic model for routine details.
    Defines the structure of routine information returned by the API.
    """
    id: str
    name: str
    description: Optional[str] = None
    steps: List[Dict] = []  # List of step configurations
    version: str = "1.0.0"  # Routine format version
    author: Optional[str] = None

class RoutineStateResponse(BaseModel):
    """
    Pydantic model for routine execution state.
    Contains information about the current state of a running routine.
    """
    is_paused: bool
    current_step_id: str
    start_time: str
    run_time_seconds: float
    cycle_count: int
    total_expected_cycles: int
    should_next_arm_move_be_guided_mode: bool
    is_preflight_test_run: bool

class StepVariablesResponse(BaseModel):
    """
    Pydantic model for step variable values.
    Contains the current values of variables in a routine's steps.
    """
    variables: Dict[str, str]
    step_id_map: Optional[Dict[str, str]] = None

class MCPStandardBotsServer(FastMCP):
    """
    FastMCP server implementation for Standard Bots.
    Provides MCP tools that map to Standard Bots API endpoints.
    """
    def __init__(self, url: str = None, api_key: str = None):
        """
        Initialize the server with API credentials.
        
        Args:
            url: Standard Bots API URL (optional, can be set via env var)
            api_key: API key for authentication (optional, can be set via env var)
        """
        super().__init__()
        self.url = url or os.getenv("STANDARD_BOTS_URL")
        self.api_key = api_key or os.getenv("STANDARD_BOTS_API_KEY")
        
        if not self.url or not self.api_key:
            raise ValueError("Standard Bots URL and API key must be provided either through constructor or environment variables")
        
        self.client = StandardBotsClient(self.url, self.api_key)

        # Register all available tools with the FastMCP server
        self.tool(name="play_routine", description="Play a routine with optional initial variable states")(self.play_routine)
        self.tool(name="pause_routine", description="Pause a running routine")(self.pause_routine)
        self.tool(name="stop_routine", description="Stop running routine and all ongoing motions")(self.stop_routine)
        self.tool(name="list_routines", description="List routines defined in Routine Editor UI")(self.list_routines)
        self.tool(name="get_routine", description="Get routine data by ID")(self.get_routine)
        self.tool(name="get_routine_state", description="Get the state from a running routine")(self.get_routine_state)
        self.tool(name="get_step_variables", description="Get all step variables from a running routine")(self.get_step_variables)

    # Tool implementations
    # Each method corresponds to a registered tool and maps to a client API call

    async def play_routine(self, routine_id: str, variables: Optional[Dict[str, str]] = None) -> Dict:
        """Tool: Start executing a routine"""
        return await self.client.play_routine(routine_id, variables)

    async def pause_routine(self, routine_id: str) -> Dict:
        """Tool: Pause a running routine"""
        return await self.client.pause_routine(routine_id)

    async def stop_routine(self) -> Dict:
        """Tool: Stop the current routine and all motion"""
        return await self.client.stop_routine()

    async def list_routines(self, limit: Optional[int] = 10, offset: Optional[int] = 0) -> Dict:
        """Tool: Get list of available routines"""
        return await self.client.list_routines(limit, offset)

    async def get_routine(self, routine_id: str) -> Dict:
        """Tool: Get routine details"""
        return await self.client.get_routine(routine_id)

    async def get_routine_state(self, routine_id: str) -> Dict:
        """Tool: Get current routine state"""
        return await self.client.get_routine_state(routine_id)

    async def get_step_variables(self, routine_id: str, step_id_map: Optional[bool] = False) -> Dict:
        """Tool: Get current variable values"""
        return await self.client.get_step_variables(routine_id, step_id_map)

    def run_stdio(self):
        """
        Run the server using stdio transport.
        This mode is suitable for command-line MCP clients.
        """
        import asyncio
        asyncio.run(self.run_stdio_async())

    def run_sse(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Run the server using SSE transport.
        This mode enables real-time updates via Server-Sent Events.
        
        Args:
            host: Network interface to bind to
            port: Port number to listen on
        """
        import asyncio
        asyncio.run(self.run_sse_async(host=host, port=port))

if __name__ == "__main__":
    # Direct execution entry point
    # Runs the server in HTTP mode using uvicorn
    import os
    from dotenv import load_dotenv
    import uvicorn
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API credentials from environment
    url = os.getenv("STANDARD_BOTS_URL")
    api_key = os.getenv("STANDARD_BOTS_API_KEY")
    
    # Create and run the server
    server = MCPStandardBotsServer(url=url, api_key=api_key)
    uvicorn.run(server.app, host="0.0.0.0", port=8000)  # Run in HTTP mode 