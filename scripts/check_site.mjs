#!/usr/bin/env node

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SITE_ROOT = path.join(PROJECT_ROOT, "site");
const CONTENT_TYPES = new Map([
  [".css", "text/css; charset=utf-8"],
  [".gif", "image/gif"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".webp", "image/webp"],
]);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function findLocalBrowser() {
  const override = process.env.ROBOT_RENDER_BROWSER || "";
  const candidates = [
    override,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate)) || "";
}

function startServer() {
  assert(fs.existsSync(path.join(SITE_ROOT, "index.html")), "site/ is missing; build it first");
  const root = path.resolve(SITE_ROOT);
  const server = http.createServer((request, response) => {
    const requestPath = new URL(request.url, "http://127.0.0.1").pathname;
    if (requestPath === "/favicon.ico") {
      response.writeHead(204);
      response.end();
      return;
    }
    const relative = requestPath === "/" ? "index.html" : requestPath.slice(1);
    const candidate = path.resolve(root, decodeURIComponent(relative));
    if (
      candidate !== root &&
      !candidate.startsWith(`${root}${path.sep}`)
    ) {
      response.writeHead(403);
      response.end("Forbidden");
      return;
    }
    if (!fs.existsSync(candidate) || !fs.statSync(candidate).isFile()) {
      response.writeHead(404);
      response.end("Not found");
      return;
    }
    response.writeHead(200, {
      "Cache-Control": "no-store",
      "Content-Type": CONTENT_TYPES.get(path.extname(candidate)) || "application/octet-stream",
    });
    fs.createReadStream(candidate).pipe(response);
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve({ server, url: `http://127.0.0.1:${address.port}/` });
    });
  });
}

async function inspectPage(browser, url, options) {
  const context = await browser.newContext(options);
  const page = await context.newPage();
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForFunction(
    () => document.querySelector("#atlas-status")?.textContent?.includes("ready"),
  );
  assert(await page.locator("#pet-canvas").isVisible(), "pet canvas is not visible");
  assert((await page.locator("#validation-verdict").textContent()) === "PASS", "validation is not PASS");
  await page.locator('button[data-state="waving"]').click();
  assert((await page.locator("#stage-state").textContent()) === "Wave", "wave control failed");
  await page.locator("#direction-slider").fill("15");
  assert(
    (await page.locator("#direction-output").textContent()).includes("337.5"),
    "look-direction control failed",
  );
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  assert(!overflow, "page has horizontal overflow");
  assert(errors.length === 0, errors.join("\n"));
  await context.close();
}

async function main() {
  const { server, url } = await startServer();
  const executablePath = findLocalBrowser();
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      ...(executablePath ? { executablePath } : {}),
    });
    await inspectPage(browser, url, { viewport: { width: 1280, height: 900 } });
    await inspectPage(browser, url, {
      reducedMotion: "reduce",
      viewport: { width: 360, height: 780 },
    });
    console.log(
      JSON.stringify(
        {
          ok: true,
          browser: executablePath ? path.basename(executablePath) : "playwright-chromium",
          checks: [
            "atlas-loaded",
            "validation-pass",
            "state-control",
            "direction-control",
            "desktop-layout",
            "mobile-reduced-motion-layout",
            "no-browser-errors",
          ],
        },
        null,
        2,
      ),
    );
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
