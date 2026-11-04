# AI Skin Specialist & Medicare Assistant

An AI-powered skincare consultation assistant built with Gradio, leveraging multimodal AI models for vision/video analysis, speech-to-text transcription, and natural voice responses.

## Features

- **Multimodal Skin Analysis**: Accepts patient symptoms, images, and videos for skincare assessment.
- **Voice Consultation**: Real-time voice recording and speech-to-text transcription powered by Whisper via Groq.
- **Doctor Guidance**: Medical guidance powered by MiniMax LLM.
- **Audio Response**: Natural doctor voice output generated using Deepgram TTS.
- **Modern Web Interface**: Intuitive, responsive Gradio web application.

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+ (or Python 3.14 recommended)
- `uv` (recommended) or `pip`
- FFmpeg (required for audio processing)

### 2. Clone the Repository
```bash
git clone https://github.com/harmitprajapati2006/sceencare_assistant-.git
cd sceencare_assistant-
```

### 3. Create and Activate Virtual Environment
Using `uv`:
```bash
uv venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

Or using standard `venv`:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
# Using uv:
uv sync

# Or using pip:
pip install -e .
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your API credentials:
```env
GROQ_API_KEY="your_groq_api_key"
DEEPGRAM_API_KEY="your_deepgram_api_key"
MINIMAX_API_KEY="your_minimax_api_key"
```

---

## Running the Application

Start the Gradio interface:
```bash
python main.py
```
Open the local URL displayed in your terminal (usually `http://127.0.0.1:7860`) to begin consultation.

---

## Project Structure

```text
├── brain.py            # AI doctor decision logic & MiniMax integration
├── main.py             # Gradio web user interface & app orchestration
├── patient_voice.py    # Audio transcription & mic recording (Groq Whisper)
├── patient_que.py      # Audio queue handling & transcription helper
├── voice.py            # Text-to-speech doctor voice synthesis (Deepgram)
├── pyproject.toml      # Project metadata & dependencies
├── .env.example        # Template for required environment variables
├── .gitignore          # Git exclusion rules
└── README.md           # Documentation
```

---

## Disclaimer
*This tool is intended for informational and demonstrative purposes only and does not constitute official medical advice, diagnosis, or treatment. Always consult a certified healthcare professional or dermatologist for medical concerns.*

