import assert from "node:assert/strict";
import test from "node:test";

import { createResumePdf } from "../app/pdf-export.ts";

const baseResume = {
  name: "Alex Morgan",
  headline: "Machine Learning Engineer",
  contact: "alex.morgan@example.com | +1 555 555 0100 | Los Angeles, CA",
  summary: "Machine learning engineer building reliable production systems.",
  skills: ["Python", "SQL", "AWS", "Machine Learning"],
  experience: [],
  education: [],
  projects: [],
  certifications: [],
};

test("PDF export produces a selectable single-page document without annotations", async () => {
  const pdf = await createResumePdf(baseResume);
  const bytes = new Uint8Array(pdf.output("arraybuffer"));
  const source = new TextDecoder("latin1").decode(bytes);

  assert.equal(pdf.getNumberOfPages(), 1);
  assert.ok(bytes.length > 1_000);
  assert.doesNotMatch(source, /\/Annots\b/);
  assert.doesNotMatch(source, /\/URI\b/);
});

test("dense resumes shrink to one page without cutting off content", async () => {
  const resume = {
    ...baseResume,
    experience: Array.from({ length: 9 }, (_, index) => ({
      company: `Company ${index + 1}`,
      role: "Senior Engineer",
      location: "Remote",
      dates: `20${10 + index} - 20${11 + index}`,
      bullets: Array.from({ length: 5 }, (__, bullet) =>
        `Built and improved production platform capability ${bullet + 1} with measurable reliability outcomes across distributed teams.`,
      ),
    })),
  };

  const pdf = await createResumePdf(resume);
  const source = new TextDecoder("latin1").decode(new Uint8Array(pdf.output("arraybuffer")));

  assert.equal(pdf.getNumberOfPages(), 1);
  assert.match(source, /Company 9/);
  assert.match(source, /capability 5/);
  assert.doesNotMatch(source, /\/Annots\b/);
  assert.doesNotMatch(source, /\/URI\b/);
});
