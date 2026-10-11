/**
 * EnCore's SnapSave - Main Application Controller
 * Handles URL inputs, platform detection, video preview rendering,
 * format filtering, and download execution.
 */

(function () {
  // DOM Elements
  const urlInput = document.getElementById("url-input");
  const fetchForm = document.getElementById("fetch-form");
  const fetchBtn = document.getElementById("fetch-btn");
  const fetchBtnText = document.getElementById("fetch-btn-text");
  const fetchSpinner = document.getElementById("fetch-spinner");
  const pasteBtn = document.getElementById("paste-btn");
  const clearBtn = document.getElementById("clear-btn");
  const errorBanner = document.getElementById("error-banner");
  const errorMessageText = document.getElementById("error-message-text");
  const platformBadges = document.querySelectorAll(".platform-badge");

  // Preview elements
  const previewSection = document.getElementById("preview-section");
  const previewPlatformTag = document.getElementById("preview-platform-tag");
  const previewThumbImg = document.getElementById("preview-thumbnail-img");
  const previewDuration = document.getElementById("preview-duration");
  const previewTitle = document.getElementById("preview-title");
  const previewUploader = document.getElementById("preview-uploader");
  const previewEngine = document.getElementById("preview-engine");
  const closePreviewBtn = document.getElementById("close-preview-btn");

  // Formats & Download elements
  const formatFilterTabs = document.querySelectorAll("#format-filter-tabs .btn-inline");
  const formatGrid = document.getElementById("format-grid");
  const downloadBtn = document.getElementById("download-btn");
  const downloadBtnText = document.getElementById("download-btn-text");
  const downloadSpinner = document.getElementById("download-spinner");
  const downloadProgressBox = document.getElementById("download-progress-box");
  const progressStatusLabel = document.getElementById("progress-status-label");
  const progressPercentLabel = document.getElementById("progress-percent-label");
  const progressBarFill = document.getElementById("progress-bar-fill");

  // Header & Status elements
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const toastContainer = document.getElementById("toast-container");

  // Application State
  let currentMediaData = null;
  let selectedFormat = null;
  let activeFilter = "all";

  /**
   * Display floating toast notification
   */
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type === "error" ? "toast-error" : (type === "success" ? "toast-success" : "")}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.25s ease";
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }

  /**
   * Health Check on Startup
   */
  async function verifyBackendStatus() {
    const health = await window.SnapSaveAPI.checkHealth();
    if (health && health.status === "ok") {
      statusDot.style.backgroundColor = "var(--color-success)";
      statusText.textContent = "Backend Connected";
    } else {
      statusDot.style.backgroundColor = "var(--color-danger)";
      statusText.textContent = "Server Offline (Run app.py)";
    }
  }

  /**
   * Detect and highlight platform badge based on input text
   */
  function updatePlatformBadges(url) {
    const val = url.toLowerCase();
    platformBadges.forEach((badge) => badge.classList.remove("platform-badge-highlight"));

    if (val.includes("youtube.com/shorts")) {
      highlightBadge("shorts");
    } else if (val.includes("youtube.com") || val.includes("youtu.be")) {
      highlightBadge("youtube");
    } else if (val.includes("instagram.com/reel")) {
      highlightBadge("reels");
    } else if (val.includes("instagram.com")) {
      highlightBadge("instagram");
    } else if (val.includes("twitter.com") || val.includes("x.com")) {
      highlightBadge("x");
    } else if (val.includes("facebook.com") || val.includes("fb.watch")) {
      highlightBadge("facebook");
    }
  }

  function highlightBadge(platformKey) {
    const target = document.querySelector(`.platform-badge[data-platform="${platformKey}"]`);
    if (target) {
      target.classList.add("platform-badge-highlight");
    }
  }

  /**
   * URL Input Events
   */
  urlInput.addEventListener("input", () => {
    const hasText = urlInput.value.trim().length > 0;
    clearBtn.style.display = hasText ? "inline-block" : "none";
    errorBanner.style.display = "none";
    updatePlatformBadges(urlInput.value);
  });

  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        urlInput.dispatchEvent(new Event("input"));
        showToast("Link pasted from clipboard", "info");
      }
    } catch (err) {
      showToast("Clipboard access denied. Please paste manually.", "info");
      urlInput.focus();
    }
  });

  clearBtn.addEventListener("click", () => {
    urlInput.value = "";
    urlInput.dispatchEvent(new Event("input"));
    previewSection.style.display = "none";
    urlInput.focus();
  });

  closePreviewBtn.addEventListener("click", () => {
    previewSection.style.display = "none";
  });

  /**
   * Fetch Video Form Submission
   */
  fetchForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();

    if (!url) {
      showError("Please enter or paste a valid video URL.");
      urlInput.focus();
      return;
    }

    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      showError("URL must start with http:// or https://");
      urlInput.focus();
      return;
    }

    // Set UI loading state
    fetchBtn.disabled = true;
    fetchBtnText.textContent = "Fetching Stream Info...";
    fetchSpinner.style.display = "inline-block";
    errorBanner.style.display = "none";
    previewSection.style.display = "none";

    try {
      const data = await window.SnapSaveAPI.fetchInfo(url);
      currentMediaData = data;
      renderPreview(data);
      showToast("Media details retrieved!", "success");
    } catch (err) {
      const isInstagram = url.toLowerCase().includes("instagram.com");
      const errLower = (err.message || "").toLowerCase();
      if (
        isInstagram &&
        (errLower.includes("private") ||
          errLower.includes("login") ||
          errLower.includes("log in") ||
          errLower.includes("sign in"))
      ) {
        showError("This post is private or needs login. Only public Instagram links are supported.");
      } else {
        showError(err.message || "Failed to retrieve media information.");
      }
    } finally {
      fetchBtn.disabled = false;
      fetchBtnText.textContent = "Fetch Video & Formats";
      fetchSpinner.style.display = "none";
    }
  });

  function showError(msg) {
    errorMessageText.textContent = msg;
    errorBanner.style.display = "flex";
    showToast(msg, "error");
  }

  /**
   * Render Preview Card and Formats
   */
  function renderPreview(data) {
    previewPlatformTag.textContent = `${data.platform || "Media"} • Preview`;
    previewThumbImg.src = data.thumbnail || "logo/logo.png";
    previewDuration.textContent = data.duration_formatted || "00:00";
    previewTitle.textContent = data.title || "Media Stream";
    previewUploader.textContent = data.uploader || "Unknown Creator";
    previewEngine.textContent = data.engine || "auto";

    // Populate formats
    renderFormatCards(data.formats || []);

    // Reveal preview card with smooth scroll
    previewSection.style.display = "flex";
    previewSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  /**
   * Render and filter format cards
   */
  function renderFormatCards(formats) {
    formatGrid.innerHTML = "";

    const filtered = formats.filter((f) => {
      if (activeFilter === "video") return !f.is_audio_only;
      if (activeFilter === "audio") return f.is_audio_only;
      return true;
    });

    if (filtered.length === 0) {
      formatGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.8125rem;">
          No formats match the selected filter.
        </div>
      `;
      selectedFormat = null;
      updateDownloadButton();
      return;
    }

    // Auto-select first item or preserve matching selection
    let foundCurrent = false;
    filtered.forEach((fmt, index) => {
      const isSelected = selectedFormat && selectedFormat.format_id === fmt.format_id;
      if (isSelected) foundCurrent = true;

      const card = document.createElement("div");
      card.className = `format-card-option ${isSelected ? "is-selected" : ""}`;
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");

      card.innerHTML = `
        <div class="format-option-header">
          <span class="micro-label">${fmt.ext.toUpperCase()}</span>
          <span class="format-size-tag">${fmt.filesize_human}</span>
        </div>
        <div class="format-quality-name">${fmt.quality_label}</div>
        <div class="format-note-text">${fmt.format_note || (fmt.has_audio ? "With Audio" : "Video Stream")}</div>
      `;

      card.addEventListener("click", () => {
        selectFormat(fmt, card);
      });

      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectFormat(fmt, card);
        }
      });

      formatGrid.appendChild(card);
    });

    // Default select first format if none selected
    if (!foundCurrent && filtered.length > 0) {
      const firstCard = formatGrid.firstElementChild;
      selectFormat(filtered[0], firstCard);
    }
  }

  function selectFormat(fmt, cardElement) {
    selectedFormat = fmt;
    document.querySelectorAll(".format-card-option").forEach((el) => el.classList.remove("is-selected"));
    if (cardElement) cardElement.classList.add("is-selected");
    updateDownloadButton();
  }

  function updateDownloadButton() {
    if (!selectedFormat) {
      downloadBtn.disabled = true;
      downloadBtnText.textContent = "Select a format above";
      return;
    }
    downloadBtn.disabled = false;
    const label = selectedFormat.is_audio_only
      ? `Download ${selectedFormat.quality_label}`
      : `Download MP4 (${selectedFormat.quality_label})`;
    downloadBtnText.textContent = label;
  }

  /**
   * Filter Tabs Handling
   */
  formatFilterTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      formatFilterTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activeFilter = tab.getAttribute("data-filter");
      if (currentMediaData) {
        renderFormatCards(currentMediaData.formats || []);
      }
    });
  });

  /**
   * Download Button Action
   */
  downloadBtn.addEventListener("click", async () => {
    if (!selectedFormat || !currentMediaData) {
      showToast("Please choose a format first.", "error");
      return;
    }

    const url = urlInput.value.trim();
    if (!url) {
      showToast("Target URL missing.", "error");
      return;
    }

    // Set Download State
    downloadBtn.disabled = true;
    downloadSpinner.style.display = "inline-block";
    downloadProgressBox.style.display = "flex";
    progressStatusLabel.textContent = "Connecting to download stream...";
    progressPercentLabel.textContent = "Starting";
    progressBarFill.className = "progress-bar-fill progress-bar-indeterminate";

    try {
      const result = await window.SnapSaveAPI.downloadMedia(
        url,
        selectedFormat.format_id,
        selectedFormat.ext,
        (statusMsg) => {
          progressStatusLabel.textContent = statusMsg;
        }
      );

      progressStatusLabel.textContent = `Completed! Saved as "${result.filename}"`;
      progressPercentLabel.textContent = "100%";
      progressBarFill.className = "progress-bar-fill";
      progressBarFill.style.width = "100%";
      showToast(`Download complete: ${result.filename}`, "success");

      setTimeout(() => {
        downloadProgressBox.style.display = "none";
        progressBarFill.style.width = "0%";
      }, 7000);
    } catch (err) {
      const isInstagram = url.toLowerCase().includes("instagram.com");
      const errLower = (err.message || "").toLowerCase();
      const displayMsg =
        isInstagram &&
        (errLower.includes("private") ||
          errLower.includes("login") ||
          errLower.includes("log in") ||
          errLower.includes("sign in"))
          ? "This post is private or needs login. Only public Instagram links are supported."
          : (err.message || "Download could not be completed.");
      progressStatusLabel.textContent = "Download failed";
      progressPercentLabel.textContent = "Error";
      showToast(displayMsg, "error");
    } finally {
      downloadBtn.disabled = false;
      downloadSpinner.style.display = "none";
      updateDownloadButton();
    }
  });

  // Initialization
  verifyBackendStatus();
})();
