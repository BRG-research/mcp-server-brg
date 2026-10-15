# Books

[Library](https://pub-c082064d3c234b25bcb6abd4240e637c.r2.dev/LIBRARY.md) · [Agent guide](../../src/brg_mcp/book_guidance.md) · [Configuration](../../config/sources.yaml)

## Read

- Connect BRG MCP; no keys needed.
- Ask: “Use BRG to find funicular polygons and cite the matching chapter.”
- Tools: `get_book_guide` → `search_books` → `read_book_section`.
- Search covers chapter summaries, not raw PDFs or full chapter text.

## Upload

- All files in `brg-books` are public.
- Configure AWS CLI once: `aws configure --profile r2`.
- Enter R2 access/secret keys, region `auto`, output `json`.

Upload a new PDF:

```bash
aws --profile r2 --region auto \
  --endpoint-url https://7a0d8a20a1daaaab0534f11839b6a552.r2.cloudflarestorage.com \
  s3 cp /path/to/book.pdf s3://brg-books/RAW/book.pdf
```

## Process

Any MCP client that supports prompts can request:

```text
Prompt: books_process
source: /path/to/scanned-book.pdf
```

- `source` also accepts an HTTPS PDF URL; optional inputs: `workspace`, `language`.
- If prompts are not exposed, ask: “Read get_book_guide and process /path/to/book.pdf.”
- Shared workflow: [skills/books-process/SKILL.md](../../skills/books-process/SKILL.md).

Claude Code shortcut, when opened at this repository:

```text
/books-process "/path/to/scanned-book.pdf"
/books-process https://pub-c082064d3c234b25bcb6abd4240e637c.r2.dev/RAW/book.pdf
```

- Use either command. No initial upload is needed for a local PDF.
- The workflow covers scans, chapters, review, and library indexes.
- It needs PDF/image tools and a local Books workspace; `BRG_BOOKS_DIR` can select it.
- Processing stays local unless you add “publish checked outputs to R2”.
- MCP supplies guidance; the host agent performs processing using your selected model.

To use `/books-process` from any project, install it once from this checkout:

```bash
mkdir -p ~/.claude/skills
cp -R skills/books-process ~/.claude/skills/
```

- Other skill-capable clients can install the same `skills/books-process/` folder using their own mechanism.
- Keep BRG MCP connected so installed skills can retrieve `get_book_guide`.
- Restart Claude Code if the command is not listed. [Claude skill documentation](https://code.claude.com/docs/en/skills).

## Publish updates

From the MCP repository root, preview the collection upload:

```bash
bash scripts/upload-books.sh brg-books \
  https://7a0d8a20a1daaaab0534f11839b6a552.r2.cloudflarestorage.com \
  /path/to/Books
```

- Append `--upload` to transfer. Matching files are updated; remote-only files remain.
- Include regenerated `LIBRARY.md`; restart MCP to refresh cached content.
- Raw PDFs become searchable through MCP only after chapters enter the library map.
