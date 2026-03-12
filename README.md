# Intelli-Credit — AI-Powered Corporate Credit Appraisal Engine

> **Hackathon Solution** for the "Intelli-Credit" Challenge  
> Theme: Next-Gen Corporate Credit Appraisal: Bridging the Intelligence Gap

---

## 🏗 Architecture Overview

```
intelli-credit/
├── backend/               # FastAPI + Python AI backend
│   ├── main.py            # App entry point
│   ├── config.py          # API keys & settings
│   ├── requirements.txt
│   ├── .env.example       # Copy → .env with your keys
│   ├── routers/
│   │   ├── health.py      # GET /api/health
│   │   ├── ingestor.py    # POST /api/ingestor/upload
│   │   ├── research.py    # POST /api/research/run
│   │   └── recommendation.py  # POST /api/recommendation/generate
│   └── services/
│       ├── pdf_parser.py       # pdfplumber + PyPDF2 cascade
│       ├── gst_analyser.py     # GST vs Bank cross-check
│       ├── gemini_service.py   # Google Gemini AI calls
│       ├── web_search.py       # Serper.dev web search
│       ├── scoring_engine.py   # Five-Cs scoring model
│       └── cam_generator.py    # ReportLab PDF generation
└── frontend/              # React + Vite frontend
    ├── src/
    │   ├── pages/
    │   │   ├── HomePage.jsx        # Landing / dashboard
    │   │   ├── IngestorPage.jsx    # Step 1: Document upload
    │   │   ├── ResearchPage.jsx    # Step 2: Research agent
    │   │   ├── RecommendationPage.jsx  # Step 3: Credit decision
    │   │   └── CAMPage.jsx         # Step 4: CAM download
    │   ├── components/
    │   │   └── Layout.jsx          # Sidebar + toast system
    │   ├── context/
    │   │   └── AppContext.jsx      # Global session state
    │   └── api.js                  # Axios API client
    └── vite.config.js              # Proxy → localhost:8000
```

---

## 🔑 API Keys Required

