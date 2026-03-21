# NovaAI-Shipping

Production-oriented AI module for Liquid Photos.

This package is responsible for:

- loading the OpenCLIP image encoder,
- building normalized image embeddings for uploaded photos,
- exposing runtime metadata for the Django backend.

The Django app imports this module lazily through `photo_ai.runtime`, so model
weights are loaded only when the AI module is enabled in `CoreAI.config`.

The actual AI runtime logic now lives inside `nova_ai_shipping` itself.
The legacy `photo_ai` package is kept only as a thin compatibility shim for
older Django imports.
