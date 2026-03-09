from __future__ import annotations

from pathlib import Path


MODEL_NAME = "ViT-B-32"
PRETRAINED_TAG = "laion2b_s34b_b79k"
SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def _detect_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _iter_image_paths(data_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in data_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    )


def export_embeddings_txt() -> None:
    import open_clip
    import torch
    from PIL import Image

    project_dir = Path(__file__).resolve().parents[2]
    data_dir = project_dir / "data"
    output_dir = project_dir / "artifacts" / "embeddings_txt"
    image_paths = _iter_image_paths(data_dir)

    if not image_paths:
        raise FileNotFoundError(f"No supported image files found under {data_dir}")

    device = _detect_device()
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED_TAG,
        device=device,
    )
    model.eval()

    print(f"Device: {device}")
    print(f"Images to export: {len(image_paths)}")
    print(f"Output directory: {output_dir}")

    exported = 0
    for image_path in image_paths:
        relative_path = image_path.relative_to(data_dir)
        txt_path = (output_dir / relative_path).with_suffix(".txt")
        txt_path.parent.mkdir(parents=True, exist_ok=True)

        image_tensor = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            embedding = model.encode_image(image_tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        vector = embedding.squeeze(0).detach().cpu().tolist()
        txt_path.write_text("\n".join(f"{value:.8f}" for value in vector), encoding="utf-8")
        exported += 1

    print(f"Exported TXT vectors: {exported}")


def main() -> None:
    export_embeddings_txt()


if __name__ == "__main__":
    main()
