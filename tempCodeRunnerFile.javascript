const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

// ── Icon helpers ─────────────────────────────────────────────
const { FaCode, FaFlask, FaDatabase, FaServer, FaUsers,
        FaCheckCircle, FaCog, FaLayerGroup, FaChartBar,
        FaGraduationCap, FaBug, FaSearch, FaShieldAlt,
        FaDocker, FaRobot, FaClipboardList, FaBook,
        FaExclamationTriangle, FaLightbulb } = require("react-icons/fa");

async function iconPng(Icon, color = "FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Icon, { color: "#" + color, size: String(size) })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ── Color palette ─────────────────────────────────────────────
const C = {
  navy:      "1B3A6B",
  blue:      "2563EB",
  lightBlue: "3B82F6",
  sky:       "BAD4F5",
  accent:    "F59E0B",
  white:     "FFFFFF",
  offWhite:  "F8FAFC",
  lightGray: "E2E8F0",
  midGray:   "94A3B8",
  darkGray:  "334155",
  darkBg:    "0F1D38",
  cardBg:    "EFF6FF",
};

async function buildPresentation() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title  = "Lab-Grader Thesis Presentation";

  // ════════════════════════════════════════════════════════
  // SLIDE 1 — COVER
  // ════════════════════════════════════════════════════════
  const s1 = pres.addSlide();
  s1.background = { color: C.darkBg };

  // Decorative circles
  s1.addShape(pres.shapes.OVAL, { x: -1.2, y: -1.2, w: 3.5, h: 3.5,
    fill: { color: C.navy }, line: { color: C.navy } });
  s1.addShape(pres.shapes.OVAL, { x: 8.2, y: 3.2, w: 3.0, h: 3.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s1.addShape(pres.shapes.OVAL, { x: 7.5, y: -0.5, w: 1.5, h: 1.5,
    fill: { color: C.blue, transparency: 70 }, line: { color: C.blue, transparency: 70 } });

  // Accent bar
  s1.addShape(pres.shapes.RECTANGLE, { x: 0, y: 2.45, w: 10, h: 0.035,
    fill: { color: C.accent }, line: { color: C.accent } });

  // Code icon top
  const codeIcon = await iconPng(FaCode, "F59E0B");
  s1.addImage({ data: codeIcon, x: 4.6, y: 0.45, w: 0.8, h: 0.8 });

  // Platform name
  s1.addText("Lab-Grader", { x: 0.5, y: 0.35, w: 9, h: 0.55,
    fontSize: 14, color: C.accent, bold: true, align: "center",
    fontFace: "Calibri", charSpacing: 4 });

  // Main title
  s1.addText("Website for Automatic Test Case\nGeneration and Evaluation\nof C Programming Assignments", {
    x: 0.5, y: 1.0, w: 9, h: 1.35,
    fontSize: 26, color: C.white, bold: true, align: "center",
    fontFace: "Calibri", valign: "middle"
  });

  // Divider
  s1.addShape(pres.shapes.RECTANGLE, { x: 3.5, y: 2.58, w: 3.0, h: 0.04,
    fill: { color: C.lightBlue }, line: { color: C.lightBlue } });

  // Info block
  const infoY = 2.75;
  const labels = ["Student:", "Supervisor:", "University:", "Department:", "Academic Year:"];
  const vals   = ["[ Student Name ]", "[ Supervisor Name ]", "[ University Name ]",
                  "Computer Science", "2025 – 2026"];
  labels.forEach((lbl, i) => {
    const y = infoY + i * 0.37;
    s1.addText(lbl, { x: 1.8, y, w: 1.8, h: 0.33,
      fontSize: 11, color: C.midGray, bold: true, fontFace: "Calibri", align: "right" });
    s1.addText(vals[i], { x: 3.7, y, w: 4.5, h: 0.33,
      fontSize: 11, color: C.sky, fontFace: "Calibri", align: "left" });
  });

  // Bottom tag
  s1.addText("University Thesis Defence  |  2026", { x: 0.5, y: 5.3, w: 9, h: 0.25,
    fontSize: 9, color: C.midGray, align: "center", fontFace: "Calibri" });

  // ════════════════════════════════════════════════════════
  // SLIDE 2 — INTRODUCTION
  // ════════════════════════════════════════════════════════
  const s2 = pres.addSlide();
  s2.background = { color: C.offWhite };

  // Title bar
  s2.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s2.addText("Introduction", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 24, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });
  const slideNum = await iconPng(FaGraduationCap, "FFFFFF");
  s2.addImage({ data: slideNum, x: 9.2, y: 0.25, w: 0.5, h: 0.5 });

  // Three info cards
  const cards2 = [
    { icon: FaGraduationCap, color: "2563EB", title: "Programming Education",
      body: "C language labs are a core component of CS curricula. Students learn through hands-on assignment-based exercises requiring rigorous evaluation." },
    { icon: FaExclamationTriangle, color: "F59E0B", title: "Manual Evaluation Limits",
      body: "With large student cohorts, manual grading is time-consuming, inconsistent, and lacks scalability — creating a bottleneck in academic assessment." },
    { icon: FaRobot, color: "10B981", title: "Automated Assessment",
      body: "Modern platforms automate compilation, execution, and scoring — yet most lack test case generation, static analysis, and intelligent feedback." },
  ];

  for (let i = 0; i < cards2.length; i++) {
    const x = 0.3 + i * 3.22;
    s2.addShape(pres.shapes.RECTANGLE, { x, y: 1.15, w: 3.05, h: 3.8,
      fill: { color: C.white },
      shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 135, opacity: 0.1 },
      line: { color: C.lightGray, width: 0.5 } });
    // Color top accent
    s2.addShape(pres.shapes.RECTANGLE, { x, y: 1.15, w: 3.05, h: 0.12,
      fill: { color: cards2[i].color }, line: { color: cards2[i].color } });
    const ic = await iconPng(cards2[i].icon, cards2[i].color);
    s2.addImage({ data: ic, x: x + 1.1, y: 1.35, w: 0.6, h: 0.6 });
    s2.addText(cards2[i].title, { x: x + 0.15, y: 2.05, w: 2.75, h: 0.5,
      fontSize: 13, color: C.navy, bold: true, fontFace: "Calibri", align: "center" });
    s2.addText(cards2[i].body, { x: x + 0.15, y: 2.6, w: 2.75, h: 2.2,
      fontSize: 10, color: C.darkGray, fontFace: "Calibri", align: "left", valign: "top" });
  }

  // ════════════════════════════════════════════════════════
  // SLIDE 3 — PROBLEMATIC
  // ════════════════════════════════════════════════════════
  const s3 = pres.addSlide();
  s3.background = { color: C.offWhite };

  s3.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s3.addText("Problem Statement", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 24, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });
  const bugIc = await iconPng(FaBug, "FFFFFF");
  s3.addImage({ data: bugIc, x: 9.2, y: 0.25, w: 0.5, h: 0.5 });

  // Left: problems list
  const problems = [
    ["Large student cohorts", "Instructors manage dozens of submissions per assignment, making individual review impractical."],
    ["Time constraints", "Manual compilation, testing, and grading consumes hours that could be redirected to teaching."],
    ["Inconsistent grading", "Human evaluation introduces subjectivity and variability across submissions and sessions."],
    ["No automated analysis", "Existing tools lack static code analysis and do not generate test cases from reference solutions."],
  ];

  problems.forEach(([title, desc], i) => {
    const y = 1.15 + i * 1.08;
    s3.addShape(pres.shapes.RECTANGLE, { x: 0.3, y, w: 5.8, h: 0.95,
      fill: { color: C.white },
      shadow: { type: "outer", color: "000000", blur: 4, offset: 1, angle: 135, opacity: 0.08 },
      line: { color: C.lightGray, width: 0.5 } });
    s3.addShape(pres.shapes.RECTANGLE, { x: 0.3, y, w: 0.1, h: 0.95,
      fill: { color: C.blue }, line: { color: C.blue } });
    s3.addText(title, { x: 0.55, y: y + 0.08, w: 5.4, h: 0.3,
      fontSize: 12, color: C.navy, bold: true, fontFace: "Calibri" });
    s3.addText(desc, { x: 0.55, y: y + 0.4, w: 5.4, h: 0.48,
      fontSize: 9.5, color: C.darkGray, fontFace: "Calibri" });
  });

  // Right: highlight box
  s3.addShape(pres.shapes.RECTANGLE, { x: 6.4, y: 1.15, w: 3.3, h: 4.25,
    fill: { color: C.navy }, line: { color: C.navy } });
  const excIc = await iconPng(FaExclamationTriangle, "F59E0B");
  s3.addImage({ data: excIc, x: 7.65, y: 1.35, w: 0.7, h: 0.7 });
  s3.addText("Core Challenge", { x: 6.5, y: 2.15, w: 3.1, h: 0.4,
    fontSize: 14, color: C.accent, bold: true, fontFace: "Calibri", align: "center" });
  s3.addText("The absence of a scalable, automated, and pedagogically meaningful evaluation system for C programming labs creates a critical gap in university computer science education.", {
    x: 6.55, y: 2.65, w: 3.0, h: 2.5,
    fontSize: 10.5, color: C.white, fontFace: "Calibri", align: "center", valign: "middle"
  });

  // ════════════════════════════════════════════════════════
  // SLIDE 4 — OBJECTIVES
  // ════════════════════════════════════════════════════════
  const s4 = pres.addSlide();
  s4.background = { color: C.offWhite };

  s4.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s4.addText("Objectives", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 24, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });
  const targetIc = await iconPng(FaCheckCircle, "FFFFFF");
  s4.addImage({ data: targetIc, x: 9.2, y: 0.25, w: 0.5, h: 0.5 });

  // Primary objective box
  s4.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 1.1, w: 9.4, h: 1.1,
    fill: { color: C.navy }, line: { color: C.navy } });
  s4.addText("PRIMARY OBJECTIVE", { x: 0.5, y: 1.12, w: 2.5, h: 0.35,
    fontSize: 9, color: C.accent, bold: true, fontFace: "Calibri", charSpacing: 2 });
  s4.addText("Design and implement a web platform that automatically generates test cases from a professor's reference solution and evaluates C programming assignments comprehensively and objectively.", {
    x: 0.5, y: 1.5, w: 9.0, h: 0.6,
    fontSize: 11.5, color: C.white, fontFace: "Calibri"
  });

  // Secondary objectives
  const secObjs = [
    [FaFlask,        "2563EB", "Auto Test Generation",    "Generate n×n test cases automatically from the reference solution using static analysis and execution capture."],
    [FaRobot,        "10B981", "Intelligent Feedback",     "Provide structured, layered feedback combining rule-based diagnostics and optional LLM-assisted suggestions."],
    [FaSearch,       "8B5CF6", "Static + Dynamic Analysis","Combine AST-based white-box analysis with black-box execution testing for hybrid evaluation."],
    [FaShieldAlt,    "F59E0B", "Secure Execution",         "Execute all student code inside isolated Docker containers with strict resource and network restrictions."],
    [FaChartBar,     "EF4444", "Academic Monitoring",      "Provide professors with aggregate statistics, leaderboards, and individual student progress tracking."],
    [FaClipboardList,"0EA5E9", "Assignment Management",    "Enable full assignment lifecycle management from creation to publication and post-deadline evaluation."],
  ];

  for (let i = 0; i < secObjs.length; i++) {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.3 + col * 3.22, y = 2.4 + row * 1.55;
    s4.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.05, h: 1.4,
      fill: { color: C.white },
      shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 135, opacity: 0.08 },
      line: { color: C.lightGray, width: 0.5 } });
    const ic = await iconPng(secObjs[i][0], secObjs[i][1]);
    s4.addImage({ data: ic, x: x + 0.15, y: y + 0.35, w: 0.38, h: 0.38 });
    s4.addText(secObjs[i][2], { x: x + 0.62, y: y + 0.1, w: 2.3, h: 0.45,
      fontSize: 11, color: C.navy, bold: true, fontFace: "Calibri" });
    s4.addText(secObjs[i][3], { x: x + 0.62, y: y + 0.55, w: 2.3, h: 0.75,
      fontSize: 8.5, color: C.darkGray, fontFace: "Calibri" });
  }

  // ════════════════════════════════════════════════════════
  // SLIDE 5 — CHAPTERS OVERVIEW
  // ════════════════════════════════════════════════════════
  const s5 = pres.addSlide();
  s5.background = { color: C.offWhite };

  s5.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s5.addText("Thesis Structure", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 24, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });
  const bookIc = await iconPng(FaBook, "FFFFFF");
  s5.addImage({ data: bookIc, x: 9.2, y: 0.25, w: 0.5, h: 0.5 });

  const chapters = [
    ["01", C.blue,    "Theoretical Foundations",      "Static analysis, dynamic testing, automated grading, AST parsing, Docker sandboxing, and hybrid evaluation concepts."],
    ["02", "8B5CF6",  "Related Work",                 "Comparative study of LeetCode, HackerRank, VPL, and CodeRunner — strengths, limitations, and identified research gaps."],
    ["03", "10B981",  "System Analysis & Design",     "Functional and non-functional requirements, actor roles, UML use case diagrams, and five-layer modular architecture design."],
    ["04", C.accent,  "System Implementation",        "Technology stack, core modules, Docker sandbox, test generation pipeline, evaluation engine, and feedback system."],
  ];

  chapters.forEach(([num, color, title, desc], i) => {
    const y = 1.18 + i * 1.08;
    s5.addShape(pres.shapes.RECTANGLE, { x: 0.3, y, w: 9.4, h: 0.97,
      fill: { color: C.white },
      shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 135, opacity: 0.08 },
      line: { color: C.lightGray, width: 0.5 } });
    s5.addShape(pres.shapes.RECTANGLE, { x: 0.3, y, w: 0.85, h: 0.97,
      fill: { color }, line: { color } });
    s5.addText(num, { x: 0.3, y, w: 0.85, h: 0.97,
      fontSize: 22, color: C.white, bold: true, fontFace: "Calibri",
      align: "center", valign: "middle" });
    s5.addText(title, { x: 1.3, y: y + 0.08, w: 4.5, h: 0.38,
      fontSize: 13, color: C.navy, bold: true, fontFace: "Calibri" });
    s5.addText(desc, { x: 1.3, y: y + 0.48, w: 8.2, h: 0.42,
      fontSize: 9.5, color: C.darkGray, fontFace: "Calibri" });
  });

  // ════════════════════════════════════════════════════════
  // SLIDE 6 — THEORETICAL FOUNDATIONS
  // ════════════════════════════════════════════════════════
  const s6 = pres.addSlide();
  s6.background = { color: C.offWhite };

  s6.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s6.addText("Chapter 1 — Theoretical Foundations", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 22, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  const concepts = [
    [FaSearch,   "2563EB", "Static Code Analysis",    "Examines source code without execution. Uses AST traversal (pycparser) to extract function signatures, detect code smells, and measure cyclomatic complexity."],
    [FaFlask,    "10B981", "Dynamic / Black-box Testing", "Executes the program with generated inputs and compares outputs to expected results captured from the reference solution."],
    [FaCog,      "8B5CF6", "Automated Grading",        "Systematically assigns scores based on weighted test case results, applying late penalties and bonus points algorithmically."],
    [FaLayerGroup,"F59E0B","Hybrid Evaluation",        "Combines static white-box metrics with dynamic black-box execution results to produce a comprehensive, multi-dimensional assessment."],
    [FaCode,     "EF4444", "Abstract Syntax Tree (AST)","Tree-structured representation of source code parsed by pycparser, enabling structural inspection without compilation."],
    [FaDocker,   "0EA5E9", "Docker Sandboxing",        "Isolated execution environment enforcing memory, CPU, network, and process limits — protecting infrastructure from untrusted student code."],
  ];

  for (let i = 0; i < concepts.length; i++) {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.3 + col * 4.85, y = 1.12 + row * 1.5;
    s6.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.6, h: 1.35,
      fill: { color: C.white },
      shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 135, opacity: 0.08 },
      line: { color: C.lightGray, width: 0.5 } });
    const ic = await iconPng(concepts[i][0], concepts[i][1]);
    s6.addImage({ data: ic, x: x + 0.2, y: y + 0.35, w: 0.48, h: 0.48 });
    s6.addText(concepts[i][2], { x: x + 0.82, y: y + 0.1, w: 3.6, h: 0.4,
      fontSize: 11.5, color: C.navy, bold: true, fontFace: "Calibri" });
    s6.addText(concepts[i][3], { x: x + 0.82, y: y + 0.52, w: 3.6, h: 0.78,
      fontSize: 9, color: C.darkGray, fontFace: "Calibri" });
  }

  // ════════════════════════════════════════════════════════
  // SLIDE 7 — RELATED WORK
  // ════════════════════════════════════════════════════════
  const s7 = pres.addSlide();
  s7.background = { color: C.offWhite };

  s7.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s7.addText("Chapter 2 — Related Work", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 22, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  // Platform comparison table
  const tableRows = [
    [
      { text: "Platform",        options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
      { text: "Auto Test Gen.",  options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
      { text: "Static Analysis", options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
      { text: "Rich Feedback",   options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
      { text: "Auto Evaluation", options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
    ],
    ["LeetCode",    "✗", "✗", "✗", "✓"],
    ["HackerRank",  "✗", "✗", "✗", "✓"],
    ["CodeRunner",  "✗", "✗", "✗", "✓"],
    ["VPL",         "✗", "✗", "✗", "✓"],
    [
      { text: "Lab-Grader", options: { bold: true, color: C.navy, fontSize: 11 } },
      { text: "✓", options: { bold: true, color: "10B981", fontSize: 13 } },
      { text: "✓", options: { bold: true, color: "10B981", fontSize: 13 } },
      { text: "✓", options: { bold: true, color: "10B981", fontSize: 13 } },
      { text: "✓", options: { bold: true, color: "10B981", fontSize: 13 } },
    ],
  ];

  s7.addTable(tableRows, {
    x: 0.3, y: 1.1, w: 9.4, h: 3.0,
    colW: [2.2, 1.8, 1.8, 1.8, 1.8],
    border: { pt: 0.5, color: "D1D5DB" },
    fontSize: 11, fontFace: "Calibri", align: "center", valign: "middle",
    fill: { color: C.white },
    rowH: 0.42,
  });

  // Limitations note
  s7.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 4.28, w: 9.4, h: 0.8,
    fill: { color: "FEF3C7" }, line: { color: "FCD34D", width: 1 } });
  const warnIc = await iconPng(FaExclamationTriangle, "F59E0B");
  s7.addImage({ data: warnIc, x: 0.5, y: 4.44, w: 0.35, h: 0.35 });
  s7.addText("Key Gap Identified: No existing platform combines automatic test case generation, static white-box analysis, and AI-assisted feedback within a single academic evaluation system.", {
    x: 0.98, y: 4.3, w: 8.5, h: 0.75,
    fontSize: 10, color: "92400E", fontFace: "Calibri", valign: "middle"
  });

  // ════════════════════════════════════════════════════════
  // SLIDE 8 — SYSTEM ANALYSIS & REQUIREMENTS
  // ════════════════════════════════════════════════════════
  const s8 = pres.addSlide();
  s8.background = { color: C.offWhite };

  s8.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s8.addText("Chapter 3 — System Analysis & Requirements", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 20, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  // Functional requirements
  s8.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 1.1, w: 4.55, h: 3.55,
    fill: { color: C.white },
    shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 135, opacity: 0.08 },
    line: { color: C.lightGray, width: 0.5 } });
  s8.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 1.1, w: 4.55, h: 0.45,
    fill: { color: C.blue }, line: { color: C.blue } });
  s8.addText("Functional Requirements", { x: 0.4, y: 1.1, w: 4.3, h: 0.45,
    fontSize: 12, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  const funcReqs = [
    "Manage assignment lifecycle (create, publish, close)",
    "Upload reference solution and generate test cases",
    "Accept and validate student C file submissions",
    "Compile and execute code in Docker sandbox",
    "Evaluate submissions against generated test cases",
    "Generate structured multilayer feedback per submission",
    "Send evaluation notifications to students",
    "Monitor student progress (professor dashboard)",
  ];
  s8.addText(funcReqs.map((r, i) => ({
    text: r, options: { bullet: true, breakLine: i < funcReqs.length - 1, color: C.darkGray, fontSize: 9.5 }
  })), { x: 0.5, y: 1.62, w: 4.2, h: 2.9, fontFace: "Calibri", valign: "top" });

  // Non-functional requirements
  s8.addShape(pres.shapes.RECTANGLE, { x: 5.15, y: 1.1, w: 4.55, h: 3.55,
    fill: { color: C.white },
    shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 135, opacity: 0.08 },
    line: { color: C.lightGray, width: 0.5 } });
  s8.addShape(pres.shapes.RECTANGLE, { x: 5.15, y: 1.1, w: 4.55, h: 0.45,
    fill: { color: "8B5CF6" }, line: { color: "8B5CF6" } });
  s8.addText("Non-Functional Requirements", { x: 5.25, y: 1.1, w: 4.3, h: 0.45,
    fontSize: 12, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  const nfReqs = [
    "Security — sandboxed execution, JWT authentication",
    "Performance — async evaluation via Celery workers",
    "Scalability — distributed task queues with Redis",
    "Reliability — retry logic and stale task cleanup",
    "Usability — role-differentiated responsive UI",
    "Maintainability — modular five-layer architecture",
    "Consistency — scores always /20, objective grading",
  ];
  s8.addText(nfReqs.map((r, i) => ({
    text: r, options: { bullet: true, breakLine: i < nfReqs.length - 1, color: C.darkGray, fontSize: 9.5 }
  })), { x: 5.3, y: 1.62, w: 4.2, h: 2.9, fontFace: "Calibri", valign: "top" });

  // Actor row
  const actors = [
    ["F", C.blue,   "Professor", "Creates assignments, uploads reference solutions, monitors results"],
    ["S", "10B981", "Student",   "Views assignments, submits C code, receives feedback and scores"],
  ];
  actors.forEach(([letter, color, role, desc], i) => {
    const x = 1.3 + i * 5.0;
    s8.addShape(pres.shapes.OVAL, { x, y: 4.78, w: 0.55, h: 0.55,
      fill: { color }, line: { color } });
    s8.addText(letter, { x, y: 4.78, w: 0.55, h: 0.55,
      fontSize: 14, color: C.white, bold: true, fontFace: "Calibri",
      align: "center", valign: "middle" });
    s8.addText(role, { x: x + 0.65, y: 4.82, w: 2.0, h: 0.28,
      fontSize: 12, color: C.navy, bold: true, fontFace: "Calibri" });
    s8.addText(desc, { x: x + 0.65, y: 5.1, w: 3.5, h: 0.4,
      fontSize: 9, color: C.darkGray, fontFace: "Calibri" });
  });

  // ════════════════════════════════════════════════════════
  // SLIDE 9 — USE CASE DIAGRAM
  // ════════════════════════════════════════════════════════
  const s9 = pres.addSlide();
  s9.background = { color: C.offWhite };

  s9.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s9.addText("UML Use Case Diagram", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 24, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  // System boundary
  s9.addShape(pres.shapes.RECTANGLE, { x: 2.1, y: 1.05, w: 5.8, h: 4.45,
    fill: { color: "EFF6FF" }, line: { color: C.blue, width: 1.5 } });
  s9.addText("«system»  Lab-Grader Platform", { x: 2.1, y: 1.05, w: 5.8, h: 0.38,
    fontSize: 10, color: C.blue, bold: true, fontFace: "Calibri", align: "center" });

  // Use cases — Professor
  const profUC = [
    [3.5, 1.65, "Manage Assignments"],
    [3.5, 2.2,  "Upload Reference Solution"],
    [3.5, 2.75, "Generate Test Cases"],
    [3.5, 3.3,  "View Submission Statistics"],
    [3.5, 3.85, "Override Feedback"],
  ];
  profUC.forEach(([x, y, label]) => {
    s9.addShape(pres.shapes.OVAL, { x, y, w: 2.9, h: 0.42,
      fill: { color: "DBEAFE" }, line: { color: C.blue, width: 0.8 } });
    s9.addText(label, { x, y, w: 2.9, h: 0.42,
      fontSize: 9.5, color: C.navy, fontFace: "Calibri", align: "center", valign: "middle" });
  });

  // Use cases — Student
  const stuUC = [
    [3.5, 4.4,  "Submit / Replace Solution"],
    [5.2, 1.65, "View Assignments"],
    [5.2, 2.2,  "Download Subject File"],
    [5.2, 2.75, "View Evaluation Results"],
    [5.2, 3.3,  "Receive Notifications"],
    [5.2, 3.85, "View Feedback Report"],
  ];
  stuUC.forEach(([x, y, label]) => {
    s9.addShape(pres.shapes.OVAL, { x, y, w: 2.9, h: 0.42,
      fill: { color: "D1FAE5" }, line: { color: "10B981", width: 0.8 } });
    s9.addText(label, { x, y, w: 2.9, h: 0.42,
      fontSize: 9.5, color: C.navy, fontFace: "Calibri", align: "center", valign: "middle" });
  });

  // Actors
  // Professor stick figure (text-based)
  s9.addShape(pres.shapes.OVAL, { x: 0.5, y: 1.55, w: 0.55, h: 0.55,
    fill: { color: C.blue }, line: { color: C.blue } });
  s9.addShape(pres.shapes.RECTANGLE, { x: 0.72, y: 2.1, w: 0.1, h: 0.6,
    fill: { color: C.blue }, line: { color: C.blue } });
  s9.addShape(pres.shapes.LINE, { x: 0.38, y: 2.35, w: 0.72, h: 0,
    line: { color: C.blue, width: 2 } });
  s9.addShape(pres.shapes.LINE, { x: 0.72, y: 2.7, w: 0.38, h: 0.35,
    line: { color: C.blue, width: 2 } });
  s9.addShape(pres.shapes.LINE, { x: 0.72, y: 2.7, w: 0.18, h: 0.35,
    line: { color: C.blue, width: 2 } });
  s9.addText("Professor", { x: 0.2, y: 3.1, w: 1.1, h: 0.3,
    fontSize: 10, color: C.navy, bold: true, fontFace: "Calibri", align: "center" });
  // Lines from professor to use cases
  profUC.forEach(([ucx, ucy]) => {
    s9.addShape(pres.shapes.LINE, { x: 1.05, y: 2.35, w: ucx - 1.05, h: ucy + 0.21 - 2.35,
      line: { color: C.midGray, width: 0.5, dashType: "dash" } });
  });

  // Student stick figure
  s9.addShape(pres.shapes.OVAL, { x: 8.95, y: 1.55, w: 0.55, h: 0.55,
    fill: { color: "10B981" }, line: { color: "10B981" } });
  s9.addShape(pres.shapes.RECTANGLE, { x: 9.17, y: 2.1, w: 0.1, h: 0.6,
    fill: { color: "10B981" }, line: { color: "10B981" } });
  s9.addShape(pres.shapes.LINE, { x: 8.83, y: 2.35, w: 0.72, h: 0,
    line: { color: "10B981", width: 2 } });
  s9.addShape(pres.shapes.LINE, { x: 9.17, y: 2.7, w: 0.38, h: 0.35,
    line: { color: "10B981", width: 2 } });
  s9.addShape(pres.shapes.LINE, { x: 9.17, y: 2.7, w: 0.18, h: 0.35,
    line: { color: "10B981", width: 2 } });
  s9.addText("Student", { x: 8.65, y: 3.1, w: 1.1, h: 0.3,
    fontSize: 10, color: C.navy, bold: true, fontFace: "Calibri", align: "center" });

  // ════════════════════════════════════════════════════════
  // SLIDE 10 — FIVE-LAYER ARCHITECTURE
  // ════════════════════════════════════════════════════════
  const s10 = pres.addSlide();
  s10.background = { color: C.offWhite };

  s10.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s10.addText("Five-Layer Modular Architecture", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 24, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });
  const layerIc = await iconPng(FaLayerGroup, "FFFFFF");
  s10.addImage({ data: layerIc, x: 9.2, y: 0.25, w: 0.5, h: 0.5 });

  const layers = [
    [FaCode,      "2563EB", "① Presentation Layer",    "React + Vite + Tailwind CSS",
     "Role-differentiated SPA for professors and students. Axios + React Query handle API communication and state."],
    [FaServer,    "8B5CF6", "② Application Layer",     "FastAPI + Pydantic + SQLAlchemy",
     "REST API gateway with JWT authentication, request validation, and service-layer delegation."],
    [FaSearch,    "10B981", "③ Service & Analysis Layer","Static Analyser + Evaluator + Feedback",
     "pycparser AST analysis, hybrid evaluation engine, test generator, and multilayer feedback service."],
    [FaShieldAlt, "F59E0B", "④ Execution Layer",       "Docker + GCC + Celery + Redis",
     "Sandboxed code execution with resource limits. Async task queue for non-blocking background evaluation."],
    [FaDatabase,  "EF4444", "⑤ Data Layer",            "PostgreSQL + File System",
     "Relational storage for users, assignments, and submissions. JSONB columns for evaluation results."],
  ];

  layers.forEach(([Icon, color, title, stack, desc], i) => {
    const y = 1.1 + i * 0.91;
    s10.addShape(pres.shapes.RECTANGLE, { x: 0.3, y, w: 9.4, h: 0.85,
      fill: { color: C.white },
      shadow: { type: "outer", color: "000000", blur: 4, offset: 1, angle: 135, opacity: 0.07 },
      line: { color: C.lightGray, width: 0.5 } });
    s10.addShape(pres.shapes.RECTANGLE, { x: 0.3, y, w: 0.12, h: 0.85,
      fill: { color }, line: { color } });
    const ic = await iconPng(Icon, color);
    s10.addImage({ data: ic, x: 0.55, y: y + 0.22, w: 0.38, h: 0.38 });
    s10.addText(title, { x: 1.08, y: y + 0.05, w: 2.8, h: 0.38,
      fontSize: 12, color: C.navy, bold: true, fontFace: "Calibri" });
    s10.addText(stack, { x: 1.08, y: y + 0.48, w: 2.8, h: 0.3,
      fontSize: 8.5, color, bold: true, fontFace: "Calibri" });
    s10.addText(desc, { x: 4.05, y: y + 0.12, w: 5.5, h: 0.65,
      fontSize: 9.5, color: C.darkGray, fontFace: "Calibri", valign: "middle" });
    // Separator
    s10.addShape(pres.shapes.LINE, { x: 3.9, y: y + 0.08, w: 0, h: 0.68,
      line: { color: C.lightGray, width: 0.5 } });
  });

  // ════════════════════════════════════════════════════════
  // SLIDE 11 — IMPLEMENTATION DETAILS
  // ════════════════════════════════════════════════════════
  const s11 = pres.addSlide();
  s11.background = { color: C.offWhite };

  s11.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s11.addText("Chapter 4 — Implementation Details", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 22, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  // Tech stack
  s11.addText("Technology Stack", { x: 0.3, y: 1.12, w: 9.4, h: 0.38,
    fontSize: 14, color: C.navy, bold: true, fontFace: "Calibri" });

  const techStack = [
    ["Frontend",   "React, Vite, Tailwind CSS, Zustand, Axios, React Query"],
    ["Backend",    "FastAPI, SQLAlchemy (async), Pydantic, JWT (python-jose)"],
    ["Workers",    "Celery, Redis (broker + results), Celery Beat (scheduler)"],
    ["Execution",  "Docker SDK, GCC, pycparser, Anthropic Claude API"],
    ["Database",   "PostgreSQL, JSONB columns, Alembic migrations"],
    ["DevOps",     "Docker Compose, bind-mount volumes, sandbox image build"],
  ];

  techStack.forEach(([label, val], i) => {
    const row = Math.floor(i / 3), col = i % 3;
    const x = 0.3 + col * 3.22, y = 1.58 + row * 0.62;
    s11.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.05, h: 0.55,
      fill: { color: C.cardBg }, line: { color: C.sky, width: 0.8 } });
    s11.addText(label + ":", { x: x + 0.12, y: y + 0.04, w: 0.85, h: 0.22,
      fontSize: 8.5, color: C.blue, bold: true, fontFace: "Calibri" });
    s11.addText(val, { x: x + 0.12, y: y + 0.26, w: 2.8, h: 0.25,
      fontSize: 8.5, color: C.darkGray, fontFace: "Calibri" });
  });

  // Algorithms
  s11.addText("Core Algorithms", { x: 0.3, y: 2.88, w: 9.4, h: 0.38,
    fontSize: 14, color: C.navy, bold: true, fontFace: "Calibri" });

  const algos = [
    [FaFlask, "2563EB", "Test Case Generation",
     "pycparser detects scanf patterns → generates n×n input combinations → runs reference solution → captures expected outputs → assigns weights summing to /20. Claude API fallback if execution fails."],
    [FaCog, "10B981", "Evaluation Engine",
     "Compiles student code via GCC inside Docker → runs each test case → compares stdout with expected output using configurable normalisation modes → applies late penalty → scores out of 20."],
    [FaLightbulb, "F59E0B", "Feedback System",
     "Rule-based engine maps GCC errors to plain-language hints, analyses per-test failures, and reports static metrics. Optional Claude API layer adds context-aware improvement suggestions."],
  ];

  algos.forEach(([Icon, color, title, desc], i) => {
    const x = 0.3 + i * 3.22;
    s11.addShape(pres.shapes.RECTANGLE, { x, y: 3.32, w: 3.05, h: 2.15,
      fill: { color: C.white },
      shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 135, opacity: 0.08 },
      line: { color: C.lightGray, width: 0.5 } });
    s11.addShape(pres.shapes.RECTANGLE, { x, y: 3.32, w: 3.05, h: 0.1,
      fill: { color }, line: { color } });
    const ic = await iconPng(Icon, color);
    s11.addImage({ data: ic, x: x + 1.25, y: 3.42, w: 0.45, h: 0.45 });
    s11.addText(title, { x: x + 0.15, y: 3.95, w: 2.75, h: 0.38,
      fontSize: 11, color: C.navy, bold: true, fontFace: "Calibri", align: "center" });
    s11.addText(desc, { x: x + 0.15, y: 4.38, w: 2.75, h: 1.0,
      fontSize: 8.5, color: C.darkGray, fontFace: "Calibri" });
  });

  // ════════════════════════════════════════════════════════
  // SLIDE 12 — SYSTEM ARCHITECTURE DIAGRAM
  // ════════════════════════════════════════════════════════
  const s12 = pres.addSlide();
  s12.background = { color: C.offWhite };

  s12.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s12.addText("System Architecture — Full Pipeline", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 22, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  // Draw 5 layered boxes with arrows
  const archLayers = [
    ["CLIENT",   C.blue,   "3B82F6", "React SPA — Professor & Student Interfaces"],
    ["API",      "7C3AED", "8B5CF6", "FastAPI — Routers · Services · Auth · Schemas"],
    ["WORKERS",  "B45309", "F59E0B", "Celery — Evaluate · Generate Tests · Notify"],
    ["SANDBOX",  "065F46", "10B981", "Docker — GCC Compile · Secure Execute · pycparser"],
    ["STORAGE",  "991B1B", "EF4444", "PostgreSQL · Redis · File System (uploads)"],
  ];

  archLayers.forEach(([tag, darkColor, lightColor, label], i) => {
    const y = 1.12 + i * 0.87;
    s12.addShape(pres.shapes.RECTANGLE, { x: 1.2, y, w: 7.6, h: 0.75,
      fill: { color: darkColor }, line: { color: darkColor } });
    s12.addText(tag, { x: 1.2, y, w: 1.4, h: 0.75,
      fontSize: 11, color: lightColor, bold: true, fontFace: "Calibri",
      align: "center", valign: "middle", charSpacing: 2 });
    s12.addShape(pres.shapes.LINE, { x: 2.6, y: y + 0.12, w: 0, h: 0.5,
      line: { color: lightColor, width: 0.5, transparency: 50 } });
    s12.addText(label, { x: 2.75, y, w: 6.0, h: 0.75,
      fontSize: 11, color: C.white, fontFace: "Calibri", valign: "middle" });

    // Arrow down (except last)
    if (i < archLayers.length - 1) {
      s12.addShape(pres.shapes.LINE, { x: 5.0, y: y + 0.75, w: 0, h: 0.12,
        line: { color: C.midGray, width: 1.5 } });
    }
  });

  // Data flow annotation
  s12.addShape(pres.shapes.RECTANGLE, { x: 0.2, y: 1.12, w: 0.85, h: 4.35,
    fill: { color: C.lightGray }, line: { color: C.lightGray } });
  s12.addText("DATA\nFLOW", { x: 0.2, y: 2.9, w: 0.85, h: 0.6,
    fontSize: 7.5, color: C.darkGray, bold: true, fontFace: "Calibri",
    align: "center", charSpacing: 1 });
  // Arrow
  s12.addShape(pres.shapes.LINE, { x: 0.62, y: 1.12, w: 0, h: 4.35,
    line: { color: C.blue, width: 2 } });

  // Bottom note
  s12.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 5.2, w: 9.4, h: 0.3,
    fill: { color: C.lightGray }, line: { color: C.lightGray } });
  s12.addText("Each submission flows: Client → API → Celery Queue → Docker Sandbox → Evaluator → Feedback Service → Notification → Client", {
    x: 0.3, y: 5.2, w: 9.4, h: 0.3,
    fontSize: 8.5, color: C.darkGray, fontFace: "Calibri", align: "center", valign: "middle"
  });

  // ════════════════════════════════════════════════════════
  // SLIDE 13 — ADVANTAGES & LIMITATIONS
  // ════════════════════════════════════════════════════════
  const s13 = pres.addSlide();
  s13.background = { color: C.offWhite };

  s13.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s13.addText("Advantages & Limitations", { x: 0.5, y: 0, w: 9, h: 1.0,
    fontSize: 24, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  // Advantages
  s13.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 1.05, w: 4.6, h: 4.35,
    fill: { color: C.white },
    shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 135, opacity: 0.08 },
    line: { color: C.lightGray, width: 0.5 } });
  s13.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 1.05, w: 4.6, h: 0.45,
    fill: { color: "10B981" }, line: { color: "10B981" } });
  const checkIc = await iconPng(FaCheckCircle, "FFFFFF");
  s13.addImage({ data: checkIc, x: 0.42, y: 1.13, w: 0.28, h: 0.28 });
  s13.addText("Advantages", { x: 0.78, y: 1.05, w: 4.0, h: 0.45,
    fontSize: 13, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  const advantages = [
    "Fully automated test case generation — no manual authoring required",
    "Objective and consistent scoring across all submissions (/20)",
    "Hybrid evaluation: static analysis + dynamic execution combined",
    "Multilayer feedback with per-test explanations and code hints",
    "Secure Docker sandbox — isolated, resource-limited execution",
    "Scalable async architecture handles large concurrent submissions",
    "Real-time evaluation status with live progress notifications",
    "Professor monitoring dashboard with statistics and leaderboard",
  ];
  s13.addText(advantages.map((a, i) => ({
    text: a, options: { bullet: true, breakLine: i < advantages.length - 1,
      color: C.darkGray, fontSize: 9.5 }
  })), { x: 0.5, y: 1.58, w: 4.25, h: 3.7, fontFace: "Calibri", valign: "top" });

  // Limitations
  s13.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 1.05, w: 4.6, h: 4.35,
    fill: { color: C.white },
    shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 135, opacity: 0.08 },
    line: { color: C.lightGray, width: 0.5 } });
  s13.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 1.05, w: 4.6, h: 0.45,
    fill: { color: "EF4444" }, line: { color: "EF4444" } });
  const warnIc2 = await iconPng(FaExclamationTriangle, "FFFFFF");
  s13.addImage({ data: warnIc2, x: 5.22, y: 1.13, w: 0.28, h: 0.28 });
  s13.addText("Limitations", { x: 5.58, y: 1.05, w: 4.0, h: 0.45,
    fontSize: 13, color: C.white, bold: true, fontFace: "Calibri", valign: "middle" });

  const limitations = [
    "Currently supports C language only — no multi-language capability",
    "Test generation depends on scanf-based input detection patterns",
    "LLM-assisted feedback requires an external Anthropic API key",
    "Docker-in-Docker introduces latency overhead per test execution",
    "No built-in plagiarism or code similarity detection module",
    "Edge cases with non-standard I/O may yield fewer test cases",
    "Reference solution must compile cleanly for generation to succeed",
  ];
  s13.addText(limitations.map((l, i) => ({
    text: l, options: { bullet: true, breakLine: i < limitations.length - 1,
      color: C.darkGray, fontSize: 9.5 }
  })), { x: 5.28, y: 1.58, w: 4.25, h: 3.7, fontFace: "Calibri", valign: "top" });

  // ════════════════════════════════════════════════════════
  // SLIDE 14 — CONCLUSION & FUTURE WORK
  // ════════════════════════════════════════════════════════
  const s14 = pres.addSlide();
  s14.background = { color: C.darkBg };

  // Decorative circles
  s14.addShape(pres.shapes.OVAL, { x: -1.0, y: 3.5, w: 3.0, h: 3.0,
    fill: { color: C.navy }, line: { color: C.navy } });
  s14.addShape(pres.shapes.OVAL, { x: 8.5, y: -0.8, w: 2.5, h: 2.5,
    fill: { color: C.navy }, line: { color: C.navy } });

  s14.addText("Conclusion & Future Work", { x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, color: C.white, bold: true, fontFace: "Calibri", align: "center" });
  s14.addShape(pres.shapes.RECTANGLE, { x: 3.5, y: 0.98, w: 3.0, h: 0.04,
    fill: { color: C.accent }, line: { color: C.accent } });

  // Conclusion box
  s14.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.1, w: 9.0, h: 1.7,
    fill: { color: C.navy }, line: { color: C.lightBlue, width: 0.8 } });
  s14.addText("Conclusion", { x: 0.7, y: 1.15, w: 2.0, h: 0.35,
    fontSize: 11, color: C.accent, bold: true, fontFace: "Calibri", charSpacing: 2 });
  s14.addText("Lab-Grader demonstrates that fully automated, objective, and pedagogically meaningful evaluation of C programming assignments is achievable within a single academic platform. By combining automatic test case generation, static code analysis, sandboxed execution, and multilayer feedback, the system reduces instructor workload while providing students with the immediate and detailed guidance needed to improve their programming skills.", {
    x: 0.7, y: 1.52, w: 8.6, h: 1.2,
    fontSize: 10.5, color: C.white, fontFace: "Calibri", valign: "middle"
  });

  // Future work
  s14.addText("Future Work", { x: 0.5, y: 2.95, w: 2.0, h: 0.35,
    fontSize: 13, color: C.accent, bold: true, fontFace: "Calibri" });

  const future = [
    [FaCode,     "3B82F6", "Multi-Language Support",   "Extend evaluation to C++, Python, and Java to broaden academic applicability."],
    [FaSearch,   "8B5CF6", "Plagiarism Detection",     "Integrate AST-based similarity analysis to support academic integrity enforcement."],
    [FaRobot,    "10B981", "Advanced AI Analysis",     "Deploy a self-hosted LLM to remove external API dependency and reduce operational costs."],
    [FaChartBar, "F59E0B", "Learning Analytics",       "Add cohort-level trend analysis to identify recurring error patterns and at-risk students."],
  ];

  future.forEach(([Icon, color, title, desc], i) => {
    const x = 0.5 + i * 2.28;
    s14.addShape(pres.shapes.RECTANGLE, { x, y: 3.38, w: 2.1, h: 2.0,
      fill: { color: C.navy }, line: { color, width: 0.8 } });
    const ic = await iconPng(Icon, color);
    s14.addImage({ data: ic, x: x + 0.78, y: 3.48, w: 0.42, h: 0.42 });
    s14.addText(title, { x: x + 0.1, y: 3.95, w: 1.9, h: 0.42,
      fontSize: 9.5, color, bold: true, fontFace: "Calibri", align: "center" });
    s14.addText(desc, { x: x + 0.1, y: 4.42, w: 1.9, h: 0.9,
      fontSize: 8.5, color: C.sky, fontFace: "Calibri", align: "center" });
  });

  // Thank you
  s14.addText("Thank You", { x: 0.5, y: 5.2, w: 9, h: 0.32,
    fontSize: 11, color: C.midGray, fontFace: "Calibri", align: "center" });

  // Write file
  await pres.writeFile({ fileName: "/mnt/user-data/outputs/LabGrader_Thesis_Presentation.pptx" });
  console.log("Done.");
}

buildPresentation().catch(console.error);