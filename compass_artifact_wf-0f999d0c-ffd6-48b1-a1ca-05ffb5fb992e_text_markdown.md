# reMarkable-to-NotebookLM pipeline: complete technical blueprint

**The pipeline is architecturally viable but faces one critical constraint: the official NotebookLM Enterprise API (v1alpha) exposes no chat/query endpoint.** Notebook CRUD and source management work via the Discovery Engine REST API, but actually querying sources for AI-grounded responses requires either the unofficial `notebooklm-py` library (cookie-based, fragile) or an alternative like the Gemini API with grounding. This single constraint shapes every architectural decision downstream. The remainder of this document provides exact specifications for every pipeline stage — authentication flows, library versions, function signatures, page dimensions, cost calculations, and error-handling patterns — ready for direct use in a Claude Code initialization document.

---

## reMarkable Cloud API: authentication and document sync

The reMarkable Cloud uses a **two-token JWT system**. A one-time registration code (generated at `https://my.remarkable.com/device/desktop/connect`) is exchanged for a permanent device token, which then produces short-lived user tokens for API calls.

**Step 1 — Device registration (one-time):**
```
POST https://webapp-production-dot-remarkable-production.appspot.com/token/json/2/device/new
Headers: Authorization: Bearer  (empty), Content-Type: application/json
Body: {"code": "<8-char-code>", "deviceDesc": "desktop-linux", "deviceID": "<uuid4>"}
Response: Plain text JWT (store permanently)
```

**Step 2 — User token renewal (per session, ~24h expiry):**
```
POST https://webapp-production-dot-remarkable-production.appspot.com/token/json/2/user/new
Headers: Authorization: Bearer <device_token>
Body: empty
Response: Plain text JWT
```

All subsequent calls use `Authorization: Bearer <user_token>`. The document storage base URL is `https://document-storage-production-dot-remarkable-production.appspot.com`. Key endpoints on this base:

- **List documents:** `GET /document-storage/json/2/docs?withBlob=true` — returns JSON array with `BlobURLGet` (signed GCS URL) for each doc
- **Download:** `GET <BlobURLGet>` — returns ZIP archive, no auth needed
- **Upload (3 steps):** `PUT /document-storage/json/2/upload/request` → upload ZIP to `BlobURLPut` → `PUT /document-storage/json/2/upload/update-status`
- **Delete:** `PUT /document-storage/json/2/delete` with `[{"ID": "<uuid>", "Version": <n>}]`

The ZIP archive structure contains `{uuid}.content` (JSON with page UUIDs, fileType), `{uuid}.pagedata` (template names), `{uuid}/{page-uuid}.rm` (binary stroke files), and `{uuid}.thumbnails/{page-uuid}.jpg`. Note the API field `VissibleName` — this typo is in the actual API, not a documentation error.

**Critical: sync protocol versions.** Accounts are being migrated from the old flat-REST API to **sync 1.5**, a hash-based content-addressable protocol with incremental diffs. The Python library `rmapy` (v0.3.1, `pip install rmapy`) **only supports the old API** and will fail on sync15-migrated accounts. The newer library **`rm-api`** (v1.1.1, `pip install rm-api`, released June 2025, Python ≥3.9) supports the current protocol including sync15. For async usage, `rmcl` (v0.4.2, `pip install rmcl`) uses `trio` but is also aging. **Recommendation: use `rm-api` for cloud operations.** No official rate limits are documented; community consensus is to avoid rapid bulk requests.

---

## Parsing .rm files with rmscene and rendering with rmc

**rmscene** (v0.7.0, March 2025, `pip install rmscene`, Python ≥3.10) parses the current v6 `.rm` binary format used by firmware 3.x+. This format is fundamentally different from the older v3/v5 formats — it uses tagged blocks with CRDT sequences to support both handwriting strokes and typed text.

```python
from rmscene import read_tree
with open("page.rm", "rb") as f:
    tree = read_tree(f)  # Returns SceneTree with groups/layers
```

