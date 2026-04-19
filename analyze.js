const image = document.getElementById("scanImage");
const progress = document.getElementById("progressFill");
const statusText = document.getElementById("statusText");

// get uploaded image
const fileData = localStorage.getItem("uploadedImage");

if (fileData) {
  image.src = fileData;
}

// steps
const steps = [
  "Analyzing pixel patterns...",
  "Checking metadata...",
  "Detecting manipulation...",
  "Running AI model...",
  "Finalizing results..."
];

let progressValue = 0;
let stepIndex = 0;

// 🔥 SEND TO BACKEND
async function sendToBackend() {
  try {
    const res = await fetch(fileData);
    const blob = await res.blob();

    const response = await fetch(
      "https://forgery-backend.onrender.com/detect",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Filename": "document.jpg"
        },
        body: blob
      }
    );

    const result = await response.json();

    console.log("AI Result:", result);

    // store result
    localStorage.setItem("analysisResult", JSON.stringify(result));

    window.location.href = "result.html";

  } catch (err) {
    console.error(err);
    alert("Error connecting to backend");
  }
}

// progress animation
const interval = setInterval(() => {
  progressValue += 2;
  progress.style.width = progressValue + "%";

  if (progressValue % 20 === 0 && stepIndex < steps.length) {
    statusText.textContent = steps[stepIndex];
    stepIndex++;
  }

  if (progressValue >= 100) {
    clearInterval(interval);
    sendToBackend(); // 🔥 REAL AI CALL
  }
}, 100);
