# ReFind

> **Find what you remember.**  
> Built by team **BitByBit**

ReFind is a privacy-focused, AI-powered contextual memory and personal search engine. It bridges the gap between human memory (fuzzy, contextual clues like person, rough time, visual appearance, subject keywords) and digital file retrieval.

Instead of requiring exact filenames or folders, ReFind understands natural queries like:
> *“Find the architecture PDF Rahul sent me around February. It had PostgreSQL and BLE.”*  
> *“Find the file containing the word sustainability.”*  
> *“Find that document where I wrote about databases.”*

It retrieves matching files through a **5-signal hybrid retrieval pipeline** (vector search, keyword search, filename relevance, metadata matching, and Jina reranking) and explains why each document matched using grounded **Gemini 2.5 Flash Lite** reasoning.

---

## 👥 Team Setup & Quick Start

Welcome to ReFind! Do NOT commit real API keys to Git.

### 1. Clone the Repository
```bash
git clone https://github.com/joyelshajii/ReFind.git
cd ReFind
```

### 2. Configure Your Local Environment Variables
Create your own local `.env` from the provided `.env.example`:

**Windows:**
```powershell
copy .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Open `.env` and fill in your keys:
```env
# AI & Embedding Providers (Free Tiers)
GEMINI_API_KEY=your_gemini_api_key_here
JINA_API_KEY=your_jina_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-2

# Database Configuration (Optional: Leave empty for zero-config SQLite + vector store)
DATABASE_URL=
```
*(The `.env` file is ignored by `.gitignore` and must never be committed).*

---

### 3. Install Backend Dependencies & Start FastAPI
Open your first terminal:
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*The backend starts at `http://127.0.0.1:8000` with interactive API docs at `http://127.0.0.1:8000/docs`.*

---

### 4. Install Frontend Dependencies & Start Next.js
Open a second terminal:
```bash
cd frontend
npm install
npm run dev
```
*(On Windows PowerShell, use `npm.cmd install` and `npm.cmd run dev` if script execution policies apply).*

Open your browser at:
```
http://localhost:3000
```

---

## 🏗️ AI-Powered Hybrid Search Pipeline

```text
                     User Query
                         │
                         ▼
              Gemini Query Understanding
                 (gemini-2.5-flash-lite)
                         │
                ┌────────┴────────┐
                ▼                 ▼
         Vector Search       Keyword Search
      (Gemini Embedding 2)  (PostgreSQL / FTS)
                │                 │
                └────────┬────────┘
                         ▼
                  Merge Candidates
                 (Deduplicated Pool)
                         │
                         ▼
                    Jina Reranker
           (jina-reranker-v2-multilingual)
                         │
                         ▼
               Grounded Explanation
                 (gemini-2.5-flash-lite)
                         │
                         ▼
                 Top Ranked Results
```

### 5-Signal Scoring Formula
$$\text{Score} = w_{\text{sem}} \cdot S_{\text{semantic}} + w_{\text{rerank}} \cdot S_{\text{reranker}} + w_{\text{kw}} \cdot S_{\text{keyword}} + w_{\text{meta}} \cdot S_{\text{metadata}} + w_{\text{fn}} \cdot S_{\text{filename}}$$

Configured in `backend/app/core/config.py`:
- `WEIGHT_SEMANTIC = 0.45`
- `WEIGHT_RERANKER = 0.20`
- `WEIGHT_KEYWORD = 0.15`
- `WEIGHT_METADATA = 0.10`
- `WEIGHT_FILENAME = 0.10`

---

## 🛡️ Privacy & Local-First Ingestion
- **Local Text Extraction**: PDFs processed locally using **PyMuPDF**, Word documents via **python-docx**, presentations via **python-pptx**, and text files natively.
- **Local OCR**: Scanned PDFs and images (PNG, JPG, JPEG) are OCR-processed locally via **PaddleOCR** / **pytesseract**.
- **No Document Uploads**: Entire documents are **never** uploaded to external AI services for indexing.
- **Minimal API Payloads**: Only compact search queries, document chunks, and retrieved context snippets are passed to Gemini / Jina.
- **Change Tracking & Caching**: SHA-256 file hashing prevents regenerating embeddings for unchanged documents.
- **Zero-Downtime Fallback**: If Gemini or Jina is temporarily unavailable or rate-limited, ReFind gracefully degrades to local regex query understanding and hybrid retrieval without throwing runtime errors.

---

## 🗄️ Database & Vector Search Engine

ReFind supports two database setups seamlessly:

1. **Zero-Configuration Mode (Default)**:
   - Uses local SQLite with 768-dimensional dense vector similarity. Runs out of the box with zero external database configuration.

2. **Production PostgreSQL + pgvector**:
   - Start the container using Docker:
     ```bash
     docker compose up -d
     ```
   - Set in `.env`:
     ```env
     DATABASE_URL=postgresql://refind_user:refind_password@localhost:5432/refind_db
     ```
   - ReFind will automatically enable the `vector` extension and utilize native pgvector indexing.

---

## 🔍 Hybrid Retrieval Formula

Results are evaluated across four weighted dimensions:

$$\text{Score} = w_{\text{sem}} \cdot S_{\text{semantic}} + w_{\text{kw}} \cdot S_{\text{keyword}} + w_{\text{meta}} \cdot S_{\text{metadata}} + w_{\text{ent}} \cdot S_{\text{entity}}$$

- **Semantic Similarity ($w = 0.35$):** Cosine similarity between query embedding and document/chunk vectors.
- **Keyword Relevance ($w = 0.25$):** Token and term frequency matching across content and filenames.
- **Metadata Relevance ($w = 0.20$):** Format matching (.pdf, .docx, .png) and temporal proximity (month/year).
- **Entity Relevance ($w = 0.20$):** Overlap with extracted people (`Rahul`), technologies (`PostgreSQL`, `BLE`), and topics (`Architecture`).

---

## 🧪 Running Automated Tests

Run the full pytest suite from the `backend/` directory:
```bash
cd backend
python -m pytest tests/test_refind.py -v
python -m pytest tests/test_ai_pipeline.py -v
```
