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

export async function createResumePdf(resume: ResumeDocument) {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF({ unit: "pt", format: "letter", orientation: "portrait" });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 50;
  const topMargin = 46;
  const bottomMargin = 32;
  const pageBottom = pageHeight - bottomMargin;
  const usablePageHeight = pageBottom - topMargin;
  const contentWidth = pageWidth - margin * 2;
  let y = topMargin;

  const newPage = () => {
    pdf.addPage();
    y = topMargin;
  };

  const addPageIfNeeded = (needed: number) => {
    if (y + needed <= pageBottom) return;
    newPage();
  };

  const linesFor = (text: string, width = contentWidth) => (
    pdf.splitTextToSize(pdfSafeText(text || ""), width) as string[]
  );

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

      // Chrome/PDFium creates an implicit mailto link from plain email text.
      // Keep the visible address unchanged while separating that text token.
      pdf.text(`${localPart} `, x, baseline);
      x += pdf.getTextWidth(localPart);
      pdf.text(domainPart, x, baseline);
      x += pdf.getTextWidth(domainPart);
      cursor = matchStart + email.length;
    });

    const after = line.slice(cursor);
    if (after) pdf.text(after, x, baseline);
  };

  const writeLines = (text: string, options: { size?: number; leading?: number; indent?: number; bold?: boolean } = {}) => {
    const size = options.size ?? 9.5;
    const leading = options.leading ?? size * 1.38;
    const indent = options.indent ?? 0;
    const lines = linesFor(text, contentWidth - indent);
    addPageIfNeeded(lines.length * leading + 2);
    pdf.setFont("helvetica", options.bold ? "bold" : "normal");
    pdf.setFontSize(size);
    pdf.setTextColor(31, 39, 49);
    pdf.text(lines, margin + indent, y);
    y += lines.length * leading;
  };

  const sectionTitleHeight = 29;
  const sectionTitle = (title: string, firstBlockHeight = 0) => {
    addPageIfNeeded(sectionTitleHeight + firstBlockHeight);
    y += 10;
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(9.5);
    pdf.setTextColor(18, 32, 51);
    pdf.text(pdfSafeText(title).toUpperCase(), margin, y);
    y += 5;
    pdf.setDrawColor(18, 32, 51);
    pdf.setLineWidth(0.7);
    pdf.line(margin, y, pageWidth - margin, y);
    y += 14;
  };

  const experienceLayout = (item: Experience) => {
    const primary = item.role || item.company;
    const primaryWidth = item.dates ? contentWidth - 132 : contentWidth;
    const primaryLines = linesFor(primary, primaryWidth);
    const secondary = [item.role ? item.company : "", item.location].filter(Boolean).join(" | ");
    const secondaryLines = secondary ? linesFor(secondary) : [];
    const bulletLines = item.bullets.map((bullet) => linesFor(`- ${bullet}`, contentWidth - 4));
    const height = Math.max(13, primaryLines.length * 13)
      + secondaryLines.length * 12
      + bulletLines.reduce((sum, lines) => sum + lines.length * 12.5 + 2, 0)
      + 5;
    return { primaryLines, secondaryLines, bulletLines, height };
  };

  const writeExperience = (item: Experience) => {
    const layout = experienceLayout(item);
    if (layout.height <= usablePageHeight) addPageIfNeeded(layout.height);

    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(10.5);
    pdf.setTextColor(21, 29, 40);
    pdf.text(layout.primaryLines, margin, y);
    if (item.dates) pdf.text(pdfSafeText(item.dates), pageWidth - margin, y, { align: "right" });
    y += Math.max(13, layout.primaryLines.length * 13);

    if (layout.secondaryLines.length) {
      pdf.setFont("helvetica", "italic");
      pdf.setFontSize(9);
      pdf.setTextColor(70, 76, 85);
      pdf.text(layout.secondaryLines, margin, y);
      y += layout.secondaryLines.length * 12;
    }

    item.bullets.forEach((bullet, index) => {
      const lines = layout.bulletLines[index];
      addPageIfNeeded(lines.length * 12.5 + 2);
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(9.3);
      pdf.setTextColor(31, 39, 49);
      pdf.text(lines, margin + 4, y);
      y += lines.length * 12.5 + 2;
    });
    y += 5;
  };

  const educationLayout = (item: Education) => {
    const primary = item.degree || item.school;
    const primaryWidth = item.dates ? contentWidth - 132 : contentWidth;
    const primaryLines = linesFor(primary, primaryWidth);
    const secondary = [item.degree ? item.school : "", item.location].filter(Boolean).join(" | ");
    const secondaryLines = secondary ? linesFor(secondary) : [];
    const detailLines = item.details.map((detail) => linesFor(`- ${detail}`, contentWidth - 4));
    const height = Math.max(13, primaryLines.length * 13)
      + secondaryLines.length * 12.42
      + detailLines.reduce((sum, lines) => sum + lines.length * 12.42, 0)
      + 3;
    return { primaryLines, secondaryLines, detailLines, height };
  };

  const writeEducation = (item: Education) => {
    const layout = educationLayout(item);
    if (layout.height <= usablePageHeight) addPageIfNeeded(layout.height);

    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(10.2);
    pdf.setTextColor(21, 29, 40);
    pdf.text(layout.primaryLines, margin, y);
    if (item.dates) pdf.text(pdfSafeText(item.dates), pageWidth - margin, y, { align: "right" });
    y += Math.max(13, layout.primaryLines.length * 13);

    if (layout.secondaryLines.length) {
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(9);
      pdf.setTextColor(31, 39, 49);
      pdf.text(layout.secondaryLines, margin, y);
      y += layout.secondaryLines.length * 12.42;
    }

    layout.detailLines.forEach((lines) => {
      addPageIfNeeded(lines.length * 12.42);
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(9);
      pdf.setTextColor(31, 39, 49);
      pdf.text(lines, margin + 4, y);
      y += lines.length * 12.42;
    });
    y += 3;
  };

  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(21);
  pdf.setTextColor(18, 32, 51);
  const nameLines = linesFor(resume.name || "Resume", contentWidth);
  pdf.text(nameLines, pageWidth / 2, y, { align: "center" });
  y += nameLines.length * 22;

  if (resume.headline) {
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(10);
    pdf.setTextColor(78, 86, 96);
    const headlineLines = linesFor(resume.headline, contentWidth);
    pdf.text(headlineLines, pageWidth / 2, y, { align: "center" });
    y += headlineLines.length * 13;
  }

  if (resume.contact) {
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(8.7);
    pdf.setTextColor(62, 69, 78);
    const contactLines = linesFor(resume.contact, contentWidth);
    contactLines.forEach((line, index) => drawContactLine(line, y + index * 11));
    y += contactLines.length * 11 + 3;
  }

  y += 4;

  if (resume.summary) {
    const summaryLines = linesFor(resume.summary);
    sectionTitle("Professional summary", summaryLines.length * 13.11);
    writeLines(resume.summary);
  }
  if (resume.skills.length) {
    const skillLines = linesFor(resume.skills.join(" | "));
    sectionTitle("Core skills", skillLines.length * 13.11);
    writeLines(resume.skills.join(" | "));
  }
  if (resume.experience.length) {
    sectionTitle("Experience", Math.min(experienceLayout(resume.experience[0]).height, usablePageHeight));
    resume.experience.forEach(writeExperience);
  }
  if (resume.projects.length) {
    sectionTitle("Selected projects", Math.min(experienceLayout(resume.projects[0]).height, usablePageHeight));
    resume.projects.forEach(writeExperience);
  }
  if (resume.education.length) {
    sectionTitle("Education", Math.min(educationLayout(resume.education[0]).height, usablePageHeight));
    resume.education.forEach(writeEducation);
  }
  if (resume.certifications.length) {
    const certificationLines = linesFor(resume.certifications.join(" | "));
    sectionTitle("Certifications", certificationLines.length * 13.11);
    writeLines(resume.certifications.join(" | "));
  }

  return pdf;
}

export async function saveResumeAsPdf(resume: ResumeDocument) {
  const pdf = await createResumePdf(resume);
  const safeName = (resume.name || "tailored-resume")
    .replace(/[^a-z0-9]+/gi, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
  pdf.save(`${safeName || "tailored-resume"}-ats-resume.pdf`);
}
