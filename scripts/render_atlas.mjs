#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(SCRIPT_DIR, "..");
const CELL_WIDTH = 192;
const CELL_HEIGHT = 208;
const ATLAS_COLUMNS = 8;
const ATLAS_ROWS = 11;
const RENDER_SCALE = 4;
const DEFAULT_MODEL = path.join(
  PROJECT_ROOT,
  "artwork",
  "source",
  "RobotExpressive.glb",
);
const DEFAULT_OUTPUT = path.join(PROJECT_ROOT, "tmp", "robot-atlas.png");
const DEFAULT_REPORT = path.join(PROJECT_ROOT, "tmp", "robot-render-report.json");

const ROWS = [
  { name: "idle", row: 0, frames: 6, clip: "Idle", loop: true, yaw: 0 },
  {
    name: "running-right",
    row: 1,
    frames: 8,
    clip: "Running",
    loop: true,
    yaw: -Math.PI / 2,
  },
  {
    name: "running-left",
    row: 2,
    frames: 8,
    clip: "Running",
    loop: true,
    yaw: Math.PI / 2,
  },
  { name: "waving", row: 3, frames: 4, clip: "Wave", loop: true, yaw: 0 },
  { name: "jumping", row: 4, frames: 5, clip: "Jump", loop: false, yaw: 0 },
  { name: "failed", row: 5, frames: 8, clip: "Death", loop: false, yaw: 0 },
  { name: "waiting", row: 6, frames: 6, clip: "Sitting", loop: true, yaw: 0 },
  { name: "running", row: 7, frames: 6, clip: "Punch", loop: false, yaw: 0 },
  {
    name: "review",
    row: 8,
    frames: 6,
    clip: "ThumbsUp",
    loop: false,
    yaw: 0,
  },
];

const LOOK_DIRECTIONS = [
  0,
  22.5,
  45,
  67.5,
  90,
  112.5,
  135,
  157.5,
  180,
  202.5,
  225,
  247.5,
  270,
  292.5,
  315,
  337.5,
];

function parseArguments(argv) {
  const values = {
    model: DEFAULT_MODEL,
    output: DEFAULT_OUTPUT,
    report: DEFAULT_REPORT,
    browser: process.env.ROBOT_RENDER_BROWSER || "",
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help") {
      console.log(`Usage: node scripts/render_atlas.mjs [options]

Options:
  --model PATH    Source RobotExpressive GLB
  --output PATH   Atlas PNG output (default: tmp/robot-atlas.png)
  --report PATH   Machine-readable render report
  --browser PATH  Chrome/Chromium executable override
  --help          Show this help
`);
      process.exit(0);
    }
    if (!["--model", "--output", "--report", "--browser"].includes(argument)) {
      throw new Error(`Unknown argument: ${argument}`);
    }
    const value = argv[index + 1];
    if (!value) {
      throw new Error(`${argument} requires a value`);
    }
    values[argument.slice(2)] = value;
    index += 1;
  }

  return {
    model: path.resolve(PROJECT_ROOT, values.model),
    output: path.resolve(PROJECT_ROOT, values.output),
    report: path.resolve(PROJECT_ROOT, values.report),
    browser: values.browser ? path.resolve(values.browser) : "",
  };
}

function sha256File(filePath) {
  const hash = crypto.createHash("sha256");
  hash.update(fs.readFileSync(filePath));
  return hash.digest("hex");
}

function findLocalBrowser(explicitPath) {
  const candidates = [
    explicitPath,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate)) || "";
}

function buildJobs() {
  const jobs = [];
  for (const row of ROWS) {
    for (let frame = 0; frame < row.frames; frame += 1) {
      const denominator = row.loop ? row.frames : Math.max(1, row.frames - 1);
      jobs.push({
        row: row.row,
        column: frame,
        state: row.name,
        clip: row.clip,
        loop: row.loop,
        timeRatio: frame / denominator,
        yaw: row.yaw,
        lookYaw: 0,
        lookPitch: 0,
      });
    }
  }

  for (let index = 0; index < LOOK_DIRECTIONS.length; index += 1) {
    const degrees = LOOK_DIRECTIONS[index];
    const radians = (degrees * Math.PI) / 180;
    jobs.push({
      row: index < 8 ? 9 : 10,
      column: index % 8,
      state: `look-${String(degrees).padStart(3, "0")}`,
      clip: "Standing",
      loop: false,
      timeRatio: 0.25,
      yaw: 0,
      lookYaw: Math.sin(radians) * 0.72,
      lookPitch: -Math.cos(radians) * 0.48,
    });
  }
  return jobs;
}

