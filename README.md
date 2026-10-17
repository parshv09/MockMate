# 🎯 MockMate – AI Powered Mock Interview System

MockMate is an **AI-driven mock interview platform** that helps candidates practice interviews using **text, voice, and live video analysis**.  
It provides **role-based questions**, **AI evaluation**, **behavioral insights**, and a **downloadable interview report**.

---

## 🚀 Features

### 🧠 AI Interview Engine
- Role-based question generation (Tech, HR, Aptitude, Behavioral)
- Dynamic difficulty handling
- Groq-powered LLM integration (LLaMA 3.1)

### ✍ Answer Modes
- Text-based answers
- Voice-based answers (Speech → Text)
- Live webcam monitoring

### 🎥 Live Video Behavior Analysis
- Face detection
- Eye contact analysis
- Head movement tracking
- Confidence scoring

### 📊 AI Evaluation & Feedback
- Question-wise scoring
- Clear, human-readable AI feedback
- Actionable improvement tips
- Session-level performance insights

### 📄 Interview Report (PDF)
- Question-wise evaluation
- AI feedback & improvement tips
- Behavioral & confidence analysis
- Coaching suggestions
- Downloadable PDF report

### 🔐 User Management
- Secure authentication
- Session history
- Delete sessions
- Resume incomplete interviews

---

## 🛠 Tech Stack

| Layer | Technology |
|------|-----------|
Backend | Django (Python)
Frontend | HTML, Tailwind CSS, Alpine.js
AI Models | Groq (LLaMA 3.1)
Speech-to-Text | OpenAI Whisper
NLP | spaCy
Video Analysis | MediaPipe + OpenCV
PDF Reports | ReportLab
Database | SQLite (dev) / PostgreSQL (prod)

---

## 📦 Installation Guide

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/parshv09/MockMate.git
cd mockmate
```
### 2️⃣ Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```


### 5️⃣ Install FFmpeg (Required for Audio Transcription)
##### Windows

- Download from: https://www.gyan.dev/ffmpeg/builds/

- Add ffmpeg/bin to System PATH

#### Verify:
```bash
ffmpeg -version
```

### 6️⃣ Environment Variables

Create a .env file in the root directory:
```bash
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
DEBUG=True
SECRET_KEY=your_django_secret_key
```

### 7️⃣ Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
```

### 8️⃣ Run the Server
```bash
python manage.py runserver
```

#### Open in browser:
```bash
http://127.0.0.1:8000
```
---

## 🔍 Retrieval-Augmented Generation (RAG) Pipeline

MockMate features a production-conscious **RAG Question Generation Engine** that grounds interview questions in verified domain knowledge while preserving full fallback safety to direct LLM generation.

### 📐 Pipeline Architecture

```
User Input (Role, Job Role, Difficulty, Count)
                      ↓
           Django Interview View
                      ↓
        RAG Question Generation Service
                      ↓
             Query Construction
                      ↓
       Local SentenceTransformers Model
           (all-MiniLM-L6-v2)
                      ↓
         ChromaDB Vector Database
       (Semantic Cosine Search & Top-K)
                      ↓
        Context Filtering & Deduplication
                      ↓
       Prompt Assembly with Safety Sandbox
                      ↓
         Groq LLM (LLaMA 3.1 8B Instant)
                      ↓
     Structured JSON Question Generation
                      ↓
        Deduplication & Validation
                      ↓
        Django Interview Session (DB)
```

### 📚 Knowledge Base Structure

The knowledge base is located at `project/knowledge_base/` and contains curated, factual interview preparation documents organized by topic:

```
project/knowledge_base/
├── python/               # Core Python, generators, decorators, GIL, memory
├── java/                 # JVM internals, collections, multithreading, OOP
├── javascript/           # Event loop, closures, prototypes, promises, async
├── react/                # Hooks, lifecycle, virtual DOM, reconciliation
├── nodejs/               # Non-blocking I/O, streams, buffers, clustering
├── sql/                  # Joins, indexing, normalization, transactions, ACID
├── dsa/                  # Data structures, trees, graphs, sorting, DP, Big-O
├── oops/                 # SOLID principles, design patterns, polymorphism
├── hr/                   # Culture fit, STAR behavioral framing, salary negotiation
└── behavioral/           # Situational leadership, conflict resolution, deadlines
```

You can add your own `.md` or `.txt` reference files under any category subdirectory. Rebuilding the index will automatically pick them up.

### ⚡ Building & Updating the Vector Index

Run the custom Django management command to index or re-index your knowledge base into ChromaDB:

```bash
# Build or update the vector index
python manage.py build_rag_index

# Rebuild from scratch (clears previous collection)
python manage.py build_rag_index --clear

# Custom knowledge base directory or chunking options
python manage.py build_rag_index --kb-dir /path/to/docs --chunk-size 800 --chunk-overlap 120
```

### ⚙️ RAG Configuration (`.env`)

Configure the RAG engine in your `.env` file:

```ini
# Enable/disable RAG (defaults to False for zero-friction standard setup)
RAG_ENABLED=True

# Number of relevant context chunks retrieved per interview round
RAG_TOP_K=5

# Document chunk size and overlap
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=120

# Minimum cosine similarity threshold for retrieved chunks [0.0 - 1.0]
RAG_SIMILARITY_THRESHOLD=0.3

# Vector store collection name and local embedding model
RAG_COLLECTION_NAME=mockmate_interview_knowledge
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### 🛡️ Resilience & Fallback Guarantees

- **Graceful Fallback:** If RAG is disabled, the vector database is unpopulated, or dependencies are missing, MockMate automatically falls back to standard Groq question generation without breaking the user experience.
- **Prompt Injection Defense:** Retrieved chunks are sandboxed inside a dedicated reference boundary marked as untrusted data, preventing prompt tampering.
- **Deduplication:** Questions are deduplicated by SHA-256 text signatures and compared against recent session history to avoid repetition.
- **Latency Monitoring:** Retrieval and generation phases are timed and logged separately for performance observability.

---

### 📁 Project Structure
```bash
mockmate/
│── interviewapp/
│   ├── views.py
│   ├── models.py
│   ├── forms.py
│   ├── qgen_groq.py
│   ├── nlp_utils.py
│   ├── speech_utils.py
│   ├── urls.py
│   ├── nlp_utils.py
│   ├── video_ai_feedback.py
│   ├── video_behavior_utils.py
│   ├── video_summary_utils.py
│   ├── video_utils.py
│   ├── views_helpers.py
│   ├── templates/
│   └── static/
│
│── project/
│   ├── urls.py
│   ├── settings.py
│   ├── asgi.py
│   ├── wsgi.py
│── manage.py
│── requirements.txt
│── README.md
```
###  ⚠ Known Limitations

- Webcam access requires HTTPS in production

- Video frames are analyzed but not stored

- Performance depends on system hardware

### 🌱 Future Enhancements

- Resume-based interview personalization

- Emotion detection

- Admin analytics dashboard

- Multi-language interviews

- Cloud deployment support

### 👨‍💻 Author

***Parshv Athane***
- Aspiring Full-Stack Developer | AI & ML Enthusiast

### ⭐ Support

- If you like this project, please ⭐ star the repository!
