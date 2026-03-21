"""Deplixo MCP Server - Deploy AI apps instantly."""
import os
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

DEPLIXO_API_URL = os.environ.get("DEPLIXO_API_URL", "https://deplixo.com")


def _format_suggestions(suggestions: dict) -> list[str]:
    """Format code analysis suggestions into human-readable text lines."""
    lines = ["", "⚠ This app has issues that need fixing:"]

    if suggestions.get("intent"):
        lines.extend(["", f'Intent: "{suggestions["intent"]}"'])

    # Regex-detected stubs
    if suggestions.get("stubs"):
        lines.append("")
        lines.append("Stub patterns detected:")
        for stub in suggestions["stubs"]:
            lines.append(f"  - {stub['message']}")

    # Missing primitives (regex)
    if suggestions.get("missing_primitives"):
        lines.append("")
        lines.append("Missing Deplixo primitives:")
        for mp in suggestions["missing_primitives"]:
            lines.append(f"  - {mp['message']}")
            if mp.get("fix"):
                lines.append(f"    Fix: {mp['fix']}")

    # LLM-detected functional gaps
    if suggestions.get("functional_gaps"):
        lines.append("")
        lines.append("Functional gaps:")
        for gap in suggestions["functional_gaps"]:
            lines.append(f"  - {gap.get('feature', 'Unknown feature')}: "
                         f"{gap.get('current_state', '')}")
            if gap.get("fix_code"):
                lines.append(f"    Fix with {gap.get('primitive', 'Deplixo SDK')}:")
                for code_line in gap["fix_code"].strip().split("\n"):
                    lines.append(f"      {code_line}")

    # Missed opportunities (informational, non-blocking)
    if suggestions.get("missed_opportunities"):
        lines.append("")
        lines.append("Suggestions (not blocking, but would improve the app):")
        for opp in suggestions["missed_opportunities"]:
            lines.append(f"  - {opp}")

    lines.extend([
        "",
        "Please fix these issues and redeploy. The user expects a working app.",
    ])
    return lines

