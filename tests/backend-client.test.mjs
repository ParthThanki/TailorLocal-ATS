import assert from "node:assert/strict";
import test from "node:test";

import {
  generateTailoredResume,
  listLocalModels,
  scoreTailoredResume,
} from "../app/backend-client.ts";

const originalFetch = globalThis.fetch;

test.afterEach(() => {
  globalThis.fetch = originalFetch;
});

test("frontend uses the Python model-list endpoint", async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "http://127.0.0.1:8000/api/models");
    assert.deepEqual(JSON.parse(init.body), { provider: "ollama", endpoint: "http://127.0.0.1:11434" });
    return new Response(JSON.stringify({ models: ["llama3.1:latest"] }), { status: 200 });
  };

  assert.deepEqual(
    await listLocalModels({ provider: "ollama", endpoint: "http://127.0.0.1:11434" }),
    ["llama3.1:latest"],
  );
});

test("generation sends one locked input snapshot to Python", async () => {
  const response = {
    resume: { name: "Alex", headline: "Engineer", contact: "", summary: "", skills: [], experience: [], education: [], projects: [], certifications: [] },
    analysis: { score: 70, matchedKeywords: [], missingKeywords: [], improvements: [], breakdown: [] },
    beforeAnalysis: { score: 40, matchedKeywords: [], missingKeywords: [], improvements: [], breakdown: [] },
    jobDescription: "Python role",
    refinementPasses: 2,
  };
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "http://127.0.0.1:8000/api/generate");
    const body = JSON.parse(init.body);
    assert.equal(body.resumeText, "Original resume");
    assert.equal(body.jobDescription, "Python role");
    assert.equal(body.targetScore, 80);
    assert.equal(body.maxRefinementPasses, 2);
    return new Response(JSON.stringify(response), { status: 200 });
  };

  assert.deepEqual(await generateTailoredResume({
    provider: "ollama",
    endpoint: "http://127.0.0.1:11434",
    model: "llama3.1:latest",
    resumeText: "Original resume",
    jobDescription: "Python role",
  }), response);
});

test("edited resumes are rescored by Python and backend errors are readable", async () => {
  globalThis.fetch = async (url) => {
    assert.equal(url, "http://127.0.0.1:8000/api/score");
    return new Response(JSON.stringify({ analysis: { score: 81, matchedKeywords: [], missingKeywords: [], improvements: [], breakdown: [] } }), { status: 200 });
  };
  const analysis = await scoreTailoredResume({
    resume: { name: "Alex", headline: "", contact: "", summary: "", skills: [], experience: [], education: [], projects: [], certifications: [] },
    jobDescription: "Python role",
  });
  assert.equal(analysis.score, 81);

  globalThis.fetch = async () => new Response(JSON.stringify({ detail: "Local model is offline." }), { status: 502 });
  await assert.rejects(
    listLocalModels({ provider: "ollama", endpoint: "http://127.0.0.1:11434" }),
    /Local model is offline/,
  );
});
