from __future__ import annotations

import html
import json


def page(title: str, headline: str, body: str, invitation_id: str | None = None, action: str | None = None, link_url: str | None = None, link_label: str = "Download Wallet pass") -> str:
    safe_title = html.escape(title)
    safe_headline = html.escape(headline)
    safe_body = html.escape(body)
    action_form = ""
    link = ""
    if link_url:
        link = f'<a class="button" href="{html.escape(link_url)}">{html.escape(link_label)}</a>'
    if invitation_id and action:
        label = "Accept invitation ❤️" if action == "accept" else "Decline invitation"
        action_form = f"""
        <form method="post" action="/api/respond/{html.escape(invitation_id)}">
          <input type="hidden" name="action" value="{html.escape(action)}" />
          <button type="submit">{label}</button>
        </form>
        """
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{safe_title} · DatePass</title>
<style>
:root {{ color-scheme: dark; font-family: -apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif; }}
body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:radial-gradient(circle at top,#2a2e3e,#11131a 62%); color:#fff; }}
.card {{ width:min(88vw,420px); padding:30px; border:1px solid rgba(255,255,255,.16); border-radius:28px; background:rgba(28,31,42,.78); backdrop-filter:blur(18px); box-shadow:0 20px 70px rgba(0,0,0,.42); }}
.kicker {{ color:#bfc5d3; font-size:12px; letter-spacing:.18em; text-transform:uppercase; }}
h1 {{ font-size:32px; margin:12px 0; }} p {{ color:#d8dce7; line-height:1.55; }}
button,a.button {{ display:block; width:100%; box-sizing:border-box; margin-top:22px; border:0; border-radius:16px; padding:15px; background:#fff; color:#141620; text-decoration:none; text-align:center; font-size:16px; font-weight:700; cursor:pointer; }}
.small {{ margin-top:18px; color:#aab0bf; font-size:13px; }}
</style>
</head>
<body><main class="card"><div class="kicker">DatePass · FR-2026</div><h1>{safe_headline}</h1><p>{safe_body}</p>{action_form}{link}<p class="small">Designed with code. Delivered through Apple Wallet.</p></main></body>
</html>"""


def admin_memory_form() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>New Memory · DatePass</title>
<style>
:root { color-scheme: dark; font-family: -apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif; background:#0f1016; color:#fff; }
* { box-sizing:border-box; }
body { margin:0; min-height:100vh; background:linear-gradient(135deg,#101119 0%,#231b25 48%,#151217 100%); }
main { width:min(1120px,100%); margin:0 auto; padding:clamp(18px,4vw,48px); display:grid; grid-template-columns:minmax(0,1.05fr) minmax(280px,.95fr); gap:24px; align-items:start; }
.panel { border:1px solid rgba(255,255,255,.13); border-radius:22px; background:rgba(20,20,28,.78); box-shadow:0 24px 90px rgba(0,0,0,.36); backdrop-filter:blur(18px); }
.form { padding:24px; }
.preview { overflow:hidden; position:sticky; top:24px; }
.photo { aspect-ratio:1/1; background:#161820; display:grid; place-items:center; color:#aeb3c2; }
.photo img { width:100%; height:100%; object-fit:cover; display:none; }
.summary { padding:22px; }
.kicker { color:#e3bfa8; font-size:12px; letter-spacing:.18em; text-transform:uppercase; font-weight:700; }
h1 { font-size:clamp(32px,6vw,62px); line-height:.96; margin:8px 0 16px; letter-spacing:0; }
h2 { margin:0 0 8px; font-size:24px; }
p { color:#d8d8df; line-height:1.55; }
label { display:block; color:#c9ccd6; font-size:13px; font-weight:700; margin:15px 0 7px; }
input,textarea,select { width:100%; border:1px solid rgba(255,255,255,.16); border-radius:14px; background:rgba(255,255,255,.07); color:#fff; padding:13px 14px; font:inherit; outline:none; }
textarea { min-height:112px; resize:vertical; }
input:focus,textarea:focus,select:focus { border-color:#e3bfa8; box-shadow:0 0 0 3px rgba(227,191,168,.16); }
.grid { display:grid; grid-template-columns:1fr 150px; gap:14px; }
.actions { display:flex; align-items:center; gap:12px; margin-top:20px; flex-wrap:wrap; }
button { border:0; border-radius:16px; padding:14px 18px; background:#fff; color:#11131a; font-weight:800; font-size:15px; cursor:pointer; }
button:disabled { opacity:.62; cursor:wait; }
.status { min-height:24px; color:#e3bfa8; font-size:14px; }
.error { color:#ffb3b3; }
.hint { color:#aeb3c2; font-size:13px; margin-top:8px; }
@media (max-width: 820px) {
  main { grid-template-columns:1fr; }
  .preview { position:static; order:-1; }
  .grid { grid-template-columns:1fr; }
}
</style>
</head>
<body>
<main>
  <section class="panel form">
    <div class="kicker">DatePass Memories</div>
    <h1>Create Memory</h1>
    <p>Private Wallet pass creator. Your Creator API Key is used only in this page session and is never stored.</p>
    <form id="memory-form">
      <label for="creator-key">Creator API Key</label>
      <input id="creator-key" name="creator_key" type="password" autocomplete="off" required />
      <label for="recipient-name">Her name</label>
      <input id="recipient-name" name="recipient_name" value="Coco" maxlength="80" required />
      <label for="title">Memory title</label>
      <input id="title" name="title" value="Our First Date" maxlength="80" required />
      <div class="grid">
        <div>
          <label for="date">Date</label>
          <input id="date" name="date" type="datetime-local" value="2026-06-23T13:00" required />
        </div>
        <div>
          <label for="memory-number">Memory number</label>
          <input id="memory-number" name="memory_number" type="number" min="1" max="999" value="1" required />
        </div>
      </div>
      <label for="place">Place</label>
      <input id="place" name="place" value="Nolitas, 1pm" maxlength="140" required />
      <label for="message">Message</label>
      <textarea id="message" name="message" maxlength="600" required>He preparado este recuerdo para recordar nuestra primera cita oficial</textarea>
      <label for="theme">Theme</label>
      <select id="theme" name="theme">
        <option value="midnight-romance">midnight-romance</option>
      </select>
      <label for="photo">Photo</label>
      <input id="photo" name="photo" type="file" accept="image/jpeg,image/png" required />
      <div class="hint">JPEG or PNG, up to 10 MB.</div>
      <div class="actions">
        <button id="submit" type="submit">Create Memory</button>
        <span id="status" class="status"></span>
      </div>
    </form>
  </section>
  <aside class="panel preview">
    <div class="photo"><span id="empty-photo">Select a photo</span><img id="preview-img" alt="Selected memory photo" /></div>
    <div class="summary">
      <div class="kicker">Memory #001</div>
      <h2 id="preview-title">Our First Date</h2>
      <p id="preview-meta">Franco + Coco · Nolitas, 1pm</p>
      <p id="preview-message">He preparado este recuerdo para recordar nuestra primera cita oficial</p>
    </div>
  </aside>
</main>
<script>
const form = document.getElementById("memory-form");
const statusEl = document.getElementById("status");
const submit = document.getElementById("submit");
const photo = document.getElementById("photo");
const img = document.getElementById("preview-img");
const emptyPhoto = document.getElementById("empty-photo");
const title = document.getElementById("title");
const recipient = document.getElementById("recipient-name");
const place = document.getElementById("place");
const message = document.getElementById("message");
const memoryNumber = document.getElementById("memory-number");

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "status error" : "status";
}
function updatePreview() {
  document.getElementById("preview-title").textContent = title.value || "Untitled Memory";
  document.getElementById("preview-meta").textContent = `Franco + ${recipient.value || "Someone"} · ${place.value || "Somewhere"}`;
  document.getElementById("preview-message").textContent = message.value || "";
  document.querySelector(".summary .kicker").textContent = `Memory #${String(memoryNumber.value || 1).padStart(3, "0")}`;
}
[title, recipient, place, message, memoryNumber].forEach((el) => el.addEventListener("input", updatePreview));
photo.addEventListener("change", () => {
  const file = photo.files[0];
  if (!file) return;
  img.src = URL.createObjectURL(file);
  img.style.display = "block";
  emptyPhoto.style.display = "none";
});
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const key = document.getElementById("creator-key").value.trim();
  const data = new FormData(form);
  data.delete("creator_key");
  submit.disabled = true;
  setStatus("Uploading photo...");
  try {
    setTimeout(() => setStatus("Creating Wallet pass..."), 250);
    const response = await fetch("/memories", {
      method: "POST",
      headers: {"X-DatePass-Creator-Key": key},
      body: data
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Unable to create memory");
    setStatus("Signing pass...");
    window.location.assign(payload.preview_url);
  } catch (error) {
    setStatus(error.message, true);
    submit.disabled = false;
  }
});
</script>
</body>
</html>"""


def memory_preview(memory: dict, photo_url: str, pass_url: str) -> str:
    title = html.escape(memory.get("title", "DatePass Memory"))
    partner = html.escape(memory.get("partner_name", ""))
    place = html.escape(memory.get("place", ""))
    story = html.escape(memory.get("story", ""))
    memory_number = int(memory.get("memory_number") or 1)
    date = html.escape(memory.get("memory_date", ""))
    memory_id = html.escape(memory["id"])
    safe_photo_url = html.escape(photo_url)
    safe_pass_url = html.escape(pass_url)
    payload = json.dumps({"passUrl": pass_url})
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{title} · DatePass</title>
<style>
:root {{ color-scheme: dark; font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif; background:#101119; color:#fff; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; display:grid; place-items:center; padding:24px; background:linear-gradient(135deg,#101119,#251b24 54%,#121219); }}
main {{ width:min(980px,100%); display:grid; grid-template-columns:minmax(0,1fr) minmax(300px,.78fr); gap:22px; }}
.media,.details {{ border:1px solid rgba(255,255,255,.13); border-radius:22px; background:rgba(21,21,29,.78); overflow:hidden; box-shadow:0 24px 90px rgba(0,0,0,.36); }}
img {{ width:100%; height:100%; object-fit:cover; display:block; min-height:420px; }}
.details {{ padding:26px; }}
.kicker {{ color:#e3bfa8; font-size:12px; letter-spacing:.18em; text-transform:uppercase; font-weight:800; }}
h1 {{ font-size:clamp(34px,6vw,60px); line-height:.96; margin:10px 0 16px; }}
p {{ color:#dbdce4; line-height:1.55; }}
.meta {{ color:#b9becb; }}
.id {{ overflow-wrap:anywhere; color:#9fa5b5; font-size:13px; }}
.actions {{ display:grid; gap:10px; margin-top:22px; }}
a,button {{ width:100%; border:0; border-radius:16px; padding:14px 16px; text-align:center; font:inherit; font-weight:800; cursor:pointer; text-decoration:none; }}
a.primary {{ background:#fff; color:#11131a; }}
a.secondary,button {{ background:rgba(255,255,255,.09); color:#fff; border:1px solid rgba(255,255,255,.14); }}
@media (max-width: 760px) {{ main {{ grid-template-columns:1fr; }} img {{ min-height:320px; }} }}
</style>
</head>
<body>
<main>
  <section class="media"><img src="{safe_photo_url}" alt="Memory photo" /></section>
  <section class="details">
    <div class="kicker">DatePass Memories · #{memory_number:03d}</div>
    <h1>{title}</h1>
    <p class="meta">Franco + {partner}<br />{date}<br />{place}</p>
    <p>{story}</p>
    <p class="id">ID: {memory_id}</p>
    <div class="actions">
      <a class="primary" href="{safe_pass_url}">Add to Apple Wallet</a>
      <a class="secondary" href="{safe_pass_url}">Download .pkpass</a>
      <button id="copy" type="button">Copy pass link</button>
    </div>
  </section>
</main>
<script>
const data = {payload};
document.getElementById("copy").addEventListener("click", async () => {{
  await navigator.clipboard.writeText(data.passUrl);
  document.getElementById("copy").textContent = "Copied";
}});
</script>
</body>
</html>"""
