import json

from brg_mcp.server import COMMANDS
from brg_mcp.teaching import SOURCE
from brg_mcp.teaching import notebooks_of
from brg_mcp.teaching import publish

OTHER = {"id": "box", "file": "01-basics/01-box.ipynb", "title": "A COMPAS box", "summary": "One box.", "section": "foundation"}


def website(tmp_path):
    """A small copy of Teaching/CAS: one notebook of another course, an old entry of ours, the Jupyter settings."""
    site = tmp_path / "website"
    site.mkdir()
    old = {"id": "fd-gone", "file": "fd/gone.ipynb", "title": "Gone", "summary": "", "section": "extension", "source": SOURCE}
    (site / "notebook-exercises.js").write_text("// header\nwindow.CAS_NOTEBOOKS = " + json.dumps([OTHER, old]) + ";\n")
    (tmp_path / "jupyter").mkdir()
    (tmp_path / "jupyter" / "jupyter-lite.json").write_text('{"contentsStorageName": "cas-jupyter-contents-6"}')
    return site


def registry(site):
    return json.loads(site.joinpath("notebook-exercises.js").read_text().partition("= ")[2].strip().removesuffix(";"))


def test_publish_copies_lists_and_keeps_other_courses(tmp_path):
    site = website(tmp_path)
    notebooks = [notebook for path in COMMANDS.values() for notebook in notebooks_of(path)]
    assert publish(site) == len(notebooks)
    entries = registry(site)
    assert entries[0] == OTHER
    assert "fd-gone" not in [entry["id"] for entry in entries]
    assert len(entries) == 1 + len(notebooks)
    assert all((site / "notebooks" / entry["file"]).read_bytes() for entry in entries[1:])
    assert all(entry["file"].count("/") == 1 for entry in entries[1:])
    assert site.joinpath("notebook-exercises.js").read_text().startswith("// header")
    assert "cas-jupyter-contents-7" in (tmp_path / "jupyter" / "jupyter-lite.json").read_text()


def test_publish_again_changes_nothing(tmp_path):
    site = website(tmp_path)
    publish(site)
    assert publish(site) == 0
    assert "cas-jupyter-contents-7" in (tmp_path / "jupyter" / "jupyter-lite.json").read_text()


def test_publish_overwrites_a_notebook_of_the_same_name(tmp_path):
    site = website(tmp_path)
    publish(site)
    entry = registry(site)[1]
    (site / "notebooks" / entry["file"]).write_text("old copy")
    assert publish(site) == 1
    assert (site / "notebooks" / entry["file"]).read_text() != "old copy"
