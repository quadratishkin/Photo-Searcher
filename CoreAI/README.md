# CoreAI

Production-oriented AI module for Liquid Photos.

This package is responsible for:

- loading the OpenCLIP image encoder,
- building normalized image embeddings for uploaded photos,
- exposing runtime metadata for the Django backend.

The Django app imports `nova_ai_shipping` directly after adding the
`CoreAI` directory to `sys.path` during `liquid_photos` startup.
Model weights are loaded only when the AI module is enabled in
`CoreAI.config`.