| Service | Purpose | Get It |
|---------|---------|--------|
| **Google Gemini** | LLM for extraction, research synthesis, credit decisions | [aistudio.google.com](https://aistudio.google.com/app/apikey) — Free tier available |
| **Serper.dev** | Web search for news, litigation, regulatory research | [serper.dev](https://serper.dev) — 2500 free queries/month |
| **OpenAI** *(optional)* | Fallback LLM if Gemini unavailable | [platform.openai.com](https://platform.openai.com/api-keys) |

---

## 🚀 Quick Start

### Step 1 — Clone & set up API keys

```bash
cd backend
copy .env.example .env
```

Edit `backend/.env`:
```env
GEMINI_API_KEY=AIza...your_key_here
SERPER_API_KEY=your_serper_key_here
```

### Step 2 — Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python main.py
```

Backend runs at: **http://localhost:8000**  
API docs (Swagger): **http://localhost:8000/docs**

### Step 3 — Frontend setup

```bash
cd frontend

# Install dependencies (if not already done)
npm install

# Start dev server
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## 📋 Three-Step Workflow

### 🗂 Step 1: Data Ingestor
- Upload PDF documents (annual reports, financial statements, legal notices, MCA filings, rating agency reports)
- Optionally provide **GST JSON** (`monthly_turnover`, `gstr_3b_tax_paid`, `gstr_2a_itc_claimed`) and **Bank Statement JSON** (`monthly_credits`) for circular trading detection
- AI extracts: Revenue, EBITDA, PAT, Debt, Net Worth, DSCR, ICR, D/E ratio, and more
- Engine flags circular trading if GST vs bank discrepancy > 30%

**GST JSON format:**
```json
{
  "monthly_turnover": { "2024-01": 5000000, "2024-02": 5200000 },
  "gstr_3b_tax_paid": { "2024-01": 900000, "2024-02": 936000 },
  "gstr_2a_itc_claimed": { "2024-01": 750000, "2024-02": 780000 }
}
```

**Bank Statement JSON format:**
```json
{
  "monthly_credits": { "2024-01": 5100000, "2024-02": 5400000 }
}
```

### 🔍 Step 2: Research Agent
- Enter company name, sector, and key promoter names
- Engine searches news, litigation (NCLT/DRT/SEBI), and regulatory updates via Serper.dev
- Input **qualitative due diligence notes** — AI adjusts the credit score (−30 to +10 points) based on field observations
- Returns early warning signals and a synthesized research brief

### 📊 Step 3: Recommendation & CAM
- Enter loan details (amount, purpose, tenure, collateral)
- Engine runs Five-Cs scoring (transparent weights):
  - **Character** 25% — Promoter integrity, governance, litigation
  - **Capacity** 30% — DSCR, ICR, EBITDA margin, operating cash flows
  - **Capital** 20% — Net worth, D/E ratio, leverage
  - **Collateral** 15% — Security cover, collateral quality
  - **Conditions** 10% — Sector outlook, macro environment
- Gemini generates: Decision (APPROVE / CONDITIONAL_APPROVE / REJECT), recommended amount, interest rate, risk premium (bps)
- Download the **Credit Appraisal Memo (CAM) PDF**

---

## 🏦 Indian Context Features

| Feature | Detail |
|---------|--------|
| **GSTR-2A vs 3B** | Flags ITC ≥95% of tax paid (circular trading signal) |
| **CIBIL/Rating context** | Prompts include India credit bureau references |
| **NCLT/DRT/SEBI** | Litigation search targets India-specific courts |
| **eCourt portal** | Included in search queries |
| **RBI regulations** | Sector regulatory searches include RBI circulars |
| **INR Crores** | All financials in Indian units |
| **MCLR/Repo** | Interest rate framing in India banking context |

---

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Check API keys, backend status |
| `/api/ingestor/upload` | POST | Upload PDFs + optional GST/bank JSON |
| `/api/ingestor/session/{id}` | GET | Retrieve extracted session data |
| `/api/research/run` | POST | Run web research agent |
| `/api/recommendation/generate` | POST | Generate Five-Cs score + decision |
| `/api/recommendation/cam/{id}` | GET | Download CAM PDF |
| `/api/recommendation/session/{id}` | GET | Get saved recommendation |

Full Swagger UI: `http://localhost:8000/docs`

---

## 🛠 Troubleshooting

### Backend won't start
- Check Python ≥ 3.9: `python --version`
- Activate virtual environment before running
- Install deps: `pip install -r requirements.txt`

### "AI Offline" in sidebar
- Add `GEMINI_API_KEY` to `backend/.env`
- Restart the backend after editing `.env`

### No search results
- Add `SERPER_API_KEY` to `backend/.env`
- Demo mode: without the key, placeholder results are returned

### PDF extraction returns empty financials
- Complex scanned PDFs may need OCR (not included in base version)
- Try uploading a text-native PDF first
- pdfplumber handles most Indian CA-certified financial statements

### CAM download fails with 404
- Run `/api/recommendation/generate` first
- CAM is generated as part of the recommendation step

---

## 📐 Scoring Model Reference

```
Total Score = Σ (C_score × weight)

Decision Logic:
  ≥ 65 → APPROVE
  50–64 → CONDITIONAL_APPROVE
  < 50 → REJECT

Grade Table:
  85+ → AAA    75–84 → AA    65–74 → A
  55–64 → BBB  45–54 → BB    35–44 → B    <35 → C
```

---

## 🧑‍💻 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11 |
| LLM | Google Gemini 1.5 Flash |
| Web Search | Serper.dev (Google Search API) |
| PDF Parsing | pdfplumber + PyPDF2 |
| PDF Generation | ReportLab |
| Frontend | React 18 + Vite 7 |
| Charts | Recharts (Radar + Bar) |
| Icons | Lucide React |
| State | React Context API |

---

*Built for the Intelli-Credit Hackathon · India-aware AI Credit Engine*
