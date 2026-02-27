# Grammaire Progressive du Français — OCR Ingestion PRD

## Overview
Progressively extract all content from the scanned PDF "Grammaire Progressive du Français - Niveau Avancé" (CLE, 1997) into structured JSON files. The PDF is 192 pages of pure images (no text layer, created by ImageToPDF). Claude Code reads rendered page images directly — no Gemini API needed.

## Approach
- **No external API**: Claude Code is multimodal and reads page images directly
- **Progressive**: Each session ingests 1-3 chapters. Progress tracked in `manifest.json`
- **Two artifacts per chapter**: a JSON file with grammar rules + exercises, and an updated manifest
- **Page offset**: book_page = pdf_1indexed + 1 (cover has no book page number). `pdf_0index = book_page - 2`

## File Locations
- Manifest: `api/data/grammaire_progressive/manifest.json`
- Chapter files: `api/data/grammaire_progressive/chapter_NN_slug.json`
- Pre-rendered pages: `/tmp/grammaire_pages/page_NNN.jpg` (render with script below)

## Page Rendering
Before each ingestion session, render the needed pages:
```python
import fitz
doc = fitz.open("grammaire progressive du Francais avance -- CLE -- 2008 -- CLE -- 49370898753e6cd5c65d0931683df7d2 -- Anna's Archive.pdf")
for pg in range(START, END):  # 0-indexed
    pix = doc.load_page(pg).get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    pix.save(f"/tmp/grammaire_pages/page_{pg+1:03d}.jpg")
```

To view book page N: read `/tmp/grammaire_pages/page_{N-1:03d}.jpg` (because pdf_page = book_page - 1 in 1-indexed terms, but file is named by pdf 1-indexed page).

## Chapter JSON Schema
```json
{
  "book": "Grammaire Progressive du Français - Niveau Avancé",
  "chapter_number": 1,
  "chapter_title": "L'ARTICLE",
  "book_pages": [8, 9, ...],
  "sections": [
    {
      "section_title": "L'ARTICLE DÉFINI",
      "subtitle": "«le», «la», «l'», «les»",
      "book_pages": [8, 9, 10, 11],
      "intro_examples": ["Le printemps est ma saison préférée.", ...],
      "grammar_rules": [
        {
          "rule": "Description of the rule",
          "examples": ["Example sentence."],
          "categories": [
            { "label": "category name", "examples": ["..."] }
          ],
          "notes": ["Exception or warning text"]
        }
      ],
      "exercises": [
        {
          "exercise_number": 1,
          "book_page": 9,
          "instruction": "Complétez avec...",
          "type": "fill_blank | composition | matching | transformation | dialogue | free_response | underline",
          "context": "any setup text or null",
          "starter": "Beginning of answer if provided",
          "items": [
            { "number": 1, "text": "_____ phrase with blanks", "blanks": 3 }
          ],
          "columns": { "left": [...], "right": [...] }
        }
      ]
    }
  ],
  "ingestion_status": {
    "pages_completed": [8, 9, 10, 11, 12, 13],
    "pages_remaining": [],
    "last_updated": "2026-02-27"
  }
}
```

## Extraction Rules
1. **Preserve ALL French text with accents**: é, è, ê, ë, à, â, ù, û, ü, ô, î, ï, ç
2. **Never translate** — everything stays in French
3. **Blanks**: Represent fill-in-the-blank spaces as `_____`
4. **Exercise types**: Classify each exercise by its actual format
5. **Ignore bleed-through**: Scanned pages may show faded reversed text from the other side — skip it
6. **Grammar rules vs page 2**: If a section's grammar spans 2+ pages, combine all rules into one `grammar_rules` array
7. **Bilans**: Extract bilan exercises the same way as chapter exercises, with `"type": "bilan"`

## Task List (effort-aware)

### Batch 1: Finish Chapter 1 + Chapters 2-3 — DONE
### Batch 2: Bilan 1 + Chapter 4 — DONE
### Batch 3: Chapters 5-6 + Bilans 2-3 — DONE
### Batch 4: Chapters 7-13 + Bilan 4 — DONE
### Batch 5: Chapters 14-16 + Bilan 5 — DONE
### Batch 6: Chapters 17-19 + Bilan 6 — DONE
### Batch 7: Chapters 20-23 + Bilan 7 — DONE
### Batch 8: Chapters 24-27 + Bilan 8 — DONE
### Batch 9: Annexes + Index — DONE
### Batch 10: Integration — DONE
- [x] Write script: `api/scripts/load_grammaire_progressive.py`
- [x] Created "Grammaire Progressive B2" language track (ID: 5eba8cda-1cbf-4d07-b770-1204a7b54a75)
- [x] Loaded 27 book_content rows linked to track
- [x] Verified: track + book_content queryable, summaries + key_concepts populated
- [x] System auto-wires: daily exercise generation already pulls book_content by language_track_id

## Final Stats
- 37 JSON files, 185 pages, 364 grammar rules, 350 exercises, 1,359 items
- 28 conjugation tables, 94 index entries
- Track: 27 topics (chapters), B2 level, French

## Verification
After each batch:
1. `python -c "import json; json.load(open('file.json'))"` — valid JSON
2. Spot-check: compare extracted text against page images for 2-3 random pages
3. Count exercises and blanks — should match what's visible on the page
