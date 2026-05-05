// Tiny progressive enhancement helpers. The skeleton works without any JS.

// Auto-scroll the message thread to the bottom on load.
document.addEventListener("DOMContentLoaded", () => {
  const thread = document.querySelector(".thread");
  if (thread) thread.scrollTop = thread.scrollHeight;
});

// Auto-dismiss flash messages after a few seconds.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity 400ms";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });
});
