import asyncio
from pathlib import Path

import pytest

from brg_mcp.server import create_server
from brg_mcp.tools.notebooks import INSTALL, box_notebook, primitives_notebook

# Every notebook skill. Add each new one here.
NOTEBOOKS = [box_notebook, primitives_notebook]


@pytest.mark.parametrize("make", NOTEBOOKS)
def test_notebook(make):
    notebook = make()
    code = [cell["source"] for cell in notebook["cells"] if cell["type"] == "code"]
    assert notebook["file"] == notebook["name"] + ".ipynb"
    assert code[0] == INSTALL                    # starts with the course's installs
    assert code[-1].endswith("viewer.show()")    # ends with the scene
    for cell in code[1:]:
        compile(cell, "cell", "exec")            # valid Python


@pytest.mark.parametrize("make", NOTEBOOKS)
def test_notebook_is_a_tool(make):
    tools = [tool.name for tool in asyncio.run(create_server(Path(__file__).parents[1]).list_tools())]
    assert "compas_" + make.__name__ in tools    # box_notebook is the tool compas_box_notebook, /box on the website


def test_box_notebook():
    assert 'box.name = "brg_mcp"' in str(box_notebook())
    with pytest.raises(ValueError):
        box_notebook(0, 1, 1)
