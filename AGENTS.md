# Liquid Photos — Agent Guide

## Project Overview

Liquid Photos is a university lab project focused on neural networks and intelligent media retrieval.

This is a **web-based smart photo library** built with **Python + Django** in a **client-server architecture**. Users can register, log in, and upload their own photos/images to a personal library. The server stores files locally and processes them to support intelligent search and person grouping.

This is **not** a commercial-scale product. It is a **demo-oriented academic project** whose success is measured mainly by:

- showing that the AI/search pipeline works,
- demonstrating meaningful neural-network-based functionality,
- having a clean and visually convincing interface,
- keeping the architecture understandable.

Formal multi-user support is required, but in practice usage will be minimal.

---

## Product Priorities

Always optimize for these priorities, in this order:

1. **Intelligent search quality**
2. **Demo readiness / visible functionality**
3. **Clean and understandable implementation**
4. **Reasonable performance on local hardware**
5. **Nice user interface**
6. **Everything else**

Do not overinvest in enterprise concerns unless they directly help the demo.

---

## Core Features

### 1. Intelligent Photo Search
This is the main feature of the project.

The system should support natural-language search over a user's personal photo library, including examples like:

- `sea`
- `girl`
- `sunset at the sea`
- `person with a dog`
- `girl with glasses near a car`

The goal is for the search to feel meaningfully "smart", not just keyword-based.

### 2. Person Discovery / Grouping
This is the second key feature.

The system should support:
- identifying the same person across multiple photos,
- grouping those photos together,
- showing a dedicated UI section/tab for discovered people,
- allowing a user to assign a readable name to a person,
- allowing search/filtering by that named person.

Behavior can be similar in spirit to Apple Photos person grouping, but implementation should remain practical for this project.

---

## Project Constraints

Assume the following unless the repository clearly defines otherwise:

- Backend: **Python + Django**
- Architecture: **client-server web app**
- Database: prefer **PostgreSQL**
- File storage: **local disk**
- Runtime target: **Windows**
- GPU target: **NVIDIA CUDA**
- CPU fallback: **not required**
- Scale: **small demo**, around **200–300 photos**
- User count: **very low**
- Search latency target on indexed data: roughly **1–2 seconds**
- Authentication: simple **username + password**
- Privacy/security hardening: **not a primary concern**
- Main goal: **prove that intelligent search works**

---

## Engineering Philosophy

### Build for a demo, not for a hyperscale system
Use practical, local-first solutions.

### Keep architecture clean but not overcomplicated
A small Django-based architecture with background processing is preferred over premature microservices.

### Prefer incremental progress
Do not rewrite large parts of the codebase unless there is a strong reason.

### Preserve clarity
Future readers should be able to understand how uploads, indexing, search, and person grouping work.

### Focus on visible value
When choosing between invisible perfection and a demo-visible improvement, prefer the demo-visible improvement unless it creates dangerous technical debt.

---

## Expected Technical Direction

Unless the existing repository clearly already chose another direction, prefer this general shape:

- Django app for auth, library, API, and UI
- local file storage for images
- background job/worker for indexing and AI processing
- generated metadata stored in database
- embeddings and/or search indexes stored locally
- search endpoint or service layer that combines metadata and AI search results
- person grouping pipeline stored in app models/tables

You do **not** need to force a specific AI stack unless the task requires it. If choosing implementation details, prefer practical solutions that fit local NVIDIA execution and a small dataset.

---

## Current Frontend State

As of March 9, 2026, the repository already contains a **frontend-only UI concept** for the demo.

### Language rules

- The product is being built for a **Russian-speaking audience**.
- All **user-facing interface text** should default to **Russian** unless the user explicitly asks otherwise.
- Demo placeholder copy shown in the UI should also be written in **Russian**.
- Internal technical artifacts may still use English when appropriate:
  - code identifiers,
  - dependency names,
  - commit messages,
  - framework/tool terminology,
  - technical comments when they are clearer in English.
