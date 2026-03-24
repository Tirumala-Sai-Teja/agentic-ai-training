# 🛑 C&D Processor — Quick Start Guide

---

## 1. Prerequisites

Make sure you have these installed:

- **Python 3.10+** → `python3 --version`
- **Node.js 18+** → `node --version`
- **Groq API key** → get one free at [console.groq.com](https://console.groq.com)

---

## 2. Install Python Packages

```bash
cd capstone-project
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements_server.txt
```

---

## 3. Install Frontend Packages

```bash
cd frontend
npm install
cd ..
```

---

## 4. Add Your API Key

```bash
cp .env.example .env
```

Open `.env` and add:

```
GROQ_API_KEY=gsk_your_key_here
```

---

---

## 5. Start Everything

Open **3 separate terminals** and run one command in each:

### Terminal 1 — Backend Server
```bash
source venv/bin/activate
python server.py
```
✅ Running at: `http://localhost:8001`

### Terminal 2 — Frontend
```bash
cd frontend
npm run dev
```
✅ Running at: `http://localhost:3000`

### Terminal 3 — Phoenix Observability (optional)
```bash
phoenix serve
```
✅ Running at: `http://localhost:6006`

---

## 7. Open the App

Go to **http://localhost:3000** in your browser.

---

## Quick Reference

| What | URL |
|---|---|
| Web application | http://localhost:3000 |
| API server | http://localhost:8001 |
| Phoenix traces | http://localhost:6006 |
| Health check | http://localhost:8001/health |