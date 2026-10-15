"""Small, explicit catalog; registered IDs are the public interface."""

from pathlib import Path

import yaml


class Catalog:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.knowledge_root = (self.root / "knowledge").resolve()
        self.domains = self._load("domains")
        self.documents = self._load("knowledge")
        self.packages = self._load("packages")
        domain_ids = {entry["id"] for entry in self.domains}
        for document in self.documents:
            if document["domain"] not in domain_ids:
                raise ValueError(f"Unknown domain: {document['domain']}")
            self._document_path(document)

    def _load(self, name: str) -> list[dict]:
        path = self.root / "config" / f"{name}.yaml"
        entries = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError(f"{path} must contain a list")
        ids = [entry["id"] for entry in entries]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate IDs in {path}")
        return entries

    def _document_path(self, document: dict) -> Path:
        path = (self.root / document["path"]).resolve()
        if not path.is_relative_to(self.knowledge_root) or path.suffix != ".md":
            raise ValueError("Documents must be Markdown files inside knowledge/")
        if not path.is_file():
            raise ValueError(f"Missing knowledge document: {path}")
        return path

    def read(self, document_id: str) -> str:
        for document in self.documents:
            if document["id"] == document_id:
                return self._document_path(document).read_text(encoding="utf-8")
        raise ValueError(f"Unknown knowledge ID: {document_id}")

    def search(self, query: str, domain: str | None = None, limit: int = 10) -> list[dict]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        if domain is not None and domain not in {item["id"] for item in self.domains}:
            raise ValueError(f"Unknown domain: {domain}")
        terms = query.casefold().split()
        if not terms:
            return []
        matches = []
        for document in self.documents:
            if domain is not None and document["domain"] != domain:
                continue
            content = self.read(document["id"])
            searchable = f"{document['title']} {content}".casefold()
            if all(term in searchable for term in terms):
                matches.append({
                    "id": document["id"],
                    "title": document["title"],
                    "domain": document["domain"],
                    "uri": f"brg://knowledge/{document['id']}",
                    "sources": document.get("sources", []),
                })
            if len(matches) == limit:
                break
        return matches