- When there is a conflict, prioritize **Russian for product/UI text** and **clarity for technical implementation details**.

### Frontend stack currently in use

- **React 19**
- **TypeScript**
- **Vite**
- plain **CSS** (no Tailwind, no component library)

### Current implementation status

- The current repo is **not yet a Django app**.
- It is a **standalone frontend prototype** used to iterate on design and interaction before backend integration.
- Main entry points:
  - `package.json`
  - `index.html`
  - `src/App.tsx`
  - `src/styles.css`
- Demo images are stored locally under:
  - `public/demo/media`
  - `public/demo/people`

### Implemented UI concept

- Fullscreen **media grid** with square photo tiles
- Bottom **Liquid Glass-style tab bar** with:
  - `Медиа`
  - `Поиск`
  - `Люди`
- Top-right circular action buttons:
  - search shortcut
  - plus button for photo picking
- `Поиск` tab:
  - centered search layout
  - editable textarea so mobile/tablet keyboards appear on focus
- `Люди` tab:
  - people shown as a grid of circular portraits

### Current interaction behavior

- The top-right `+` button opens the system image/file picker via a hidden `input[type="file"]`.
- Selected file count is shown in a temporary glass-style toast.
- Search input is already interactive, but search logic is still mock/demo-only.

### Local development workflow

- Install deps with `pnpm install`
- Run dev server with `pnpm dev`
- Production build check with `pnpm build`

### Local network preview

For testing on other devices in the same LAN, run Vite with host binding enabled:

- `pnpm dev --host 0.0.0.0`

Typical LAN URL on this Mac during the current setup:

- `http://192.168.1.175:5173/`

This IP can change between networks, so always verify it before reporting it as current.

---

## Context Recovery in a New Chat

When a new chat starts and no conversation context is available, you must first restore context from the repository **efficiently**.

### Goals
- understand the current architecture,
- understand what has already been implemented,
- understand recent project direction,
- avoid wasting tokens.

### Required context recovery workflow
Start with the smallest useful set of information:

1. Inspect repository structure at a high level.
2. Read key project files only:
   - `README*`
   - dependency/manifests (`pyproject.toml`, `requirements.txt`, `package.json`, etc.)
   - main Django settings / app config / routes
   - top-level docs or architecture notes, if they exist
3. Inspect recent git history:
   - current branch
   - recent commits, especially the latest meaningful task commits
4. Identify which files are relevant to the requested task.
5. Read only those relevant files in detail.
6. Summarize the recovered context briefly before making large changes.

### Token-efficiency rules
Do **not**:
- read every file in the repo,
- dump huge files into context without need,
- inspect unrelated modules deeply,
- spend a large amount of context budget on initial exploration.

Do:
- use targeted discovery,
- inspect recent commits to infer project state,
- focus on files directly related to the current task,
- expand exploration only when required.

A good agent should recover context with discipline, not brute force.

---

## Git Workflow Rules

These rules are mandatory.

### Branch
Work only in the branch:

- `Egor-Dev`

Do not switch to another branch unless explicitly instructed.

### After every completed task
After finishing a task, you must:

1. verify the implementation,
2. create a **detailed commit**,
3. push to the remote repository,
4. push specifically from/to the current working branch `Egor-Dev`.

### Commit quality
Commit messages must be descriptive and useful for future context recovery.

Bad example:
- `fix`
- `update`
- `changes`

Good example style:
- `Add background photo indexing pipeline for semantic search`
- `Implement person grouping page and name assignment flow`
- `Fix search result ranking and photo detail filters`

If appropriate, include a longer body describing:
- what changed,
- why it changed,
- what was verified.

### Push requirement
After the commit, push the changes remotely.

The commit and push steps must be executed sequentially, not in parallel.
Do not start `git push` at the same time as `git commit`.
First run `git commit`, wait for it to finish successfully, then wait about 0.5-1 second, and only after that run `git push`.

