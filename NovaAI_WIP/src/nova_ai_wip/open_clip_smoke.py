from __future__ import annotations


def run_open_clip_smoke_test() -> None:
    try:
        import open_clip
    except Exception as exc:  # pragma: no cover - import failure path
        print(f"OpenCLIP import failed: {exc}")
        return

    try:
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k",
            device="cpu",
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
    except Exception as exc:  # pragma: no cover - runtime failure path
        print(f"OpenCLIP model init failed: {exc}")
        return

    print("OpenCLIP import: OK")
    print(f"Model type: {type(model).__name__}")
    print(f"Tokenizer type: {type(tokenizer).__name__}")
    print(f"Preprocess pipeline: {type(preprocess).__name__}")
