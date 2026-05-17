# KDP Publishing SOP — Breathline Books
## Standard Operating Procedure for Publishing on Amazon KDP
### Author: Kenneth Mangum | Imprint: Breathline Books

**Created:** April 20, 2026
**Based on:** Book 1 (Strategic Finance For Growth) publishing experience
**Purpose:** Repeat this exact process for Books 2-5 with minimal iteration

---

## OVERVIEW

Each book requires THREE KDP listings (created in this order):
1. **Kindle eBook** (EPUB upload, 70% royalty)
2. **Paperback** (PDF interior + full wrap cover PDF)
3. **Hardcover** (same PDF interior + larger wrap cover PDF)

**Total time per book:** ~2-3 hours (Tiger prep) + ~30 min (Kenneth KDP upload)
**Total cost per book:** ~$5-7 Grok API for images

---

## PHASE 1: MANUSCRIPT PREPARATION

### 1.1 Content Polish
- Source: `books/kdp/XX_bookname/v1.0/manuscript_v1.0.md`
- Run Editorial Board v1.1 upgrade (optional but recommended for flagship quality)
- Output: `manuscript_v1.1.md`

### 1.2 Pre-Publication Checklist
Run these checks on the final manuscript BEFORE generating any output files:

```bash
# Zero edit markers
grep -c '<!-- NEW' manuscript.md  # Must be 0

# Zero TODOs
grep -ci 'TODO\|FIXME\|TBD' manuscript.md  # Must be 0

# Zero "fractional" (unless legitimate context)
grep -ci 'fractional' manuscript.md

# ISBN inserted (or "Pending" if not yet assigned)
grep 'ISBN' manuscript.md

# "Other Books" section removed (until other books are published)
grep -c 'Other Books' manuscript.md  # Must be 0 for first book

# Front matter present
grep -c 'Dedication\|Table of Contents\|Preface\|Copyright' manuscript.md

# Back matter present  
grep -c 'About the Author\|Connect\|Glossary' manuscript.md
```

### 1.3 Markdown Formatting Rules (learned the hard way)
- **Bullets after bold headers:** MUST have a blank line between `**Header:**` and first `- bullet`
- **Image references:** Use `![Alt Text](filename.png)` in the markdown — NOT manual HTML embedding
- **Page breaks:** Use `\newpage` — the build script converts to CSS page breaks
- **Checkboxes:** `- [ ]` gets converted to plain `- ` during build
- **Stage dividers/cards:** Embed directly in manuscript at correct positions — do NOT try to insert via regex in the build script

---

## PHASE 2: IMAGE GENERATION

### 2.1 Strategy (Hybrid Approach)
| Category | Tool | Why |
|---|---|---|
| Data charts, tables, matrices with specific numbers | **Python matplotlib** | Zero AI hallucination risk, pixel-perfect data |
| Framework diagrams, flowcharts, conceptual | **Grok Imagine Pro API** (`grok-imagine-image-pro`, $0.07/image) | Executive visual quality |

### 2.2 Grok Imagine Pro — Master Prompt Template
```
Ultra-clean minimalist professional business diagram. Navy #1B2A4A, 
gold #C5A55A, white #FFFFFF background. SHORT labels only — no sentences. 
Perfect spelling. No watermarks, no branding text. 300 DPI print quality. 
Self-explanatory diagram.

[SPECIFIC DIAGRAM DESCRIPTION WITH EVERY TEXT ELEMENT LISTED VERBATIM]
```

### 2.3 Critical Rules for AI Image Generation
1. **NEVER** include "Mangum Executive Series" in prompts — it leaks into visible text
2. **ULTRA-MINIMAL TEXT** — titles and single-word labels only. Book text explains; image shows structure
3. **List EVERY text element verbatim** in the prompt — AI spells exactly what you specify
4. **WHITE background only** — no photos, no office backgrounds
5. Use **`grok-imagine-image-pro`** model (NOT `grok-imagine-image`) — $0.07 vs $0.02, significantly better quality
6. **3-4 second delays** between API calls to avoid rate limits (30 rpm for pro)
7. For RACI matrices, BCG quadrants, 9-box grids — **USE MATPLOTLIB**, not AI. AI fundamentally cannot do one-value-per-cell logic.

