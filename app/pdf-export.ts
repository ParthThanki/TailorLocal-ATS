export type Experience = {
  company: string;
  role: string;
  location: string;
  dates: string;
  bullets: string[];
};

export type Education = {
  school: string;
  degree: string;
  location: string;
  dates: string;
  details: string[];
};

export type ResumeDocument = {
  name: string;
  headline: string;
  contact: string;
  summary: string;
  skills: string[];
  experience: Experience[];
  education: Education[];
  projects: Experience[];
  certifications: string[];
};

function pdfSafeText(value: string): string {
  return value
    .replace(/[\u2010-\u2015\u2212]/g, "-")
    .replace(/\u00a0/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

type FontStyle = "normal" | "bold" | "italic";
type TextColor = readonly [number, number, number];

export async function createResumePdf(resume: ResumeDocument) {
  const { jsPDF } = await import("jspdf");

  const renderAtScale = (scale: number) => {
    const pdf = new jsPDF({ unit: "pt", format: "letter", orientation: "portrait" });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const scaled = (value: number) => value * scale;
    const margin = Math.max(24, scaled(50));
    const topMargin = Math.max(22, scaled(46));
    const bottomMargin = Math.max(18, scaled(32));
    const pageBottom = pageHeight - bottomMargin;
    const contentWidth = pageWidth - margin * 2;
    let y = topMargin;

    const setText = (
      size: number,
      style: FontStyle = "normal",
      color: TextColor = [31, 39, 49],
    ) => {
      pdf.setFont("helvetica", style);
      pdf.setFontSize(scaled(size));
      pdf.setTextColor(color[0], color[1], color[2]);
    };

    const linesFor = (
      text: string,
      width = contentWidth,
      size = 9.5,
      style: FontStyle = "normal",
    ) => {
      setText(size, style);
      return pdf.splitTextToSize(pdfSafeText(text || ""), width) as string[];
    };

    const drawContactLine = (line: string, baseline: number) => {
      const emailPattern = /[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/gi;
      const matches = [...line.matchAll(emailPattern)];
      if (!matches.length) {
        pdf.text(line, pageWidth / 2, baseline, { align: "center" });
        return;
      }

      let x = (pageWidth - pdf.getTextWidth(line)) / 2;
      let cursor = 0;
      matches.forEach((match) => {
        const matchStart = match.index ?? cursor;
        const before = line.slice(cursor, matchStart);
        if (before) {
          pdf.text(before, x, baseline);
          x += pdf.getTextWidth(before);
        }

        const email = match[0];
        const atIndex = email.indexOf("@");
        const localPart = email.slice(0, atIndex);
        const domainPart = email.slice(atIndex);

        // Keep the address visually unchanged while preventing PDF viewers from
        // creating an implicit mailto annotation around a single text token.
        pdf.text(`${localPart} `, x, baseline);
        x += pdf.getTextWidth(localPart);
        pdf.text(domainPart, x, baseline);
        x += pdf.getTextWidth(domainPart);
        cursor = matchStart + email.length;
      });

      const after = line.slice(cursor);
      if (after) pdf.text(after, x, baseline);
    };

    const writeLines = (
      text: string,
      options: { size?: number; leading?: number; indent?: number; bold?: boolean } = {},
    ) => {
      const size = options.size ?? 9.5;
      const leading = scaled(options.leading ?? size * 1.38);
      const indent = scaled(options.indent ?? 0);
      const style = options.bold ? "bold" : "normal";
      const lines = linesFor(text, contentWidth - indent, size, style);
      setText(size, style);
      pdf.text(lines, margin + indent, y);
      y += lines.length * leading;
    };

    const sectionTitle = (title: string) => {
      y += scaled(10);
      setText(9.5, "bold", [18, 32, 51]);
      pdf.text(pdfSafeText(title).toUpperCase(), margin, y);
      y += scaled(5);
      pdf.setDrawColor(18, 32, 51);
      pdf.setLineWidth(Math.max(0.35, scaled(0.7)));
      pdf.line(margin, y, pageWidth - margin, y);
      y += scaled(14);
    };

    const experienceLayout = (item: Experience) => {
      const primary = item.role || item.company;
      const dateReserve = item.dates ? Math.min(contentWidth * 0.45, scaled(132)) : 0;
      const primaryLines = linesFor(primary, contentWidth - dateReserve, 10.5, "bold");
      const secondary = [item.role ? item.company : "", item.location].filter(Boolean).join(" | ");
      const secondaryLines = secondary
        ? linesFor(secondary, contentWidth, 9, "italic")
        : [];
      const bulletLines = item.bullets.map((bullet) =>
        linesFor(`- ${bullet}`, contentWidth - scaled(4), 9.3),
      );
      const height = Math.max(scaled(13), primaryLines.length * scaled(13))
        + secondaryLines.length * scaled(12)
        + bulletLines.reduce((sum, lines) => sum + lines.length * scaled(12.5) + scaled(2), 0)
        + scaled(5);
      return { primaryLines, secondaryLines, bulletLines, height };
    };

    const writeExperience = (item: Experience) => {
      const layout = experienceLayout(item);

      setText(10.5, "bold", [21, 29, 40]);
      pdf.text(layout.primaryLines, margin, y);
      if (item.dates) {
        pdf.text(pdfSafeText(item.dates), pageWidth - margin, y, { align: "right" });
      }
      y += Math.max(scaled(13), layout.primaryLines.length * scaled(13));

      if (layout.secondaryLines.length) {
        setText(9, "italic", [70, 76, 85]);
        pdf.text(layout.secondaryLines, margin, y);
        y += layout.secondaryLines.length * scaled(12);
      }

      item.bullets.forEach((_, index) => {
        const lines = layout.bulletLines[index];
        setText(9.3);
        pdf.text(lines, margin + scaled(4), y);
        y += lines.length * scaled(12.5) + scaled(2);
      });
      y += scaled(5);
    };

    const educationLayout = (item: Education) => {
      const primary = item.degree || item.school;
      const dateReserve = item.dates ? Math.min(contentWidth * 0.45, scaled(132)) : 0;
      const primaryLines = linesFor(primary, contentWidth - dateReserve, 10.2, "bold");
      const secondary = [item.degree ? item.school : "", item.location].filter(Boolean).join(" | ");
      const secondaryLines = secondary ? linesFor(secondary, contentWidth, 9) : [];
      const detailLines = item.details.map((detail) =>
        linesFor(`- ${detail}`, contentWidth - scaled(4), 9),
      );
      const height = Math.max(scaled(13), primaryLines.length * scaled(13))
        + secondaryLines.length * scaled(12.42)
        + detailLines.reduce((sum, lines) => sum + lines.length * scaled(12.42), 0)
        + scaled(3);
      return { primaryLines, secondaryLines, detailLines, height };
    };

    const writeEducation = (item: Education) => {
      const layout = educationLayout(item);

      setText(10.2, "bold", [21, 29, 40]);
      pdf.text(layout.primaryLines, margin, y);
      if (item.dates) {
        pdf.text(pdfSafeText(item.dates), pageWidth - margin, y, { align: "right" });
      }
      y += Math.max(scaled(13), layout.primaryLines.length * scaled(13));

      if (layout.secondaryLines.length) {
        setText(9);
        pdf.text(layout.secondaryLines, margin, y);
        y += layout.secondaryLines.length * scaled(12.42);
      }

      layout.detailLines.forEach((lines) => {
        setText(9);
        pdf.text(lines, margin + scaled(4), y);
        y += lines.length * scaled(12.42);
      });
      y += scaled(3);
    };

    setText(21, "bold", [18, 32, 51]);
    const nameLines = linesFor(resume.name || "Resume", contentWidth, 21, "bold");
    setText(21, "bold", [18, 32, 51]);
    pdf.text(nameLines, pageWidth / 2, y, { align: "center" });
    y += nameLines.length * scaled(22);

    if (resume.headline) {
      const headlineLines = linesFor(resume.headline, contentWidth, 10, "bold");
      setText(10, "bold", [78, 86, 96]);
      pdf.text(headlineLines, pageWidth / 2, y, { align: "center" });
      y += headlineLines.length * scaled(13);
    }

    if (resume.contact) {
      const contactLines = linesFor(resume.contact, contentWidth, 8.7);
      setText(8.7, "normal", [62, 69, 78]);
      contactLines.forEach((line, index) =>
        drawContactLine(line, y + index * scaled(11)),
      );
      y += contactLines.length * scaled(11) + scaled(3);
    }

    y += scaled(4);

    if (resume.summary) {
      sectionTitle("Professional summary");
      writeLines(resume.summary);
    }
    if (resume.skills.length) {
      sectionTitle("Core skills");
      writeLines(resume.skills.join(" | "));
    }
    if (resume.experience.length) {
      sectionTitle("Experience");
      resume.experience.forEach(writeExperience);
    }
    if (resume.projects.length) {
      sectionTitle("Selected projects");
      resume.projects.forEach(writeExperience);
    }
    if (resume.education.length) {
      sectionTitle("Education");
      resume.education.forEach(writeEducation);
    }
    if (resume.certifications.length) {
      sectionTitle("Certifications");
      writeLines(resume.certifications.join(" | "));
    }

    return { pdf, contentBottom: y, pageBottom };
  };

  const result = renderAtScale(1);
  if (result.contentBottom <= result.pageBottom) return result.pdf;

  // Find the largest scale that keeps the complete selectable-text resume on
  // one Letter page. This mirrors the single-page preview without truncating
  // sections or converting the resume to an image.
  let upperScale = 1;
  let lowerScale = 0.82;
  let lowerResult = renderAtScale(lowerScale);

  while (lowerResult.contentBottom > lowerResult.pageBottom && lowerScale > 0.1) {
    upperScale = lowerScale;
    lowerScale *= 0.82;
    lowerResult = renderAtScale(lowerScale);
  }

  let bestFit = lowerResult;
  for (let iteration = 0; iteration < 12; iteration += 1) {
    const candidateScale = (lowerScale + upperScale) / 2;
    const candidate = renderAtScale(candidateScale);
    if (candidate.contentBottom <= candidate.pageBottom) {
      lowerScale = candidateScale;
      bestFit = candidate;
    } else {
      upperScale = candidateScale;
    }
  }

  return bestFit.pdf;
}

export async function saveResumeAsPdf(resume: ResumeDocument) {
  const pdf = await createResumePdf(resume);
  const safeName = (resume.name || "tailored-resume")
    .replace(/[^a-z0-9]+/gi, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
  pdf.save(`${safeName || "tailored-resume"}-ats-resume.pdf`);
}
