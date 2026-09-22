// webapp/static/js/app.js
// Every form submit disables its button and shows a working state, since several routes
// (briefing, compliance, entities, actions, Q&A) call an LLM or a NER model that can take
// 10-30+ seconds with no other feedback otherwise. Re-enables automatically if the page
// hasn't navigated away after a while, in case the request errors out.
document.addEventListener("submit", (event) => {
  const form = event.target;
  const btn = form.querySelector('button[type="submit"]');
  if (!btn || btn.disabled) return;

  btn.dataset.label = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = "⏳ Working…";

  setTimeout(() => {
    if (btn.isConnected) {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.label;
    }
  }, 120000); // safety net: LLM calls can legitimately take ~2 minutes on a slow CPU
});
