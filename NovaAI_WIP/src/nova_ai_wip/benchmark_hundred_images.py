from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from time import perf_counter


MODEL_NAME = "ViT-B-32"
PRETRAINED_TAG = "laion2b_s34b_b79k"
RUN_COUNT = 100


@dataclass
class BatchBenchmarkResult:
    device: str
    unique_image_count: int
    processed_image_count: int
    load_seconds: float
    warmup_seconds: float
    preprocess_seconds: float
    encode_seconds: float
    total_seconds: float
    average_preprocess_seconds: float
    average_encode_seconds: float
    average_total_seconds: float


def _sync_if_needed(device: str) -> None:
    if device != "cuda":
        return

    import torch

    torch.cuda.synchronize()


def _iter_image_paths(limit: int) -> list[Path]:
    data_dir = Path(__file__).resolve().parents[2] / "data"
    all_paths = sorted(data_dir.rglob("*.jpg"))
    if not all_paths:
        raise FileNotFoundError(f"No .jpg files found under {data_dir}")

    repeated: list[Path] = []
    while len(repeated) < limit:
        remaining = limit - len(repeated)
        repeated.extend(islice(all_paths, remaining))

    return repeated


def benchmark_hundred_images(device: str) -> BatchBenchmarkResult:
    import open_clip
    import torch
    from PIL import Image

    image_paths = _iter_image_paths(RUN_COUNT)
    unique_image_count = len(set(image_paths))

    load_started_at = perf_counter()
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED_TAG,
        device=device,
    )
    model.eval()
    _sync_if_needed(device)
    load_seconds = perf_counter() - load_started_at

    warmup_started_at = perf_counter()
    warmup_tensor = preprocess(Image.open(image_paths[0]).convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        model.encode_image(warmup_tensor)
    _sync_if_needed(device)
    warmup_seconds = perf_counter() - warmup_started_at

    preprocess_seconds = 0.0
    encode_seconds = 0.0

    for image_path in image_paths:
        preprocess_started_at = perf_counter()
        image_tensor = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(device)
        _sync_if_needed(device)
        preprocess_seconds += perf_counter() - preprocess_started_at

        encode_started_at = perf_counter()
        with torch.no_grad():
            model.encode_image(image_tensor)
        _sync_if_needed(device)
        encode_seconds += perf_counter() - encode_started_at

    total_seconds = load_seconds + warmup_seconds + preprocess_seconds + encode_seconds

    return BatchBenchmarkResult(
        device=device,
        unique_image_count=unique_image_count,
        processed_image_count=len(image_paths),
        load_seconds=load_seconds,
        warmup_seconds=warmup_seconds,
        preprocess_seconds=preprocess_seconds,
        encode_seconds=encode_seconds,
        total_seconds=total_seconds,
        average_preprocess_seconds=preprocess_seconds / len(image_paths),
        average_encode_seconds=encode_seconds / len(image_paths),
        average_total_seconds=(preprocess_seconds + encode_seconds) / len(image_paths),
    )


def format_result(result: BatchBenchmarkResult) -> str:
    return "\n".join(
        [
            f"Device: {result.device}",
            f"Unique images used: {result.unique_image_count}",
            f"Processed images: {result.processed_image_count}",
            f"Model load: {result.load_seconds:.4f}s",
            f"Warm-up: {result.warmup_seconds:.4f}s",
            f"Preprocess total: {result.preprocess_seconds:.4f}s",
            f"Encode total: {result.encode_seconds:.4f}s",
            f"Total wall time: {result.total_seconds:.4f}s",
            f"Average preprocess per image: {result.average_preprocess_seconds:.6f}s",
            f"Average encode per image: {result.average_encode_seconds:.6f}s",
            f"Average total per image (warm model): {result.average_total_seconds:.6f}s",
        ]
    )


def main() -> None:
    for device in ("cuda", "cpu"):
        try:
            result = benchmark_hundred_images(device)
        except Exception as exc:
            print(f"{device}: benchmark failed: {exc}")
            continue

        print(format_result(result))
        print()


if __name__ == "__main__":
    main()
