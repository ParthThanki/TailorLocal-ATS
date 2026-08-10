import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the TailorLocal workspace", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>TailorLocal/i);
  assert.match(html, /Private ATS resume workspace/);
  assert.match(html, /Add your materials/);
  assert.match(html, /Connect local AI/);
  assert.match(html, /Generate resume/);
  assert.match(html, /Resume preview/);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
});

test("routes generation and scoring through the local Python backend", async () => {
  const [page, backendClient, pdfExporter, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/backend-client.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/pdf-export.ts", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(packageJson, /"name": "tailorlocal-ats"/);
  assert.match(page, /127\.0\.0\.1:11434/);
  assert.match(page, /127\.0\.0\.1:1234/);
  assert.match(page, /generateTailoredResume/);
  assert.match(page, /scoreTailoredResume/);
  assert.match(page, /disabled=\{jobDescriptionLocked\}/);
  assert.doesNotMatch(page, /fetch\(`\$\{base\}\/api\/chat/);
  assert.match(backendClient, /127\.0\.0\.1:8000/);
  assert.match(backendClient, /"\/api\/models"/);
  assert.match(backendClient, /"\/api\/generate"/);
  assert.match(backendClient, /"\/api\/score"/);
  assert.match(pdfExporter, /new jsPDF/);
  await access(new URL("../public/pdf.worker.min.mjs", import.meta.url));
});
