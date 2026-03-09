from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


MODEL_NAME = "ViT-B-32"
PRETRAINED_TAG = "laion2b_s34b_b79k"
TOP_K = 3


@dataclass
class SearchHit:
    image_path: Path
    score: float


def _detect_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _configure_console_encoding() -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        reconfigure(encoding="utf-8")


def _paths() -> tuple[Path, Path]:
    project_dir = Path(__file__).resolve().parents[2]
    data_dir = project_dir / "data"
    embedding_dir = project_dir / "artifacts" / "embeddings_txt"
    return data_dir, embedding_dir


def _load_embedding(txt_path: Path) -> list[float]:
    return [float(line.strip()) for line in txt_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_index() -> tuple[list[Path], list[list[float]]]:
    data_dir, embedding_dir = _paths()
    txt_paths = sorted(embedding_dir.rglob("*.txt"))
    if not txt_paths:
        raise FileNotFoundError(
            f"No TXT embeddings found under {embedding_dir}. Run `python -m nova_ai_wip.export_embeddings_txt` first."
        )

    image_paths: list[Path] = []
    vectors: list[list[float]] = []

    for txt_path in txt_paths:
        relative_path = txt_path.relative_to(embedding_dir).with_suffix(".jpg")
        image_path = data_dir / relative_path
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found for embedding: {image_path}")

        image_paths.append(image_path)
        vectors.append(_load_embedding(txt_path))

    return image_paths, vectors


def search(query: str, top_k: int = TOP_K) -> tuple[str, list[SearchHit]]:
    import open_clip
    import torch

    image_paths, vectors = _load_index()
    device = _detect_device()

    image_matrix = torch.tensor(vectors, dtype=torch.float32, device=device)
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    model, _, _ = open_clip.create_model_and_transforms(
        MODEL_NAME,
        pretrained=PRETRAINED_TAG,
        device=device,
    )
    model.eval()

    tokens = tokenizer([query]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    scores = image_matrix @ text_features.squeeze(0)
    top_scores, top_indices = torch.topk(scores, k=min(top_k, len(image_paths)))

    hits = [
        SearchHit(image_path=image_paths[index], score=float(score))
        for score, index in zip(top_scores.detach().cpu().tolist(), top_indices.detach().cpu().tolist(), strict=True)
    ]
    return device, hits


def _print_hits(query: str, device: str, hits: list[SearchHit]) -> None:
    print(f"Запрос: {query}")
    print(f"Устройство: {device}")
    print("Топ-3 результатов:")
    for rank, hit in enumerate(hits, start=1):
        print(f"{rank}. {hit.image_path.name} | score={hit.score:.6f} | {hit.image_path}")


def _interactive_loop() -> None:
    print("Семантический поиск по изображениям.")
    print("Введите текстовый запрос. Для выхода введите `exit`.")

    while True:
        query = input("Поиск> ").strip()
        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            break

        device, hits = search(query)
        _print_hits(query, device, hits)
        print()


def main() -> None:
    _configure_console_encoding()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
        device, hits = search(query)
        _print_hits(query, device, hits)
        return

    _interactive_loop()


if __name__ == "__main__":
    main()
