# MDM OpsFlow — Phase 2 Starter

AI-first bilingual construction operating system starter.

## Included
- FastAPI backend
- Next.js frontend
- Flutter mobile scaffold
- English/Spanish localization
- Super-admin foundation
- Docker Compose

## Run
```bash
docker compose up --build
```

## Streamlit
```powershell
& .\.venv311\Scripts\python.exe -m streamlit run streamlit_app.py
```

The Streamlit app is a separate operational dashboard that talks to the FastAPI backend at `http://localhost:8080` by default.

## OCR And AI Setup
1. Create a root `.env` file from `.env.example`.
2. Paste your OpenAI key into `OPENAI_API_KEY` in that file.
3. Restart the stack with `docker compose up --build`.

If `OPENAI_API_KEY` is not set, uploads still work, but OCR and AI summarization for scanned files and images will stay limited.

Backend: http://localhost:8080/docs
Frontend: http://localhost:3000