const RENDERER_SOURCE = String.raw`
import * as THREE from "/three.module.js";
import { GLTFLoader } from "/jsm/loaders/GLTFLoader.js";

const CELL_WIDTH = ${CELL_WIDTH};
const CELL_HEIGHT = ${CELL_HEIGHT};
const ATLAS_COLUMNS = ${ATLAS_COLUMNS};
const ATLAS_ROWS = ${ATLAS_ROWS};
const RENDER_SCALE = ${RENDER_SCALE};

const renderCanvas = document.querySelector("#render");
const atlasCanvas = document.querySelector("#atlas");
renderCanvas.width = CELL_WIDTH * RENDER_SCALE;
renderCanvas.height = CELL_HEIGHT * RENDER_SCALE;
atlasCanvas.width = CELL_WIDTH * ATLAS_COLUMNS;
atlasCanvas.height = CELL_HEIGHT * ATLAS_ROWS;

const renderer = new THREE.WebGLRenderer({
  alpha: true,
  antialias: true,
  canvas: renderCanvas,
  preserveDrawingBuffer: true,
  premultipliedAlpha: true,
  powerPreference: "high-performance",
});
renderer.setPixelRatio(1);
renderer.setSize(renderCanvas.width, renderCanvas.height, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;
renderer.setClearColor(0x000000, 0);

const scene = new THREE.Scene();
const aspect = CELL_WIDTH / CELL_HEIGHT;
const viewHeight = 3.1;
const camera = new THREE.OrthographicCamera(
  (-viewHeight * aspect) / 2,
  (viewHeight * aspect) / 2,
  viewHeight / 2,
  -viewHeight / 2,
  0.01,
  100,
);
camera.position.set(0, 0.08, 7);
camera.lookAt(0, 0, 0);

scene.add(new THREE.HemisphereLight(0xffffff, 0x536174, 2.1));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
keyLight.position.set(3, 5, 6);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0xc5ddff, 1.2);
rimLight.position.set(-4, 2, -3);
scene.add(rimLight);

const gltf = await new GLTFLoader().loadAsync("/model.glb");
const robot = gltf.scene;
scene.add(robot);
const clips = new Map(gltf.animations.map((clip) => [clip.name, clip]));
const requiredClips = [
  "Death",
  "Idle",
  "Jump",
  "Punch",
  "Running",
  "Sitting",
  "Standing",
  "ThumbsUp",
  "Wave",
];
for (const clipName of requiredClips) {
  if (!clips.has(clipName)) {
    throw new Error("Required animation clip is missing: " + clipName);
  }
}

const originalTransforms = new Map();
robot.traverse((node) => {
  originalTransforms.set(node.uuid, {
    position: node.position.clone(),
    quaternion: node.quaternion.clone(),
    scale: node.scale.clone(),
  });
  if (node.isMesh) {
    node.frustumCulled = false;
  }
});

const headCandidates = [];
robot.traverse((node) => {
  if (node.name === "Head") {
    headCandidates.push(node);
  }
});
const head = headCandidates.find((node) => node.isBone) || headCandidates[0];
if (!head) {
  throw new Error("RobotExpressive Head node was not found");
}

const mixer = new THREE.AnimationMixer(robot);
let activeAction = null;

function restorePose() {
  mixer.stopAllAction();
  activeAction = null;
  robot.traverse((node) => {
    const original = originalTransforms.get(node.uuid);
    if (!original) return;
    node.position.copy(original.position);
    node.quaternion.copy(original.quaternion);
    node.scale.copy(original.scale);
  });
  robot.position.set(0, 0, 0);
  robot.rotation.set(0, 0, 0);
  robot.scale.setScalar(1);
  robot.updateMatrixWorld(true);
}

function applyAnimation(clipName, timeRatio, loop) {
  const clip = clips.get(clipName);
  activeAction = mixer.clipAction(clip);
  activeAction.reset();
  activeAction.enabled = true;
  activeAction.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, loop ? Infinity : 1);
  activeAction.clampWhenFinished = !loop;
  activeAction.setEffectiveTimeScale(1);
  activeAction.setEffectiveWeight(1);
  activeAction.play();
  mixer.setTime(Math.max(0, Math.min(clip.duration, clip.duration * timeRatio)));
  return clip;
}

function boundsForCurrentPose() {
  robot.updateMatrixWorld(true);
  return new THREE.Box3().setFromObject(robot);
}

let maximumHeight = 0;
let maximumWidth = 0;
for (const clipName of requiredClips) {
  for (const timeRatio of [0, 0.25, 0.5, 0.75, 1]) {
    for (const yaw of [0, -Math.PI / 2, Math.PI / 2]) {
      restorePose();
      applyAnimation(clipName, timeRatio, false);
      robot.rotation.y = yaw;
      const box = boundsForCurrentPose();
      const size = box.getSize(new THREE.Vector3());
      maximumHeight = Math.max(maximumHeight, size.y);
      maximumWidth = Math.max(maximumWidth, size.x);
    }
  }
}
restorePose();

const targetHeight = 2.34;
const targetWidth = viewHeight * aspect * 0.86;
const fixedScale = Math.min(
  targetHeight / maximumHeight,
  targetWidth / maximumWidth,
);

function frameCurrentPose(job) {
  robot.rotation.y = job.yaw;
  if (job.lookPitch || job.lookYaw) {
    const lookDelta = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(job.lookPitch, job.lookYaw, 0, "YXZ"),
    );
    head.quaternion.multiply(lookDelta);
  }
  robot.scale.setScalar(fixedScale);
  robot.position.set(0, 0, 0);
  let box = boundsForCurrentPose();
  const centerX = (box.min.x + box.max.x) / 2;
  robot.position.x -= centerX;
  robot.position.y += -1.34 - box.min.y;
  box = boundsForCurrentPose();
  if (box.max.y > 1.43 || box.min.y < -1.43) {
    throw new Error(
      "Pose escaped the vertical safe area for " +
        job.state +
        ": " +
        JSON.stringify({ minY: box.min.y, maxY: box.max.y }),
    );
  }
}

function renderPose(job) {
  restorePose();
  const clip = applyAnimation(job.clip, job.timeRatio, job.loop);
  frameCurrentPose(job);
  renderer.clear();
  renderer.render(scene, camera);
  return {
    clip: clip.name,
    clipDuration: clip.duration,
  };
}

window.renderAtlas = async (jobs) => {
  const atlasContext = atlasCanvas.getContext("2d", { alpha: true });
  atlasContext.clearRect(0, 0, atlasCanvas.width, atlasCanvas.height);
  atlasContext.imageSmoothingEnabled = true;
  atlasContext.imageSmoothingQuality = "high";
  const rendered = [];
  for (const job of jobs) {
    const result = renderPose(job);
    atlasContext.drawImage(
      renderCanvas,
      job.column * CELL_WIDTH,
      job.row * CELL_HEIGHT,
      CELL_WIDTH,
      CELL_HEIGHT,
    );
    rendered.push({ ...job, ...result });
  }
  return {
    atlas: atlasCanvas.toDataURL("image/png"),
    rendered,
    renderer: renderer.info.render,
    threeRevision: THREE.REVISION,
    webgl: {
      renderer: renderer.getContext().getParameter(
        renderer.getContext().RENDERER,
      ),
      vendor: renderer.getContext().getParameter(renderer.getContext().VENDOR),
    },
    fixedScale,
    sourceBounds: { maximumHeight, maximumWidth },
  };
};

window.robotRendererReady = true;
`;

