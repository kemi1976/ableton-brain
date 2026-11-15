#!/usr/bin/env python3
"""
WebSocket Bridge Server
Connects the HTML dashboard (frontend) to the MCP server (backend).
Runs on port 8051, proxies MCP tool calls over WebSocket.
"""

import asyncio
import json
import logging
import sys
import os
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets

from mcp_server import AbletonBrainMCP

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


class DashboardBridge:
    """WebSocket bridge between dashboard and MCP."""

    def __init__(self, mcp: AbletonBrainMCP, host: str = "0.0.0.0", port: int = 8051):
        self.mcp = mcp
        self.host = host
        self.port = port
        self.clients = set()
        self.client_info = {}

    async def handle_client(self, websocket, path):
        """Handle incoming WebSocket connection."""
        client_id = id(websocket)
        self.clients.add(websocket)
        self.client_info[client_id] = {"connected_at": asyncio.get_event_loop().time()}
        logger.info(f"Client connected: {client_id} (total: {len(self.clients)})")

        try:
            # Send welcome + available tools
            await websocket.send(json.dumps({
                "type": "welcome",
                "tools": await self.get_tool_list(),
                "version": "1.0.0"
            }))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, client_id, data)
                except json.JSONDecodeError:
                    await self.send_error(websocket, "Invalid JSON")
                except Exception as e:
                    logger.error(f"Message handling error: {e}")
                    await self.send_error(websocket, str(e))

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            self.client_info.pop(client_id, None)
            logger.info(f"Client disconnected: {client_id} (total: {len(self.clients)})")

    async def handle_message(self, websocket, client_id: int, data: Dict):
        """Route incoming messages."""
        msg_type = data.get("type")

        if msg_type == "call_tool":
            await self.handle_tool_call(websocket, data)
        elif msg_type == "get_status":
            await self.send_status(websocket)
        elif msg_type == "subscribe":
            await self.handle_subscribe(websocket, data)
        elif msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))
        else:
            await self.send_error(websocket, f"Unknown message type: {msg_type}")

    async def handle_tool_call(self, websocket, data: Dict):
        """Execute an MCP tool and return result."""
        tool_name = data.get("tool")
        arguments = data.get("arguments", {})
        request_id = data.get("id")

        logger.info(f"Tool call: {tool_name} with args: {arguments}")

        try:
            # Get the tool handler from MCP server
            result = await self.call_mcp_tool(tool_name, arguments)

            response = {
                "type": "tool_result",
                "id": request_id,
                "tool": tool_name,
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            response = {
                "type": "tool_result",
                "id": request_id,
                "tool": tool_name,
                "success": False,
                "error": str(e)
            }

        await websocket.send(json.dumps(response))

    async def call_mcp_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Call an MCP tool via the internal server."""
        # Use the MCP server's internal call mechanism
        from mcp.types import CallToolRequest, CallToolRequestParams
        from mcp.server import Server

        # Find the tool handler
        for name, handler in self.mcp._tool_handlers.items():
            if name == tool_name:
                # Call the handler directly
                result = await handler(arguments)
                # Extract text content from TextContent list
                if isinstance(result, list) and result:
                    if hasattr(result[0], 'text'):
                        return json.loads(result[0].text)
                return result

        raise ValueError(f"Tool not found: {tool_name}")

    async def get_tool_list(self) -> list:
        """Get list of available MCP tools."""
        tools = []
        for tool in await self.mcp._get_tool_definitions():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            })
        return tools

    async def send_status(self, websocket):
        """Send server status."""
        status = {
            "type": "status",
            "mcp_connected": True,
            "fleet_nodes": len(self.mcp.fleet_coordinator.nodes) if hasattr(self.mcp, 'fleet_coordinator') else 0,
            "analyzer_connected": self.mcp.analyzer_bridge is not None,
            "uptime": "running"
        }
        await websocket.send(json.dumps(status))

    async def handle_subscribe(self, websocket, data: Dict):
        """Handle event subscriptions (metrics, logs, etc.)."""
        events = data.get("events", [])
        self.client_info[id(websocket)]["subscriptions"] = events
        await websocket.send(json.dumps({"type": "subscribed", "events": events}))

    async def send_error(self, websocket, error: str):
        await websocket.send(json.dumps({"type": "error", "error": error}))

    async def broadcast(self, event_type: str, data: Dict):
        """Broadcast event to all subscribed clients."""
        message = json.dumps({"type": event_type, **data})
        dead = []
        for ws in self.clients:
            try:
                if "subscriptions" in self.client_info.get(id(ws), {}):
                    if event_type in self.client_info[id(ws)]["subscriptions"] or "*" in self.client_info[id(ws)]["subscriptions"]:
                        await ws.send(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting Dashboard Bridge on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever


async def main():
    """Main entry point."""
    mcp = AbletonBrainMCP()
    bridge = DashboardBridge(mcp)
    await bridge.start()


if __name__ == "__main__":
    asyncio.run(main())