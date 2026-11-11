import json
import re

import pytest

from brg_mcp.server import COMMANDS
from brg_mcp.teaching import notebooks_of

NOTEBOOKS = sorted(notebook for path in COMMANDS.values() for notebook in notebooks_of(path))


def cells(notebook):
    return [(cell["cell_type"], "".join(cell["source"])) for cell in json.loads(notebook.read_text(encoding="utf-8"))["cells"]]


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda notebook: notebook.name)
def test_title_is_the_file_name(notebook):
    words = notebook.stem.split("_")
    assert cells(notebook)[0] == ("markdown", "# " + " ".join([words[0].capitalize(), words[1], words[2].capitalize()] + words[3:]))


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda notebook: notebook.name)
def test_second_cell_installs_what_the_notebook_imports(notebook):
    kind, install = cells(notebook)[1]
    assert kind == "code" and install.startswith("%pip install -q ")
    code = "\n".join(source for kind, source in cells(notebook) if kind == "code")
    for module in set(re.findall(r"^\s*(?:from|import)\s+([a-z_]+)", code, re.M)):
        assert module.replace("_", "-") in install


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda notebook: notebook.name)
def test_no_dashes(notebook):
    for kind, source in cells(notebook):
        if kind == "markdown":
            assert "\u2014" not in source and "\u2013" not in source
