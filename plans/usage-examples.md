# Deplixo MCP — Usage Examples for Marketplace Submission

These examples demonstrate the `deplixo_deploy` tool across common use cases. Each shows a user prompt and the kind of response the tool produces.

---

## Example 1 — Custom App with Persistent Storage

**Prompt:**

> I would like a customized exercise regimen tracking app for weightlifting over a given week and deploy it with Deplixo.

**Response:**

I'll build you a weightlifting tracker app and deploy it to Deplixo. Let me start by reading the relevant skill files. Now let me build the app. I'll go with a bold, industrial-meets-modern aesthetic — think iron plates and gym chalk vibes with clean data presentation.

Your **Iron Log** weightlifting tracker is ready! Click this link to claim your app:

https://deplixo.com/claim/a2509c9f36d9dce5f5f45acd8bdd8188c96493b1ab793ee86d320f359159aa68/

The app will be **permanently deleted in 1 hour** if not claimed. Claiming is free and takes seconds — no credit card required. Once claimed, you get a permanent URL, a dashboard, and the ability to keep editing the app with me.

Here's what's packed in:

- **Day-by-day tabs** for Mon–Sun with status dots (green = has exercises, yellow = rest day)
- **Week navigation** to browse previous/future weeks — all data persists via deplixo.db
- **Per-exercise tracking** with weight (lbs), reps, RPE, and a completion checkbox per set
- **Add/remove exercises and sets** freely — new exercises start with 3 empty sets
- **Rest day toggle** per day
- **Weekly volume bar chart** showing total lbs moved each day at a glance
- **Summary stats** — total volume, sets completed, exercise count, and today's volume
- **Session notes** textarea for each day

The whole aesthetic is dark, industrial — Bebas Neue headers, warm orange accent, subtle grid-line texture. Should feel right at home on your phone between sets. Let me know if you want any tweaks like kg support, preset workout templates, or exercise history!

---

## Example 2 — Simple Single-File App

**Prompt:**

> Build me a pomodoro timer with ambient sounds and deploy it so I can share with my team.

**Response:**

I'll create a polished pomodoro timer with ambient sound options and deploy it to Deplixo.

Your **Deep Focus** pomodoro timer is ready! Click this link to claim your app:

https://deplixo.com/claim/7b3e1a4f92c8d0e6f1a5b9c3d7e2f8a4b6c0d9e3f5a1b7c2d8e4f0a6b3c9d5/

The app will be **permanently deleted in 1 hour** if not claimed. Claiming is free — no credit card required. Once claimed, you'll get a permanent URL you can share with your team.

Features:

- **25/5/15 timer** — standard pomodoro with short and long breaks, auto-advancing through cycles
- **Ambient sounds** — rain, coffee shop, white noise, lo-fi — toggle on/off, volume slider
- **Session counter** — tracks completed pomodoros with a visual progress ring
- **Keyboard shortcuts** — Space to start/pause, R to reset, N to skip to next phase
- **Desktop notifications** — alerts when a phase ends (with permission prompt)
- **Minimal dark UI** — large centered timer, no distractions

Want me to add custom timer durations or a task list?

---

## Example 3 — Multi-File React App

**Prompt:**

> Create a kanban board app with React — I need columns for Backlog, In Progress, Review, and Done with drag and drop. Deploy it to Deplixo.

**Response:**

I'll build a kanban board with drag-and-drop using React and deploy it as a multi-file app to Deplixo.

Your **FlowBoard** kanban app is ready! Click this link to claim your app:

https://deplixo.com/claim/d4a8c2e6f0b3d7a1c5e9f2b6d0a4c8e3f7b1d5a9c3e7f0b4d8a2c6e0f3b7d1/

The app will be **permanently deleted in 1 hour** if not claimed. Claiming is free and takes seconds — no credit card required. Once claimed, you get a permanent URL and dashboard.

Built with React via CDN (no build tools needed). Here's what you get:

- **4 columns** — Backlog, In Progress, Review, Done — each with card count
- **Drag and drop** — click and drag cards between columns, smooth animations
- **Add cards** — click "+" on any column, enter title and optional description
- **Edit/delete cards** — click a card to edit inline, trash icon to remove
- **Color labels** — assign priority colors (red/yellow/green/blue) to cards
- **Persistent data** — all cards and positions saved via deplixo.db, survives refresh and syncs across devices
- **Clean light UI** — soft shadows, rounded cards, column header accents

Files deployed: `index.html`, `app.js`, `style.css`. Let me know if you want features like card filtering, due dates, or multiple boards!

---

## Example 4 — Remixing an Existing App

This example shows a two-step interaction: first inspecting an existing app's source, then deploying a modified version with attribution.

### Step 1 — Inspect the source

**Prompt:**

> I found an app I want to remix. Please fetch the source from deplixo.com/ckty-zktl/source and show me a brief description of what it does. Then I'll tell you what I want to change. When we're done, deploy the result to Deplixo using the deplixo_deploy tool (if available) or show me how to paste it at deplixo.com/launch. This is a remix of deplixo.com/ckty-zktl — please include remixed_from: ckty-zktl when deploying.

**Response:**

Got it! Here's a quick rundown:

**Iron Log — Weekly Weightlifting Tracker**

It's a mobile-first workout logging app with a dark/industrial aesthetic. Key features:

- **Day-by-day workout view** — navigates a Mon–Sun week with a PPL-style default program (Push, Pull, Rest, Legs, Upper, Rest, Legs/Core)
- **Exercise cards** — each exercise shows muscle group tag, expandable set table with weight/reps inputs, and checkboxes to mark sets complete
- **Volume tracking** — calculates total volume (weight × reps) per day with a stats bar
- **Week navigation** — browse past/future weeks, data saved per-week via deplixo.db
- **Add/delete exercises** — modal for adding custom exercises with muscle group + set count
- **Week Summary view** — bar chart of volume by day, plus overall completion stats
- **Completion dots** on day tabs (none/partial/complete/rest)

What would you like to change? Theme swap, different default program, new features, different sport/activity type — whatever direction you want to take it.

### Step 2 — Deploy the remix

**Prompt:**

> Switch it to a running training log — weekly mileage, pace tracking, and a route notes field. Keep the dark theme but make it blue instead of orange.

**Response:**

I've rebuilt it as a running tracker and deployed the remix to Deplixo.

Your **Run Log** is ready! Click this link to claim your app:

https://deplixo.com/claim/e5f1a3b7c9d2e6f0a4b8c1d5e9f3a7b0c4d8e2f6a0b3c7d1e5f9a2b6c0d4e8/

The app will be **permanently deleted in 1 hour** if not claimed. Claiming is free — no credit card required. Once claimed, you get a permanent URL and dashboard.

Forked from: https://deplixo.com/ckty-zktl/

What changed from the original:

- **Exercise cards → Run entries** — distance (mi), duration, pace (auto-calculated), and elevation gain
- **Volume chart → Mileage chart** — weekly miles bar chart with a target line
- **Orange accent → Blue accent** — same dark industrial base, swapped to a cool blue palette
- **Route notes** — free-text field per run for course details, weather, how you felt
- **Weekly summary** — total miles, average pace, longest run, elevation total
- **Rest days preserved** — same toggle, now shows recovery notes option

Let me know if you want to add GPS integration or training plan templates!
