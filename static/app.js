const form = document.querySelector("#question-form");
const input = document.querySelector("#files");
const dropZone = document.querySelector("#drop-zone");
const fileList = document.querySelector("#file-list");
const status = document.querySelector("#form-status");
const submit = document.querySelector("#submit");
const result = document.querySelector("#result");
const emptyAnswer = document.querySelector("#empty-answer");
const answer = document.querySelector("#answer");
const verification = document.querySelector("#verification-text");
const answerSources = document.querySelector("#answer-sources");
const newSession = document.querySelector("#new-session");
let selectedFiles = [];

function syncFiles() {
  const transfer = new DataTransfer();
  selectedFiles.forEach((file) => transfer.items.add(file));
  input.files = transfer.files;
  fileList.replaceChildren(...selectedFiles.map((file, index) => {
    const row = document.createElement("li");
    row.className = "file-row";
    row.innerHTML = '<span class="document-mark" aria-hidden="true">▣</span><span class="file-name"></span>';
    row.querySelector(".file-name").textContent = file.name;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.ariaLabel = `Remove ${file.name}`;
    remove.textContent = "×";
    remove.addEventListener("click", () => { selectedFiles.splice(index, 1); syncFiles(); });
    row.append(remove);
    return row;
  }));
}

function addFiles(files) {
  selectedFiles = [...selectedFiles, ...files].filter((file, index, all) =>
    index === all.findIndex((item) => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified)
  );
  syncFiles();
}

function renderSources(sources) {
  answerSources.replaceChildren(...sources.map((source) => {
    const item = document.createElement("li");
    item.textContent = source;
    return item;
  }));
}
input.addEventListener("change", () => addFiles(input.files));
["dragenter", "dragover"].forEach((event) => dropZone.addEventListener(event, (e) => { e.preventDefault(); dropZone.classList.add("dragging"); }));
["dragleave", "drop"].forEach((event) => dropZone.addEventListener(event, (e) => { e.preventDefault(); dropZone.classList.remove("dragging"); }));
dropZone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedFiles.length) { status.textContent = "Upload at least one document."; status.className = "form-status error"; return; }
  status.textContent = "Analyzing your documents…"; status.className = "form-status"; submit.disabled = true; submit.textContent = "Working…";
  try {
    const response = await fetch("/api/ask", { method: "POST", body: new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Something went wrong.");
    answer.textContent = data.answer; verification.textContent = data.verification || "No verification report was returned."; renderSources(data.sources);
    result.hidden = false; emptyAnswer.hidden = true; status.textContent = "Answer ready.";
  } catch (error) { status.textContent = error.message; status.className = "form-status error"; } finally { submit.disabled = false; submit.innerHTML = 'Ask question <span aria-hidden="true">→</span>'; }
});

newSession.addEventListener("click", async () => {
  newSession.disabled = true;
  try {
    const response = await fetch("/api/session", { method: "DELETE" });
    if (!response.ok) throw new Error("Unable to start a new session.");
    selectedFiles = []; syncFiles(); form.reset(); answerSources.replaceChildren(); result.hidden = true; emptyAnswer.hidden = false;
    status.textContent = "New session started."; status.className = "form-status";
  } catch (error) { status.textContent = error.message; status.className = "form-status error"; } finally { newSession.disabled = false; }
});

document.querySelector("#copy-answer").addEventListener("click", async () => {
  await navigator.clipboard.writeText(answer.textContent);
  document.querySelector("#copy-answer").textContent = "Copied";
  setTimeout(() => { document.querySelector("#copy-answer").textContent = "Copy"; }, 1200);
});
