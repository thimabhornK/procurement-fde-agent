import asyncio

import pytest

pytest.importorskip("mcp")

from procurement_agent.erp.mcp_server import server  # noqa: E402


def test_mcp_server_lists_the_three_erp_tools():
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {"get_vendor_info", "check_budget", "get_po_status"}