### 2.4 API Setup
```python
import subprocess, requests, os, time

result = subprocess.run(['bash', '-c', 'source ~/.bashrc && echo $XAI_API_KEY'], 
                       capture_output=True, text=True)
api_key = result.stdout.strip()

# For direct bash scripts:
# export XAI_API_KEY=$(grep XAI_API_KEY /home/kmangum/.bashrc | head -1 | cut -d'"' -f2)

def gen_pro(prompt, filename, output_dir):
    STYLE = "Ultra-clean minimalist business diagram. Navy #1B2A4A, gold #C5A55A, white #FFFFFF background. SHORT labels only. Perfect spelling. No watermarks. 300 DPI."
    full = STYLE + " " + prompt
    r = requests.post("https://api.x.ai/v1/images/generations",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json={"model": "grok-imagine-image-pro", "prompt": full, "n": 1}, timeout=180)
    d = r.json()
    if 'data' in d and d['data']:
        url = d['data'][0].get('url','')
        if url:
            img = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
            path = os.path.join(output_dir, filename)
            with open(path, 'wb') as f: f.write(img.content)
            return True
    return False
```

### 2.5 Image QC Process
After generating all images:
1. Count total: should match visual plan
2. Check for `test_*` or `sample_*` files — delete
3. Human review: scan each image for misspellings, wrong structure, prompt text leaks
4. Archive replaced versions in `archive_vN/` subdirectories
5. Keep only the best version of each image in the main images/ folder

---

## PHASE 3: FILE GENERATION

### 3.1 Interior PDF (for Paperback AND Hardcover — same file)

