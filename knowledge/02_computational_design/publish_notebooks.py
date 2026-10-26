"""Publish this course's notebook sources to the BRG Teaching static website.

python3 knowledge/02_computational_design/publish_notebooks.py \
    --website /path/to/Teaching/CAS/website [--check]

This copies only files declared in tutorials.json. It never deletes student files,
fetches external repositories, changes notebooks, commits, or deploys the website.
"""

import argparse
import json
import re
from pathlib import Path


COURSE = Path(__file__).resolve().parent


def publish(website: Path, check: bool = False) -> None:
    if not (website / "library.html").is_file() or not (website / "data.js").is_file():
        raise ValueError("--website must point to Teaching/CAS/website")
    manifest = json.loads((COURSE / "tutorials.json").read_text())
    tutorials = manifest["tutorials"]
    files = {}
    ids = set()
    for tutorial in tutorials:
        slug, filename = tutorial["id"], tutorial["file"]
        if not re.fullmatch(r"[a-z][a-z0-9-]*", slug) or slug in ids:
            raise ValueError(f"Invalid or duplicate tutorial ID: {slug}")
        if not re.fullmatch(r"[a-z0-9-]+/[a-z0-9-]+\.ipynb", filename) or filename in files:
            raise ValueError(f"Invalid or duplicate notebook filename: {filename}")
        if not tutorial["title"] or not tutorial["summary"]:
            raise ValueError(f"Missing title or summary: {slug}")
        content = (COURSE / "notebooks" / filename).read_bytes()
        notebook = json.loads(content)
        if notebook.get("nbformat") != 4 or not notebook.get("cells"):
            raise ValueError(f"Not a version 4 notebook: {filename}")
        if any(cell.get("outputs") or cell.get("execution_count") is not None
               for cell in notebook["cells"] if cell["cell_type"] == "code"):
            raise ValueError(f"Clear execution outputs before publishing: {filename}")
        files[filename] = content
        ids.add(slug)
    if not {"box", "cable"} <= ids:
        raise ValueError("Keep the existing box and cable tutorial routes")
    # Both the course Submission panel and the workspace use this same registry.
    registry = ("// Generated from knowledge/02_computational_design/tutorials.json.\n"
                "// Edit the source course and run publish_notebooks.py.\n"
                "window.CAS_NOTEBOOKS = " + json.dumps(tutorials, indent=2, ensure_ascii=False) + ";\n")
    targets = {website / "notebooks" / name: data for name, data in files.items()}
    targets[website / "notebook-exercises.js"] = registry.encode()
    differences = [str(path) for path, data in targets.items()
                   if not path.is_file() or path.read_bytes() != data]
    if check:
        if differences:
            raise ValueError("Published copies differ from course sources:\n" + "\n".join(differences))
        print(f"Verified {len(files)} notebooks and the website registry match the course sources.")
        return
    for path, data in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f"Published {len(files)} notebooks and their registry to {website}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--website", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="Verify copies without writing files")
    args = parser.parse_args()
    try:
        publish(args.website.resolve(), args.check)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"{error}\n")
