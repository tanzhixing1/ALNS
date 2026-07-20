import fs from "node:fs";
import path from "node:path";
import { createCanvas } from "file:///C:/Users/19088/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas/index.js";
import * as pdfjsLib from "file:///C:/Users/19088/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pdfjs-dist/legacy/build/pdf.mjs";

const [pdfPath, outputDir, ...rawPages] = process.argv.slice(2);
const pageNumbers = rawPages.map(Number);
const bytes = new Uint8Array(fs.readFileSync(pdfPath));
const document = await pdfjsLib.getDocument({ data: bytes }).promise;

for (const pageNumber of pageNumbers) {
  const page = await document.getPage(pageNumber);
  const viewport = page.getViewport({ scale: 2.25 });
  const canvas = createCanvas(Math.ceil(viewport.width), Math.ceil(viewport.height));
  const context = canvas.getContext("2d");
  await page.render({ canvasContext: context, viewport }).promise;
  const target = path.join(outputDir, `paper_pdf_page_${pageNumber}.png`);
  fs.writeFileSync(target, canvas.toBuffer("image/png"));
  process.stdout.write(`${target}\n`);
}
