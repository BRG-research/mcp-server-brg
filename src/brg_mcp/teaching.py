"""Publish the notebooks of the commands to the BRG Teaching website, where they open in the browser.

A page and the notebook folder with the same name, numbers aside, belong together::

    fd/06_exercises.md   +   fd/07_exercises/exercise_01_forces.ipynb

    -> Teaching/CAS/website/notebooks/fd/exercise_01_forces.ipynb
    -> https://brg-teaching.github.io/Teaching/CAS/website/library.html#/notebook/fd-exercise-01-forces

``uv run brg-publish /path/to/Teaching/CAS/website`` copies every notebook, always overwriting the copy of the same name,
and lists it in ``notebook-exercises.js``. The GitHub Action ``.github/workflows/teaching.yml`` runs it on every push.

"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
LINK = "https://brg-teaching.github.io/Teaching/CAS/website/library.html#/notebook/{}"
SOURCE = "mcp-server-brg"

# ==============================================================================
# Notebooks
# ==============================================================================


def plain(name):
    """A file or folder name without the number that orders it: ``07_exercises`` -> ``exercises``."""
    return name.lstrip("0123456789_")


def notebooks_of(page):
    """The notebooks that belong to a page: those in the folders next to it with the same name, numbers aside.

    Parameters
    ----------
    page : :class:`pathlib.Path`
        A markdown page, such as ``fd/06_exercises.md``.

    Returns
    -------
    list[:class:`pathlib.Path`]

    """
    folders = [folder for folder in page.parent.iterdir() if folder.is_dir() and plain(folder.name) == plain(page.stem)]
    return sorted(notebook for folder in folders for notebook in folder.glob("*.ipynb"))


def notebook_id(notebook):
    """The id of a notebook on the website: ``fd/07_exercises/exercise_01_forces.ipynb`` -> ``fd-exercise-01-forces``."""
    return "{}-{}".format(notebook.parent.parent.name, notebook.stem).replace("_", "-")


def link(notebook):
    """The web address that opens a notebook in the Jupyter of the teaching website."""
    return LINK.format(notebook_id(notebook))


def title(notebook):
    """The title of a notebook: the first heading of its first cell, ``Exercise 01 Forces``."""
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    lines = "".join(cells[0]["source"]).splitlines() if cells else []
    return next((line[2:].strip() for line in lines if line.startswith("# ")), notebook.stem)


# ==============================================================================
# Publish
# ==============================================================================


def publish(website):
    """Copy every notebook into the teaching website and list it there.

    Notebooks of the same name are always overwritten. The entries of ``notebook-exercises.js`` written earlier by
    this function are replaced, all other entries stay. When a notebook changed, the Jupyter storage name is raised,
    so that browsers load the new copies instead of the ones they keep.

    Parameters
    ----------
    website : :class:`pathlib.Path`
        The folder ``Teaching/CAS/website``.

    Returns
    -------
    int
        The number of notebooks that changed.

    """
    website = Path(website)
    registry = website / "notebook-exercises.js"
    header, _, body = registry.read_text(encoding="utf-8").partition("window.CAS_NOTEBOOKS = ")
    entries = [entry for entry in json.loads(body.strip().removesuffix(";")) if entry.get("source") != SOURCE]
    taken = {entry["id"] for entry in entries}

    changed = 0
    for page in sorted(HERE.glob("*/*.md")):
        for notebook in notebooks_of(page):
            if notebook_id(notebook) in taken:
                raise ValueError("The id {} is already used on the website, rename {}.".format(notebook_id(notebook), notebook))
            taken.add(notebook_id(notebook))
            file = "{}/{}".format(page.parent.name, notebook.name)
            target = website / "notebooks" / file
            if not target.is_file() or target.read_bytes() != notebook.read_bytes():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(notebook.read_bytes())
                changed += 1
            entries.append(
                {
                    "id": notebook_id(notebook),
                    "file": file,
                    "title": "{} ({})".format(title(notebook), plain(page.stem)),
                    "summary": "mcp_brg_{}_{}".format(page.parent.name, plain(page.stem)),
                    "section": "extension",
                    "source": SOURCE,
                }
            )

    registry.write_text(header + "window.CAS_NOTEBOOKS = " + json.dumps(entries, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8")
    if changed:
        lite = website.parent / "jupyter" / "jupyter-lite.json"
        text = lite.read_text(encoding="utf-8")
        lite.write_text(re.sub(r'("contentsStorageName": "[^"]*?)(\d+)"', lambda match: '{}{}"'.format(match.group(1), int(match.group(2)) + 1), text), encoding="utf-8")
    print("{} notebooks changed".format(changed))
    return changed


def main():
    publish(sys.argv[1])
