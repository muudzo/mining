// Copy-to-clipboard for the reproduction command. The page works without it.
const COPIED_RESET_MS = 1800;

document.querySelectorAll("button[data-copy]").forEach((button) => {
  const source = document.getElementById(button.dataset.copy);
  if (!source || !navigator.clipboard) {
    button.hidden = true;
    return;
  }
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(source.textContent.trim());
      button.textContent = "Copied";
      button.dataset.state = "done";
    } catch {
      button.textContent = "Select and copy";
    }
    setTimeout(() => {
      button.textContent = "Copy";
      delete button.dataset.state;
    }, COPIED_RESET_MS);
  });
});
