---
name: books-process
description: Process a scanned structural engineering book from a local PDF path or HTTPS URL using the shared BRG workflow.
---

Input: $ARGUMENTS

- Call `get_book_guide(include_library_map=false)` and follow its `processing_workflow`
  and `guide` for this input.
- Without MCP, read `skills/books-process/SKILL.md` from this checkout
  (three parents above this skill directory) and follow it.
- Keep processing local unless the user also requests publishing.
