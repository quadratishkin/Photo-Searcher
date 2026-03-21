# NovaAI-Shipping

Production-oriented AI module for Liquid Photos.

This package is responsible for:

- loading the OpenCLIP image encoder,
- building normalized image embeddings for uploaded photos,
- exposing runtime metadata for the Django backend.

The Django app imports this module lazily through `photo_ai.runtime`, so model
weights are loaded only when the AI module is enabled in `CoreAI.config`.