function rendererHtml() {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>RobotExpressive deterministic atlas renderer</title>
    <link rel="icon" href="data:,">
    <style>
      html, body { margin: 0; background: transparent; }
      canvas { display: block; }
      #atlas { display: none; }
    </style>
  </head>
  <body>
    <canvas id="render"></canvas>
    <canvas id="atlas"></canvas>
    <script type="importmap">
      {
        "imports": {
          "three": "/three.module.js",
          "three/addons/": "/jsm/"
        }
      }
    </script>
    <script type="module" src="/renderer.js"></script>
  </body>
</html>`;
}

function startServer(modelPath) {
  const threeModule = path.join(
    PROJECT_ROOT,
    "node_modules",
    "three",
    "build",
    "three.module.js",
  );
  const threeCoreModule = path.join(
    PROJECT_ROOT,
    "node_modules",
    "three",
    "build",
    "three.core.js",
  );
  const addonsRoot = path.join(
    PROJECT_ROOT,
    "node_modules",
    "three",
    "examples",
    "jsm",
  );
  const loaderModule = path.join(addonsRoot, "loaders", "GLTFLoader.js");
  for (const requiredPath of [threeModule, threeCoreModule, loaderModule]) {
    if (!fs.existsSync(requiredPath)) {
      throw new Error(
        `Missing renderer dependency ${requiredPath}. Run pnpm install first.`,
      );
    }
  }

  const routes = new Map([
    ["/", { type: "text/html; charset=utf-8", body: rendererHtml() }],
    [
      "/renderer.js",
      { type: "text/javascript; charset=utf-8", body: RENDERER_SOURCE },
    ],
    [
      "/three.module.js",
      { type: "text/javascript; charset=utf-8", file: threeModule },
    ],
    [
      "/three.core.js",
      { type: "text/javascript; charset=utf-8", file: threeCoreModule },
    ],
    ["/model.glb", { type: "model/gltf-binary", file: modelPath }],
  ]);

  const server = http.createServer((request, response) => {
    const requestPath = new URL(request.url, "http://127.0.0.1").pathname;
    let route = routes.get(requestPath);
    if (requestPath.startsWith("/jsm/")) {
      const relativePath = requestPath.slice("/jsm/".length);
      const resolvedPath = path.resolve(addonsRoot, relativePath);
      if (
        resolvedPath.startsWith(`${path.resolve(addonsRoot)}${path.sep}`) &&
        fs.existsSync(resolvedPath)
      ) {
        route = {
          type: "text/javascript; charset=utf-8",
          file: resolvedPath,
        };
      }
    }
    if (!route) {
      response.writeHead(404, { "Content-Type": "text/plain" });
      response.end("Not found");
      return;
    }
    response.writeHead(200, {
      "Cache-Control": "no-store",
      "Content-Type": route.type,
    });
    if (route.file) {
      fs.createReadStream(route.file).pipe(response);
    } else {
      response.end(route.body);
    }
  });

  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve({
        server,
        url: `http://127.0.0.1:${address.port}/`,
      });
    });
  });
}