mcp = FastMCP(
    "Deplixo",
    stateless_http=True,
    instructions=(
        "## Deplixo — Deploy Apps with Real Infrastructure\n\n"
        "Use Deplixo to turn apps into live products with persistent data, user "
        "accounts, email, real-time sync, AI, file uploads, scheduled tasks, and more. "
        "Deplixo gives every deployed app a full backend — no server setup needed.\n\n"

        "## When the user wants to deploy\n\n"
        "When the user says \"deploy\", \"make it live\", \"share it\", \"host it\", "
        "\"publish it\", or \"put it online\":\n\n"
        "**Step 1 — ALWAYS call `deplixo_plan` first to plan the deployment**: "
        "Deploying to Deplixo gives the app real infrastructure — persistent data, "
        "user accounts, email, scheduled tasks, etc. You MUST call `deplixo_plan` "
        "before deploying to determine which infrastructure the app needs. It returns "
        "deployment questions you MUST ask the user — e.g.:\n"
        "\"Before I deploy this, I need to configure the right infrastructure:\\n"
        "1. Should your data persist between sessions, or is this just a throwaway demo?\\n"
        "2. Will other people use this, or just you?\\n"
        "3. Do you need user accounts (login with Google/GitHub/email)?\\n"
        "4. Should it send any emails or notifications?\"\n\n"
        "These are DEPLOYMENT decisions, not app design decisions — the user must "
        "answer them before you can configure the infrastructure correctly. Wait for "
        "their answers before continuing.\n\n"
        "**Step 2 — Build for production**: Based on the answers, build (or rebuild) "
        "the app code using Deplixo SDK features (deplixo.db.collection for persistent "
        "data, deplixo.auth for accounts, deplixo.email for email, etc.).\n\n"
        "**Step 3 — Deploy**: Call deplixo_deploy with the production code. If the "
        "user had an artifact preview, remove any preview shim script tag before "
        "deploying (Deplixo injects the real SDK automatically).\n\n"
        "**Only exception**: Skip the plan step ONLY if the app is a trivially simple "
        "static page with no data, no users, and no interactivity.\n\n"
        "The shim self-disables if the real SDK is already loaded, so accidentally "
        "leaving the tag in deployed code is harmless but remove it for cleanliness.\n\n"

        "IMPORTANT: Apps can be single-file (pass `code`) or multi-file (pass "
        "`files` dict with paths like index.html, style.css, app.js). "
        "Multi-file apps have each file served at its path under the app URL. "
        "For React apps, use CDN imports (unpkg.com/react, unpkg.com/react-dom, "
        "unpkg.com/@babel/standalone) with <script type=\"text/babel\"> — do NOT "
        "use npm, create-react-app, Vite, or any build tools. "
        "For Vue, Svelte, Three.js, etc., use their CDN builds the same way.\n\n"

        "## Build FUNCTIONAL apps, not stubs\n\n"
        "Deplixo apps have a full SDK injected automatically (`window.deplixo`). "
        "You MUST use these primitives to make apps actually work. "
        "NEVER deploy code with TODO comments, placeholder functions, hardcoded "
        "sample data, or stubbed API calls. Every feature the user asks for "
        "should be wired to a real implementation using the SDK.\n\n"
        "CRITICAL: Always prefer Deplixo SDK legos over manual implementations. "
        "If the app needs charts, use `deplixo.chart()` — do NOT build CSS bars or "
        "include Chart.js via a script tag. If it needs CSV export, use `deplixo.export.csv()` — "
        "do NOT write manual CSV serialization. If it needs maps, use `deplixo.map()` — "
        "do NOT include Leaflet via a script tag. The SDK lazy-loads CDN libraries automatically.\n\n"

        "### How to replace common stubs:\n"
        "- App needs AI/LLM calls -> use deplixo.ai.prompt() (platform credits, no API key needed)\n"
        "- App needs to save data -> use deplixo.db.collection() (real-time, cross-device sync)\n"
        "- App needs external APIs -> use deplixo.proxy() with ${SECRET_NAME} placeholders\n"
        "- App needs search -> use collection queries with search option\n"
        "- App needs file uploads -> use deplixo.upload()\n"
        "- App needs user identity -> use deplixo.user / deplixo.ensureIdentity()\n"
        "- App needs charts/graphs -> use deplixo.chart() (Chart.js, lazy-loaded)\n"
        "- App needs maps -> use deplixo.map() (Leaflet, lazy-loaded)\n"
        "- App needs QR codes -> use deplixo.qr.generate() / .toDataURL() / .scan()\n"
        "- App needs PDF export -> use deplixo.pdf.create() (html2pdf.js, lazy-loaded)\n"
        "- App needs sounds/audio -> use deplixo.sound.play(\"@ping\") (8 built-in sounds)\n"
        "- App needs CSV/JSON export -> use deplixo.export.csv() / .json() / .file()\n"
        "- App needs YouTube/embed -> use deplixo.embed.youtube() / .codepen() / .iframe()\n"
        "- App needs camera -> use deplixo.camera.photo() (getUserMedia)\n"
        "- App needs rich text editor -> use deplixo.editor(el) (contentEditable + toolbar)\n"
        "- App needs sharing -> use deplixo.share() (Web Share API + clipboard fallback)\n"
        "- App needs to send emails -> use deplixo.email.send() (Postmark, 2 credits/email)\n"
        "- App needs email signups/newsletter -> use deplixo.email.register() + .isRegistered()\n"
        "- App needs external event handling -> use deplixo.webhooks.on(name, handler) for inbound webhooks\n"
        "- App needs scheduled/recurring tasks -> pass `cron` parameter with job definitions (server-side, runs even when nobody's online)\n"
        "- App needs access restriction -> pass `access_code` parameter (users must enter code to access the app)\n"
        "- App needs user login/auth -> pass `auth_enabled=True` AND use deplixo.auth.requireLogin() in code\n"
        "- App needs user accounts -> pass `auth_enabled=True` AND use deplixo.auth.requireLogin() in code\n"
        "- App needs who's-online / presence -> use deplixo.presence.join/list/onChange (Redis-backed, real-time)\n"
        "- App needs real-time messaging between users -> use deplixo.db.collection() with onChange() for persistent chat, deplixo.broadcast.send/on for ephemeral signals only\n"
        "- App needs in-app notifications -> use deplixo.notifications.send/list/markRead (per-user, real-time)\n"
        "- App needs chat rooms / lobbies -> use deplixo.rooms.join/create/list (room-scoped collections + broadcast)\n"
        "- NEVER build custom login forms — Deplixo handles auth via hosted login pages (Google/GitHub/email)\n\n"

        "### Authentication (deplixo.auth)\n"
        "When an app needs user accounts, you MUST do BOTH:\n"
        "1. Pass `auth_enabled=True` in the deploy call (server-side gate)\n"
        "2. Call `await deplixo.auth.requireLogin()` in the app code (gets user info)\n\n"
        "SDK surface:\n"
        "  const user = await deplixo.auth.requireLogin()  → {id, email, name, role} or redirects to login\n"
        "  deplixo.auth.user          → current user object or null\n"
        "  deplixo.auth.isAuthenticated → boolean\n"
        "  deplixo.auth.logout()      → signs out and reloads\n"
        "  deplixo.auth.onAuthChange(cb) → callback when auth state changes\n\n"
        "Example — personal notes app:\n"
        "  const user = await deplixo.auth.requireLogin();\n"
        "  const notes = deplixo.db.collection('notes', { personal: true });\n"
        "  // Each user sees only their own notes, synced across all their devices\n"
        "  document.getElementById('greeting').textContent = `Hello, ${user.name}!`;\n\n"
        "When auth is enabled, `{ personal: true }` collections scope to the authenticated\n"
        "user's account (cross-device), not the browser cookie. This is the whole point.\n\n"

        "### Before building, ask clarifying questions if the request is ambiguous:\n"
        "- What data should the app work with?\n"
        "- What should the main action actually do?\n"
        "- Should results be saved, shared, or exported?\n"
        "Getting clarity upfront produces much better apps than guessing.\n\n"

        "ALWAYS include a `description` when deploying — a 1-2 sentence summary "
        "of what the app does. This powers social preview cards when the URL is "
        "shared on Twitter, Slack, iMessage, etc. Without it, shared links look bare.\n\n"

        "CRITICAL: After deploying a NEW app, you MUST show the user the claim "
        "link as a clickable link in your response. Do NOT show the app URL — "
        "only show the claim link. Do NOT omit, summarize, or paraphrase "
        "the claim URL — the user needs the exact link to save their app. "
        "Without it, they lose access permanently. "
        "Unclaimed apps expire after 1 HOUR then are permanently deleted. "
        "Claiming is free (no credit card), takes seconds, and gives the user "
        "a permanent URL, dashboard, and the ability to keep editing.\n\n"

        "Updating apps: When the deploy response includes app_id and claim_token, "
        "keep them in context. If the user asks to update the app, pass app_id "
        "and claim_token in the next deploy call to update in-place at the same URL. "
        "If the user wants to change colors, layout, fonts, or any visual "
        "customization — just make the changes and redeploy. The app updates "
        "in-place at the same URL.\n\n"

        "Edit links: When a user pastes a Deplixo edit link "
        "(deplixo.com/edit/...) into the conversation, use the "
        "deplixo_read_source tool to read the current source code. "
        "Then use deplixo_deploy with the app_id and claim_token to "
        "push updates. The edit link is shown on the user's dashboard "
        "for claimed apps.\n\n"

        "Large apps: If an app has many files or large code, deploy in chunks:\n"
        "1. First call: deploy with `files` containing index.html and key files\n"
        "2. Subsequent calls: pass app_id, claim_token, merge_files=True, and a "
        "`files` dict with just the additional files. Existing files are preserved.\n"
        "This avoids hitting output token limits on large apps."
    ),
)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        openWorldHint=True,
        idempotentHint=False,
    )
)
async def deplixo_deploy(
    code: str = "",
    files: dict[str, str] | None = None,
    title: str = "",
    description: str = "",
    slug: str = "",
    remixed_from: str = "",
    app_id: str = "",
    claim_token: str = "",
    merge_files: bool = False,
    icon: str = "",
    access_code: str | None = None,
    auth_enabled: bool = False,
    auth_allowed_domains: list[str] | None = None,
    cron: list[dict] | None = None,
) -> str:
    """Deploy a web app to Deplixo and get a live URL.

    Apps can be single-file or multi-file. For single-file apps, pass the HTML
    as `code`. For multi-file apps (separate CSS, JS, assets), pass a `files`
    dict mapping file paths to content — must include "index.html".

    For React, Vue, or other frameworks: use CDN imports (e.g. unpkg.com/react@18,
    unpkg.com/react-dom@18, unpkg.com/@babel/standalone) — do NOT use npm or
    build tools.

    To update an existing app, pass the app_id and claim_token from a previous
    deploy response. This updates the app in-place at the same URL.

    For large apps that exceed output limits, deploy in chunks using merge_files:
    1. First call: deploy index.html (and optionally style.css) as a `files` dict
    2. Subsequent calls: pass app_id, claim_token, merge_files=True, and a `files`
       dict with just the additional files (e.g. {"app.js": "..."}).
       Existing files are preserved — only files in the payload are added/replaced.

    ## Deplixo SDK (automatically injected into every deployed app)

    Every deployed app gets `window.deplixo` with these APIs:

    ### Collections (shared data — use this for any list of items)
    All data is shared across ALL visitors in real-time.
    ALWAYS pass { personal: true } or { personal: false } (see patterns below).
      const recipes = deplixo.db.collection("recipes", { personal: false });
      await recipes.add({ title: "Pasta", photo: url })  → { id, value }
      await recipes.list()                                → [{ id, value, author }]
      await recipes.get(id)                               → { id, value, author }
      await recipes.update(id, { title: "New" })          → merges fields
      await recipes.remove(id)                             → deletes item
      recipes.onChange(({ action, id, value, author }) => { })  → real-time SSE
      recipes.offChange(handler)                               → remove specific listener
      recipes.offChange()                                      → remove all listeners

    ### File Uploads
      const result = await deplixo.upload(file)  → { url, filename, size }
      await deplixo.uploads.list()               → [{ filename, url, size }]
      await deplixo.uploads.delete(filename)

    Upload first, then store the URL in a collection entry:
      const photo = await deplixo.upload(fileInput.files[0]);
      await recipes.add({ title: "Pasta", photo: photo.url });
    Max 5MB per file. Do NOT use base64, data URLs, or FileReader.readAsDataURL().

    ### Identity
      deplixo.user  → { id, name } for the current visitor
      await deplixo.ensureIdentity()  → prompts for display name (multi-user apps only)
      Author info is included in collection .list() and .onChange() results.
      NOTE: You MUST always pass the `personal` option when creating a collection:
      - Personal apps: `deplixo.db.collection("state", { personal: true })`
      - Multi-user apps: `deplixo.db.collection("recipes", { personal: false })`

    ### Proxy (call external APIs with server-side secrets)
      const data = await deplixo.proxy(url, { method, headers, body })
      → { status: 200, body: { ... } }
    Secrets are resolved server-side: use ${SECRET_NAME} in headers or body.
    The app owner must configure secrets and allowed domains in the dashboard.
    Example:
      const weather = await deplixo.proxy(
        "https://api.weather.gov/gridpoints/OKX/33,37/forecast",
        { headers: { "Authorization": "Bearer ${WEATHER_KEY}" } }
      );
    NEVER embed API keys in HTML/JS source. Use deplixo.proxy() with secrets.

    ### AI (platform-managed LLM access)
      const answer = await deplixo.ai.prompt("Generate 5 quiz questions")
      → "1. What is..."

      const result = await deplixo.ai.prompt({
        system: "You are a quiz master. Return JSON.",
        user: "Generate 5 questions about space",
        json: true
      })
      → { questions: [...] }

      // Streaming
      const stream = deplixo.ai.stream("Write a story about a robot");
      for await (const chunk of stream) {
        outputEl.textContent += chunk;
      }
    AI uses the app owner's credits (included with their tier). No API key
    needed — it just works. The app owner can configure the model tier (low,
    medium, high) and preferred provider in the dashboard.
    NEVER embed LLM API keys in source code. Use deplixo.ai.prompt() instead.

    ### Charts (Chart.js 4.x, lazy-loaded)
      const chart = await deplixo.chart(containerEl, {
        type: "bar",
        data: { labels: ["A","B","C"], datasets: [{ data: [10,20,30] }] },
        options: { responsive: true }
      });
    Returns a Chart.js instance. All Chart.js config options work.

    ### Maps (Leaflet 1.9, lazy-loaded)
      const map = await deplixo.map(containerEl, { center: [40.7, -74], zoom: 12 });
      map.addMarker(40.7, -74, "New York");
      // Geolocation:
      const pos = await deplixo.location.get();  → { lat, lng, accuracy }

    ### QR Codes (qr-creator, lazy-loaded)
      await deplixo.qr.generate(el, "https://example.com", { size: 200 });
      const dataUrl = await deplixo.qr.toDataURL("https://example.com");
      const text = await deplixo.qr.scan();  // Camera-based scan via BarcodeDetector

    ### PDF Export (html2pdf.js, lazy-loaded)
      await deplixo.pdf.create(el, { filename: "report.pdf" });
      const iframe = await deplixo.pdf.preview(el, container);

    ### Sound (Web Audio synth, no CDN)
      deplixo.sound.play("@ping");   // 8 built-ins: ping, pop, click, ding, error, success, whoosh, beep
      await deplixo.sound.load("alert", "/my-sound.mp3");
      deplixo.sound.play("alert");
      deplixo.sound.stop("alert");

    ### Export (CSV, JSON, file download)
      deplixo.export.csv(data, "report.csv");           // RFC 4180 compliant
      deplixo.export.json(data, "data.json");
      deplixo.export.file("notes.txt", content);
      const dataUrl = await deplixo.export.screenshot(el);  // html2canvas lazy-loaded

    ### Embeds (YouTube, CodePen, iframe)
    Two modes: pass an element to append, OR pass null to get an HTML string (for templates).
      // DOM mode — appends iframe to container
      deplixo.embed.youtube(containerEl, "dQw4w9WgXcQ", { autoplay: true });
      // HTML string mode — returns iframe HTML for use in template literals
      card.innerHTML = `<div>${deplixo.embed.youtube(null, videoUrl)}</div><p>${note}</p>`;
      // Same for codepen and iframe:
      deplixo.embed.codepen(el, "https://codepen.io/user/pen/abc", { theme: "dark" });
      deplixo.embed.iframe(el, "https://example.com", { height: "400" });
    ALWAYS use deplixo.embed.youtube() instead of writing raw <iframe> tags. Pass null
    as the first arg when building HTML strings in templates.

    ### Camera
    Two modes: start() for live viewfinder, photo() for one-shot capture.
      // Live viewfinder (selfie booth, photo app, scanner):
      const cam = await deplixo.camera.start(previewEl, { facing: "user" });
      // cam.video is the live <video> element in previewEl
      const blob = await cam.capture();  // capture current frame as JPEG Blob
      cam.stop();                        // stop stream, remove video
      // One-shot capture (no preview needed):
      const blob = await deplixo.camera.photo({ facing: "environment" });
    ALWAYS use deplixo.camera.start() for apps with live camera preview.
    Use deplixo.camera.photo() only for instant capture without a viewfinder.
      const qrText = await deplixo.camera.scan();  // Delegates to deplixo.qr.scan()

    ### Rich Text Editor
      const editor = deplixo.editor(containerEl, { placeholder: "Write here..." });
      editor.getContent();       // Returns HTML string
      editor.setContent("<b>Hello</b>");
      editor.onChange(html => { });

    ### Sharing (Web Share API + clipboard fallback)
      const result = await deplixo.share({ title: "My App", url: location.href });
      // result is "shared" (native) or "copied" (clipboard fallback)

    ### Email (platform credits, claimed apps only)
      const result = await deplixo.email.send({
        to: "user@example.com",
        subject: "Your receipt",
        body: "Thanks for your order!",       // plain text
        html: "<h1>Thanks!</h1><p>Order #123</p>"  // optional HTML (sanitized server-side)
      });  // → { status: "sent", message_id, credits_used, credits_remaining }
    Costs 2 platform credits per email. Daily limit per app (5 free / 50 personal / 500 pro).
    Emails are wrapped in a branded template with the app's icon and title.
    App must be claimed to send emails. Do NOT use external email APIs — use deplixo.email.send().

    Email opt-in (collect visitor emails):
      await deplixo.email.register("user@example.com", "Jane")  // → { status: "registered", email }
      const isOpted = await deplixo.email.isRegistered("user@example.com")  // → true/false
    Use register() to build newsletter signups, waitlists, or notification opt-ins.
    Stored in the app's database — no external service needed.

    ### Inbound Webhooks (receive events from external services)
      // Listen for webhook events in real-time via SSE
      deplixo.webhooks.on("github", function(payload) {
        console.log("Got GitHub event:", payload);
      });
      // List past webhook payloads
      const events = await deplixo.webhooks.list("github", { limit: 20 });
    External services POST to: https://deplixo.com/hooks/{app-id}/{webhook-name}/
    Payloads are stored in the per-app database and broadcast via SSE.

    ### Broadcast (ephemeral real-time messages)
      deplixo.broadcast.send("cursor-move", { x: 100, y: 200 });
      deplixo.broadcast.on("cursor-move", (data, senderId) => {
        console.log("Cursor at", data.x, data.y, "from", senderId);
      });
      deplixo.broadcast.off("cursor-move");  // remove all handlers for this type
      deplixo.broadcast.off("cursor-move", specificHandler);  // remove one handler
    Messages are ephemeral — not stored. Rate limit: 20/sec. Max payload: 4KB.
    Use for: live cursors, typing indicators, game state, drawing strokes.

    ### Scheduled Tasks (server-side cron jobs)
    Pass a `cron` parameter when deploying to set up server-side scheduled tasks.
    These run even when nobody has the app open.

      cron=[
        {"name": "daily-quote", "schedule": "0 9 * * *", "action": "event",
         "config": {"event_type": "new-quote"}},
        {"name": "cleanup", "schedule": "0 0 * * 0", "action": "trim-collection",
         "config": {"collection": "logs", "limit": 100}}
      ]

    Actions: event (broadcast SSE), clear-collection, trim-collection, random-pick, fetch.
    Schedule uses cron syntax (e.g. "0 9 * * *" = daily at 9am UTC).
    Client SDK (read-only): deplixo.cron.list(), .pause(name), .resume(name).
    Listen for cron events: collection.onChange() fires when cron modifies data.
    Limits: Free 3 jobs, Personal 10, Pro 50. Minimum interval: 5 minutes.

    ### Presence (who's online)
      await deplixo.presence.join({ name: "Alice", status: "online" });
      const users = await deplixo.presence.list();  // → [{id, name, status, avatar, joined_at}]
      deplixo.presence.onChange(({ action, userId, data }) => {
        // action: "presence:join" or "presence:leave"
      });
      deplixo.presence.leave();  // auto-called on page unload
    Heartbeat sent every 15s. Users removed after 30s of no heartbeat.

    ### Notifications (per-user in-app)
      await deplixo.notifications.send("user123", {
        title: "New message", body: "Alice sent you a message", type: "message"
      });
      const { items, unread_count } = await deplixo.notifications.list({ unread_only: true });
      await deplixo.notifications.markRead([notifId]);  // or markRead() for all
      deplixo.notifications.onChange((notif) => { showBadge(notif); });
    Stored in per-app database. Auto-expires after 30 days. Rate limit: 10/min.

    ### Rooms (namespaced multiplayer)
      const room = deplixo.rooms.join("lobby-1");
      const notes = room.collection("messages", { personal: false });
      room.broadcast.send("typing", { user: "Alice" });
      room.broadcast.on("typing", (data) => { showTyping(data.user); });
      room.broadcast.off("typing");  // remove all handlers (or pass specific handler)
      const rooms = await deplixo.rooms.list();
      const newRoom = await deplixo.rooms.create({ name: "Game Room" });
    Rooms scope collections and broadcast to a namespace. Room data stored in _rooms collection.

    ### Multi-Channel Chat Pattern (CRITICAL — read before building any chat app)
    For apps with multiple channels/rooms that users switch between, use ONE global
    messages collection with a channelId field — do NOT create per-channel collections
    or per-channel rooms. This avoids listener accumulation on channel switch.

    CORRECT pattern — single collection, filter in onChange:
      const msgColl = deplixo.db.collection("messages", { personal: false });

      // ONE onChange listener handles ALL channels
      msgColl.onChange(({ action, id, value, author }) => {
        if (action === "reconnect") { loadCurrentChannel(); return; }
        if (action === "add") {
          if (value.channelId === currentChannelId) {
            appendMessage({ id, value, author });  // show in current view
          } else {
            unreadCounts[value.channelId] = (unreadCounts[value.channelId] || 0) + 1;
            renderChannelList();  // update badge
            deplixo.sound.play("@pop");
          }
        }
      });

      // Send: include channelId in every message
      await msgColl.add({ channelId: currentChannelId, text, ts: Date.now() });

      // Switch channel: just re-filter and re-render, no new listeners
      async function switchChannel(id) {
        currentChannelId = id;
        unreadCounts[id] = 0;
        const all = await msgColl.list();
        const msgs = all.filter(m => m.value.channelId === id);
        renderMessages(msgs);
      }

    WRONG — do NOT do this (creates leaked listeners on every switch):
      function switchChannel(id) {
        const room = deplixo.rooms.join(id);
        const coll = room.collection("messages", { personal: false });
        coll.onChange(handler);  // BUG: old listener from previous channel still active!
      }

    Use Rooms only when users are in ONE room at a time and don't switch frequently
    (e.g., game lobbies, video calls). For multi-channel chat, use the single-collection pattern above.

    ### Real-Time Best Practices (CRITICAL for chat / collaborative apps)
    onChange() delivers events via SSE. Follow these rules to avoid duplicates and missed messages:

    1. **Do NOT use optimistic rendering with onChange()**. When you call collection.add(),
       do NOT immediately render the item in the UI. Instead, let the onChange() callback
       handle ALL rendering — it fires for the sender too (~50-100ms latency, imperceptible).
       Optimistic rendering causes duplicate messages when the SSE event races the HTTP response.

    2. **Handle the "reconnect" action in onChange()**. When the SSE connection drops and
       reconnects, onChange fires with `{ action: "reconnect" }`. Use this to refetch data:
         collection.onChange(({ action }) => {
           if (action === "reconnect") { loadMessages(); return; }
           // ...handle add/update/remove normally
         });

    3. **Guard async channel/view switches**. If your app switches between views that
       load data with `await collection.list()`, set a generation counter before the
       await and check it after — discard stale loads if the user switched again.

    4. **Clean up listeners when switching contexts**. If you MUST use per-view collections,
       call `collection.offChange(handler)` before switching to remove the old listener.
       Or call `collection.offChange()` (no args) to remove all listeners on that collection.

    5. **Use broadcast for ephemeral signals, collections for persistent data**.
       Typing indicators, cursor positions → broadcast. Messages, posts → collections.

    ## Making Apps Functional — CRITICAL

    The #1 mistake is deploying apps with stubbed functionality. Users expect
    the app to WORK, not just look nice. Follow these rules:

    ### NEVER do this:
    - `// TODO: implement API call` -> Use deplixo.ai.prompt() or deplixo.proxy()
    - `return hardcodedSampleData` -> Wire to a real data source
    - `function search() { /* implement later */ }` -> Implement it now
    - `alert("Feature coming soon")` -> Either build it or don't include the button

    ### ALWAYS do this:
    - If the app generates content (names, stories, quizzes, plans, recipes):
      -> Use deplixo.ai.prompt() with a specific system prompt and the user's input
    - If the app searches or looks up information:
      -> Use deplixo.ai.prompt() with instructions to return structured results
      -> OR use deplixo.proxy() to call a real API
    - If the app collects and saves data:
      -> Use deplixo.db.collection() with appropriate personal/multi-user mode
    - If the app needs user-specific state:
      -> Use deplixo.db.collection("state", { personal: true }) — NOT localStorage
    - If the app has a "calculate" or "analyze" button:
      -> Implement the actual logic in JavaScript, or use deplixo.ai.prompt()
        for complex analysis

    ### Example: Brand Name Generator (the RIGHT way)
    Instead of returning hardcoded names, wire the form to deplixo.ai.prompt():

      async function generateNames(businessInfo) {
        const result = await deplixo.ai.prompt({
          system: "You are a branding expert. Generate 10 creative brand names. Return JSON: { names: [{ name, tagline, reasoning }] }",
          user: `Business: ${businessInfo.description}\nValues: ${businessInfo.values}\nAudience: ${businessInfo.audience}`,
          json: true
        });
        return result.names;
      }

    ### Example: Using AI as a data source when no real API is available
    When a real API isn't available, use AI to provide useful (if approximate) results:

      async function searchTrademarks(query) {
        const result = await deplixo.ai.prompt({
          system: "You are a trademark research assistant. Analyze potential conflicts. Return JSON: { conflicts: [{ name, similarity, risk_level }], recommendation }",
          user: `Analyze trademark conflicts for: "${query}"`,
          json: true
        });
        return result;
      }

    ### IMPORTANT RULES
    - ALWAYS use deplixo.db.collection() for ANY persistent data — even for
      single-user apps. Users expect their data on all their devices (phone,
      desktop, tablet). localStorage does NOT sync across devices.
    - NEVER use localStorage. Always use deplixo.db.collection() instead.
      Collections sync across all devices and browsers in real-time via SSE.
    - NEVER use base64/data URLs for images — use deplixo.upload()
    - NEVER embed API keys in HTML/JS — use deplixo.proxy() with ${SECRET_NAME}
    - NEVER embed LLM API keys — use deplixo.ai.prompt() (uses platform credits)
    - Collections are shared across ALL visitors automatically
    - Real-time updates work via .onChange() — ALWAYS use it to re-render on changes
    - If the user's existing code uses localStorage, REWRITE it to use
      deplixo.db.collection() before deploying. Do not deploy localStorage code.
    - NEVER include Chart.js/Leaflet/html2canvas/html2pdf/qr-creator via <script> tags —
      use deplixo.chart(), deplixo.map(), deplixo.export.screenshot(), deplixo.pdf.create(),
      deplixo.qr.generate() instead. The SDK lazy-loads the right CDN version automatically.
    - NEVER manually create <audio> elements for UI sounds — use deplixo.sound.play("@ping")
    - NEVER write CSV serialization by hand — use deplixo.export.csv(data, filename)
    - NEVER build a contentEditable editor from scratch — use deplixo.editor(el)
    - NEVER build custom login/signup forms — use deplixo.auth.requireLogin() with auth_enabled=True
    - When an app needs user accounts, ALWAYS pass auth_enabled=True in the deploy call AND
      call `await deplixo.auth.requireLogin()` at app startup to get the user object
    - NEVER use setInterval/setTimeout for recurring server tasks — use the `cron` deploy parameter
    - When an app needs scheduled tasks (daily, hourly, weekly), ALWAYS pass `cron` in the deploy call

    ### Two patterns: Personal Apps vs Multi-User Apps

    CRITICAL: Choose the right pattern based on how many people use the app.
    You MUST always pass the `personal` option explicitly on every collection.

    **Personal app** (one person, multiple devices — tracker, journal, todo):
    - MUST pass `{ personal: true }`:
        `deplixo.db.collection("state", { personal: true })`
    - Use ONE shared record. All devices read and write the SAME record.
    - Do NOT filter by deplixo.user.id or author — visitor IDs are per-browser,
      so phone and desktop have DIFFERENT IDs even for the same person.
    - Do NOT use ensureIdentity or require a display name.
    - onChange fires on ALL devices, all re-render the same data.

    **Multi-user app** (multiple people — chat, shared list, scoreboard):
    - MUST pass `{ personal: false }`:
        `deplixo.db.collection("recipes", { personal: false })`
    - Each person adds their own entries via .add() — author is tracked.
    - Use deplixo.user and author info to show who contributed what.
    - Identity modal will prompt for a display name on first write.
    - onChange fires for everyone, all re-render the full shared list.

    ### Example: Personal App — Progress Tracker
    One person across phone, tablet, desktop. All devices stay in sync.

      const store = deplixo.db.collection("state", { personal: true });
      let appState = {};
      let recordId = null;

      async function loadState() {
        const items = await store.list();
        if (items.length > 0) {
          recordId = items[0].id;
          appState = items[0].value;
        }
        render(appState);
      }

      async function saveState(newState) {
        appState = newState;
        if (recordId) await store.update(recordId, newState);
        else {
          const result = await store.add(newState);
          recordId = result.id;
        }
        render(appState);
      }

      // Any device saves → all other devices re-render automatically
      store.onChange(() => loadState());
      loadState();

    ### Example: Multi-User App — Shared Recipe Box
    Multiple people contribute and see each other's entries.

      const recipes = deplixo.db.collection("recipes", { personal: false });
      // Identity prompt happens automatically on first write (add/update/remove)

      async function loadRecipes() {
        const all = await recipes.list();
        renderRecipes(all);  // each item: { id, value, author: { id, name } }
      }
      async function addRecipe(title, ingredients, photoFile) {
        const photo = await deplixo.upload(photoFile);
        await recipes.add({ title, ingredients, photo: photo.url });
      }
      recipes.onChange(() => loadRecipes());
      loadRecipes();

    Args:
        code: HTML code for single-file apps. Mutually exclusive with `files`.
        files: Dict of {path: content} for multi-file apps. Must include
               "index.html". Example: {"index.html": "...", "style.css": "...",
               "app.js": "..."}. Files are served at their paths relative to
               the app URL (e.g. deplixo.com/abcd-efgh/style.css).
        title: A short title for the app
        description: A 1-2 sentence description of what the app does. Used for
                     social preview cards (OG tags) when the URL is shared on
                     Twitter, Slack, iMessage, etc. Always include this.
        slug: Optional URL slug for a named app URL (requires an account)
        remixed_from: Optional app ID of the app this was remixed from (e.g. abcd-efgh)
        app_id: Hash ID from a previous deploy to update an existing app
        claim_token: Claim token from a previous deploy, required when updating
                     an unclaimed app
        merge_files: When True on an update, only add/replace files in the payload
                     and keep all other existing files. Use this to deploy large
                     apps in multiple calls.
        access_code: Optional shared access code. When set, visitors must enter
                     this code to view the app. Pass empty string to remove.
        auth_enabled: When True, users must sign in with a Deplixo account
                     (Google, GitHub, or email) to use this app.
        auth_allowed_domains: Optional list of email domains allowed to sign in
                             (e.g. ["company.com"]). Empty = any domain.
        cron: Optional list of server-side scheduled tasks. Each job is a dict
              with: name (str), schedule (cron expression like "0 9 * * *"),
              action ("event"|"clear-collection"|"trim-collection"|"random-pick"|"fetch"),
              config (dict with action-specific settings like event_type, collection, url).
    """
    if not code and not files:
        return "Error: Either 'code' or 'files' must be provided."
    if files and "index.html" not in files and not (merge_files and app_id):
        return "Error: 'files' must include 'index.html'."

    payload: dict = {"title": title, "description": description}
    if files:
        payload["files"] = files
    else:
        payload["code"] = code
    if slug:
        payload["slug"] = slug
    if remixed_from:
        payload["remixed_from"] = remixed_from
    if app_id:
        payload["app_id"] = app_id
    if claim_token:
        payload["claim_token"] = claim_token
    if merge_files:
        payload["merge_files"] = True
    if icon:
        payload["icon"] = icon
    if access_code is not None:
        payload["access_code"] = access_code
    if auth_enabled:
        payload["auth_enabled"] = True
    if auth_allowed_domains:
        payload["auth_allowed_domains"] = auth_allowed_domains
    if cron:
        payload["cron"] = cron

    timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{DEPLIXO_API_URL}/api/v1/deploy",
                json=payload,
            )
    except httpx.TimeoutException:
        return "Error: Deploy request timed out. The app code may be too large — try deploying in chunks using merge_files=True."
    except httpx.ConnectError:
        return "Error: Could not connect to Deplixo API. Please try again in a moment."
    except httpx.HTTPError as e:
        return f"Error: HTTP request failed: {str(e)[:500]}"

    if response.status_code == 200:
        data = response.json()
        url = data.get("url", "")
        hash_id = data.get("hash_id", "")
        updated = data.get("updated", False)
        resp_claim_token = data.get("claim_token", "")
        claim_url = data.get("claim_url")

        suggestions = data.get("suggestions")

        if updated:
            # App was updated in-place (same URL)
            parts = [
                f"App updated successfully at: {url}",
            ]
            if claim_url:
                # Still unclaimed — remind about claiming
                parts.extend([
                    "",
                    "REMINDER: This app is still UNCLAIMED and will be permanently "
                    "deleted in less than 1 hour.",
                    f"Claim link: {claim_url}",
                    "",
                    "Show the claim link to the user again so they don't lose "
                    "their app. Claiming is free — no credit card required.",
                ])
            parts.append("")
            update_line = f'To update again, pass app_id="{hash_id}"'
            if resp_claim_token:
                update_line += f' and claim_token="{resp_claim_token}".'
            else:
                update_line += "."
            parts.append(update_line)
            if suggestions:
                parts.extend(_format_suggestions(suggestions))
            return "\n".join(parts)

        # --- First deploy of this app ---
        if claim_url:
            # New unclaimed app — claim link is the primary output
            parts = [
                "App deployed! Here is the claim link:",
                "",
                f"  {claim_url}",
                "",
                "INSTRUCTIONS FOR YOUR RESPONSE:",
                "1. Show ONLY the claim link above to the user — do NOT show the "
                "   app URL. The claim page has a live preview of the app.",
                "2. Tell the user: \"Click this link to claim your app.\"",
                "3. Explain: The app will be PERMANENTLY DELETED in 1 hour if "
                "   not claimed. Claiming is free and takes seconds — no credit "
                "   card required. They can create a free account or sign in.",
                "4. Mention: Once claimed, they get a permanent URL, a dashboard, "
                "   analytics, and they can keep editing the app with you.",
                "5. Do NOT say \"here is your app URL\" — the claim link IS the "
                "   link to show. It includes a live preview of the running app.",
                "",
                "You can keep editing this app in the same conversation. Ask the "
                "user what they'd like to change.",
            ]
            if resp_claim_token:
                parts.extend([
                    "",
                    f'(Internal — to update this app, pass app_id="{hash_id}" '
                    f'and claim_token="{resp_claim_token}".)',
                ])
            if suggestions:
                parts.extend(_format_suggestions(suggestions))
            return "\n".join(parts)
        else:
            # App was deployed by an authenticated user (already claimed)
            parts = [
                f"App deployed at: {url}",
            ]
            if resp_claim_token:
                parts.extend([
                    "",
                    f'To update this app, pass app_id="{hash_id}" '
                    f'and claim_token="{resp_claim_token}".',
                ])
            if suggestions:
                parts.extend(_format_suggestions(suggestions))
            return "\n".join(parts)
    else:
        error_text = response.text[:5000] if len(response.text) > 5000 else response.text
        return f"Deployment failed (HTTP {response.status_code}): {error_text}"


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
        idempotentHint=True,
    )
)
async def deplixo_read_source(url: str) -> str:
    """Read the source code of a Deplixo app.

    Accepts a Deplixo app URL (e.g. deplixo.com/abcd-efgh) or an edit link
    (e.g. deplixo.com/edit/abc123...). Edit links grant access to the full
    source even for private or non-remixable apps.

    Use this when a user pastes a Deplixo URL or edit link and wants to
    modify the app. After reading the source, use deplixo_deploy with
    app_id and claim_token to push updates.

    Args:
        url: A Deplixo app URL or edit link URL
    """
    import re

    # Parse URL to extract hash_id or edit token
    url = url.strip().rstrip("/")

    # Edit link format: deplixo.com/edit/{token}
    edit_match = re.search(r'/edit/([a-f0-9]{64})', url)
    # App URL format: deplixo.com/xxxx-xxxx or deplixo.com/abcdefgh
    app_match = re.search(r'/([a-z]{4}-?[a-z]{4})/?$', url)

    if not edit_match and not app_match:
        return "Error: Could not parse Deplixo URL. Expected format: deplixo.com/abcd-efgh or deplixo.com/edit/{token}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if edit_match:
                token = edit_match.group(1)
                # First resolve the edit token to get the app hash_id
                resp = await client.get(
                    f"{DEPLIXO_API_URL}/edit/{token}/",
                    headers={"Accept": "application/json"},
                    follow_redirects=False,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    hash_id = data.get("hash_id", "")
                    token_param = token
                else:
                    return f"Error: Edit link not found or invalid (HTTP {resp.status_code})"
            else:
                hash_id = app_match.group(1).replace("-", "")
                hash_id = f"{hash_id[:4]}-{hash_id[4:]}"
                token_param = ""

            # Fetch source
            source_url = f"{DEPLIXO_API_URL}/api/v1/apps/{hash_id}/source"
            if token_param:
                source_url += f"?token={token_param}"
            resp = await client.get(source_url)

            if resp.status_code != 200:
                error_text = resp.text[:2000]
                return f"Error: Could not read source (HTTP {resp.status_code}): {error_text}"

            data = resp.json()
            parts = [
                f"Source code for: {data.get('title', 'Untitled')} ({data.get('hash_id', hash_id)})",
                f"Author: {data.get('author', 'unknown')}",
            ]
            if data.get('description'):
                parts.append(f"Description: {data['description']}")
            parts.append("")

            # Main code
            code = data.get("code", "")
            if code:
                parts.append("## index.html")
                parts.append(code)

            # Additional files
            files = data.get("files", {})
            for path, content in sorted(files.items()):
                if path != "index.html" and content:
                    parts.append(f"\n## {path}")
                    parts.append(content)

            if token_param:
                parts.extend([
                    "",
                    f'To update this app, use deplixo_deploy with app_id="{data.get("hash_id", hash_id)}" '
                    f'and claim_token="{token_param}".',
                ])

            return "\n".join(parts)

    except httpx.TimeoutException:
        return "Error: Request timed out while reading source."
    except Exception as e:
        return f"Error reading source: {str(e)[:500]}"


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
        idempotentHint=True,
    )
)
async def deplixo_plan(
    description: str,
    constraints: dict | None = None,
) -> str:
    """Plan a deployment — determine what infrastructure the app needs before going live.

    ALWAYS call this before deplixo_deploy. Deploying gives the app real
    infrastructure (persistent database, user accounts, email, scheduled tasks,
    etc.) and you need to know which features to enable. This tool analyzes the
    app and returns deployment questions you MUST ask the user before proceeding.

    Do NOT skip this step — deploying without planning may give the user an app
    that loses data on refresh, doesn't support multiple users when it should,
    or is missing features they need.

    Args:
        description: What the app does (plain English description)
        constraints: Optional dict of known constraints, e.g. {"personal": true, "auth": true}
    """
    payload = {"description": description}
    if constraints:
        payload["constraints"] = constraints

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{DEPLIXO_API_URL}/api/v1/plan", json=payload)

        if resp.status_code != 200:
            return f"Planning failed (HTTP {resp.status_code}). Build the app using your best judgment."

        data = resp.json()
        parts = ["## App Plan\n"]

        if data.get("pattern"):
            parts.append(f"**Pattern**: {data['pattern']} app\n")

        if data.get("clarifying_questions"):
            parts.append("**Ask the user these questions before building:**")
            for q in data["clarifying_questions"]:
                parts.append(f"- {q}")
            parts.append("")

        if data.get("recommended_primitives"):
            parts.append("**Recommended primitives:**")
            for p in data["recommended_primitives"]:
                parts.append(f"- {p}")
            parts.append("")

        if data.get("architecture_notes"):
            parts.append(f"**Architecture**: {data['architecture_notes']}\n")

        parts.append("Ask the clarifying questions, then build the app using the recommended primitives.")
        return "\n".join(parts)
    except Exception as e:
        return f"Planning unavailable: {str(e)[:200]}. Build the app using your best judgment."


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
        idempotentHint=True,
    )
)
async def deplixo_query(
    app_id: str,
    claim_token: str,
    collection: str = "",
    sql: str = "",
    limit: int = 50,
) -> str:
    """Query data from a deployed Deplixo app.

    Use this when the user asks about data in their app — "how many entries?",
    "show me the feedback", "what are the top items?", etc.

    Requires the claim_token from a previous deploy (proves ownership).

    Args:
        app_id: The app's hash ID (e.g. "abcd-efgh" from a previous deploy)
        claim_token: The claim token from the deploy response (proves ownership)
        collection: Name of the collection to query (e.g. "recipes", "tasks")
        sql: Raw SQL query (alternative to collection — for power users)
        limit: Max entries to return (default 50, max 200)
    """
    payload = {
        "app_id": app_id,
        "claim_token": claim_token,
        "limit": min(limit, 200),
    }
    if collection:
        payload["collection"] = collection
    elif sql:
        payload["sql"] = sql
    else:
        return "Error: Specify either 'collection' or 'sql' to query."

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{DEPLIXO_API_URL}/api/v1/query", json=payload)

        if resp.status_code == 403:
            return "Error: Invalid claim token. Make sure you're using the claim_token from the deploy response."
        if resp.status_code != 200:
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            return f"Query failed: {data.get('error', resp.text[:500])}"

        data = resp.json()
        parts = [f"## Data from {data.get('app_id', app_id)}\n"]

        if "collection" in data:
            parts.append(f"**Collection**: {data['collection']} ({data.get('total', '?')} total entries)\n")
            entries = data.get("entries", [])
            if not entries:
                parts.append("No entries found.")
            else:
                for entry in entries[:limit]:
                    author = entry.get("author", {})
                    author_name = author.get("name", "anonymous") if author else "anonymous"
                    parts.append(f"- **{entry.get('id', '?')}** (by {author_name}): {entry.get('value', {})}")
        elif "rows" in data:
            parts.append(f"**SQL result**: {data.get('count', '?')} rows\n")
            columns = data.get("columns", [])
            rows = data.get("rows", [])
            if columns:
                parts.append("| " + " | ".join(str(c) for c in columns) + " |")
                parts.append("| " + " | ".join("---" for _ in columns) + " |")
            for row in rows[:limit]:
                if isinstance(row, dict):
                    parts.append("| " + " | ".join(str(v) for v in row.values()) + " |")

        return "\n".join(parts)
    except Exception as e:
        return f"Query failed: {str(e)[:300]}"


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=True,
        idempotentHint=True,
    )
)
async def deplixo_list_apps(
    claim_token: str,
) -> str:
    """List all apps owned by the user. Requires a claim_token from any of their apps.

    Use this when the user says "update my app" or "which apps do I have?" and
    you need to find the right app_id and claim_token.

    Args:
        claim_token: A claim token from any of the user's apps (proves account ownership)
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{DEPLIXO_API_URL}/api/v1/apps/by-token",
                params={"claim_token": claim_token},
            )

        if resp.status_code == 404:
            return "Error: Invalid claim token. No app found with this token."
        if resp.status_code != 200:
            return f"Error listing apps (HTTP {resp.status_code})."

        data = resp.json()
        apps = data.get("apps", [])

        if not apps:
            return "No apps found."

        parts = [f"## Your Apps ({len(apps)} total)\n"]
        for app in apps:
            title = app.get("title", "Untitled")
            app_id = app.get("app_id", "?")
            url = app.get("url", "")
            token = app.get("claim_token", "")
            parts.append(f"- **{title}** — {url}")
            parts.append(f"  app_id=\"{app_id}\", claim_token=\"{token}\"")

        parts.extend([
            "",
            "To update any app, use deplixo_deploy with the app_id and claim_token shown above.",
        ])
        return "\n".join(parts)
    except Exception as e:
        return f"Error listing apps: {str(e)[:300]}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
