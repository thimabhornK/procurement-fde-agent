"""The same ERP tools served over the Model Context Protocol (stdio).

Run:  python -m procurement_agent.erp.mcp_server
Any MCP client (for example an ADK agent or Claude Desktop) can then list and
call get_vendor_info, check_budget and get_po_status.
"""

from __future__ import annotations

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

from procurement_agent.erp import tools

server = MCPServer("procurement-erp")

server.tool()(tools.get_vendor_info)
server.tool()(tools.check_budget)
server.tool()(tools.get_po_status)

if __name__ == "__main__":
    server.run()