Key capabilities: all **21 pen types** supported (ballpoint, fineliner, marker, highlighter, calligraphy, pencil, mechanical pencil, eraser, plus v2 variants), **layers** via SceneTree groups, **typed text** via CRDT sequences (the library's original motivation), **bold/italic formatting** since v0.4.0 (firmware 3.3+), and **highlighted text in PDFs** via GlyphRange. Unrecognized data from newer firmware degrades gracefully via `UnreadableBlock` rather than crashing. For low-level access, `read_blocks(f)` returns raw Block objects including `SceneLineItemBlock`, `RootTextBlock`, `PageInfoBlock`, and `SceneGroupItemBlock`.

**rmc** (v0.3.0 on GitHub, `pip install git+https://github.com/ricklupton/rmc.git` for latest, Python ≥3.10) converts .rm files to SVG, PDF, or Markdown:

```bash
rmc -t svg -o page.svg page.rm    # Render strokes as SVG
rmc -t markdown page.rm            # Extract text
rmc -t pdf -o page.pdf page.rm     # Render as PDF
```

The page coordinate space is **1404×1872 pixels** (width × height). Known limitation: text boxes with multi-line content may render on a single line, and stroke positions near text boxes can be corrupted.

**For the OCR pipeline, the recommended approach is:** extract the `.rm` file from the ZIP, use rmscene to check if the page has handwriting strokes (SceneLineItemBlock) or only typed text (RootTextBlock/CrdtSequence). For typed text, extract directly — no OCR needed. For handwriting, render to PNG via rmc or direct SVG→PNG conversion, then send to a vision LLM.

---

## The NotebookLM API gap and how to work around it

**The official NotebookLM Enterprise API (v1alpha, released September 2025) does not expose a chat or query endpoint.** It covers only notebook CRUD, source management (add/get/delete/upload), audio overview generation, and a standalone podcast API. The base URL is `https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_NUMBER}/locations/{LOCATION}/notebooks`. Authentication uses OAuth2 via `gcloud auth print-access-token`. Required IAM roles include `Cloud NotebookLM Admin` and `Cloud NotebookLM User`, and the Discovery Engine API must be enabled.

The API supports creating notebooks (`POST .../notebooks`), adding sources via Google Drive (`sources:batchCreate` with `googleDriveContent`), direct file upload (`sources:uploadFile` supporting PDF, TXT, MD, DOCX, PPTX, XLSX, audio, images up to 200MB), and sharing notebooks. **But there is no `notebooks.query` or `notebooks.chat` endpoint** — chat is web-UI only.

This creates three architectural paths:

**Path A — Unofficial `notebooklm-py` (v0.3.0, `pip install "notebooklm-py[browser]"`):** This library reverse-engineers Google's internal `batchexecute` RPC protocol with obfuscated method IDs to target the consumer NotebookLM at notebooklm.google.com. It provides the **full API surface including chat:**

```python
from notebooklm import NotebookLMClient
async with await NotebookLMClient.from_storage() as client:
    notebooks = await client.notebooks.list()
    nb = await client.notebooks.create("Research")
    await client.sources.add_text(nb.id, "OCR'd text content")
    result = await client.chat.ask(nb.id, "Summarize the key points")
    print(result.answer)  # Grounded in loaded sources
```

Authentication requires browser-based Google login (`notebooklm login` opens Playwright Chromium) which extracts session cookies (`SID`, `HSID`, `SSID`, `APISID`, `SAPISID`, `__Secure-1PSID`, `__Secure-3PSID`) to `~/.notebooklm/storage_state.json`. **Cookies expire every 1–2 weeks**, requiring re-authentication. For CI, set `NOTEBOOKLM_AUTH_JSON` environment variable. The library has **968 GitHub stars**, 397 commits, and active development — but relies on undocumented, obfuscated RPC method IDs that Google can break at any time. **Best for prototypes, not production.**

**Path B — NotebookLM Enterprise API + manual chat:** Use the official API for notebook/source management, then rely on the web UI for querying. This is production-grade for everything except the chat step.

**Path C — Gemini API with grounding (recommended alternative for production):** Use Google's Gemini API directly with document grounding capabilities. Upload documents to Google Cloud Storage, use Gemini's document understanding features. Different product but similar RAG-over-documents capability, fully official API, and far more reliable.

Additionally, `dandye/notebooklm_sdk` wraps the official Enterprise API in Python with Application Default Credentials, but inherits the same no-chat limitation.

---

## Vision-LLM OCR: model comparison and optimal prompting

For converting reMarkable handwriting renders (black strokes on white background, 1404×1872px at 226 DPI) to text, three providers were evaluated:

| Model | Input cost/page | Output cost (~500 tokens) | Total/page | Handwriting quality |
|-------|----------------|--------------------------|------------|-------------------|
| **Gemini 2.5 Flash** | ~$0.0002 | ~$0.0018 | **$0.002** | Good, free tier available |
| GPT-4o-mini | ~$0.0002 | ~$0.0003 | **$0.0005** | Adequate for clean writing |
| GPT-4o | ~$0.003 | ~$0.005 | ~$0.008 | Best general handwriting |
| Claude Haiku 4.5 | ~$0.0025 | ~$0.0025 | ~$0.005 | Good, fast |
| Claude Sonnet 4.5 | ~$0.007 | ~$0.0075 | ~$0.015 | Best for complex layouts |

**GPT-4o** achieves the most reliable handwriting recognition across styles. **Gemini 2.5 Flash** offers the best cost efficiency with a free tier for development. **Claude Sonnet 4.5** excels at structured layouts, diagrams, and mathematical notation. Note that Claude auto-resizes images where the long edge exceeds **1568px** — since reMarkable's 1872px height exceeds this, images will be resized server-side. Pre-resize to ≤1568px on the long edge to control quality.

**Optimal OCR prompt** (tested across providers):
```
System: You are the world's greatest transcriber of handwritten notes.

User: Transcribe the handwritten text from this image accurately. This is from 
a digital e-ink tablet (black ink on white background).

Rules:
- Transcribe EXACTLY what is written — do not add, remove, or correct words
- Preserve paragraph breaks, bullet points, numbered lists, and indentation
- For mathematical notation, use LaTeX: inline $...$ and display $$...$$
- For diagrams, arrows, or drawings, describe in [brackets]
- If a word is ambiguous, use context to make your best guess
- Output ONLY the transcribed text, no commentary
```

**Image preprocessing pipeline** (critical for quality):
```python
from PIL import Image, ImageEnhance

def preprocess_remarkable_image(image_path):
    img = Image.open(image_path)
    if img.mode != 'L':
        img = img.convert('L')
    # Crop left toolbar (~120px) and margins (~40px)
    w, h = img.size
    img = img.crop((120, 40, w - 40, h - 40))
    # Boost contrast 50% for light pencil strokes
    img = ImageEnhance.Contrast(img).enhance(1.5)
    # Resize to fit within 1568px (prevents Claude server-side resize)
    if max(img.size) > 1568:
        ratio = 1568 / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)
    return img  # Save as PNG (lossless, best for line art)
```

Key preprocessing findings: **keep grayscale** (don't binarize — LLMs handle gradients well), **use PNG not JPEG** (lossless preserves stroke edges), **do not upscale** (226 DPI is sufficient for vision LLMs), and **always crop the 120px left toolbar** to reduce token cost and remove irrelevant UI elements.

---

## PDF generation with exact reMarkable 2 dimensions

The reMarkable 2 display is **1404 × 1872 pixels at 226 DPI**, giving physical dimensions of **6.212 × 8.283 inches** or **447.3 × 596.4 PDF points**. This is close to A5 but not a standard paper size.

```python
# Constants for all PDF generation
RM2_WIDTH_PT = 447.3    # 6.212 inches × 72 pt/inch
RM2_HEIGHT_PT = 596.4   # 8.283 inches × 72 pt/inch
RM2_WIDTH_MM = 157.8
RM2_HEIGHT_MM = 210.4
LEFT_MARGIN_PT = 72     # 1 inch — accounts for reMarkable left toolbar
RIGHT_MARGIN_PT = 18    # 0.25 inch
TOP_MARGIN_PT = 28
BOTTOM_MARGIN_PT = 28
```

**fpdf2** (`pip install fpdf2`) is recommended for this use case — zero dependencies, simple API, handles pagination automatically:

```python
from fpdf import FPDF

class RemarkablePDF(FPDF):
    def __init__(self):
        super().__init__(unit='mm', format=(157.8, 210.4))
        self.set_auto_page_break(auto=True, margin=7)
        self.set_left_margin(25)  # ~72pt for toolbar
        self.set_right_margin(5)

    def header(self):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(128)
        self.cell(0, 5, 'AI Response', align='R')
        self.ln(8)

    def footer(self):
        self.set_y(-10)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 5, f'Page {self.page_no()}', align='C')
```

For richer styled content (Markdown/HTML output from LLMs), use **WeasyPrint** (`pip install weasyprint`) with a CSS `@page` rule: `@page { size: 157.8mm 210.4mm; margin: 7mm 5mm 7mm 25mm; }`. For maximum layout control, **ReportLab** (`pip install reportlab`) provides Platypus flow layout with `SimpleDocTemplate(output, pagesize=(447.3, 596.4))`.

E-ink typography rules: **minimum 12pt font size**, **1.3–1.5× line spacing** (wider than print), **embed all fonts** (reMarkable has limited built-in fonts), prefer serif fonts (Liberation Serif, Noto Serif) for body text. Hyperlinks are not clickable. Color renders as 16 shades of gray. Maximum PDF file size is **100MB**.

---

## Google Drive as the intermediary layer

The `google-api-python-client` (v2.189.0) with `google-auth-oauthlib` (v1.31.0) handles all Drive operations. For the NotebookLM intermediary pattern, the pipeline uploads OCR'd text as Google Docs, then references them as sources.

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

**Scope selection:** Use `https://www.googleapis.com/auth/drive.file` (non-sensitive, only accesses app-created files) unless you need access to pre-existing files, which requires the restricted `https://www.googleapis.com/auth/drive` scope.

**Desktop OAuth flow** (for development):
```python
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/drive.file']
creds = None
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as f:
        f.write(creds.to_json())
service = build('drive', 'v3', credentials=creds)
```

**Key operation — upload string as Google Doc:**
```python
from googleapiclient.http import MediaInMemoryUpload

def upload_text_as_doc(service, content, name, folder_id=None):
    metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.document'}
    if folder_id:
        metadata['parents'] = [folder_id]
    media = MediaInMemoryUpload(content.encode('utf-8'), mimetype='text/plain', resumable=True)
    return service.files().create(body=metadata, media_body=media, fields='id,name,webViewLink').execute()
```

Access tokens expire after **1 hour**; refresh tokens are long-lived for Workspace/published apps but expire after **7 days** for external apps in testing mode. Service accounts have their own 15GB Drive and auto-manage tokens — files they create must be explicitly shared with the target user via `permissions().create()` with at minimum `reader` role.

For the NotebookLM Enterprise integration, the Google Doc's `id` field maps directly to the `documentId` in the `sources:batchCreate` call. The authenticated user must have read access to the doc. Run `gcloud auth login --enable-gdrive-access` to authorize Drive access for NotebookLM API calls.

---

## Workspace verification and NotebookLM Enterprise setup

**NotebookLM Enterprise is a separate Google Cloud product** — not the same as NotebookLM/NotebookLM Plus in Workspace. The consumer version (including Plus) became a Workspace core service in February 2025 for Business Standard, Business Plus, Enterprise Standard, Enterprise Plus, and Education Plus editions. The admin enables it at `Admin Console → Generative AI → NotebookLM`.

NotebookLM Enterprise is purchased through **Google Cloud Console** (not Workspace Admin), requires a GCP project with billing and the **Discovery Engine API** enabled (`discoveryengine.googleapis.com`). It offers the v1alpha REST API, VPC-SC compliance, data residency (US/EU), **300 sources per notebook** (vs ~50 consumer), audit logs, and CMEK encryption. A 14-day free trial provides 5,000 licenses.

Setup sequence: create GCP project → enable billing → enable Discovery Engine API → configure identity provider → assign IAM roles (`Cloud NotebookLM Admin`, `Cloud NotebookLM User`) → purchase licenses → distribute the unique Enterprise URL.

**To check if an account is Workspace:** navigate to `https://admin.google.com/` — only Workspace admins can access. Consumer @gmail.com accounts cannot. For API-based verification, the Admin SDK Directory API (`admin.googleapis.com`) returns user data for managed accounts and 403/404 for consumer accounts.

---

## Testing each pipeline stage

**reMarkable API mocking** uses the `responses` library (v0.25.x) to intercept `requests` calls:

```python
@responses.activate
def test_token_refresh_on_401():
    responses.add(responses.GET, DOCS_URL, status=401, body="Token is expired")
    responses.add(responses.POST, USER_TOKEN_URL, body="new-jwt-token", status=200)
    responses.add(responses.GET, DOCS_URL, json=[{"ID": "test", "Success": True}], status=200)
    client = RemarkableClient(device_token="dev-tok", user_token="expired-tok")
    docs = client.list_documents()
    assert len(responses.calls) == 3
```

For record/replay of real API interactions, `vcrpy` (v6.x+) with `pytest-recording` (v0.13.x) captures HTTP cassettes. Use `--vcr-record=none` in CI to fail if cassettes are missing.

**OCR quality verification** uses `jiwer` (v3.x, RapidFuzz backend) for Character Error Rate and Word Error Rate:

```python
from jiwer import cer, wer

@pytest.mark.parametrize("image,expected", KNOWN_SAMPLES)
def test_ocr_quality(image, expected):
    result = run_vision_llm_ocr(image)
    assert cer(expected, result) < 0.10  # <10% character error rate
    assert wer(expected, result) < 0.15  # <15% word error rate
```

Sample .rm files for testing come from the `rmscene` repo's `tests/` directory. The `rm-files` package (`github.com/jacob414/rm-files`) provides both fixtures and programmatic .rm file generation for synthetic test data.

---

## Error handling, retry patterns, and state management

Each pipeline stage has distinct failure modes requiring different strategies:

**Token refresh decorator** (generic pattern for reMarkable and Google):
```python
def auto_refresh_token(max_retries=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(self, *args, **kwargs)
                except AuthenticationError:
                    if attempt < max_retries:
                        self._refresh_token()
                    else:
                        raise
        return wrapper
    return decorator
```

**Retry with exponential backoff** via `tenacity` (for vision LLM and API calls):
```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

@retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=1, max=60, jitter=2),
       retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)))
def call_vision_llm(image_bytes, prompt):
    ...
```

**Circuit breaker** via `pybreaker` (prevents hammering downed services):
```python
import pybreaker
remarkable_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60, success_threshold=3)
```

**SQLite state tracking** prevents duplicate processing:
```sql
CREATE TABLE processed_pages (
    page_id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    ocr_text TEXT,
    notebooklm_notebook_id TEXT,
    pdf_uploaded BOOLEAN DEFAULT FALSE,
    processed_at TEXT NOT NULL,
    version INTEGER NOT NULL
);
```

Use SHA-256 content hashing on .rm file bytes to detect changes. Always fetch the latest document version before uploading — reMarkable requires `Version = server_version + 1` and returns `"Version on server is not -1 of what you supplied"` on mismatch.

**Blank page detection:** Check if rmscene's `read_tree()` returns an empty scene tree (no SceneLineItemBlock items). Pages with only templates or eraser marks should be skipped. Pages with only typed text (RootTextBlock present, no stroke items) should use direct text extraction from rmscene rather than OCR. Use **structlog** for structured JSON logging in production, with context binding per page/notebook for traceability.

## Conclusion

The pipeline's architecture hinges on one decision: **how to get AI responses grounded in NotebookLM sources**. The official Enterprise API handles everything except chat — so production deployments should either accept that limitation and use the Enterprise API for source management while routing queries through the Gemini API with grounding, or accept the fragility of `notebooklm-py`'s cookie-based approach for the full NotebookLM experience. The reMarkable side is well-served by `rm-api` (cloud sync) + `rmscene` (parsing) + vision LLM OCR, with `fpdf2` generating correctly-dimensioned response PDFs at 447.3 × 596.4 points with a 72-point left margin. Every component has exact library versions, authentication flows, and code patterns documented above — sufficient to begin implementation in Claude Code immediately.