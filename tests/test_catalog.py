from pathlib import Path
import shutil

import pytest
import yaml

from brg_mcp.catalog import Catalog

ROOT = Path(__file__).resolve().parents[1]


def test_starter_knowledge():
    catalog = Catalog(ROOT)
    assert len(catalog.domains) == 7
    results = catalog.search("EQUILIBRIUM", "graphic_statics")
    assert results[0]["uri"] == "brg://knowledge/equilibrium"
    assert "A f + p = 0" in catalog.read(results[0]["id"])
    assert catalog.search("equilibrium", "history") == []
    assert catalog.search("   ") == []
    assert all(item["status"] == "planned" for item in catalog.packages)


def test_invalid_requests():
    catalog = Catalog(ROOT)
    for document_id in ["missing", "../../README", "/etc/passwd"]:
        with pytest.raises(ValueError, match="Unknown knowledge ID"):
            catalog.read(document_id)
    with pytest.raises(ValueError, match="Unknown domain"):
        catalog.search("equilibrium", "missing")
    with pytest.raises(ValueError, match="limit"):
        catalog.search("equilibrium", limit=0)


@pytest.mark.parametrize("symlink", [False, True])
def test_catalog_cannot_escape_knowledge_root(tmp_path, symlink):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    (tmp_path / "knowledge").mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("not knowledge", encoding="utf-8")
    if symlink:
        (tmp_path / "knowledge" / "escape.md").symlink_to(outside)
        path = "knowledge/escape.md"
    else:
        path = "knowledge/../outside.md"
    entries = [{"id": "escape", "title": "Escape", "domain": "history", "path": path}]
    (tmp_path / "config" / "knowledge.yaml").write_text(yaml.safe_dump(entries))
    with pytest.raises(ValueError, match="inside knowledge"):
        Catalog(tmp_path)