function decodeDataUrl(dataUrl) {
  const marker = "base64,";
  const markerIndex = dataUrl.indexOf(marker);
  if (markerIndex < 0) {
    throw new Error("Renderer did not return a base64 PNG data URL");
  }
  return Buffer.from(dataUrl.slice(markerIndex + marker.length), "base64");
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  if (!fs.existsSync(options.model)) {
    throw new Error(`Model does not exist: ${options.model}`);
  }
  const jobs = buildJobs();
  if (jobs.length !== 73) {
    throw new Error(`Unexpected populated cell count: ${jobs.length}`);
  }
  fs.mkdirSync(path.dirname(options.output), { recursive: true });
  fs.mkdirSync(path.dirname(options.report), { recursive: true });

  const { server, url } = await startServer(options.model);
  const executablePath = findLocalBrowser(options.browser);
  const launchOptions = {
    headless: true,
    args: [
      "--disable-gpu-sandbox",
      "--enable-webgl",
      "--ignore-gpu-blocklist",
      "--use-angle=swiftshader",
      "--use-gl=angle",
    ],
  };
  if (executablePath) {
    launchOptions.executablePath = executablePath;
  }

  let browser;
  let renderingComplete = false;
  try {
    browser = await chromium.launch(launchOptions);
    const page = await browser.newPage({
      viewport: { width: 900, height: 900 },
    });
    page.on("console", (message) => {
      if (message.type() === "error") {
        console.error(`[browser] ${message.text()}`);
      }
    });
    page.on("pageerror", (error) => {
      console.error(`[browser-page] ${error.message}`);
    });
    page.on("response", (response) => {
      if (!renderingComplete && response.status() >= 400) {
        console.error(`[browser-response] ${response.status()} ${response.url()}`);
      }
    });
    page.on("requestfailed", (request) => {
      if (!renderingComplete) {
        console.error(
          `[browser-request] ${request.failure()?.errorText || "failed"} ${request.url()}`,
        );
      }
    });
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForFunction(() => window.robotRendererReady === true, null, {
      timeout: 30_000,
    });
    const result = await page.evaluate(
      async (renderJobs) => window.renderAtlas(renderJobs),
      jobs,
    );
    fs.writeFileSync(options.output, decodeDataUrl(result.atlas));
    const report = {
      schemaVersion: 1,
      project: "robot-expressive-codex-pet",
      model: {
        path: path.relative(PROJECT_ROOT, options.model).replaceAll("\\", "/"),
        sha256: sha256File(options.model),
      },
      output: {
        path: path.relative(PROJECT_ROOT, options.output).replaceAll("\\", "/"),
        sha256: sha256File(options.output),
        width: CELL_WIDTH * ATLAS_COLUMNS,
        height: CELL_HEIGHT * ATLAS_ROWS,
        populatedCells: jobs.length,
      },
      browser: executablePath ? path.basename(executablePath) : "playwright-chromium",
      threeRevision: result.threeRevision,
      webgl: result.webgl,
      sourceBounds: result.sourceBounds,
      fixedScale: result.fixedScale,
      jobs: result.rendered,
    };
    fs.writeFileSync(options.report, `${JSON.stringify(report, null, 2)}\n`);
    renderingComplete = true;
    console.log(
      JSON.stringify(
        {
          ok: true,
          output: options.output,
          report: options.report,
          populatedCells: jobs.length,
          modelSha256: report.model.sha256,
          atlasSha256: report.output.sha256,
        },
        null,
        2,
      ),
    );
  } finally {
    if (browser) {
      await browser.close();
    }
    await new Promise((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error));
  process.exitCode = 1;
});
