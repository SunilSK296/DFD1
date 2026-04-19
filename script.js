const uploadBox = document.getElementById("uploadBox");
const fileInput = document.getElementById("fileInput");

const previewContainer = document.getElementById("previewContainer");
const previewImage = document.getElementById("previewImage");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const removeBtn = document.getElementById("removeBtn");

// click upload
uploadBox.addEventListener("click", () => fileInput.click());

// file selected
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;

  const reader = new FileReader();

  reader.onload = () => {
    previewImage.src = reader.result;

    // ✅ SAVE IMAGE FOR ANALYZE PAGE
    localStorage.setItem("uploadedImage", reader.result);
  };

  reader.readAsDataURL(file);

  fileName.textContent = file.name;
  fileSize.textContent = (file.size / 1024).toFixed(2) + " KB";

  previewContainer.classList.remove("hidden");
  uploadBox.style.display = "none";
});

// remove file
removeBtn.addEventListener("click", () => {
  previewContainer.classList.add("hidden");
  uploadBox.style.display = "block";
  fileInput.value = "";
});

// ✅ GO TO ANALYZE PAGE
const analyzeBtn = document.querySelector(".analyze-btn");

analyzeBtn.addEventListener("click", () => {
  window.location.href = "analyze.html";
});
