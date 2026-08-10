# TailorLocal ATS

I built TailorLocal ATS to create role-specific resumes without sending personal career information to a hosted AI provider. I run a Python backend and a local model on my own computer, provide my current resume and a job description, and export the tailored result as a clean PDF.

## Why I built it

I wanted a resume-tailoring workflow that keeps sensitive documents on my device. The browser sends extracted text to my local Python backend, and the Python backend communicates only with a loopback Ollama, LM Studio, or OpenAI-compatible model server. There is no hosted-model API, account system, or resume database in the generation flow.

## What it does

- I can upload a PDF, DOCX, TXT, or Markdown resume.
- I can paste or upload a job description.
- I can connect Ollama or a local OpenAI-compatible server through the Python backend.
- The Python backend validates all request data and rejects non-loopback model endpoints.
- The local model rewrites and reorganizes only facts supported by my source resume.
- The backend performs additional local revision passes when truthful improvements can raise the score.
- I can compare before-and-after ATS compatibility scores and review the full scoring breakdown.
- The job description is locked to the generated result so a different role cannot silently change its metrics.
- Edited resume content is rescored by the same Python scoring engine.
- I can download a selectable-text, single-column PDF with clean pagination.

## Local architecture

```text
Browser on localhost:3000
        |
        | validated local JSON
        v
Python FastAPI backend on 127.0.0.1:8000
        |
        | loopback-only model requests
        v
Ollama on 127.0.0.1:11434
or LM Studio on 127.0.0.1:1234
```

The browser continues to parse uploaded documents and build the final PDF locally. Python owns model discovery, model requests, response normalization, multi-pass resume generation, job-description snapshots, and ATS scoring.

## ATS scoring

I use a deterministic Python rubric based on keyword alignment, section completeness, impact wording, contact readability, and parseable formatting. I use the exact job-description snapshot submitted during generation for every score attached to that result.

The score is a practical compatibility estimate, not a guaranteed score from every commercial ATS. Different employers and ATS products use private ranking systems that are not available to this project.

## Requirements

I use:

- Node.js 22.13 or newer;
- Python 3.11 or newer;
- Ollama, LM Studio, or another local OpenAI-compatible server.

## First-time setup

I install the web dependencies from the project root:

```powershell
npm install
```

I create and install the Python backend environment:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e "backend[dev]"
```

## Starting the app

I start the Python backend in the first terminal:

```powershell
npm run dev:backend
```

I start the web app in a second terminal:

```powershell
npm run dev:web
```

I then open [http://localhost:3000](http://localhost:3000). The Python health endpoint is available at [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health), and local API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Ollama setup

I can download and start a model such as Llama 3.1:

```powershell
ollama pull llama3.1
ollama serve
```

Inside TailorLocal, I keep the Ollama endpoint set to:

```text
http://127.0.0.1:11434
```

The browser no longer needs direct Ollama CORS access because Python makes the model request.

## LM Studio and compatible servers

I start the local OpenAI-compatible server and use its base URL in the app. The default LM Studio address is:

```text
http://127.0.0.1:1234
```

## My workflow

1. I start the Python backend, web app, and local model server.
2. I upload my existing resume.
3. I paste or upload the target job description.
4. I connect and select my installed model.
5. I generate the tailored resume.
6. I review the ATS comparison and edit any wording I want to change.
7. I download the final PDF.
8. I select **Start over** before using a different job description.

## Local API

The Python backend exposes:

| Route | Purpose |
| --- | --- |
| `GET /health` | Confirm the backend is running |
| `POST /api/models` | List models from the selected local provider |
| `POST /api/generate` | Generate, refine, normalize, and score a resume |
| `POST /api/score` | Rescore an edited resume against its locked job description |

The backend accepts browser requests only from `localhost:3000` and `127.0.0.1:3000` by default. Model endpoints must use HTTP and resolve to `localhost` or another loopback address.

## Validation

I run every backend, frontend, integration-contract, PDF, and production-build check with:

```powershell
npm test
```

The test suite covers:

- deterministic Python ATS scoring;
- source-document scoring;
- supported-keyword selection;
- loopback endpoint enforcement;
- Ollama model discovery and chat contracts;
- OpenAI-compatible fallback behavior;
- generation snapshots and multi-pass refinement;
- malformed model output handling;
- FastAPI validation and CORS policy;
- frontend-to-Python request contracts;
- server-rendered application content;
- PDF creation, annotation safety, and multi-page pagination;
- the complete production web build.

GitHub Actions runs the same full suite on Windows with Node.js 24 and Python 3.12.

## Privacy model

My original files remain in the browser. Extracted resume text and the job description are sent only to the Python service running on my device. The Python service calls only a loopback model endpoint and does not persist submitted content. I do not need an OpenAI API key or another hosted-model key.

## Main technologies

- Python 3.11+
- FastAPI, Pydantic, HTTPX, and Uvicorn
- React 19 and TypeScript
- vinext and Vite
- jsPDF
- PDF.js
- Mammoth
- Ollama or another local model server
