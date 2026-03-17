# 🧠 QuizGenius — AI-Powered Quiz Generator

A fully-featured web app that generates MCQ, True/False, and Fill-in-the-Blank quizzes from any topic, text, or PDF using the Claude AI API.

---

## 🚀 Quick Setup (3 steps)

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## 📁 Project Structure

```
quiz-generator/
├── app.py                  # Flask backend + API routes
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Main HTML (single page app)
├── static/
│   ├── css/style.css       # All styles
│   └── js/app.js           # All frontend logic
└── uploads/                # Temp folder for PDF uploads (auto-created)
```

---

## ✨ Features

| Feature | Details |
|---|---|
| **Topic-based generation** | Type any topic → instant quiz |
| **Text/Notes input** | Paste study material → AI extracts questions |
| **PDF upload** | Upload a PDF → AI generates from it |
| **Question types** | MCQ, True/False, Fill in the Blank |
| **Difficulty levels** | Easy, Medium, Hard |
| **Question count** | 5, 10, 15, or 20 questions |
| **Live timer** | Tracks how long you take |
| **Score & review** | Full result breakdown with explanations |
| **Retake quiz** | Retry the same quiz instantly |

---

## 🔑 API Key

You need an Anthropic API key. Get one free at:
👉 https://console.anthropic.com

Enter it in the form on the website — it's sent directly to the AI and never stored.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, Vanilla JS |
| Backend | Python + Flask |
| AI | Anthropic Claude (claude-sonnet-4) |
| PDF Parsing | PyPDF2 |

---

## 💡 Troubleshooting

**"ModuleNotFoundError"** → Run `pip install -r requirements.txt`

**"Invalid API key"** → Check your key at console.anthropic.com

**"Port already in use"** → Change port in app.py: `app.run(port=5001)`

**PDF not extracting** → Make sure the PDF has selectable text (not scanned images)
