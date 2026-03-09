# Liquid Photos

Liquid Photos is a smart photo library concept for a university lab project focused on neural networks, intelligent media retrieval, and demo-ready interface design.

The goal of the project is to build a web application where a user can:

- upload and browse a personal photo library,
- search photos using natural language,
- discover and group people found across images,
- interact with the system through a clean, modern interface inspired by Liquid Glass design.

## Current Status

The repository currently contains a **frontend prototype** used to design and validate the user interface before backend integration.

Implemented so far:

- fullscreen media gallery,
- bottom tab navigation for `Медиа`, `Поиск`, and `Люди`,
- interactive search input,
- people grid with circular portrait cards,
- top action buttons for search and photo selection,
- local demo assets for reliable preview across devices in the same network.

Backend logic for authentication, uploads, indexing, semantic search, and people clustering is planned but not yet implemented in this repository.

## Features

### Media Library

- square photo grid layout,
- mobile-app style fullscreen presentation,
- upload entry point from the main interface.

### Smart Search

- natural-language photo search concept,
- editable search composer,
- layout prepared for future AI-powered search results.

### People

- grouped people view,
- circular person cards,
- space for named and unnamed person clusters.

## Tech Stack

Current frontend stack:

- **React 19**
- **TypeScript**
- **Vite**
- **CSS**

Planned broader project direction:

- **Python**
- **Django**
- local image storage
- AI-based search and person grouping pipeline

## Project Goals

The main priorities of Liquid Photos are:

1. intelligent photo search quality,
2. visible demo-ready functionality,
3. understandable architecture,
4. clean and convincing UI.

This is a lab/demo project, not a production-scale platform.

## Getting Started

### Install dependencies

```bash
pnpm install
```

### Run the development server

```bash
pnpm dev
```

### Run with LAN access

```bash
pnpm dev --host 0.0.0.0
```

### Build for production

```bash
pnpm build
```

## Project Structure

```text
.
├── public/demo/         # local demo images for media and people
├── src/
│   ├── App.tsx          # main UI prototype
│   ├── main.tsx         # React entry point
│   └── styles.css       # global styling
├── AGENTS.md            # repository-specific agent context
├── package.json
└── vite.config.ts
```

## Design Direction

The interface is being explored in a style inspired by:

- Apple-like Liquid Glass surfaces,
- mobile gallery interactions,
- minimal AI-search interfaces.

The current prototype focuses on visual direction and interaction flow first, then backend integration second.

## Roadmap

- add login and registration screens,
- connect photo upload to backend,
- implement semantic search API,
- implement person detection and grouping flow,
- integrate real search and people results into the frontend.

## License

This project is currently developed as an academic/lab work in progress.
