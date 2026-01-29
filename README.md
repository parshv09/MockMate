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

- Download from: https://ffmpeg.org

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
