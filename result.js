// ================= IMAGE =================
const img = document.getElementById("resultImage");
const stored = localStorage.getItem("uploadedImage");

if (stored) img.src = stored;

// ================= RESULT DATA =================
const result = JSON.parse(localStorage.getItem("analysisResult"));

if (result) {
  const score = Math.round(result.overall_score * 100);

  document.getElementById("scoreValue").textContent = score + "%";

  document.querySelector(".risk-badge").textContent = result.verdict;

  document.querySelector(".desc").textContent = result.summary;

  document.querySelector(".panel-header.green p").textContent =
    result.detections.length + " anomalies detected";
}

// ================= ZOOM =================
let scale = 1;
let posX = 0;
let posY = 0;

const wrapper = document.getElementById("wrapper");

function updateTransform() {
  img.style.transform =
    `translate(calc(-50% + ${posX}px), calc(-50% + ${posY}px)) scale(${scale})`;
}

document.getElementById("zoomIn").onclick = () => {
  scale += 0.2;
  updateTransform();
};

document.getElementById("zoomOut").onclick = () => {
  scale = Math.max(0.5, scale - 0.2);
  updateTransform();
};

document.getElementById("reset").onclick = () => {
  scale = 1;
  posX = 0;
  posY = 0;
  updateTransform();
};

// ================= DRAG =================
let isDragging = false;
let startX, startY;

wrapper.addEventListener("mousedown", (e) => {
  isDragging = true;
  startX = e.clientX - posX;
  startY = e.clientY - posY;
});

window.addEventListener("mouseup", () => isDragging = false);

window.addEventListener("mousemove", (e) => {
  if (!isDragging) return;
  posX = e.clientX - startX;
  posY = e.clientY - startY;
  updateTransform();
});

// ================= OVERLAY =================
const toggle = document.getElementById("toggleOverlay");
const tags = document.querySelectorAll(".tag");

toggle.addEventListener("change", () => {
  tags.forEach(tag => {
    tag.style.display = toggle.checked ? "block" : "none";
  });
});

// ================= OPACITY =================
const slider = document.getElementById("opacityRange");

slider.addEventListener("input", () => {
  tags.forEach(tag => {
    tag.style.opacity = slider.value / 100;
  });
});

// ================= HEATMAP (OPTIONAL COOL FEATURE) =================
if (result && result.heatmap_b64) {
  const heatmap = document.createElement("img");
  heatmap.src = "data:image/png;base64," + result.heatmap_b64;
  heatmap.style.width = "100%";
  heatmap.style.marginTop = "10px";

  document.querySelector(".preview-panel").appendChild(heatmap);
}

// ================= DOWNLOAD =================
document.querySelector(".download-btn").onclick = () => {
  const blob = new Blob([JSON.stringify(result, null, 2)], {
    type: "application/json"
  });

  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "report.json";
  link.click();
};

// ================= RESET =================
document.querySelector(".new-btn").onclick = () => {
  localStorage.clear();
  window.location.href = "index.html";
};
