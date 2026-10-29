import asyncio
from pathlib import Path

import pytest

from brg_mcp.server import create_server
from brg_mcp.tools.additions import primitives_add

# Every addition. Add each new one here.
ADDITIONS = [primitives_add]


@pytest.mark.parametrize("make", ADDITIONS)
def test_addition(make):
    addition = make()
    for part in [*addition["imports"], addition["code"], *addition["scene"], addition["viewer"]]:
        compile(part, "part", "exec")              # valid Python
    assert all(line.startswith("viewer.scene.add(") for line in addition["scene"])


@pytest.mark.parametrize("make", ADDITIONS)
def test_addition_is_a_tool(make):
    tools = [tool.name for tool in asyncio.run(create_server(Path(__file__).parents[1]).list_tools())]
    assert "compas_" + make.__name__ in tools      # primitives_add is the tool compas_primitives_add, /add-primitives on the website
