from __future__ import annotations

import html


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