If push fails due to authentication, remote setup, or network issues:
- report it honestly,
- explain the exact reason,
- provide the exact command/output needed to finish manually.

Do not claim the push succeeded unless it actually succeeded.

---

## Task Execution Workflow

For each task, follow this general sequence:

1. Recover context efficiently if needed.
2. Understand the task and locate relevant files.
3. Make the smallest reasonable change that solves it cleanly.
4. Verify the implementation.
5. Summarize what changed.
6. Commit with a detailed message.
7. Push to `Egor-Dev`.

---

## Verification Rules

Always verify changes as much as the repository allows.

Prefer repository-native verification first:
- existing test scripts
- existing lint scripts
- existing build scripts
- existing run commands

If the repository does not provide clear scripts, use reasonable stack-specific verification.

Examples:
- backend tests
- Django checks/migrations validation
- frontend build if applicable
- app startup sanity checks
- targeted manual flow verification for the changed feature

### Required verification for Python changes

If a task changes Python code in this repository, the agent must run:

- `python manage.py check`

before finishing the task, and confirm that the command reports no errors.

### Required verification for web/API changes

If a task adds or changes web functionality, HTTP routes, form submission, authentication, uploads, or any API behavior, the agent must verify the behavior with real HTTP requests against the locally running application.

Expected verification methods:
- `curl`
- PowerShell `Invoke-WebRequest` / `Invoke-RestMethod`
- another equivalent HTTP client available in the environment

The agent must not treat static code inspection alone as sufficient verification for web request handling when live local verification is possible.

### Required server restart after backend changes

If a task changes Django backend code, routes, settings, startup behavior, templates served by Django, or any API behavior, the agent must explicitly check whether a local dev server is already running.

If an older server process is running, the agent must:
- stop the old process,
- restart the server from the current workspace state,
- verify that the restarted process is the one actually serving requests.

Refreshing the browser tab alone is not sufficient after backend changes when the active server may still be running old code, especially if it was started with `--noreload`.

Before finishing the task, the agent must ensure that:
- the old server process is no longer active,
- the current server process is serving the new code,
- live HTTP verification is performed against that restarted server.

In your final task report, clearly distinguish:
- what you changed,
- what you verified,
- what you could not verify.

---

## UI / UX Guidance

The project should look polished enough for a university demo.

Guidelines:
- keep the interface clean and modern,
- favor clarity over visual complexity,
- make the main AI features easy to find,
- ensure search and person-grouping are presented clearly,
- do not spend excessive effort on edge-case UI polish if core AI functionality is still weak.

The most important visible screens are likely:
- login/register,
- library/gallery,
- upload flow,
- search UI/results,
- people/person grouping page.

---

## Scope Discipline

Because this is a lab project, avoid unnecessary scope growth.

Do not prioritize:
- advanced enterprise auth,
- distributed infrastructure,
- large-scale observability,
- complex permissions systems,
- excessive optimization for huge datasets,
- full production hardening.

Do prioritize:
- working upload flow,
- working indexing flow,
- convincing search,
- working people grouping,
- a nice demo interface,
- understandable architecture.

---

## Decision-Making Rules

When the repository does not force a single solution:

- choose the most practical option,
- keep it local-first,
- prefer simpler architecture,
- optimize for visible functionality,
- avoid choices that create needless setup pain.

If a major tradeoff exists, briefly state it and choose a sensible default instead of blocking progress.

Do not ask unnecessary questions when a reasonable assumption can be made safely.

---

## Reporting Style

At the end of each task, provide a concise engineering report including:

- what was implemented,
- which files were changed,
- how it was verified,
- the commit hash/message,
- whether push to `Egor-Dev` succeeded.

Keep reports concise, factual, and honest.

---

## Honesty Rule

Never pretend to have:
- run a command that was not run,
- verified behavior that was not verified,
- pushed commits that were not pushed,
- understood context that was not actually inspected.

Be precise and truthful.
