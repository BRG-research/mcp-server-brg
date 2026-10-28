import pytest

from brg_mcp.tools.notebooks import BOX_NAME, box_notebook


def test_box_notebook_follows_the_course_and_names_the_box():
    notebook = box_notebook(3, 2, 1)
    assert notebook["name"] == BOX_NAME == "brg_mcp" and notebook["file"] == "brg_mcp.ipynb"
    code = [cell["source"] for cell in notebook["cells"] if cell["type"] == "code"]
    assert code[0].startswith("%pip install -q compas==2.15.1")          # the course's pinned installs first
    assert "Box(3, 2, 1)" in code[2] and 'box.name = "brg_mcp"' in code[2]
    assert code[-1].endswith("viewer.show()")                             # ends in a COMPAS scene
    for cell in code[1:]:
        compile(cell, "cell", "exec")                                     # valid Python


def test_box_notebook_rejects_bad_input():
    with pytest.raises(ValueError):
        box_notebook(0, 1, 1)
    with pytest.raises(ValueError):
        box_notebook(color="red; import os")
