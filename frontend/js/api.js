/**
 * EnCore's SnapSave - Frontend API Client
 * Manages all communication with FastAPI backend endpoints.
 */

const SnapSaveAPI = (function () {
  // Relative paths ensure requests resolve correctly both locally and on cloud deployments (e.g., Render)
  const BASE_URL = "";

  /**
   * Health Check
   */
  async function checkHealth() {
    try {
      const response = await fetch("/api/health", { method: "GET" });
      if (!response.ok) throw new Error("Backend server unhealthy");
      return await response.json();
    } catch (err) {
      console.warn("SnapSave health check failed:", err);
      return null;
    }
  }

  /**
   * Fetch Video / Media Info
   * @param {string} url - Target media link
   */
  async function fetchInfo(url) {
    try {
      const response = await fetch("/api/info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() })
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const errorMsg = data.detail || data.error || `Server responded with status ${response.status}`;
        throw new Error(errorMsg);
      }
      return data;
    } catch (err) {
      throw err;
    }
  }

  /**
   * Trigger Media Download
   * @param {string} url - Media URL
   * @param {string} formatId - Chosen format identifier
   * @param {string} ext - Target extension ("mp4", "mp3", etc.)
   * @param {function} onStatusUpdate - Status callback
   */
  async function downloadMedia(url, formatId, ext = "mp4", onStatusUpdate = null) {
    if (onStatusUpdate) onStatusUpdate("Contacting downloader server...");

    try {
      const response = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          format_id: formatId,
          ext: ext
        })
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        const errorMsg = errJson.detail || errJson.error || `Download failed with status ${response.status}`;
        throw new Error(errorMsg);
      }

      if (onStatusUpdate) onStatusUpdate("Receiving media stream...");

      // Extract filename from Content-Disposition header if available
      let filename = `SnapSave_${Date.now()}.${ext}`;
      const disposition = response.headers.get("Content-Disposition");
      if (disposition && disposition.includes("filename=")) {
        const matches = disposition.match(/filename=["']?([^"';]+)["']?/i);
        if (matches && matches[1]) {
          filename = decodeURIComponent(matches[1]);
        }
      }

      // Read response stream as Blob
      const blob = await response.blob();
      if (blob.size === 0) {
        throw new Error("Received empty file from server.");
      }

      if (onStatusUpdate) onStatusUpdate("Saving file to device...");

      // Trigger standard browser download
      const objectUrl = window.URL.createObjectURL(blob);
      const tempLink = document.createElement("a");
      tempLink.href = objectUrl;
      tempLink.download = filename;
      document.body.appendChild(tempLink);
      tempLink.click();
      document.body.removeChild(tempLink);

      // Revoke blob URL after short delay
      setTimeout(() => window.URL.revokeObjectURL(objectUrl), 5000);

      if (onStatusUpdate) onStatusUpdate("Download completed successfully!");
      return { success: true, filename: filename };
    } catch (err) {
      throw err;
    }
  }

  return {
    BASE_URL,
    checkHealth,
    fetchInfo,
    downloadMedia
  };
})();

window.SnapSaveAPI = SnapSaveAPI;
