from __future__ import annotations


def _detect_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def run_open_clip_smoke_test() -> None:
    try:
        import open_clip
        import torch
    except Exception as exc:  # pragma: no cover - import failure path
        print(f"OpenCLIP import failed: {exc}")
        return

    device = _detect_device()

    try:
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k",
            device=device,
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        tokens = tokenizer(["cat", "dog"])
        tokens = tokens.to(device)
        with torch.no_grad():
            text_features = model.encode_text(tokens)
    except Exception as exc:  # pragma: no cover - runtime failure path
        print(f"OpenCLIP model init failed: {exc}")
        return

    print("OpenCLIP import: OK")
    print(f"Device: {device}")
    if device == "cuda":
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")
    print(f"Model type: {type(model).__name__}")
    print(f"Tokenizer type: {type(tokenizer).__name__}")
    print(f"Preprocess pipeline: {type(preprocess).__name__}")
    print(f"Text feature shape: {tuple(text_features.shape)}")
    print(f"Text feature device: {text_features.device}")