**Specs:**
- Page size: 6 × 9 inches
- Margins: 0.75" top, 0.5" outside, **0.75" bottom** (not 0.5" — page numbers need room), 0.75" inside (gutter)
- Font: Georgia 11pt body, navy (#1B2A4A) headings
- Page numbers: centered at bottom, suppressed on page 1
- Chapter headings (h1): page-break-before: always
- Section headings (h2): NO page-break-before (causes too many blank pages)
- Images: max-width 100%, centered, with caption

**Key CSS:**
```css
@page { 
    size: 6in 9in; 
    margin: 0.75in 0.5in 0.75in 0.75in;
    @bottom-center { content: counter(page); font-family: Georgia; font-size: 9pt; color: #666; }
}
@page :first { @bottom-center { content: none; } }

h1 { page-break-before: always; }  /* Chapters get new pages */
h1:first-of-type { page-break-before: avoid; }  /* Title page doesn't break */
h2 { /* NO page-break-before */ }  /* Sections flow naturally */

/* CRITICAL for bullet lists */
ul, ol { margin: 8pt 0 12pt 0; padding-left: 24pt; }
li { margin-bottom: 6pt; line-height: 1.5; }
```

**Build tool:** WeasyPrint (`/tmp/pdfgen/bin/python` with `/tmp/pdfgen/lib/python3.12/site-packages`)

**Image embedding strategy:**
- Inline images (dividers, cards, manual placements): embedded directly in manuscript markdown as `![alt](filename.png)` — build script converts paths to absolute `file://` URLs
- Figure/table references: regex finds `See Figure X.Y` in HTML and appends `<img>` tag after the paragraph

### 3.2 EPUB (for Kindle eBook)

**Build tool:** `ebooklib` Python library

**Key settings:**
```python
book.set_identifier('isbn-XXXXXXXXXXXXX')
book.set_title('Book Title')
book.set_language('en')
book.add_author('Kenneth Mangum')
book.add_metadata('DC', 'publisher', 'Breathline Books')
```

**Image handling:** All images added as `epub.EpubImage()` items, referenced as `images/filename.png` in chapter HTML

**Split into chapters** at `# ` (h1) headings — each becomes a separate XHTML file in the EPUB

### 3.3 Cover — Front Only (for Kindle eBook)

**Specs:** 1800 × 2700 px minimum (300 DPI at 6×9)
**Format:** JPG (KDP requires JPG/TIFF for ebook covers)
**Tool:** Grok Imagine Pro API, then upscale with PIL if needed:

```python
from PIL import Image
img = Image.open('cover_front.png')
img = img.convert('RGB')
img_up = img.resize((1800, 2700), Image.LANCZOS)
img_up.save('cover_KDP.jpg', 'JPEG', quality=95, dpi=(300, 300))
```

### 3.4 Cover — Full Wrap (for Paperback)

**Dimensions:** Get EXACT size from KDP Cover Calculator (kdp.amazon.com/cover-calculator)
- Select: Paperback, trim 6×9, white/cream paper, page count
- KDP gives you exact width × height in inches
- **DO NOT calculate manually** — always use their calculator, it changes based on page count

**Format:** PDF, 300 DPI
**Layout:** Back cover (left) + Spine (center) + Front cover (right)
**Spine text:** Reads top-to-bottom: "BOOK TITLE" + "AUTHOR NAME"
**Back cover:** Gold headline, description bullets, author credentials, Breathline Books, white barcode area
**Barcode area:** Leave white rectangle ~450×300px in bottom-right of back cover — KDP overlays their barcode

### 3.5 Cover — Full Wrap (for Hardcover)

**DIFFERENT dimensions than paperback** — hardcover has board overhang and case wrap
- Get EXACT size from KDP Cover Calculator selecting **Hardcover**
- Hardcover covers are significantly larger (typically ~14" × 10.4" vs ~12.8" × 9.25" for paperback)
- **Spine is wider** for hardcover (includes board thickness)
- Use the EXACT dimensions KDP tells you — even a 0.1" difference will be rejected

**Same layout as paperback** but scaled to the larger dimensions

---

## PHASE 4: KDP UPLOAD

### 4.1 Kindle eBook (do first)

1. kdp.amazon.com → Bookshelf → **+ Create** → **Kindle eBook**
2. **Book Details:**
   - Title, subtitle, author
   - Description: from metadata.md
   - Publishing rights: "I own the copyright"
   - Keywords: 7 keywords from metadata.md
   - Categories: 3 placements (use Strategic Management, Corporate Finance > Valuation, Entrepreneurship > Management as baseline)
3. **Content:**
   - Upload EPUB as manuscript
   - Cover: upload JPG (`cover_KDP.jpg`)
   - DRM: No
   - AI-Generated Content: **Yes**
4. **Pricing:** (Agentic AI Playbooks SERIES STANDARD — LOCKED;
   matches live Books 1–3; applies to ALL books in the series)
   - Royalty: **70%** (for prices $2.99-$9.99)
   - US price: **$6.99**
   - Other markets: auto-calculate

### 4.2 Paperback (do second)

1. Same Bookshelf → under the ebook listing → **+ Create Paperback**
2. **Book Details:** Auto-populated from ebook — verify
3. **Content:**
   - ISBN: **Get free KDP ISBN**
   - Ink: **Standard color interior with white paper** (for books with color images)
   - Trim: **6 × 9 in**
   - Bleed: **No Bleed**
   - Cover finish: **Matte** (executive/professional look)
   - Upload interior PDF
   - Upload cover PDF (full wrap, exact KDP calculator dimensions)
   - AI Content: **Yes**
4. **Pricing:** (series standard — LOCKED)
   - US price: **$14.99**
   - Other markets: auto-calculate
   - Expanded distribution: optional (enable later)

### 4.3 Hardcover (do third)

1. Same Bookshelf → under the ebook listing → **+ Create Hardcover**
2. **Content:**
   - Same interior PDF as paperback
   - **DIFFERENT cover PDF** — hardcover dimensions from KDP calculator
   - If cover size is rejected, read the EXACT expected dimensions from the error message and regenerate
3. **Pricing:** (series standard — LOCKED)
   - US price: **$24.99**

### 4.4 After Publishing

- Amazon reviews: **24-72 hours** per format
- Once live, get the Amazon product URL
- Update mangumcfo.com: add buy link to book preview page
- Update LinkedIn: add to Publications section
- Order author copies for gifting

---

## PHASE 5: POST-PUBLISH UPDATES

### 5.1 Update mangumcfo.com
```bash
# Copy final PDF to website
cp .../final/Strategic_Finance_For_Growth_PRINT.pdf /home/kmangum/Documents/mangumcfo.com/BookTitle.pdf

# Deploy
cd /home/kmangum/Documents/mangumcfo.com && npx netlify-cli deploy --prod --dir=.
```

### 5.2 Update Job Search Tracker
Update `books published` count in TRACKER.md

### 5.3 ISBN Tracking
Record each ISBN in a central location:
| Book | Format | ISBN | KDP ASIN |
|------|--------|------|----------|
| Strategic Finance For Growth | Paperback | 979-8-258-22082-0 | (after live) |
| Strategic Finance For Growth | Kindle | (KDP assigns ASIN) | |

---

## FILE STRUCTURE (per book)

```
books/kdp/XX_bookname/
├── raw_extracted.txt              ← original PDF text extraction
├── v1.0/
│   ├── manuscript_v1.0.md         ← first polish
│   ├── metadata_v1.0.md
│   ├── visual_plan_v1.0.md
│   └── cover_prompts_v1.0.md
├── v1.1/
│   ├── manuscript_v1.1.md         ← editorial board upgrade
│   ├── metadata_v1.1.md
│   ├── visual_plan_v1.1.md
│   ├── editorial_board_report.md
│   └── images/                    ← production images (best version only)
│       ├── fig_0_1_lifecycle.png
│       ├── ...
│       ├── archive_v1/            ← replaced v1 originals
│       ├── archive_v2/            ← replaced v2
│       └── archive_v3/            ← replaced v3
├── v1.2/
│   ├── images/                    ← pro model regeneration (if done)
│   └── final/                     ← UPLOAD THESE FILES
│       ├── BookTitle_PRINT.pdf    ← interior (paperback + hardcover)
│       ├── BookTitle.epub          ← Kindle ebook
│       ├── cover_KDP.png          ← front cover (1800x2700)
│       ├── cover_KDP.jpg          ← front cover JPG for ebook upload
│       ├── cover_full_wrap.pdf    ← paperback wrap cover
│       └── cover_hardcover_wrap.pdf ← hardcover wrap cover
```

---

## COMMON ERRORS & FIXES

| Error | Cause | Fix |
|---|---|---|
| "Cover size mismatch" | Dimensions don't match KDP calculator | Use EXACT dimensions from KDP Cover Calculator or error message |
| "Text outside margins" | Page numbers too close to edge | Increase bottom margin to 0.75" |
| Bullets render as paragraph | No blank line between bold header and first bullet in markdown | Add blank line before `- ` items |
| Images bunched at top | Regex inserts at first text match (TOC) | Embed images directly in manuscript markdown, not via build script |
| "Mangum Executive Series" in image | Prompt text leaks into AI output | Remove that phrase from all prompts |
| RACI shows all letters per cell | AI can't do one-value-per-cell logic | Use matplotlib, not AI |
| Missing images in PDF | Regex didn't match reference text | Add manual `![alt](file.png)` in manuscript at correct location |

---

## PRICING SUMMARY

| Format | Price | Royalty Rate | Est. Royalty/Copy |
|---|---|---|---|
| Kindle eBook | $9.99 | 70% | ~$6.60 |
| Paperback (color) | $24.99 | 60% | ~$5-7 |
| Hardcover (color) | $34.99 | Fixed | ~$6-8 |

---

## TOOLS REQUIRED

| Tool | Location | Purpose |
|---|---|---|
| WeasyPrint | `/tmp/pdfgen/bin/python` | HTML → PDF conversion |
| matplotlib | same venv | Data charts/tables |
| ebooklib | same venv | EPUB generation |
| Pillow (PIL) | same venv | Cover image manipulation |
| Grok Imagine Pro API | xAI API (`$XAI_API_KEY` in ~/.bashrc) | Framework diagrams |
| Netlify CLI | `npx netlify-cli` | Website deployment |
| markdown (Python) | same venv | Markdown → HTML |

---

*This SOP was created from the Book 1 publishing experience. Apply to Books 2-5 with the same process — the manuscript and images are already at v1.0 for all four books.*
