"use strict";

const CELL_WIDTH = 192;
const CELL_HEIGHT = 208;

const STATES = {
  idle: { row: 0, label: "Idle", durations: [280, 110, 110, 140, 140, 320] },
  "running-right": {
    row: 1,
    label: "Travel right",
    durations: [120, 120, 120, 120, 120, 120, 120, 220],
  },
  "running-left": {
    row: 2,
    label: "Travel left",
    durations: [120, 120, 120, 120, 120, 120, 120, 220],
  },
  waving: { row: 3, label: "Wave", durations: [140, 140, 140, 280] },
  jumping: { row: 4, label: "Jump", durations: [140, 140, 140, 140, 280] },
  failed: {
    row: 5,
    label: "Failed",
    durations: [140, 140, 140, 140, 140, 140, 140, 240],
  },
  waiting: { row: 6, label: "Needs input", durations: [150, 150, 150, 150, 150, 260] },
  running: { row: 7, label: "Working", durations: [120, 120, 120, 120, 120, 220] },
  review: { row: 8, label: "Reviewing", durations: [150, 150, 150, 150, 150, 280] },
};

const DIRECTIONS = [
  ["000", "up"],
  ["022.5", "up-right"],
  ["045", "up-right"],
  ["067.5", "up-right"],
  ["090", "right"],
  ["112.5", "down-right"],
  ["135", "down-right"],
  ["157.5", "down-right"],
  ["180", "down"],
  ["202.5", "down-left"],
  ["225", "down-left"],
  ["247.5", "down-left"],
  ["270", "left"],
  ["292.5", "up-left"],
  ["315", "up-left"],
  ["337.5", "up-left"],
];

const canvas = document.querySelector("#pet-canvas");
const context = canvas.getContext("2d", { alpha: true });
const stateControls = document.querySelector("#state-controls");
const stageState = document.querySelector("#stage-state");
const stageFrame = document.querySelector("#stage-frame");
const status = document.querySelector("#atlas-status");
const directionSlider = document.querySelector("#direction-slider");
const directionOutput = document.querySelector("#direction-output");
const motionToggle = document.querySelector("#motion-toggle");
const validationVerdict = document.querySelector("#validation-verdict");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

let currentState = "idle";
let currentFrame = 0;
let directionIndex = null;
let playing = !reducedMotion.matches;
let loaded = false;
let nextFrameAt = 0;
let animationRequest = 0;

const atlas = new Image();
atlas.decoding = "async";
atlas.src = "assets/spritesheet.webp";

function fitCanvasToDisplay() {
  const ratio = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
  canvas.width = Math.round(384 * ratio);
  canvas.height = Math.round(416 * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
}

function renderFrame() {
  if (!loaded) {
    return;
  }
  const spec = STATES[currentState];
  let row = spec.row;
  let column = currentFrame;
  if (directionIndex !== null) {
    row = 9 + Math.floor(directionIndex / 8);
    column = directionIndex % 8;
  }
  context.clearRect(0, 0, 384, 416);
  context.drawImage(
    atlas,
    column * CELL_WIDTH,
    row * CELL_HEIGHT,
    CELL_WIDTH,
    CELL_HEIGHT,
    0,
    0,
    384,
    416,
  );
  if (directionIndex === null) {
    stageState.textContent = spec.label;
    stageFrame.textContent = `Frame ${currentFrame + 1} of ${spec.durations.length}`;
  } else {
    const [degree, label] = DIRECTIONS[directionIndex];
    stageState.textContent = "Look direction";
    stageFrame.textContent = `${degree} degrees, ${label}`;
  }
}

function animate(timestamp) {
  if (loaded && playing && directionIndex === null && timestamp >= nextFrameAt) {
    const spec = STATES[currentState];
    const duration = spec.durations[currentFrame];
    currentFrame = (currentFrame + 1) % spec.durations.length;
    nextFrameAt = timestamp + duration;
    renderFrame();
  }
  animationRequest = window.requestAnimationFrame(animate);
}

function selectState(name) {
  if (!(name in STATES)) {
    return;
  }
  currentState = name;
  currentFrame = 0;
  directionIndex = null;
  nextFrameAt = performance.now() + STATES[name].durations[0];
  directionSlider.value = "0";
  directionOutput.textContent = "000 degrees, up";
  for (const button of stateControls.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(button.dataset.state === name));
  }
  renderFrame();
}

function selectDirection(index) {
  directionIndex = Math.max(0, Math.min(index, DIRECTIONS.length - 1));
  const [degree, label] = DIRECTIONS[directionIndex];
  directionOutput.textContent = `${degree} degrees, ${label}`;
  for (const button of stateControls.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", "false");
  }
  renderFrame();
}

function setPlaying(value) {
  playing = value;
  motionToggle.textContent = playing ? "Pause motion" : "Play motion";
  if (playing) {
    nextFrameAt = performance.now() + STATES[currentState].durations[currentFrame];
  }
  renderFrame();
}

atlas.addEventListener("load", () => {
  loaded = true;
  fitCanvasToDisplay();
  status.textContent = "Atlas loaded. Controls are ready.";
  renderFrame();
  animationRequest = window.requestAnimationFrame(animate);
});

atlas.addEventListener("error", () => {
  status.dataset.kind = "error";
  status.textContent = "The atlas could not be loaded. Open the GitHub issue tracker for help.";
  stageState.textContent = "Atlas error";
  stageFrame.textContent = "No frame";
});

stateControls.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-state]");
  if (button) {
    selectState(button.dataset.state);
  }
});

directionSlider.addEventListener("input", () => {
  selectDirection(Number(directionSlider.value));
});

motionToggle.addEventListener("click", () => {
  setPlaying(!playing);
});

reducedMotion.addEventListener("change", (event) => {
  if (event.matches) {
    setPlaying(false);
  }
});

window.addEventListener("resize", () => {
  fitCanvasToDisplay();
  renderFrame();
});

fetch("assets/validation.json")
  .then((response) => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  })
  .then((report) => {
    validationVerdict.textContent = report.ok ? "PASS" : "FAIL";
    if (!report.ok) {
      validationVerdict.closest("div").setAttribute("data-failed", "true");
    }
  })
  .catch(() => {
    validationVerdict.textContent = "Unavailable";
  });

motionToggle.textContent = playing ? "Pause motion" : "Play motion";

window.addEventListener("beforeunload", () => {
  if (animationRequest) {
    window.cancelAnimationFrame(animationRequest);
  }
});
