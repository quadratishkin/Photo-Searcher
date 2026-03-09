from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter


@dataclass
class BenchmarkResult:
    device: str
    image_path: Path
    load_seconds: float
    preprocess_seconds: float
    encode_seconds: float
    total_seconds: float
    embedding_shape: tuple[int, ...]
    embedding_device: str


def _sync_if_needed(device: str) -> None:
    if device != "cuda":
        return

    import torch

    torch.cuda.synchronize()


def benchmark_single_image(image_path: Path, device: str) -> BenchmarkResult:
    import open_clip
    import torch
    from PIL import Image

    load_started_at = perf_counter()
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained="laion2b_s34b_b79k",
        device=device,
    )
    model.eval()
    _sync_if_needed(device)
    load_seconds = perf_counter() - load_started_at

    preprocess_started_at = perf_counter()
    image_tensor = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(device)
    _sync_if_needed(device)
    preprocess_seconds = perf_counter() - preprocess_started_at

    encode_started_at = perf_counter()
    with torch.no_grad():
        embedding = model.encode_image(image_tensor)
    _sync_if_needed(device)
    encode_seconds = perf_counter() - encode_started_at

    total_seconds = load_seconds + preprocess_seconds + encode_seconds

    return BenchmarkResult(
        device=device,
        image_path=image_path,
        load_seconds=load_seconds,
        preprocess_seconds=preprocess_seconds,
        encode_seconds=encode_seconds,
        total_seconds=total_seconds,
        embedding_shape=tuple(embedding.shape),
        embedding_device=str(embedding.device),
    )


def format_result(result: BenchmarkResult) -> str:
    return "\n".join(
        [
            f"Device: {result.device}",
            f"Image: {result.image_path.name}",
            f"Model load: {result.load_seconds:.4f}s",
            f"Preprocess: {result.preprocess_seconds:.4f}s",
            f"Encode image: {result.encode_seconds:.4f}s",
            f"Total: {result.total_seconds:.4f}s",
            f"Embedding shape: {result.embedding_shape}",
            f"Embedding device: {result.embedding_device}",
        ]
    )


def main() -> None:
    image_path = Path(__file__).resolve().parents[2] / "data" / "media" / "media-01.jpg"

    for device in ("cuda", "cpu"):
        try:
            result = benchmark_single_image(image_path, device)
        except Exception as exc:
            print(f"{device}: benchmark failed: {exc}")
            continue

        print(format_result(result))
        print()


if __name__ == "__main__":
    main()
