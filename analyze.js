const image = document.getElementById("scanImage");
const progress = document.getElementById("progressFill");
const statusText = document.getElementById("statusText");

// get uploaded image from previous page
const fileData = localStorage.getItem("uploadedImage");

if (fileData) {
  image.src = fileData;
}

// fake ML processing steps
const steps = [
  "Analyzing pixel patterns...",
  "Checking metadata...",
  "Detecting manipulation...",
  "Running AI model...",
  "Finalizing results..."
];

let progressValue = 0;
let stepIndex = 0;

const interval = setInterval(() => {
  progressValue += 2;
  progress.style.width = progressValue + "%";

  if (progressValue % 20 === 0 && stepIndex < steps.length) {
    statusText.textContent = steps[stepIndex];
    stepIndex++;
  }

  if (progressValue >= 100) {
    clearInterval(interval);

    // next page later
    setTimeout(() => {
      alert("Analysis Complete (connect backend here)");
      window.location.href = "results.html";
    }, 500);
  }
}, 100);