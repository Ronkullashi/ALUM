// Tiny progressive enhancement helpers. The skeleton works without any JS.

// --- Auto-scroll the message thread to the bottom on load. ---
document.addEventListener("DOMContentLoaded", () => {
  const thread = document.querySelector(".thread");
  if (thread) thread.scrollTop = thread.scrollHeight;
});

// --- Auto-dismiss flash messages after a few seconds. ---
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity 400ms";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });
});

// ---------------------------------------------------------------------------
// Live updates: re-fetch the current page on a timer and swap in any element
// marked with [data-live]. No new API endpoint needed — we just re-render the
// same URL and pull out the bits that have changed.
//
// - Skips polling while the user is typing or focused on a form field.
// - Compares innerHTML so it only touches the DOM if something actually changed.
// - For .thread, scrolls to bottom after update so new messages are visible.
// ---------------------------------------------------------------------------

(function setupLiveUpdates() {
  const liveEls = document.querySelectorAll("[data-live]");
  if (liveEls.length === 0) return;

  // Tighter polling on messages, slower on admin (less time-sensitive).
  const isMessagesThread = !!document.querySelector('[data-live="thread"]');
  const POLL_MS = isMessagesThread ? 3500 : 8000;

  let userBusy = false;
  document.addEventListener("focusin", (e) => {
    if (e.target.matches("input, textarea, select")) userBusy = true;
  });
  document.addEventListener("focusout", (e) => {
    if (e.target.matches("input, textarea, select")) userBusy = false;
  });

  // Don't poll if the tab isn't visible — saves CPU and battery.
  function tabVisible() {
    return document.visibilityState === "visible";
  }

  async function fetchAndPatch() {
    if (userBusy || !tabVisible()) return;
    try {
      const resp = await fetch(window.location.href, {
        credentials: "same-origin",
        headers: { "X-Requested-Live": "1" },
      });
      if (!resp.ok) return;
      // If the server redirected us to login (e.g. session expired), bail.
      if (resp.redirected && /\/login|\/$|\/about/.test(resp.url)) return;

      const html = await resp.text();
      const doc = new DOMParser().parseFromString(html, "text/html");

      document.querySelectorAll("[data-live]").forEach((current) => {
        const tag = current.getAttribute("data-live");
        const incoming = doc.querySelector(`[data-live="${tag}"]`);
        if (!incoming) return;
        if (incoming.innerHTML === current.innerHTML) return;

        current.innerHTML = incoming.innerHTML;

        // Special case: keep the thread scrolled to the bottom on update.
        if (tag === "thread") {
          current.scrollTop = current.scrollHeight;
        }
      });
    } catch (e) {
      // Silently retry on the next tick.
    }
  }

  setInterval(fetchAndPatch, POLL_MS);
})();
