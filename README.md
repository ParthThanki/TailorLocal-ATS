# TailorLocal ATS

I built TailorLocal ATS to create role-specific resumes without uploading personal information to a cloud AI service. I connect the app directly to a model running on my own computer, provide my current resume and a job description, and export the tailored result as a clean PDF.

## Why I built it

I wanted a resume-tailoring workflow that keeps sensitive career information local. The browser talks directly to Ollama, LM Studio, or another OpenAI-compatible local server. There is no hosted model API, account system, or resume database in the generation flow.

## What it does

- I can upload a PDF, DOCX, TXT, or Markdown resume.
- I can paste or upload a job description.
- I can connect Ollama or a local OpenAI-compatible server.
- The local model rewrites and reorganizes only facts supported by my source resume.
- The app performs additional local revision passes when truthful improvements can raise the score.
- I can compare before-and-after ATS compatibility scores and review the scoring breakdown.
- The job description is locked to the generated result so a different role cannot silently change its ATS metrics.
- I can edit the generated resume before downloading it.
- The PDF uses a selectable-text, single-column layout with standard section headings.
- Long resumes paginate cleanly without cutting content off.

## ATS scoring

I use a deterministic local scoring rubric based on keyword alignment, section completeness, impact wording, contact readability, and parseable formatting. I use the same job-description snapshot for generation and for every score shown with that result.

The score is a practical compatibility estimate, not a guaranteed score from every commercial ATS. Different employers and ATS products use private ranking systems that are not available to this project.

## Local setup

I use Node.js 22.13 or newer and a local model server.

```powershell
npm install
npm run dev
```

I then open [http://localhost:3000](http://localhost:3000).

## Ollama setup

I can install and start Ollama, then download a model such as Llama 3.1:

```powershell
ollama pull llama3.1
ollama serve
```

Inside TailorLocal, I keep the Ollama endpoint set to:

```text
http://127.0.0.1:11434
```

If Ollama blocks browser requests, I restart it with the local site origin allowed:

```powershell
$env:OLLAMA_ORIGINS="http://localhost:3000"
ollama serve
```

## LM Studio and compatible servers

I start the local OpenAI-compatible server and use its base URL in the app. The default LM Studio address is:

```text
http://127.0.0.1:1234
```

## My workflow

1. I upload my existing resume.
2. I paste or upload the target job description.
3. I connect my local model and select it.
4. I generate the tailored resume.
5. I review the ATS comparison and edit any wording I want to change.
6. I download the final PDF.
7. I select **Start over** before using a different job description.

## Privacy model

My resume and job description remain in the browser during the session. Generation requests go to the local endpoint I configure. I do not need an OpenAI API key or another hosted-model key to use the app.

## Validation

I use the following commands before publishing changes:

```powershell
npm run build
npm test
```

## Main technologies

- React 19
- TypeScript
- vinext and Vite
- jsPDF
- PDF.js
- Mammoth
- Ollama or another local model server
