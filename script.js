const uploadBox = document.getElementById("uploadBox");
const fileInput = document.getElementById("fileInput");

// click → open file
uploadBox.addEventListener("click", () => fileInput.click());

// file selected
fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    const file = fileInput.files[0];
    alert("Selected: " + file.name);

    // next page later
    // window.location.href = "analyze.html";
  }
});

// drag over
uploadBox.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadBox.style.borderColor = "#0F766E";
});

// drag leave
uploadBox.addEventListener("dragleave", () => {
  uploadBox.style.borderColor = "#E2E3E5";
});

// drop file
uploadBox.addEventListener("drop", (e) => {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  alert("Dropped: " + file.name);
});